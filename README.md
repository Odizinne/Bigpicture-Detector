# Bigpicture-Detector

Python daemon to automate switching from PC to TV when launching Steam in big picture mode.  
Supports X11, gnome-wayland and plasma-wayland.

It will switch display using provided adapters with launch arguments.
Also it will switch audio devices on the one you provided with launch arguments.

This script will reset your system to desktop mode at exit.

## Primary use case

This script is meant to be ran when using single monitor and TV plugged in.  
Using a dual screen plus a TV might lead to random result.  
I made this script for my own use, and I'll not address issue about other configuration than this one.

## Dependencies

- `wmctrl` for window detection
- `pactl` for audio device manipulation
- `xrandr` for screen detection and manipulation under X11
- `gnome-randr` (work only with [my custom version](https://github.com/Odizinne/gnome-randr-py)) in path for gnome-wayland support

## Usage

For first run you should do `./bigpicture-detector --settings`

Both audio settings should be filled with device description. You can get it from `pactl list sinks | grep device.description`

Output should look like this:

```bash
flora@fedora:~/Projects$ pactl list sinks | grep device.description
        device.description = "CORSAIR VOID ELITE Wireless Gaming Dongle"
```

If you plan to switch to HDMI audio, be sure to turn your HDMI monitor before running this command, else it wont be listed here.

I do not recommand going below 100ms for check rate. If unsure, do not edit.

when everything is done, close the app, and launch without arguments. I recommend to setup a systemd service (set and forget).

## To do

Will probably do one day but low priority

- Add feature to disable audio switching.
- PyQt gui to create / manage settings and avoid using launch arguments.