import subprocess
import time
import re
import atexit
import os
import sys
import json
import logging
import shutil
import threading
from PyQt6.QtWidgets import QMainWindow, QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject
from design import Ui_MainWindow

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".config/BigPictureTV/settings.json")
ICON_DESKTOP = "icons/icon_desktop.png"
ICON_GAMEMODE = "icons/icon_gamemode.png"


class Communicator(QObject):
    detection_status_changed = pyqtSignal(bool)

class Mode:
    def __init__(self, screen_command, audio, mode_name, screen_name, disable_audio=False):
        self.screen_command = screen_command
        self.audio = audio
        self.mode_name = mode_name
        self.screen_name = screen_name
        self.current_mode = False
        self.disable_audio = disable_audio

    def activate(self):
        logger.info("Activating mode: %s", self.mode_name)
        self.switch_screen()
        if not self.disable_audio:
            self.switch_audio()
        self.current_mode = True

    def deactivate(self):
        self.current_mode = False

    def is_active(self):
        return self.current_mode

    def switch_screen(self):
        logger.info("Switching screen to: %s with command: %s", self.screen_name, self.screen_command)
        subprocess.run(self.screen_command, stdout=subprocess.DEVNULL)

    def switch_audio(self):
        while True:
            result = subprocess.run(['pactl', 'list', 'sinks'], stdout=subprocess.PIPE)
            sinks = result.stdout.decode('utf-8')
            for sink in sinks.split('\n\n'):
                if self.audio in sink:
                    match = re.search(r'Name: (.*)', sink)
                    if match:
                        node_name = match.group(1)
                        logger.info(f"Switching audio to: {node_name}")
                        subprocess.run(['pactl', 'set-default-sink', node_name])
                        return

