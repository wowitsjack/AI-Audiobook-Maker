#!/bin/bash

# AI Audiobook Generator - macOS Launcher
# This script sets up the environment and runs the audiobook generator

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🎧 AI Audiobook Generator - macOS Launcher"
echo "==========================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3 from https://python.org"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check if we're in the project directory
if [ ! -f "$PROJECT_DIR/audiobook_gui.py" ]; then
    echo "❌ Could not find audiobook_gui.py"
    echo "Please ensure this launcher is in the project directory"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

echo "📂 Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🔧 Setting up virtual environment..."
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Press any key to exit..."
        read -n 1
        exit 1
    fi
fi

# Activate virtual environment
echo "🚀 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "Please create a .env file with your Google API key:"
    echo "GOOGLE_API_KEY=your_api_key_here"
    echo "NARRATOR_VOICE=Kore"
    echo ""
    echo "Press any key to continue anyway..."
    read -n 1
fi

# Launch the application
echo "🎧 Starting AI Audiobook Generator..."
echo ""
python audiobook_gui.py

# Deactivate virtual environment
deactivate

echo ""
echo "✅ Application closed. Press any key to exit..."
read -n 1