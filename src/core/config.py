"""
Configuration management for the AI Audiobook Generator.

Centralizes all configuration loading, environment variable handling,
and settings validation in one place.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        """Fallback load_dotenv function"""
        pass


@dataclass
class TTSConfig:
    """TTS-specific configuration"""
    api_key: str
    narrator_voice: str = "Charon"
    model: str = "gemini-2.5-flash-preview-tts"
    chunk_limit: int = 30000
    safe_chunk_mode: bool = False
    safe_chunk_limit: int = 1800


@dataclass
class CorruptionDetectionConfig:
    """Audio corruption detection configuration"""
    enabled: bool = True
    retry_attempts: int = 2
    auto_split: bool = True


@dataclass
class BackgroundMusicConfig:
    """Background music generation configuration"""
    enabled: bool = False
    volume: float = 0.2
    mood: str = "ambient"
    genre: str = "ambient"
    bpm: int = 80
    density: float = 0.3
    brightness: float = 0.4
    guidance: float = 4.0
    temperature: float = 1.0
    custom_prompts: List[str] = field(default_factory=list)
    continuous: bool = True
    fade_duration: float = 2.0
    segment_length: float = 10.0


@dataclass
class Config:
    """Main configuration class"""
    tts: TTSConfig
    corruption_detection: CorruptionDetectionConfig
    background_music: BackgroundMusicConfig
    working_directory: Optional[str] = None
    project_directory: Optional[str] = None

    def __post_init__(self):
        if self.working_directory is None:
            self.working_directory = os.getcwd()
        if self.project_directory is None:
            self.project_directory = os.path.expanduser('~/AI-Audiobook-Generator')


def load_config() -> Config:
    """
    Load configuration from .env files and environment variables.
    
    Returns:
        Config: Fully populated configuration object
    """
    # Load environment variables from multiple possible locations
    config_locations = [
        '.env',  # Current directory (for development)
        os.path.expanduser('~/.config/ai-audiobook-generator/.env'),  # System config
        os.path.expanduser('~/.ai-audiobook-generator.env'),  # Home directory fallback
    ]
    
    loaded = False
    for env_file in config_locations:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            loaded = True
            print(f"Loaded configuration from: {env_file}")
            break
    
    if not loaded:
        print("No .env file found. Using environment variables...")
    
    # Validate required API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        config_dir = os.path.expanduser('~/.config/ai-audiobook-generator')
        raise EnvironmentError(f"""GOOGLE_API_KEY not found in environment variables.

Please set up your API key by either:
1. Creating a .env file in the current directory
2. Creating {config_dir}/.env
3. Setting the GOOGLE_API_KEY environment variable

