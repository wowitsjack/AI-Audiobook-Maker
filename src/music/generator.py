#!/usr/bin/env python3
"""
Background Music Generator using Lyria RealTime API
Generates real-time instrumental music for audiobook backgrounds
"""

import asyncio
import os
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import wave
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor

try:
    from google import genai
    from google.genai import types
    LYRIA_AVAILABLE = True
except ImportError:
    LYRIA_AVAILABLE = False
    logging.warning("google-genai package required for music generation. Install with: pip install google-genai")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class MusicMood(Enum):
    """Predefined music moods for audiobooks"""
    AMBIENT = "ambient"
    DRAMATIC = "dramatic"
    PEACEFUL = "peaceful"
    MYSTERIOUS = "mysterious"
    ADVENTURE = "adventure"
    ROMANTIC = "romantic"
    TENSE = "tense"
    UPLIFTING = "uplifting"
    MELANCHOLY = "melancholy"
    FANTASY = "fantasy"


class MusicGenre(Enum):
    """Predefined music genres for audiobooks"""
    CLASSICAL = "classical"
    AMBIENT = "ambient"
    CINEMATIC = "cinematic"
    FOLK = "folk"
    ELECTRONIC = "electronic"
    ORCHESTRAL = "orchestral"
    PIANO = "piano"
    STRINGS = "strings"
    NEW_AGE = "new_age"
    MEDITATION = "meditation"


@dataclass
class MusicConfig:
    """Configuration for music generation"""
    bpm: int = 90
    temperature: float = 1.0
    guidance: float = 4.0
    density: float = 0.5
    brightness: float = 0.5
    scale: Optional[str] = None
    volume: float = 0.3
    mood: MusicMood = MusicMood.AMBIENT
    genre: MusicGenre = MusicGenre.AMBIENT
    custom_prompts: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.custom_prompts is None:
            self.custom_prompts = []


