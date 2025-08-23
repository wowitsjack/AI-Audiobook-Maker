#!/usr/bin/env python3
"""
Create source code release packages for all platforms (code + launcher in zip)
"""

import os
import shutil
import zipfile
from pathlib import Path

class SourceReleaseBuilder:
    def __init__(self):
        self.src_dir = Path(__file__).parent.parent
        self.root_dir = self.src_dir.parent
        self.version = "2.1.0"
        self.release_dir = self.root_dir / "releases"
        
        # Platform-specific launchers
        self.platforms = {
            'Windows': 'Start-GUI-Windows.bat',
            'macOS': 'Start-GUI-macOS.command', 
            'Linux': 'Start-GUI-Linux.sh'
        }
        
        # Files to exclude from releases
        self.exclude_dirs = {'releases', 'build', 'dist', '__pycache__', '.git'}
        self.exclude_files = {'*.pyc', '*.pyo', '*.spec'}
    
    def should_exclude(self, path):
        """Check if path should be excluded"""
        for exclude_dir in self.exclude_dirs:
            if exclude_dir in path.parts:
                return True
        if path.name.startswith('.'):
            return True
        if path.suffix in ['.pyc', '.pyo', '.spec']:
            return True
        return False
    
    def create_platform_release(self, platform_name):
        """Create a release zip for specific platform"""
        launcher_file = self.platforms[platform_name]
        zip_name = f"AI-Audiobook-Generator-v{self.version}-{platform_name}-Easy-Launcher.zip"
        zip_path = self.release_dir / zip_name
        
        print(f"Creating {platform_name} Easy-Launcher release...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all source files except excluded ones
            for file_path in self.root_dir.rglob('*'):
                if file_path.is_file() and not self.should_exclude(file_path):
                    # Get relative path from root
                    rel_path = file_path.relative_to(self.root_dir)
                    # Skip files outside audiobook_maker directory
                    if str(rel_path).startswith('audiobook_maker/'):
                        # Remove audiobook_maker prefix for cleaner zip structure
                        arc_path = rel_path.relative_to('audiobook_maker')
                        zipf.write(file_path, arc_path)
            
            # Add platform-specific launcher to root of zip
            launcher_path = self.root_dir / launcher_file
            if launcher_path.exists():
                zipf.write(launcher_path, launcher_file)
        
        print(f"✅ Created: {zip_name}")
        return zip_path
    
    def create_all_releases(self):
        """Create releases for all platforms"""
        self.release_dir.mkdir(exist_ok=True)
        
        created_files = []
        for platform_name in self.platforms:
            zip_path = self.create_platform_release(platform_name)
            created_files.append(zip_path)
        
        return created_files

def main():
    builder = SourceReleaseBuilder()
    files = builder.create_all_releases()
    
    print(f"\n🎉 Created {len(files)} release packages:")
    for file_path in files:
        print(f"  - {file_path.name}")

if __name__ == "__main__":
    main()