#!/usr/bin/env python3
"""
Setup script for AI Audiobook Generator
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = """
    # AI Audiobook Generator
    
    A sophisticated AI-powered audiobook generator using Google's Gemini 2.5 TTS.
    
    ## Features
    - 30+ different narrator voices
    - Smart text chunking with token counting
    - Audio corruption detection and retry logic
    - Background music generation with Google's Lyria RealTime API
    - Modern CustomTkinter GUI
    - Resume functionality for large projects
    - Cross-platform support
    """

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt')) as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ai-audiobook-generator",
    version="3.0.0",
    author="wowitsjack",
    author_email="nolol",
    description="AI-powered audiobook generator using Google Gemini 2.5 TTS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wowitsjack/ai-audiobook-generator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "audio_quality": ["librosa>=0.10.0", "scipy>=1.10.0", "soundfile>=0.12.0", "matplotlib>=3.7.0"],
        "build": ["pyinstaller>=6.15.0"],
    },
    entry_points={
        "console_scripts": [
            "audiobook-generator=audiobook_maker.core.cli:main",
            "audiobook-gui=audiobook_maker.gui.launch_gui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "audiobook_maker": [
            "*.md",
            "*.txt",
            "*.sh",
            "*.bat",
            "*.command",
        ]
    },
    zip_safe=False,
    keywords="audiobook tts text-to-speech ai gemini google",
    project_urls={
        "Bug Reports": "https://github.com/wowitsjack/ai-audiobook-generator/issues",
        "Source": "https://github.com/wowitsjack/ai-audiobook-generator",
        "Documentation": "https://github.com/wowitsjack/ai-audiobook-generator/blob/main/README.md",
    },
)