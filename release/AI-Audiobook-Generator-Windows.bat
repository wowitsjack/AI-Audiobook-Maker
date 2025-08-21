@echo off
REM AI Audiobook Generator - Windows Launcher
REM This script sets up the environment and runs the audiobook generator

title AI Audiobook Generator - Windows

echo.
echo    🎧 AI Audiobook Generator - Windows Launcher
echo    ===============================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ Python is required but not installed.
    echo    Please install Python 3.8+ from https://python.org
    echo    Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Check if we're in the project directory
if not exist "%PROJECT_DIR%\audiobook_gui.py" (
    echo    ❌ Could not find audiobook_gui.py
    echo    Please ensure this launcher is in the project directory
    echo.
    pause
    exit /b 1
)

echo    📂 Project directory: %PROJECT_DIR%
cd /d "%PROJECT_DIR%"

REM Check if virtual environment exists
if not exist "venv" (
    echo    🔧 Setting up virtual environment...
    python -m venv venv
    
    if errorlevel 1 (
        echo    ❌ Failed to create virtual environment
        echo.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo    🚀 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo    📦 Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if errorlevel 1 (
    echo    ❌ Failed to install dependencies
    echo    Please check your internet connection and try again
    echo.
    pause
    exit /b 1
)

REM Check for .env file
if not exist ".env" (
    echo    ⚠️  No .env file found!
    echo    Please create a .env file with your Google API key:
    echo    GOOGLE_API_KEY=your_api_key_here
    echo    NARRATOR_VOICE=Kore
    echo.
    echo    Press any key to continue anyway...
    pause >nul
)

REM Launch the application
echo    🎧 Starting AI Audiobook Generator...
echo.
python audiobook_gui.py

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat

echo.
echo    ✅ Application closed. Press any key to exit...
pause >nul