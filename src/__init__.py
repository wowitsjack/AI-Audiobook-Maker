"""
AI Audiobook Generator

A comprehensive system for generating high-quality audiobooks using AI TTS,
with features including background music generation, audio corruption detection,
and intelligent text chunking.

Features:
- Google Gemini 2.5 TTS integration
- Background music generation using Lyria RealTime API
- Audio corruption detection and automatic retry
- Smart text chunking with token counting
- Project state management and resume capability
- Modern GUI with CustomTkinter
"""

__version__ = "2.1.0"
__author__ = "wowitsjack"

from .core.engine import AudiobookEngine
from .core.config import Config, load_config

__all__ = [
    "AudiobookEngine", 
    "Config", 
    "load_config",
    "__version__",
    "__author__"
]