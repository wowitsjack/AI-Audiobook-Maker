@echo off
:: Audiobook Generator Launcher for Windows
:: Navigate to the script directory and launch the application

cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required but not installed.
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Check if resources directory exists
if not exist "resources\" (
    echo Error: Resources directory not found.
    echo Please ensure the application files are properly installed.
    pause
    exit /b 1
)

:: Launch the audiobook generator
echo Starting Audiobook Generator...
cd resources
python audiobook_gui.py

:: Keep window open on error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause >nul
)