Example .env file content:
GOOGLE_API_KEY=your_gemini_api_key_here
NARRATOR_VOICE=Charon""")
    
    # Build TTS configuration
    tts_config = TTSConfig(
        api_key=api_key,
        narrator_voice=os.getenv('NARRATOR_VOICE', 'Charon'),
        model=os.getenv('TTS_MODEL', 'gemini-2.5-flash-preview-tts'),
        chunk_limit=int(os.getenv('CHUNK_LIMIT', '30000')),
        safe_chunk_mode=os.getenv('SAFE_CHUNK_MODE', 'false').lower() == 'true',
        safe_chunk_limit=int(os.getenv('SAFE_CHUNK_LIMIT', '1800'))
    )
    
    # Build corruption detection configuration
    corruption_config = CorruptionDetectionConfig(
        enabled=os.getenv('ENABLE_CORRUPTION_DETECTION', 'true').lower() == 'true',
        retry_attempts=int(os.getenv('CORRUPTION_RETRY_ATTEMPTS', '2')),
        auto_split=os.getenv('CORRUPTION_AUTO_SPLIT', 'true').lower() == 'true'
    )
    
    # Build background music configuration
    custom_prompts = [p.strip() for p in os.getenv('BACKGROUND_MUSIC_CUSTOM_PROMPTS', '').split(',') if p.strip()]
    music_config = BackgroundMusicConfig(
        enabled=os.getenv('ENABLE_BACKGROUND_MUSIC', 'false').lower() == 'true',
        volume=float(os.getenv('BACKGROUND_MUSIC_VOLUME', '0.2')),
        mood=os.getenv('BACKGROUND_MUSIC_MOOD', 'ambient'),
        genre=os.getenv('BACKGROUND_MUSIC_GENRE', 'ambient'),
        bpm=int(os.getenv('BACKGROUND_MUSIC_BPM', '80')),
        density=float(os.getenv('BACKGROUND_MUSIC_DENSITY', '0.3')),
        brightness=float(os.getenv('BACKGROUND_MUSIC_BRIGHTNESS', '0.4')),
        guidance=float(os.getenv('BACKGROUND_MUSIC_GUIDANCE', '4.0')),
        temperature=float(os.getenv('BACKGROUND_MUSIC_TEMPERATURE', '1.0')),
        custom_prompts=custom_prompts,
        continuous=os.getenv('BACKGROUND_MUSIC_CONTINUOUS', 'true').lower() == 'true',
        fade_duration=float(os.getenv('BACKGROUND_MUSIC_FADE_DURATION', '2.0')),
        segment_length=float(os.getenv('BACKGROUND_MUSIC_SEGMENT_LENGTH', '10.0'))
    )
    
    return Config(
        tts=tts_config,
        corruption_detection=corruption_config,
        background_music=music_config,
        working_directory=os.getcwd(),
        project_directory=os.getenv('PROJECT_DIRECTORY', os.path.expanduser('~/AI-Audiobook-Generator'))
    )


def save_config_to_env(config: Config, env_file: str = '.env') -> bool:
    """
    Save configuration to an .env file.
    
    Args:
        config: Configuration object to save
        env_file: Path to .env file
        
    Returns:
        bool: True if saved successfully
    """
    try:
        env_lines = [
            "# AI Audiobook Generator Configuration",
            "",
            "# TTS Configuration",
            f"GOOGLE_API_KEY={config.tts.api_key}",
            f"NARRATOR_VOICE={config.tts.narrator_voice}",
            f"TTS_MODEL={config.tts.model}",
            f"CHUNK_LIMIT={config.tts.chunk_limit}",
            f"SAFE_CHUNK_MODE={'true' if config.tts.safe_chunk_mode else 'false'}",
            f"SAFE_CHUNK_LIMIT={config.tts.safe_chunk_limit}",
            "",
            "# Corruption Detection",
            f"ENABLE_CORRUPTION_DETECTION={'true' if config.corruption_detection.enabled else 'false'}",
            f"CORRUPTION_RETRY_ATTEMPTS={config.corruption_detection.retry_attempts}",
            f"CORRUPTION_AUTO_SPLIT={'true' if config.corruption_detection.auto_split else 'false'}",
            "",
            "# Background Music",
            f"ENABLE_BACKGROUND_MUSIC={'true' if config.background_music.enabled else 'false'}",
            f"BACKGROUND_MUSIC_VOLUME={config.background_music.volume}",
            f"BACKGROUND_MUSIC_MOOD={config.background_music.mood}",
            f"BACKGROUND_MUSIC_GENRE={config.background_music.genre}",
            f"BACKGROUND_MUSIC_BPM={config.background_music.bpm}",
            f"BACKGROUND_MUSIC_DENSITY={config.background_music.density}",
            f"BACKGROUND_MUSIC_BRIGHTNESS={config.background_music.brightness}",
            f"BACKGROUND_MUSIC_GUIDANCE={config.background_music.guidance}",
            f"BACKGROUND_MUSIC_TEMPERATURE={config.background_music.temperature}",
            f"BACKGROUND_MUSIC_CUSTOM_PROMPTS={','.join(config.background_music.custom_prompts)}",
            f"BACKGROUND_MUSIC_CONTINUOUS={'true' if config.background_music.continuous else 'false'}",
            f"BACKGROUND_MUSIC_FADE_DURATION={config.background_music.fade_duration}",
            f"BACKGROUND_MUSIC_SEGMENT_LENGTH={config.background_music.segment_length}",
            "",
            "# Directories",
            f"PROJECT_DIRECTORY={config.project_directory}",
            ""
        ]
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_lines))
        
        return True
        
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def get_default_config() -> Config:
    """
    Get a default configuration for testing or initial setup.
    
    Returns:
        Config: Default configuration object
    """
    return Config(
        tts=TTSConfig(
            api_key="your_api_key_here",
            narrator_voice="Charon",
            model="gemini-2.5-flash-preview-tts",
            chunk_limit=30000,
            safe_chunk_mode=False,
            safe_chunk_limit=1800
        ),
        corruption_detection=CorruptionDetectionConfig(
            enabled=True,
            retry_attempts=2,
            auto_split=True
        ),
        background_music=BackgroundMusicConfig(
            enabled=False,
            volume=0.2,
            mood="ambient",
            genre="ambient",
            bpm=80,
            density=0.3,
            brightness=0.4,
            guidance=4.0,
            temperature=1.0,
            custom_prompts=[],
            continuous=True,
            fade_duration=2.0,
            segment_length=10.0
        )
    )