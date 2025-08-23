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
        self.root_dir = Path(__file__).parent.parent
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
        
        # PyInstaller command
        cmd = [
            "pyinstaller",
            "--onefile",
            "--name", binary_name.replace('.exe', ''),
            "--distpath", str(self.dist_dir),
            "--clean",
            "--noconfirm",
            str(self.root_dir / "audiobook_gui_launcher.py")
        ]
        
        # Add platform-specific options
        if target_platform == 'windows':
            cmd.extend(["--windowed", "--icon", "icon.ico"])  # If we have an icon
        elif target_platform == 'darwin':
            cmd.extend(["--windowed"])
        
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

## Usage

1. **Load Text**: Click "Browse" and select your text file (.txt, .md, .epub)
2. **Configure Settings**: 
   - Select voice and model
   - Adjust chunk size if needed
   - Enable background music (optional)
   - Enable quality detection (optional)
3. **Set Output**: Choose where to save your audiobook
4. **Generate**: Click "Generate Audiobook" and wait for completion

## Supported Formats

- **Input**: .txt, .md, .epub files
- **Output**: .wav audio files

## Troubleshooting

- **API Errors**: Check your Gemini API key and internet connection
- **Large Files**: Use smaller chunk sizes for very large texts
- **Audio Issues**: Enable quality detection for better error handling

## System Requirements

- **Windows**: 10/11 (64-bit)
- **macOS**: 10.14+ (Intel/Apple Silicon)
- **Linux**: Ubuntu 18.04+ or equivalent (64-bit)

## Support

For issues and updates: https://github.com/wowitsjacks/audiobook-maker

---
Built with ❤️ using Python, CustomTkinter, and Google's AI APIs
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
        if (self.root_dir / "requirements.txt").exists():
            shutil.copy2(self.root_dir / "requirements.txt", package_dir)
        
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
    
    def build_all_platforms(self):
        """Build releases for all platforms"""
        self.clean_build_dirs()
        self.install_dependencies()
        
        # Create release directory
        self.release_dir.mkdir(exist_ok=True)
        
        current_platform = platform.system().lower()
        print(f"Building on {current_platform} platform...")
        
        # Note: Cross-compilation is complex with PyInstaller
        # This script focuses on the current platform
        if current_platform == 'linux':
            platforms_to_build = ['linux']
        elif current_platform == 'darwin':
            platforms_to_build = ['darwin']
        elif current_platform == 'windows':
            platforms_to_build = ['windows']
        else:
            platforms_to_build = ['linux']  # Default fallback
        
        built_packages = []
        
        for target_platform in platforms_to_build:
            try:
                print(f"\n=== Building for {target_platform} ===")
                binary_path = self.build_binary(target_platform)
                archive_path, package_dir = self.create_release_package(target_platform, binary_path)
                built_packages.append((target_platform, archive_path, package_dir))
                print(f"✅ Successfully built {target_platform} package")
            except Exception as e:
                print(f"❌ Failed to build {target_platform}: {e}")
        
        return built_packages
    
    def install_to_local_bin(self):
        """Install the binary to ~/.local/bin for the current user"""
        if platform.system().lower() != 'linux':
            print("Local bin installation only supported on Linux")
            return
        
        binary_path = self.build_binary('linux')
        local_bin = Path.home() / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        
        target_path = local_bin / self.app_name
        shutil.copy2(binary_path, target_path)
        os.chmod(target_path, 0o755)
        
        print(f"✅ Installed to {target_path}")
        print("Make sure ~/.local/bin is in your PATH")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Build AI Audiobook Generator releases")
    parser.add_argument("--platform", choices=['windows', 'darwin', 'linux'], 
                       help="Target platform (default: current platform)")
    parser.add_argument("--install-local", action="store_true",
                       help="Install binary to ~/.local/bin (Linux only)")
    parser.add_argument("--all", action="store_true",
                       help="Build all supported platforms")
    
    args = parser.parse_args()
    
    builder = AudiobookBuilder()
    
    if args.install_local:
        builder.install_to_local_bin()
    elif args.all:
        packages = builder.build_all_platforms()
        print(f"\n🎉 Build complete! Created {len(packages)} packages:")
        for platform_name, archive_path, _ in packages:
            print(f"  - {platform_name}: {archive_path.name}")
    else:
        target_platform = args.platform or platform.system().lower()
        builder.clean_build_dirs()
        builder.install_dependencies()
        builder.release_dir.mkdir(exist_ok=True)
        
        binary_path = builder.build_binary(target_platform)
        archive_path, package_dir = builder.create_release_package(target_platform, binary_path)
        print(f"\n🎉 Build complete! Created: {archive_path.name}")


if __name__ == "__main__":
    main()