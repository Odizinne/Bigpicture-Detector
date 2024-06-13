#!/bin/bash

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Python is not installed. Please install Python before proceeding."
    exit 1
fi

echo "Python is installed."

echo "Copying bigpicture-detector to /usr/local/bin."
sudo cp bigpicture-detector /usr/local/bin

if [[ $? -ne 0 ]]; then
    echo "Failed to copy bigpicture-detector. Check your permissions or the file path."
    exit 1
fi

echo "bigpicture-detector copied successfully."

# Check if the session is Wayland with GNOME
if [[ "$XDG_SESSION_TYPE" == "wayland" ]] && [[ "$XDG_CURRENT_DESKTOP" =~ "GNOME" ]]; then
    echo "Detected Wayland session with GNOME."
    read -p "Do you want to download and install custom version of gnome-randr? (required for gnome-wayland support) (Y/n): " install_gnome_randr

    install_gnome_randr=$(echo "${install_gnome_randr:-y}" | tr '[:upper:]' '[:lower:]')

    if [[ "$install_gnome_randr" == "y" || "$install_gnome_randr" == "yes" ]]; then
        GNOME_RANDR_URL="https://raw.githubusercontent.com/Odizinne/gnome-randr-py/main/gnome-randr"
        GNOME_RANDR_LOCAL="/usr/local/bin/gnome-randr"

        echo "Downloading gnome-randr..."
        sudo curl -o $GNOME_RANDR_LOCAL $GNOME_RANDR_URL

        if [[ $? -ne 0 ]]; then
            echo "Failed to download gnome-randr."
            exit 1
        fi

        sudo chmod +x $GNOME_RANDR_LOCAL

        echo "gnome-randr installed successfully to /usr/local/bin."
    fi
fi

echo "All tasks completed."
