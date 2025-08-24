@echo off
REM AI Audiobook Generator - Windows GUI Launcher
REM Double-click this file to start the GUI application

echo.
echo ======================================
echo AI Audiobook Generator
echo Starting GUI Application...
echo ======================================
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

REM Try to run with python3 first, then python
python3 src/audiobook_gui_launcher.py
if %errorlevel% neq 0 (
    echo Python3 not found, trying python...
    python src/audiobook_gui_launcher.py
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Python not found or GUI failed to start
        echo.
        echo Please ensure Python is installed and try running:
        echo   pip install -r src/requirements.txt
        echo.
        pause
        exit /b 1
    )
)

echo.
echo GUI application has closed.
pause