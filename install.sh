#!/bin/bash

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Python is not installed. Please install Python before proceeding."
    exit 1
fi

echo "Copying bigpicture-detector and gnome-randr to /usr/local/bin."

sudo cp bigpicture-detector /usr/local/bin
sudo cp gnome-randr /usr/local/bin

echo "All good."