class MusicGenerator:
    """Real-time background music generator for audiobooks using Lyria RealTime"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize music generator
        
        Args:
            api_key: Google AI API key. If None, will use GEMINI_API_KEY env var
        """
        self.logger = logging.getLogger(__name__)
        
        if not LYRIA_AVAILABLE:
            raise ImportError("google-genai package required for music generation. Install with: pip install google-genai")
            
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("API key required for music generation. Set GEMINI_API_KEY environment variable.")
            
        # Initialize client with v1alpha API version for Lyria access
        self.client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1alpha'}
        )
        
        self.session = None
        self.is_generating = False
        self.audio_queue = queue.Queue()
        self.config = MusicConfig()
        self.audio_buffer = []
        self.buffer_lock = threading.Lock()
        self.receive_task = None
        
        # Audio format specs from Lyria RealTime
        self.sample_rate = 48000
        self.channels = 2
        self.bit_depth = 16
        
    def get_prompts_for_mood_and_genre(self, mood: MusicMood, genre: MusicGenre) -> List[types.WeightedPrompt]:
        """Generate prompts based on mood and genre using Lyria format"""
        prompts = []
        
        # Genre-specific prompts
        genre_prompts = {
            MusicGenre.CLASSICAL: ["Classical", "Orchestra", "Strings", "Elegant"],
            MusicGenre.AMBIENT: ["Ambient", "Atmospheric", "Ethereal", "Spacey Synths"],
            MusicGenre.CINEMATIC: ["Cinematic", "Orchestral Score", "Film Music", "Rich Orchestration"],
            MusicGenre.FOLK: ["Acoustic Guitar", "Folk", "Organic", "Warm"],
            MusicGenre.ELECTRONIC: ["Electronic", "Synths", "Digital", "Smooth"],
            MusicGenre.ORCHESTRAL: ["Orchestra", "Symphonic", "Full Orchestra", "Classical"],
            MusicGenre.PIANO: ["Piano", "Solo Piano", "Gentle Piano", "Melodic"],
            MusicGenre.STRINGS: ["Strings", "Violin", "Cello", "String Section"],
            MusicGenre.NEW_AGE: ["New Age", "Healing", "Meditation", "Peaceful"],
            MusicGenre.MEDITATION: ["Meditation", "Mindfulness", "Calm", "Tranquil"]
        }
        
        # Mood-specific prompts
        mood_prompts = {
            MusicMood.AMBIENT: ["Ambient", "Chill", "Subdued", "Background"],
            MusicMood.DRAMATIC: ["Dramatic", "Emotional", "Intense", "Powerful"],
            MusicMood.PEACEFUL: ["Peaceful", "Tranquil", "Serene", "Gentle"],
            MusicMood.MYSTERIOUS: ["Mysterious", "Ominous", "Dark", "Unsettling"],
            MusicMood.ADVENTURE: ["Adventure", "Epic", "Heroic", "Upbeat"],
            MusicMood.ROMANTIC: ["Romantic", "Tender", "Warm", "Emotional"],
            MusicMood.TENSE: ["Tense", "Ominous Drone", "Building", "Suspenseful"],
            MusicMood.UPLIFTING: ["Uplifting", "Bright", "Hopeful", "Inspiring"],
            MusicMood.MELANCHOLY: ["Melancholy", "Sad", "Nostalgic", "Reflective"],
            MusicMood.FANTASY: ["Fantasy", "Magical", "Mystical", "Ethereal"]
        }
        
        # Add genre prompts
        for prompt_text in genre_prompts.get(genre, []):
            prompts.append(types.WeightedPrompt(text=prompt_text, weight=1.0))
            
        # Add mood prompts with higher weight
        for prompt_text in mood_prompts.get(mood, []):
            prompts.append(types.WeightedPrompt(text=prompt_text, weight=1.2))
            
        return prompts
        
    async def start_generation(self, config: Optional[MusicConfig] = None) -> bool:
        """Start background music generation using Lyria RealTime
        
        Args:
            config: Music configuration. If None, uses default config
            
        Returns:
            True if generation started successfully
        """
        if self.is_generating:
            self.logger.warning("Music generation already in progress")
            return False
            
        if config:
            self.config = config
            
        try:
            # Connect to Lyria RealTime
            self.session = await self.client.aio.live.music.connect(
                model='models/lyria-realtime-exp'
            )
            
            # Set up audio receiver task
            self.receive_task = asyncio.create_task(self._receive_audio())
            
            # Get prompts for mood and genre
            prompts = self.get_prompts_for_mood_and_genre(self.config.mood, self.config.genre)
            
            # Add custom prompts
            for custom_prompt in self.config.custom_prompts:
                prompts.append(types.WeightedPrompt(text=custom_prompt, weight=1.0))
                
            # Send initial prompts
            await self.session.set_weighted_prompts(prompts=prompts)
            
            # Set music generation configuration
            music_config = types.LiveMusicGenerationConfig(
                bpm=self.config.bpm,
                temperature=self.config.temperature,
                guidance=self.config.guidance,
                density=self.config.density,
                brightness=self.config.brightness
            )
            
            # Set scale if specified
            if self.config.scale:
                try:
                    scale_value = getattr(types.Scale, self.config.scale)
                    music_config.scale = scale_value
                except AttributeError:
                    self.logger.warning(f"Unknown scale: {self.config.scale}, using default")
                    music_config.scale = types.Scale.SCALE_UNSPECIFIED
                
            await self.session.set_music_generation_config(config=music_config)
            
            # Start music generation
            await self.session.play()
            self.is_generating = True
            
            self.logger.info(f"Started Lyria music generation: {self.config.mood.value} {self.config.genre.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start music generation: {e}")
            self.is_generating = False
            if self.session:
                try:
                    await self.session.stop()
                except:
                    pass
                self.session = None
            return False
            
    async def _receive_audio(self):
        """Background task to receive and buffer audio chunks from Lyria"""
        try:
            async for message in self.session.receive():
                if hasattr(message, 'server_content') and hasattr(message.server_content, 'audio_chunks'):
                    if message.server_content.audio_chunks:
                        audio_data = message.server_content.audio_chunks[0].data
                        
                        with self.buffer_lock:
                            self.audio_buffer.append(audio_data)
                            
                        # Keep buffer size manageable (about 30 seconds)
                        max_buffer_size = self.sample_rate * self.channels * 2 * 30  # 30 seconds
                        if len(self.audio_buffer) * len(audio_data) > max_buffer_size:
                            with self.buffer_lock:
                                self.audio_buffer.pop(0)
                                
        except Exception as e:
            self.logger.error(f"Error receiving audio from Lyria: {e}")
            self.is_generating = False
            
    async def change_mood(self, mood: MusicMood, transition_weight: float = 0.5):
        """Change music mood with smooth transition
        
        Args:
            mood: New mood to transition to
            transition_weight: Weight for smooth transition (0.1-1.0)
        """
        if not self.is_generating or not self.session:
            self.logger.warning("Cannot change mood - generation not active")
            return
            
        try:
            self.config.mood = mood
            
            # Get new prompts and blend with current ones for smooth transition
            new_prompts = self.get_prompts_for_mood_and_genre(mood, self.config.genre)
            
            # Adjust weight for smooth transition
            for prompt in new_prompts:
                prompt.weight *= transition_weight
                
            await self.session.set_weighted_prompts(prompts=new_prompts)
            self.logger.info(f"Transitioned to mood: {mood.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to change mood: {e}")
            
    async def change_genre(self, genre: MusicGenre, transition_weight: float = 0.5):
        """Change music genre with smooth transition"""
        if not self.is_generating or not self.session:
            self.logger.warning("Cannot change genre - generation not active")
            return
            
        try:
            self.config.genre = genre
            
            new_prompts = self.get_prompts_for_mood_and_genre(self.config.mood, genre)
            
            for prompt in new_prompts:
                prompt.weight *= transition_weight
                
            await self.session.set_weighted_prompts(prompts=new_prompts)
            self.logger.info(f"Transitioned to genre: {genre.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to change genre: {e}")
            
    async def adjust_config(self, **kwargs):
        """Adjust music generation parameters in real-time
        
        Accepts: bpm, density, brightness, guidance, scale, etc.
        """
        if not self.is_generating or not self.session:
            self.logger.warning("Cannot adjust config - generation not active")
            return
            
        try:
            # Update config
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    
            # Create new config
            music_config = types.LiveMusicGenerationConfig(
                bpm=self.config.bpm,
                temperature=self.config.temperature,
                guidance=self.config.guidance,
                density=self.config.density,
                brightness=self.config.brightness
            )
            
            if self.config.scale:
                try:
                    scale_value = getattr(types.Scale, self.config.scale)
                    music_config.scale = scale_value
                except AttributeError:
                    music_config.scale = types.Scale.SCALE_UNSPECIFIED
                
            await self.session.set_music_generation_config(config=music_config)
            
            # Reset context for bpm/scale changes (per Lyria docs)
            if 'bpm' in kwargs or 'scale' in kwargs:
                await self.session.reset_context()
                
            self.logger.info(f"Updated music config: {kwargs}")
            
        except Exception as e:
            self.logger.error(f"Failed to adjust config: {e}")
            
    def get_audio_chunk(self, duration_seconds: float = 1.0) -> Optional[bytes]:
        """Get audio chunk for specified duration
        
        Args:
            duration_seconds: Duration of audio to retrieve
            
        Returns:
            Raw PCM audio data or None if not available
        """
        if not self.audio_buffer:
            return None
            
        # Calculate required bytes for 16-bit stereo PCM
        bytes_per_second = self.sample_rate * self.channels * 2  # 2 bytes per 16-bit sample
        bytes_needed = int(bytes_per_second * duration_seconds)
        
        with self.buffer_lock:
            if not self.audio_buffer:
                return None
                
            # Combine audio chunks to get required duration
            combined_audio = b''.join(self.audio_buffer)
            
            if len(combined_audio) >= bytes_needed:
                # Return requested duration and remove from buffer
                result = combined_audio[:bytes_needed]
                remaining = combined_audio[bytes_needed:]
                
                # Update buffer with remaining audio
                self.audio_buffer = [remaining] if remaining else []
                
                return result
                
        return None
        
    def save_audio_chunk(self, audio_data: bytes, filename: str):
        """Save audio chunk to WAV file
        
        Args:
            audio_data: Raw PCM audio data
            filename: Output filename
        """
        try:
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self.bit_depth // 8)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
                
            self.logger.info(f"Saved audio chunk: {filename} ({len(audio_data)} bytes)")
            
        except Exception as e:
            self.logger.error(f"Failed to save audio: {e}")
            
    async def pause(self):
        """Pause music generation"""
        if self.session and self.is_generating:
            try:
                await self.session.pause()
                self.logger.info("Music generation paused")
            except Exception as e:
                self.logger.error(f"Failed to pause: {e}")
                
    async def resume(self):
        """Resume music generation"""
        if self.session and self.is_generating:
            try:
                await self.session.play()
                self.logger.info("Music generation resumed")
            except Exception as e:
                self.logger.error(f"Failed to resume: {e}")
                
    async def stop(self):
        """Stop music generation"""
        if self.session:
            try:
                self.is_generating = False
                
                # Cancel receive task
                if self.receive_task:
                    self.receive_task.cancel()
                    try:
                        await self.receive_task
                    except asyncio.CancelledError:
                        pass
                
                # Stop session
                await self.session.stop()
                self.session = None
                
                with self.buffer_lock:
                    self.audio_buffer.clear()
                    
                self.logger.info("Music generation stopped")
                
            except Exception as e:
                self.logger.error(f"Failed to stop: {e}")
                
    def is_available(self) -> bool:
        """Check if music generation is available"""
        return LYRIA_AVAILABLE and bool(self.api_key)
        
    def get_buffer_duration(self) -> float:
        """Get current buffer duration in seconds"""
        with self.buffer_lock:
            if not self.audio_buffer:
                return 0.0
                
            total_bytes = sum(len(chunk) for chunk in self.audio_buffer)
            bytes_per_second = self.sample_rate * self.channels * 2  # 16-bit samples
            return total_bytes / bytes_per_second


