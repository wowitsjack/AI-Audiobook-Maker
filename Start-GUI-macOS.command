#!/bin/bash
# AI Audiobook Generator - macOS GUI Launcher
# Double-click this file to start the GUI application

echo ""
echo "======================================"
echo "AI Audiobook Generator"
echo "Starting GUI Application..."
echo "======================================"
echo ""

# Change to the directory containing this script
cd "$(dirname "$0")"

# Try to run with python3 first, then python
if command -v python3 &> /dev/null; then
    python3 src/audiobook_gui_launcher.py
    exit_code=$?
elif command -v python &> /dev/null; then
    echo "Python3 not found, trying python..."
    python src/audiobook_gui_launcher.py
    exit_code=$?
else
    echo ""
    echo "ERROR: Python not found"
    echo ""
    echo "Please install Python and try running:"
    echo "  pip3 install -r src/requirements.txt"
    echo ""
    read -p "Press Enter to continue..."
    exit 1
fi

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "ERROR: GUI failed to start"
    echo ""
    echo "Please ensure dependencies are installed:"
    echo "  pip3 install -r src/requirements.txt"
    echo ""
    read -p "Press Enter to continue..."
    exit 1
fi

echo ""
echo "GUI application has closed."
read -p "Press Enter to continue..."