#!/usr/bin/env python3
"""
Setup script for AI Audiobook Generator
A comprehensive TTS audiobook generation system with background music and corruption detection
"""

from setuptools import setup, find_packages
import os

def read_requirements():
    """Read requirements from requirements.txt"""
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

def read_readme():
    """Read README file"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "AI Audiobook Generator with TTS, background music, and corruption detection"

setup(
    name="ai-audiobook-generator",
    version="2.1.0",
    description="AI-powered audiobook generator with TTS, background music, and quality detection",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="wowitsjack",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=read_requirements(),
    extras_require={
        'audio': ['librosa', 'scipy', 'soundfile', 'numpy', 'matplotlib'],
        'gui': ['customtkinter', 'tkinter'],
        'dev': ['pytest', 'pytest-asyncio', 'black', 'flake8']
    },
    entry_points={
        'console_scripts': [
            'audiobook-maker=audiobook_maker.cli:main',
            'audiobook-gui=audiobook_maker.gui.application:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="audiobook tts text-to-speech ai gemini background-music",
    project_urls={
        "Bug Reports": "https://github.com/wowitsjack/ai-audiobook-generator/issues",
        "Source": "https://github.com/wowitsjack/ai-audiobook-generator",
    },
)