# Convenience functions for quick usage
async def generate_background_music(
    mood: MusicMood = MusicMood.AMBIENT,
    genre: MusicGenre = MusicGenre.AMBIENT,
    duration_minutes: float = 5.0,
    output_file: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """Generate background music for specified duration using Lyria RealTime
    
    Args:
        mood: Music mood
        genre: Music genre
        duration_minutes: Duration to generate
        output_file: Output file path (optional)
        api_key: API key (optional)
        
    Returns:
        Path to generated audio file or None if failed
    """
    generator = MusicGenerator(api_key)
    config = MusicConfig(mood=mood, genre=genre)
    
    try:
        if not await generator.start_generation(config):
            return None
            
        # Wait for buffer to fill
        await asyncio.sleep(3)
        
        # Collect audio for specified duration
        audio_chunks = []
        duration_seconds = duration_minutes * 60
        chunk_duration = 1.0  # 1 second chunks
        
        for i in range(int(duration_seconds / chunk_duration)):
            chunk = generator.get_audio_chunk(chunk_duration)
            if chunk:
                audio_chunks.append(chunk)
            await asyncio.sleep(chunk_duration)
            
        # Save to file
        if audio_chunks:
            if not output_file:
                output_file = f"background_music_{mood.value}_{genre.value}_{int(time.time())}.wav"
                
            combined_audio = b''.join(audio_chunks)
            generator.save_audio_chunk(combined_audio, output_file)
            
            await generator.stop()
            return output_file
            
    except Exception as e:
        logging.error(f"Failed to generate music: {e}")
        
    finally:
        await generator.stop()
        
    return None


if __name__ == "__main__":
    # Example usage
    async def main():
        generator = MusicGenerator()
        
        if not generator.is_available():
            print("Music generation not available. Check API key and dependencies.")
            return
            
        config = MusicConfig(
            mood=MusicMood.PEACEFUL,
            genre=MusicGenre.AMBIENT,
            bpm=80,
            density=0.3,
            brightness=0.4
        )
        
        print("Starting Lyria RealTime music generation...")
        if await generator.start_generation(config):
            print("Music generation started successfully!")
            
            # Wait for buffer to fill
            await asyncio.sleep(5)
            
            # Get some audio
            audio_chunk = generator.get_audio_chunk(3.0)
            if audio_chunk:
                generator.save_audio_chunk(audio_chunk, "test_lyria_music.wav")
                print("Saved test music chunk from Lyria!")
                
            # Change mood
            print("Changing to dramatic mood...")
            await generator.change_mood(MusicMood.DRAMATIC)
            
            await asyncio.sleep(3)
            await generator.stop()
            print("Music generation stopped")
            
        else:
            print("Failed to start music generation")
            
    asyncio.run(main())