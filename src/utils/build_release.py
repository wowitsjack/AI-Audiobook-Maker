#!/usr/bin/env python3
"""
Multi-platform builder and release script for AI Audiobook Generator
Creates standalone executables and release packages for Windows, macOS, and Linux
"""

import os
import sys
import subprocess
import shutil
import platform
import zipfile
from pathlib import Path
import tempfile

class AudiobookBuilder:
    def __init__(self):
        self.src_dir = Path(__file__).parent.parent
        self.root_dir = self.src_dir.parent
        self.version = "2.1.0"  # Updated version
        self.app_name = "ai-audiobook-generator"
        self.build_dir = self.root_dir / "build"
        self.dist_dir = self.root_dir / "dist"
        self.release_dir = self.root_dir / "releases"
        
        # Platform-specific settings
        self.platform_configs = {
            'windows': {
                'binary_name': f'{self.app_name}.exe',
                'launcher_ext': '.bat',
                'archive_ext': '.zip'
            },
            'darwin': {  # macOS
                'binary_name': self.app_name,
                'launcher_ext': '.command',
                'archive_ext': '.zip'
            },
            'linux': {
                'binary_name': self.app_name,
                'launcher_ext': '.sh',
                'archive_ext': '.zip'
            }
        }
    
    def clean_build_dirs(self):
        """Clean previous build artifacts"""
        print("Cleaning build directories...")
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
        
        # Clean PyInstaller spec files
        for spec_file in self.root_dir.glob("*.spec"):
            spec_file.unlink()
    
    def install_dependencies(self):
        """Install required dependencies"""
        print("Installing dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "pyinstaller", "wheel", "setuptools"
        ], check=True)
    
    def build_binary(self, target_platform=None):
        """Build PyInstaller binary"""
        if target_platform is None:
            target_platform = platform.system().lower()
        
        config = self.platform_configs.get(target_platform, self.platform_configs['linux'])
        binary_name = config['binary_name']
        
        print(f"Building binary for {target_platform}...")
        
        # PyInstaller command with proper module detection
        cmd = [
            "pyinstaller",
            "--onefile",
            "--name", binary_name.replace('.exe', ''),
            "--distpath", str(self.dist_dir),
            "--clean",
            "--noconfirm",
            # Add paths
            "--paths", str(self.src_dir),
            # Hidden imports for all our modules
            "--hidden-import", "gui",
            "--hidden-import", "gui.application",
            "--hidden-import", "gui.launch_gui",
            "--hidden-import", "core",
            "--hidden-import", "core.app_functions",
            "--hidden-import", "core.cli",
            "--hidden-import", "core.config",
            "--hidden-import", "core.engine",
            "--hidden-import", "music",
            "--hidden-import", "music.generator",
            "--hidden-import", "quality",
            "--hidden-import", "quality.detector",
            "--hidden-import", "state",
            "--hidden-import", "state.manager",
            "--hidden-import", "state.project_manager",
            "--hidden-import", "tts",
            "--hidden-import", "tts.generator",
            "--hidden-import", "utils",
            "--hidden-import", "utils.api_retry_handler",
            "--hidden-import", "utils.rate_limiter",
            "--hidden-import", "utils.text_processing",
            # Common dependencies
            "--hidden-import", "customtkinter",
            "--hidden-import", "tkinter",
            "--hidden-import", "tkinter.ttk",
            "--hidden-import", "tkinter.filedialog",
            "--hidden-import", "tkinter.messagebox",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL.Image",
            "--hidden-import", "PIL.ImageTk",
            "--hidden-import", "google.genai",
            "--hidden-import", "google.generativeai",
            "--hidden-import", "numpy",
            "--hidden-import", "soundfile",
            str(self.src_dir / "audiobook_gui_launcher.py")
        ]
        
        # Add platform-specific options
        if target_platform == 'windows':
            cmd.extend(["--windowed"])
            # Add icon if available
            if (self.root_dir / "book.png").exists():
                cmd.extend(["--icon", str(self.root_dir / "book.png")])
        elif target_platform == 'darwin':
            cmd.extend(["--windowed"])
            # Add icon if available
            if (self.root_dir / "book.png").exists():
                cmd.extend(["--icon", str(self.root_dir / "book.png")])
        elif target_platform == 'linux':
            # Add icon if available
            if (self.root_dir / "book.png").exists():
                cmd.extend(["--icon", str(self.root_dir / "book.png")])
        
        # Run PyInstaller
        subprocess.run(cmd, cwd=self.root_dir, check=True)
        
        return self.dist_dir / binary_name
    
    def create_launcher_script(self, platform_name):
        """Create platform-specific launcher script"""
        config = self.platform_configs[platform_name]
        launcher_name = f"START-HERE{config['launcher_ext']}"
        
        if platform_name == 'windows':
            content = f'''@echo off
echo Starting AI Audiobook Generator...
echo.
echo If this is your first time running the application:
echo 1. Make sure you have your Gemini API key ready
echo 2. Check the README.txt for setup instructions
echo.
pause
"{config['binary_name']}"
pause
'''
        elif platform_name == 'darwin':
            content = f'''#!/bin/bash
echo "Starting AI Audiobook Generator..."
echo ""
echo "If this is your first time running the application:"
echo "1. Make sure you have your Gemini API key ready"
echo "2. Check the README.txt for setup instructions"
echo ""
read -p "Press Enter to continue..."

# Get the directory of this script
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" &> /dev/null && pwd )"
cd "$DIR"

# Run the application
./{config['binary_name']}
'''
        else:  # Linux
            content = f'''#!/bin/bash
echo "Starting AI Audiobook Generator..."
echo ""
echo "If this is your first time running the application:"
echo "1. Make sure you have your Gemini API key ready"
echo "2. Check the README.txt for setup instructions"
echo ""
read -p "Press Enter to continue..."

# Get the directory of this script
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" &> /dev/null && pwd )"
cd "$DIR"

# Make binary executable
chmod +x {config['binary_name']}

# Run the application
./{config['binary_name']}
'''
        
        return launcher_name, content
    
    def create_readme(self, platform_name):
        """Create platform-specific README"""
        readme_content = f"""# AI Audiobook Generator v{self.version}

## Quick Start

1. **Run the Application**:
   - Double-click `START-HERE{self.platform_configs[platform_name]['launcher_ext']}`
   - Or run the binary directly: `{self.platform_configs[platform_name]['binary_name']}`

2. **First-Time Setup**:
   - You'll need a Google Gemini API key
   - Get one at: https://ai.google.dev/
   - Enter it in the GUI when prompted

## Features

- **Text-to-Speech**: Convert text to high-quality audio using Google's Gemini 2.5 TTS
- **Smart Chunking**: Intelligent text splitting for optimal audio generation
- **Audio Quality Detection**: Optional corruption detection (disabled by default)
- **Background Music**: Generate ambient music using Google's Lyria RealTime API
- **Resume Functionality**: Continue interrupted audiobook generation
- **Multiple Voices**: Choose from various voice options and models

For issues and updates: https://github.com/wowitsjack/audiobook-maker
"""
        return readme_content
    
    def create_release_package(self, platform_name, binary_path):
        """Create a complete release package for a platform"""
        config = self.platform_configs[platform_name]
        package_name = f"AI-Audiobook-Generator-v{self.version}-{platform_name.title()}"
        package_dir = self.release_dir / package_name
        
        # Create package directory
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy binary
        shutil.copy2(binary_path, package_dir / config['binary_name'])
        
        # Create launcher script
        launcher_name, launcher_content = self.create_launcher_script(platform_name)
        launcher_path = package_dir / launcher_name
        launcher_path.write_text(launcher_content)
        
        # Make launcher executable on Unix systems
        if platform_name in ['darwin', 'linux']:
            os.chmod(launcher_path, 0o755)
            os.chmod(package_dir / config['binary_name'], 0o755)
        
        # Create README
        readme_content = self.create_readme(platform_name)
        (package_dir / "README.txt").write_text(readme_content)
        
        # Copy requirements.txt for reference
        if (self.src_dir / "requirements.txt").exists():
            shutil.copy2(self.src_dir / "requirements.txt", package_dir)
        
        # Copy install script for Linux
        if platform_name == 'linux' and (self.src_dir / "install.sh").exists():
            shutil.copy2(self.src_dir / "install.sh", package_dir)
        
        # Create archive
        archive_name = f"{package_name}{config['archive_ext']}"
        archive_path = self.release_dir / archive_name
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.release_dir)
                    zipf.write(file_path, arcname)
        
        print(f"Created release package: {archive_path}")
        return archive_path, package_dir


def main():
    builder = AudiobookBuilder()
    builder.clean_build_dirs()
    builder.install_dependencies()
    builder.release_dir.mkdir(exist_ok=True)
    
    binary_path = builder.build_binary('linux')
    archive_path, package_dir = builder.create_release_package('linux', binary_path)
    print(f"\n🎉 Build complete! Created: {archive_path.name}")


if __name__ == "__main__":
    main()