class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("BigPictureTV - Settings")
        self.setFixedSize(self.size())
        self.settings = self.load_settings()
        self.apply_settings()
        self.init_ui_connections()
        self.tray_icon = self.create_tray_icon()

        self.gamemode = None
        self.desktopmode = None
        self.detection_active = True
        self.communicator = Communicator()
        self.communicator.detection_status_changed.connect(self.update_detection_status)

        self.main_loop_thread = threading.Thread(target=self.start_main_loop, daemon=True)
        self.main_loop_thread.start()

    def update_detection_status(self, status):
        self.detection_active = status
        self.update_tray_menu()

    def create_tray_icon(self):
        tray_icon = QSystemTrayIcon(self)
        tray_icon.setIcon(QIcon(ICON_DESKTOP))
        tray_icon.setContextMenu(self.create_menu())
        tray_icon.show()
        return tray_icon

    def create_menu(self):
        menu = QMenu()

        self.current_mode_action = QAction('Current Mode: Unknown', menu)
        self.current_mode_action.setEnabled(False)
        menu.addAction(self.current_mode_action)

        self.detection_status = QAction('Detection State: Active', menu)
        self.detection_status.setEnabled(False)
        menu.addAction(self.detection_status)

        menu.addSeparator()

        self.pause_resume_action = QAction('Pause Detection', menu)
        self.pause_resume_action.triggered.connect(self.toggle_detection)
        menu.addAction(self.pause_resume_action)

        settings_action = QAction('Settings', menu)
        settings_action.triggered.connect(self.show)
        menu.addAction(settings_action)

        exit_action = QAction('Exit', menu)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        return menu

    def update_tray_menu(self):
        if self.detection_active:
            self.pause_resume_action.setText('Pause Detection')
        else:
            self.pause_resume_action.setText('Resume Detection')

        if self.gamemode and self.gamemode.is_active():
            self.current_mode_action.setText('Current Mode: Game Mode')
            self.tray_icon.setIcon(QIcon(ICON_GAMEMODE))
        elif self.desktopmode and self.desktopmode.is_active():
            self.current_mode_action.setText('Current Mode: Desktop Mode')
            self.tray_icon.setIcon(QIcon(ICON_DESKTOP))
        else:
            self.current_mode_action.setText('Current Mode: Unknown')

        if self.detection_active:
            self.detection_status.setText('Detection State: Active')
        else:
            self.detection_status.setText('Detection State: Paused')

    def toggle_detection(self):
        self.communicator.detection_status_changed.emit(not self.detection_active)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def init_ui_connections(self):
        self.ui.checkRate.valueChanged.connect(self.save_settings)
        self.ui.gamemodeAudio.textChanged.connect(self.save_settings)
        self.ui.desktopAudio.textChanged.connect(self.save_settings)
        self.ui.gamemodeAdapter.textChanged.connect(self.save_settings)
        self.ui.desktopAdapter.textChanged.connect(self.save_settings)
        self.ui.disableAudiobox.stateChanged.connect(self.on_disableAudioBox_stateChanged)
        self.ui.bigPictureKeywords.textChanged.connect(self.save_settings)

    def toggle_audio_settings(self, state):
        self.ui.gamemodeAudio.setEnabled(not state)
        self.ui.desktopAudio.setEnabled(not state)
        self.ui.desktopAudioLabel.setEnabled(not state)
        self.ui.gamemodeAudioLabel.setEnabled(not state)

    def on_disableAudioBox_stateChanged(self):
        self.toggle_audio_settings(self.ui.disableAudiobox.isChecked())
        self.save_settings()

    def check_window_names(self):
        result = subprocess.run(['wmctrl', '-l'], stdout=subprocess.PIPE)
        windows = result.stdout.decode('utf-8')

        keywords = self.ui.bigPictureKeywords.text().split()

        for line in windows.splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4:
                title = parts[3].lower()
                if all(keyword in title for keyword in keywords):
                    return True

        return False

    def get_session_type(self):
        session_type = os.getenv("XDG_SESSION_TYPE").lower()
        if session_type == "x11":
            return "x11"
        elif session_type == "wayland":
            desktop_session = os.getenv("XDG_CURRENT_DESKTOP").lower()
            if desktop_session == "gnome":
                return "gnome-wayland"
            elif desktop_session == "kde":
                return "kde-wayland"
        else:
            return "Unsupported"

    def get_randr_command(self):
        session_type = self.get_session_type()

        if session_type == "x11":
            logger.info("Session type: X11. Using xrandr.")
            return "xrandr"
        elif session_type == "gnome-wayland":
            logger.info("Session type: GNOME Wayland. Using gnome-randr.")
            return "gnome-randr"
        elif session_type == "kde-wayland":
            logger.info("Session type: KDE Wayland. Using kscreen-doctor.")
            return "kscreen-doctor"
        else:
            logger.error(f"Unsupported session type: {session_type}")
            sys.exit(1)

    def validate_commands(self, commands):
        for command in commands:
            if shutil.which(command) is None:
                logger.error(f"The required command '{command}' is not installed.")
                sys.exit(1)

    def generate_screen_command(self, randr_command, output_screen, off_screen, session_type):
        if session_type == "x11" or session_type == "gnome-wayland":
            return [randr_command, '--output', output_screen, '--auto', '--output', off_screen, '--off']
        elif session_type == "kde-wayland":
            return [randr_command, f'output.{output_screen}.enable', f'output.{off_screen}.disable']

    def load_settings(self):
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, 'r') as f:
                return json.load(f)
        else:
            return self.create_default_settings()

    def apply_settings(self):
        self.ui.bigPictureKeywords.setText(' '.join(self.settings.get('bigPictureKeywords', [])))
        self.ui.checkRate.setValue(self.settings["checkRate"])
        self.ui.gamemodeAudio.setText(self.settings["gamemodeAudio"])
        self.ui.desktopAudio.setText(self.settings["desktopAudio"])
        self.ui.gamemodeAdapter.setText(self.settings["gamemodeAdapter"])
        self.ui.desktopAdapter.setText(self.settings["desktopAdapter"])
        self.ui.disableAudiobox.setChecked(self.settings["disableAudio"])
        self.toggle_audio_settings(self.ui.disableAudiobox.isChecked())

    def save_settings(self):
        settings = {
            "bigPictureKeywords": self.ui.bigPictureKeywords.text().split(),
            "checkRate": self.ui.checkRate.value(),
            "gamemodeAudio": self.ui.gamemodeAudio.text(),
            "desktopAudio": self.ui.desktopAudio.text(),
            "gamemodeAdapter": self.ui.gamemodeAdapter.text(),
            "desktopAdapter": self.ui.desktopAdapter.text(),
            "disableAudio": self.ui.disableAudiobox.isChecked()
        }
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=4)
            logger.info("Settings saved to %s", SETTINGS_PATH)

    def create_default_settings(self):
        self.show()
        settings = {
            "bigPictureKeywords": ["Steam", "Big", "Picture", "mode"],
            "checkRate": 1000,
            "gamemodeAudio": "",
            "desktopAudio": "",
            "gamemodeAdapter": "",
            "desktopAdapter": "",
            "disableAudio": False
        }
        self.save_settings()
        
        return settings

    def start_main_loop(self):
        self.monitor_window_changes()

    def monitor_window_changes(self):
        while True:
            if self.detection_active:
                if self.check_window_names():
                    if not (self.gamemode and self.gamemode.is_active()):
                        self.create_and_activate_modes()
                else:
                    if not (self.desktopmode and self.desktopmode.is_active()):
                        self.create_and_activate_modes()
                self.update_tray_menu()
            time.sleep(self.settings["checkRate"] / 1000)

    def create_and_activate_modes(self):
        session_type = self.get_session_type()
        randr_command = self.get_randr_command()
        self.validate_commands(['pactl', 'wmctrl', randr_command])

        external_screen = self.ui.gamemodeAdapter.text()
        internal_screen = self.ui.desktopAdapter.text()
        gamemode_audio = self.ui.gamemodeAudio.text()
        desktop_audio = self.ui.desktopAudio.text()
        disable_audio = self.ui.disableAudiobox.isChecked()
        checkRate = self.ui.checkRate.value()
        bigpicture_keywords = self.ui.bigPictureKeywords.text().split()

        logger.info(f"PARAM: Detecting: {bigpicture_keywords}")
        logger.info(f"PARAM: audio switching: {not disable_audio}")
        logger.info(f"PARAM: window check rate (ms): {checkRate}")
        logger.info(f"PARAM: gamemode screen: {external_screen}")
        logger.info(f"PARAM: desktop screen: {internal_screen}")
        logger.info(f"PARAM: gamemode audio output: {gamemode_audio}")
        logger.info(f"PARAM: desktop audio output: {desktop_audio}")

        self.gamemode = Mode(
            self.generate_screen_command(randr_command, external_screen, internal_screen, session_type),
            gamemode_audio,
            "Game Mode",
            external_screen,
            disable_audio
        )
        self.desktopmode = Mode(
            self.generate_screen_command(randr_command, internal_screen, external_screen, session_type),
            desktop_audio,
            "Desktop Mode",
            internal_screen,
            disable_audio
        )

        if self.check_window_names():
            self.gamemode.activate()
            self.desktopmode.deactivate()
        else:
            self.desktopmode.activate()
            self.gamemode.deactivate()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    BigPictureTV = SettingsWindow()
    sys.exit(app.exec())