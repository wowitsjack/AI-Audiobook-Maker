#!/bin/bash

# Audiobook Generator Launcher for macOS
# Navigate to the script directory and launch the application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Please install Python 3 and try again."
    echo "You can install Python from https://www.python.org/downloads/"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if resources directory exists
if [ ! -d "resources" ]; then
    echo "Error: Resources directory not found."
    echo "Please ensure the application files are properly installed."
    read -p "Press Enter to exit..."
    exit 1
fi

# Launch the audiobook generator
echo "Starting Audiobook Generator..."
cd resources
python3 audiobook_gui.py

# Keep terminal open on error
if [ $? -ne 0 ]; then
    echo "An error occurred."
    read -p "Press Enter to exit..."
fi