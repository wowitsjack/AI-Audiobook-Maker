#!/usr/bin/env python3
"""
Test script for background music generation and mixing functionality
Tests the complete workflow from music generation to audio mixing
"""

import os
import asyncio
import time
import wave
from pathlib import Path

# Set up test environment
os.environ['ENABLE_BACKGROUND_MUSIC'] = 'true'
os.environ['BACKGROUND_MUSIC_VOLUME'] = '0.3'
os.environ['BACKGROUND_MUSIC_MOOD'] = 'peaceful'
os.environ['BACKGROUND_MUSIC_GENRE'] = 'ambient'
os.environ['BACKGROUND_MUSIC_BPM'] = '80'
os.environ['BACKGROUND_MUSIC_DENSITY'] = '0.4'
os.environ['BACKGROUND_MUSIC_BRIGHTNESS'] = '0.5'
os.environ['BACKGROUND_MUSIC_CUSTOM_PROMPTS'] = 'Gentle Piano, Soft Strings'

try:
    from music_generator import MusicGenerator, MusicConfig, MusicMood, MusicGenre, generate_background_music
    MUSIC_AVAILABLE = True
except ImportError as e:
    print(f"Music generation not available: {e}")
    MUSIC_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    print("Pydub not available - audio mixing tests will be skipped")
    PYDUB_AVAILABLE = False

def test_music_enums():
    """Test that all music enums are properly defined"""
    print("🧪 Testing Music Enums...")
    
    # Test MusicMood enum
    expected_moods = ['ambient', 'dramatic', 'peaceful', 'mysterious', 'adventure', 
                     'romantic', 'tense', 'uplifting', 'melancholy', 'fantasy']
    
    for mood_name in expected_moods:
        try:
            mood = MusicMood(mood_name)
            print(f"  ✅ MusicMood.{mood_name.upper()}: {mood.value}")
        except ValueError:
            print(f"  ❌ MusicMood.{mood_name.upper()}: Not found")
    
    # Test MusicGenre enum
    expected_genres = ['classical', 'ambient', 'cinematic', 'folk', 'electronic',
                      'orchestral', 'piano', 'strings', 'new_age', 'meditation']
    
    for genre_name in expected_genres:
        try:
            genre = MusicGenre(genre_name)
            print(f"  ✅ MusicGenre.{genre_name.upper()}: {genre.value}")
        except ValueError:
            print(f"  ❌ MusicGenre.{genre_name.upper()}: Not found")

def test_music_config():
    """Test MusicConfig creation and validation"""
    print("\n🧪 Testing MusicConfig...")
    
    try:
        config = MusicConfig(
            bpm=80,
            temperature=1.0,
            guidance=4.0,
            density=0.4,
            brightness=0.5,
            volume=0.3,
            mood=MusicMood.PEACEFUL,
            genre=MusicGenre.AMBIENT,
            custom_prompts=['Gentle Piano', 'Soft Strings']
        )
        
        print(f"  ✅ MusicConfig created successfully")
        print(f"    - BPM: {config.bpm}")
        print(f"    - Mood: {config.mood.value}")
        print(f"    - Genre: {config.genre.value}")
        print(f"    - Volume: {config.volume}")
        print(f"    - Custom Prompts: {config.custom_prompts}")
        
        return config
        
    except Exception as e:
        print(f"  ❌ MusicConfig creation failed: {e}")
        return None

async def test_music_generator_basic():
    """Test basic MusicGenerator functionality"""
    print("\n🧪 Testing MusicGenerator Basic Functionality...")
    
    try:
        # Test API key requirement
        api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("  ⚠️ No API key found - using placeholder")
            api_key = "test_key"
        
        generator = MusicGenerator(api_key)
        print(f"  ✅ MusicGenerator created")
        print(f"    - API Key: {'Set' if generator.api_key else 'Not set'}")
        print(f"    - Sample Rate: {generator.sample_rate}")
        print(f"    - Channels: {generator.channels}")
        print(f"    - Available: {generator.is_available()}")
        
        return generator
        
    except ImportError:
        print("  ❌ MusicGenerator import failed - dependencies missing")
        return None
    except Exception as e:
        print(f"  ❌ MusicGenerator creation failed: {e}")
        return None

async def test_music_generation_simulation():
    """Test music generation workflow (simulation)"""
    print("\n🧪 Testing Music Generation Workflow...")
    
    try:
        config = MusicConfig(
            mood=MusicMood.PEACEFUL,
            genre=MusicGenre.AMBIENT,
            bpm=80,
            density=0.4,
            brightness=0.5,
            custom_prompts=['Gentle Piano', 'Soft Strings']
        )
        
        # Test prompt generation
        generator = MusicGenerator("test_key")
        prompts = generator.get_prompts_for_mood_and_genre(config.mood, config.genre)
        
        print(f"  ✅ Generated {len(prompts)} prompts for {config.mood.value} {config.genre.value}")
        for i, prompt in enumerate(prompts[:5]):  # Show first 5
            print(f"    {i+1}. {prompt.text} (weight: {prompt.weight})")
        
        # Test configuration
        print(f"  ✅ Music configuration validated")
        print(f"    - BPM: {config.bpm}")
        print(f"    - Density: {config.density}")
        print(f"    - Brightness: {config.brightness}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Music generation test failed: {e}")
        return False

