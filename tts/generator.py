"""
TTS generation module.

Handles all text-to-speech generation using Google Gemini APIs,
including chunking, retry logic, and audio quality validation.
"""

import os
import wave
import time
from typing import Optional, Callable, List
from dataclasses import dataclass

from ..core.config import TTSConfig
from ..utils.text_processing import count_tokens, chunk_text_smartly
from ..utils.rate_limiter import generate_audio_with_quota_awareness
from ..utils.api_retry_handler import MaxRetriesExceededError, HTTPAPIError

try:
    from google import genai
    from google.genai import types
except ImportError:
    try:
        import google.generativeai as genai
        types = genai.types
    except ImportError:
        genai = None
        types = None

try:
    from pydub import AudioSegment
except ImportError:
    class AudioSegment:
        @staticmethod
        def empty():
            raise ImportError("Pydub library not available. Please install pydub package.")
        
        @staticmethod
        def from_wav(file_path):
            raise ImportError("Pydub library not available. Please install pydub package.")
        
        @staticmethod
        def silent(duration):
            raise ImportError("Pydub library not available. Please install pydub package.")


class TTSGenerator:
    """
    Text-to-speech generator using Google Gemini APIs.
    
    Handles chunking, retry logic, corruption detection, and background music mixing.
    """
    
    def __init__(self, config: TTSConfig):
        """
        Initialize TTS generator.
        
        Args:
            config: TTS configuration
        """
        self.config = config
        self.current_chunk_limit = config.chunk_limit
        self.chunk_reduction_steps = [25000, 20000, 15000, 10000, 5000]
        self.chunk_step_index = 0
        
        if not genai:
            raise ImportError("Google Genai library not available. Please install google-genai package.")
    
    def wave_file(self, filename: str, pcm: bytes, channels: int = 1, 
                  rate: int = 24000, sample_width: int = 2):
        """Save PCM data to a wave file."""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)
    
    def reduce_chunk_limit(self) -> bool:
        """Reduce the global chunk limit when server errors occur."""
        if self.chunk_step_index < len(self.chunk_reduction_steps):
            old_limit = self.current_chunk_limit
            self.current_chunk_limit = self.chunk_reduction_steps[self.chunk_step_index]
            self.chunk_step_index += 1
            print(f"🔧 Reducing chunk limit from {old_limit:,} to {self.current_chunk_limit:,} tokens due to server errors")
            return True
        return False
    
    def generate_chunk_audio(self, chunk_text: str, chunk_output_file: str, 
                           custom_prompt: Optional[str] = None, 
                           quality_detector=None, music_generator=None,
                           progress_callback: Optional[Callable] = None,
                           _retry_count: int = 0) -> str:
        """
        Generate TTS audio for a single text chunk.
        
        Args:
            chunk_text: Text content to convert
            chunk_output_file: Output file path
            custom_prompt: Optional custom narration prompt
            quality_detector: Optional quality detector for corruption checking
            music_generator: Optional music generator for background music
            progress_callback: Optional callback for progress updates
            _retry_count: Internal retry counter
            
        Returns:
            str: Path to generated audio file
        """
        print(f"🔍 DEBUG: Starting chunk audio generation")
        print(f"🔍 DEBUG: Model: {self.config.model}")
        print(f"🔍 DEBUG: Output file: {chunk_output_file}")
        print(f"🔍 DEBUG: Safe chunk mode: {self.config.safe_chunk_mode}")
        print(f"🔍 DEBUG: Custom prompt provided: {bool(custom_prompt and custom_prompt.strip())}")
        print(f"🔍 DEBUG: Chunk length: {len(chunk_text)} characters")
        print(f"🔍 DEBUG: Chunk tokens: {count_tokens(chunk_text):,}")
        
        # Determine effective chunk limit based on safe mode
        effective_limit = self.current_chunk_limit
        if self.config.safe_chunk_mode:
            effective_limit = min(self.current_chunk_limit, self.config.safe_chunk_limit)
            print(f"🛡️ Safe chunk mode active: Using {effective_limit:,} token limit for optimal performance")
        
        # Check if chunk exceeds effective limit
        if count_tokens(chunk_text) > effective_limit:
            print(f"⚠️ Chunk ({count_tokens(chunk_text):,} tokens) exceeds effective limit ({effective_limit:,}), re-chunking...")
            # Re-chunk with effective limit
            sub_chunks = chunk_text_smartly(chunk_text, effective_limit)
            print(f"🔍 DEBUG: Split into {len(sub_chunks)} sub-chunks")
            
            # Generate audio for each sub-chunk and combine
            sub_chunk_files = []
            base_name = chunk_output_file.replace('.wav', '')
            
            for i, sub_chunk in enumerate(sub_chunks, 1):
                sub_output = f"{base_name}_sub_{i:02d}.wav"
                print(f"🔍 DEBUG: Processing sub-chunk {i}/{len(sub_chunks)}: {count_tokens(sub_chunk):,} tokens")
                sub_file = self.generate_chunk_audio(
                    sub_chunk, sub_output, custom_prompt, quality_detector, 
                    music_generator, progress_callback
                )
                sub_chunk_files.append(sub_file)
            
            # Combine sub-chunks
            print(f"🔍 DEBUG: Combining {len(sub_chunk_files)} sub-chunks into final output")
            return self.combine_audio_chunks(sub_chunk_files, chunk_output_file, music_generator)
        
        # Build TTS prompt
        if custom_prompt and custom_prompt.strip():
            tts_prompt = f"{custom_prompt.strip()}: {chunk_text}"
            print(f"🔍 DEBUG: Applied custom prompt: '{custom_prompt[:50]}...'")
        else:
            tts_prompt = f"Narrate this audiobook chapter in a professional, engaging style: {chunk_text}"
            print(f"🔍 DEBUG: Using default prompt format")
        
        print(f"🔍 DEBUG: Final TTS prompt length: {len(tts_prompt)} characters, {count_tokens(tts_prompt):,} tokens")
        
        def progress_update(message):
            if progress_callback:
                progress_callback(message)
            print(f"🎤 {message}")
        
        try:
            print(f"🔍 DEBUG: Initializing Gemini client...")
            client = genai.Client(api_key=self.config.api_key)
            print(f"🔍 DEBUG: Client initialized successfully")
            
            # Generate audio using REST API with proper TTS prompting
            audio_data = generate_audio_with_quota_awareness(
                client,
                tts_prompt,
                self.config.narrator_voice,
                model=self.config.model,
                max_retries=3,
                progress_callback=progress_update
            )
            
            print(f"🔍 DEBUG: Audio generation completed, received {len(audio_data)} bytes")
            
            # Save audio to file
            print(f"🔍 DEBUG: Saving audio to file: {chunk_output_file}")
            self.wave_file(chunk_output_file, audio_data)
            print(f"Chunk audio saved to {chunk_output_file}")
            
            # Audio corruption detection
            if quality_detector:
                print(f"🔍 DEBUG: Running corruption detection on {chunk_output_file}")
                try:
                    is_corrupted = quality_detector.quick_corruption_check(chunk_output_file)
                    if is_corrupted:
                        print(f"🚨 CORRUPTION DETECTED in {chunk_output_file}")
                        
                        # Check if we should retry
                        if _retry_count < quality_detector.config.retry_attempts:
                            print(f"🔄 Regenerating due to API corruption (attempt {_retry_count + 1}/{quality_detector.config.retry_attempts})...")
                            
                            # Remove corrupted file
                            try:
                                os.remove(chunk_output_file)
                                print(f"🗑️ Removed corrupted file: {chunk_output_file}")
                            except Exception as e:
                                print(f"⚠️ Could not remove corrupted file: {e}")
                            
                            # Retry with progressive fallback strategy
                            if quality_detector.config.auto_split and count_tokens(chunk_text) > 1000:
                                print(f"🔧 Large chunk detected, reducing size for retry...")
                                if not self.config.safe_chunk_mode:
                                    print(f"🛡️ Enabling safe chunk mode for retry")
                                    # Create temporary config with safe mode enabled
                                    temp_config = TTSConfig(
                                        api_key=self.config.api_key,
                                        narrator_voice=self.config.narrator_voice,
                                        model=self.config.model,
                                        chunk_limit=self.config.chunk_limit,
                                        safe_chunk_mode=True,
                                        safe_chunk_limit=self.config.safe_chunk_limit
                                    )
                                    temp_generator = TTSGenerator(temp_config)
                                    return temp_generator.generate_chunk_audio(
                                        chunk_text, chunk_output_file, custom_prompt, 
                                        quality_detector, music_generator, progress_callback, _retry_count + 1
                                    )
                                else:
                                    # Already in safe mode, try splitting the chunk
                                    smaller_chunks = chunk_text_smartly(chunk_text, max_tokens=600)
                                    if len(smaller_chunks) > 1:
                                        print(f"📦 Splitting into {len(smaller_chunks)} smaller chunks for retry")
                                        # Generate and combine smaller chunks
                                        sub_chunk_files = []
                                        base_name = chunk_output_file.replace('.wav', '')
                                        
                                        for i, sub_chunk in enumerate(smaller_chunks, 1):
                                            sub_output = f"{base_name}_retry_{i:02d}.wav"
                                            print(f"🔄 Generating retry chunk {i}/{len(smaller_chunks)}")
                                            sub_file = self.generate_chunk_audio(
                                                sub_chunk, sub_output, custom_prompt, 
                                                quality_detector, music_generator, progress_callback, 0
                                            )
                                            sub_chunk_files.append(sub_file)
                                        
                                        # Combine sub-chunks
                                        return self.combine_audio_chunks(sub_chunk_files, chunk_output_file, music_generator)
                            
                            # Simple retry for smaller chunks
                            print(f"🔄 Retrying generation with same parameters...")
                            return self.generate_chunk_audio(
                                chunk_text, chunk_output_file, custom_prompt, 
                                quality_detector, music_generator, progress_callback, _retry_count + 1
                            )
                        else:
                            print(f"❌ Maximum retry attempts ({quality_detector.config.retry_attempts}) reached for {chunk_output_file}")
                            print(f"⚠️ Proceeding with potentially corrupted audio")
                    else:
                        print(f"✅ Audio quality check passed for {chunk_output_file}")
                except Exception as e:
                    print(f"⚠️ Audio quality check failed: {e}")
                    print(f"📋 Proceeding with generated audio (detection error)")
            
            return chunk_output_file
            
        except Exception as e:
            error_str = str(e)
            print(f"🔍 DEBUG: Exception caught: {type(e).__name__}")
            print(f"🔍 DEBUG: Exception message: {error_str}")
            
            # Handle server errors with adaptive chunking
            if "500" in error_str or "502" in error_str or "timeout" in error_str.lower():
                print(f"🔧 Server error detected: {error_str}")
                if self.reduce_chunk_limit():
                    print(f"🔄 Retrying with smaller chunks...")
                    return self.generate_chunk_audio(
                        chunk_text, chunk_output_file, custom_prompt, 
                        quality_detector, music_generator, progress_callback
                    )
            
            # Re-raise if not a server error or can't reduce further
            print(f"❌ API Error: {error_str}")
            raise
    
    def combine_audio_chunks(self, chunk_files: List[str], output_file: str, 
                           music_generator=None) -> str:
        """Combine multiple audio chunks into a single file with optional background music."""
        print(f"Combining {len(chunk_files)} audio chunks...")
        combined = AudioSegment.empty()
        
        for i, chunk_file in enumerate(chunk_files, 1):
            print(f"Adding chunk {i}/{len(chunk_files)}: {chunk_file}")
            audio = AudioSegment.from_wav(chunk_file)
            
            # Ensure stereo
            if audio.channels == 1:
                audio = audio.set_channels(2)
            
            # Mix with background music if enabled
            if music_generator:
                duration_seconds = len(audio) / 1000.0  # Convert ms to seconds
                audio = self.mix_audio_with_background_music(audio, music_generator, duration_seconds)
            
            # Add the chunk audio
            combined += audio
            
            # Add a brief pause between chunks (0.5 seconds)
            if i < len(chunk_files):
                pause = AudioSegment.silent(duration=500)
                combined += pause
        
        # Export combined audio
        combined.export(output_file, format="wav")
        print(f"Combined chapter audio saved to {output_file}")
        
        # Clean up chunk files
        for chunk_file in chunk_files:
            try:
                os.remove(chunk_file)
                print(f"Cleaned up temporary chunk: {chunk_file}")
            except Exception as e:
                print(f"Warning: Could not clean up {chunk_file}: {e}")
        
        return output_file
    
    def mix_audio_with_background_music(self, speech_audio, music_generator, duration_seconds):
        """Mix speech audio with background music."""
        try:
            # Get background music for the duration needed
            fade_duration = getattr(music_generator.config, 'fade_duration', 2.0)
            music_duration = duration_seconds + fade_duration * 2
            music_chunk = music_generator.get_audio_chunk(music_duration)
            
            if not music_chunk:
                print("⚠️ No background music available, using speech only")
                return speech_audio
                
            # Convert music chunk to AudioSegment
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                music_generator.save_audio_chunk(music_chunk, temp_file.name)
                music_audio = AudioSegment.from_wav(temp_file.name)
                os.unlink(temp_file.name)
            
            # Ensure both audio segments have the same format
            if speech_audio.channels == 1:
                speech_audio = speech_audio.set_channels(2)
            if music_audio.channels == 1:
                music_audio = music_audio.set_channels(2)
                
            # Match sample rates
            if speech_audio.frame_rate != music_audio.frame_rate:
                music_audio = music_audio.set_frame_rate(speech_audio.frame_rate)
            
            # Adjust music volume
            volume = getattr(music_generator.config, 'volume', 0.2)
            music_audio = music_audio - (60 - int(volume * 60))  # Convert volume to dB reduction
            
            # Trim music to match speech duration + fade time
            speech_duration_ms = len(speech_audio)
            music_audio = music_audio[:speech_duration_ms + int(fade_duration * 2000)]
            
            # Add fade in/out to music
            fade_duration_ms = int(fade_duration * 1000)
            if len(music_audio) > fade_duration_ms * 2:
                music_audio = music_audio.fade_in(fade_duration_ms).fade_out(fade_duration_ms)
            
            # Mix speech and music
            mixed_audio = speech_audio.overlay(music_audio[:len(speech_audio)])
            
            print(f"🎵 Mixed {duration_seconds:.1f}s of speech with background music")
            return mixed_audio
            
        except Exception as e:
            print(f"⚠️ Failed to mix background music: {e}")
            return speech_audio
    
    def generate_chapter_audio(self, chapter_text: str, output_file: str, 
                             custom_prompt: Optional[str] = None, 
                             quality_detector=None, music_generator=None,
                             progress_callback: Optional[Callable] = None) -> str:
        """
        Generate TTS audio for a chapter, automatically chunking if needed.
        
        Args:
            chapter_text: Full chapter text
            output_file: Output file path
            custom_prompt: Optional custom narration prompt
            quality_detector: Optional quality detector
            music_generator: Optional music generator
            progress_callback: Optional progress callback
            
        Returns:
            str: Path to generated audio file
        """
        # Determine effective chunk limit based on safe mode
        effective_limit = self.current_chunk_limit
        if self.config.safe_chunk_mode:
            effective_limit = min(self.current_chunk_limit, self.config.safe_chunk_limit)
            print(f"🛡️ Safe chunk mode active: Using {effective_limit:,} token limit for optimal performance")
        
        # Check if chapter needs to be chunked
        token_count = count_tokens(chapter_text)
        
        if token_count <= effective_limit:
            # Small enough for single request
            print(f"Chapter size: {token_count:,} tokens - processing as single chunk (limit: {effective_limit:,})")
            return self.generate_chunk_audio(
                chapter_text, output_file, custom_prompt, 
                quality_detector, music_generator, progress_callback
            )
        
        # Chapter is too large, needs chunking
        print(f"Chapter size: {token_count:,} tokens - splitting into chunks (limit: {effective_limit:,})...")
        chunks = chunk_text_smartly(chapter_text, max_tokens=effective_limit)
        print(f"Split into {len(chunks)} chunks")
        
        # Process chunks with smart resume capability
        chunk_files = []
        base_name = output_file.replace('.wav', '')
        chunk_index = 0
        chunk_file_counter = 1
        
        while chunk_index < len(chunks):
            chunk = chunks[chunk_index]
            chunk_tokens = count_tokens(chunk)
            print(f"Processing chunk {chunk_index+1}/{len(chunks)} ({chunk_tokens:,} tokens)...")
            
            chunk_output = f"{base_name}_chunk_{chunk_file_counter:03d}.wav"
            
            try:
                chunk_file = self.generate_chunk_audio(
                    chunk, chunk_output, custom_prompt, 
                    quality_detector, music_generator, progress_callback
                )
                chunk_files.append(chunk_file)
                chunk_index += 1
                chunk_file_counter += 1
                
            except (MaxRetriesExceededError, HTTPAPIError) as e:
                # Check if this is a server error that warrants chunk size reduction
                if ("500" in str(e) or "502" in str(e) or "timeout" in str(e).lower()):
                    if self.reduce_chunk_limit():
                        print(f"🔧 Server error on chunk {chunk_index+1}, reducing limit to {self.current_chunk_limit:,} tokens")
                        
                        # Update effective limit after reduction
                        new_effective_limit = self.current_chunk_limit
                        if self.config.safe_chunk_mode:
                            new_effective_limit = min(self.current_chunk_limit, self.config.safe_chunk_limit)
                        
                        # Split the failing chunk with new smaller limit
                        sub_chunks = chunk_text_smartly(chunk, max_tokens=new_effective_limit)
                        print(f"📦 Split failing chunk into {len(sub_chunks)} sub-chunks")
                        
                        # Replace the failing chunk with sub-chunks in the list
                        chunks = chunks[:chunk_index] + sub_chunks + chunks[chunk_index+1:]
                        print(f"📋 Updated processing queue: now {len(chunks)} total chunks")
                        
                        # Continue from the same index (first sub-chunk)
                        continue
                    else:
                        print(f"❌ Cannot reduce chunk size further, re-raising error")
                        raise
                else:
                    # Not a server error or not retryable - re-raise
                    raise
        
        # Combine chunks into final chapter audio with background music
        return self.combine_audio_chunks(chunk_files, output_file, music_generator)