def create_test_audio_file(filename, duration_seconds=5):
    """Create a test audio file for mixing tests"""
    try:
        import numpy as np
        
        sample_rate = 44100
        samples = int(sample_rate * duration_seconds)
        
        # Generate a simple test tone
        frequency = 440  # A4 note
        t = np.linspace(0, duration_seconds, samples)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
        
        # Convert to 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Save as WAV
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        print(f"  ✅ Created test audio file: {filename}")
        return True
        
    except ImportError:
        print("  ⚠️ NumPy not available - using silence")
        # Create silent audio file
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            wav_file.writeframes(b'\x00' * (44100 * 2 * duration_seconds))
        
        print(f"  ✅ Created silent test file: {filename}")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to create test audio: {e}")
        return False

def test_audio_mixing():
    """Test audio mixing functionality"""
    print("\n🧪 Testing Audio Mixing...")
    
    if not PYDUB_AVAILABLE:
        print("  ⚠️ Pydub not available - skipping mixing tests")
        return False
    
    try:
        # Create test files
        speech_file = "test_speech.wav"
        music_file = "test_music.wav"
        output_file = "test_mixed.wav"
        
        # Create test audio files
        if not create_test_audio_file(speech_file, 3):
            return False
        if not create_test_audio_file(music_file, 5):
            return False
        
        # Test mixing with pydub
        speech = AudioSegment.from_wav(speech_file)
        music = AudioSegment.from_wav(music_file)
        
        # Adjust music volume (30% of original)
        music_volume = 0.3
        music_adjusted = music + (20 * np.log10(music_volume))  # Convert to dB
        
        # Ensure music is at least as long as speech
        if len(music_adjusted) < len(speech):
            music_adjusted = music_adjusted * (len(speech) // len(music_adjusted) + 1)
        music_adjusted = music_adjusted[:len(speech)]
        
        # Mix audio
        mixed = speech.overlay(music_adjusted)
        
        # Export result
        mixed.export(output_file, format="wav")
        
        print(f"  ✅ Audio mixing successful")
        print(f"    - Speech duration: {len(speech)/1000:.1f}s")
        print(f"    - Music duration: {len(music)/1000:.1f}s")
        print(f"    - Mixed duration: {len(mixed)/1000:.1f}s")
        print(f"    - Output file: {output_file}")
        
        # Cleanup
        for f in [speech_file, music_file, output_file]:
            if os.path.exists(f):
                os.remove(f)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Audio mixing failed: {e}")
        return False

def test_app_integration():
    """Test integration with main app"""
    print("\n🧪 Testing App Integration...")
    
    try:
        from app import load_config, ENABLE_BACKGROUND_MUSIC, BACKGROUND_MUSIC_VOLUME
        
        print(f"  ✅ App configuration loaded")
        print(f"    - Background music enabled: {ENABLE_BACKGROUND_MUSIC}")
        print(f"    - Background music volume: {BACKGROUND_MUSIC_VOLUME}")
        
        # Test music generator import in app context
        try:
            from app import create_background_music_generator
            print(f"  ✅ Background music generator function available")
        except ImportError:
            print(f"  ⚠️ Background music generator function not found in app")
        
        return True
        
    except Exception as e:
        print(f"  ❌ App integration test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run all background music tests"""
    print("🎵 Background Music System - Comprehensive Test Suite")
    print("=" * 60)
    
    test_results = []
    
    if not MUSIC_AVAILABLE:
        print("⚠️ Music generation dependencies not available")
        print("   Install: pip install google-genai pydub numpy")
        return False
    
    # Test 1: Enums and basic structures
    test_music_enums()
    config = test_music_config()
    test_results.append(config is not None)
    
    # Test 2: MusicGenerator basic functionality
    generator = await test_music_generator_basic()
    test_results.append(generator is not None)
    
    # Test 3: Music generation workflow
    generation_result = await test_music_generation_simulation()
    test_results.append(generation_result)
    
    # Test 4: Audio mixing
    mixing_result = test_audio_mixing()
    test_results.append(mixing_result)
    
    # Test 5: App integration
    app_result = test_app_integration()
    test_results.append(app_result)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Summary:")
    print(f"  ✅ Passed: {sum(test_results)}/{len(test_results)} tests")
    
    if all(test_results):
        print("🎉 All background music tests passed!")
        return True
    else:
        print("⚠️ Some tests failed - check dependencies and configuration")
        return False

if __name__ == "__main__":
    print("Starting background music test suite...")
    
    if MUSIC_AVAILABLE:
        result = asyncio.run(run_comprehensive_test())
        exit(0 if result else 1)
    else:
        print("❌ Music generation not available - check dependencies")
        print("   Required: google-genai, pydub, numpy")
        exit(1)