import os
import wave
import glob
import re
try:
    import tiktoken  # type: ignore
except ImportError:
    tiktoken = None  # type: ignore

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except ImportError:
    try:
        import google.generativeai as genai  # type: ignore
        types = genai.types  # type: ignore
    except ImportError:
        genai = None  # type: ignore
        types = None  # type: ignore

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    def load_dotenv(*args, **kwargs):  # type: ignore
        pass

# Removed PyDub dependency - using numpy/soundfile only

try:
    import numpy as np
    import soundfile as sf
    NUMPY_SOUNDFILE_AVAILABLE = True
except ImportError:
    NUMPY_SOUNDFILE_AVAILABLE = False
    np = None
    sf = None

def load_config():
    """Load configuration from .env files in order of priority."""
    config_locations = [
        '.env',
        os.path.expanduser('~/.config/ai-audiobook-generator/.env'),
        os.path.expanduser('~/.ai-audiobook-generator.env'),
    ]
    
    loaded = False
    for env_file in config_locations:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            loaded = True
            print(f"Loaded configuration from: {env_file}")
            break
    
    if not loaded:
        print("No .env file found. Trying environment variables...")

def read_file_content(file_path):
    """Read file content."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM data to a wave file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

try:
    if tiktoken:
        tokenizer = tiktoken.get_encoding("cl100k_base")
    else:
        tokenizer = None
except Exception:
    tokenizer = None

def count_tokens(text: str) -> int:
    """Count actual tokens in text using tiktoken."""
    if tokenizer is None:
        return max(1, len(text) // 4)
    
    try:
        return len(tokenizer.encode(text))
    except Exception:
        return max(1, len(text) // 4)

def chunk_text_smartly(text: str, max_tokens: int = 30000) -> list[str]:
    """Split text into chunks that stay under the token limit, breaking at natural boundaries."""
    chunks = []
    current_chunk = ""
    
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph
        
        if count_tokens(test_chunk) <= max_tokens:
            current_chunk = test_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                if count_tokens(paragraph) > max_tokens:
                    para_chunks = chunk_text_smartly(paragraph, max_tokens)
                    chunks.extend(para_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    test_sentence_chunk = temp_chunk + (' ' if temp_chunk else '') + sentence
                    
                    if count_tokens(test_sentence_chunk) <= max_tokens:
                        temp_chunk = test_sentence_chunk
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            if count_tokens(sentence) > max_tokens:
                                sent_chunks = chunk_text_smartly(sentence, max_tokens)
                                chunks.extend(sent_chunks)
                                temp_chunk = ""
                            else:
                                temp_chunk = sentence
                        else:
                            words = sentence.split()
                            word_chunk = ""
                            
                            for word in words:
                                test_word_chunk = word_chunk + (' ' if word_chunk else '') + word
                                
                                if count_tokens(test_word_chunk) <= max_tokens:
                                    word_chunk = test_word_chunk
                                else:
                                    if word_chunk:
                                        chunks.append(word_chunk.strip())
                                        word_chunk = word
                                    else:
                                        if count_tokens(word) > max_tokens:
                                            char_chunk = ""
                                            for char in word:
                                                test_char_chunk = char_chunk + char
                                                if count_tokens(test_char_chunk) <= max_tokens:
                                                    char_chunk = test_char_chunk
                                                else:
                                                    if char_chunk:
                                                        chunks.append(char_chunk)
                                                        char_chunk = char
                                                    else:
                                                        chunks.append(char)
                                            if char_chunk:
                                                word_chunk = char_chunk
                                        else:
                                            word_chunk = word
                            
                            if word_chunk:
                                temp_chunk = word_chunk
                
                if temp_chunk:
                    current_chunk = temp_chunk
    
    if current_chunk:
        if count_tokens(current_chunk) > max_tokens:
            final_chunks = chunk_text_smartly(current_chunk, max_tokens)
            chunks.extend(final_chunks)
        else:
            chunks.append(current_chunk.strip())
    
    verified_chunks = []
    for chunk in chunks:
        if chunk.strip():
            if count_tokens(chunk) > max_tokens:
                words = chunk.split()
                char_chunk = ""
                for word in words:
                    test_chunk = char_chunk + (' ' if char_chunk else '') + word
                    if count_tokens(test_chunk) <= max_tokens:
                        char_chunk = test_chunk
                    else:
                        if char_chunk:
                            verified_chunks.append(char_chunk.strip())
                        char_chunk = word
                if char_chunk:
                    verified_chunks.append(char_chunk.strip())
            else:
                verified_chunks.append(chunk.strip())
    
    return verified_chunks

def generate_chapter_audio(chapter_text, output_file, model="gemini-2.5-flash-preview-tts", custom_prompt=None, safe_chunk_mode=False):
    """Generate TTS audio for a chapter, automatically chunking if needed."""
    from src.utils.rate_limiter import generate_audio_with_quota_awareness
    
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    NARRATOR_VOICE = os.getenv('NARRATOR_VOICE', 'Charon')
    ENABLE_BACKGROUND_MUSIC = os.getenv('ENABLE_BACKGROUND_MUSIC', 'false').lower() == 'true'
    PER_CHUNK_MUSIC = os.getenv('PER_CHUNK_MUSIC', 'false').lower() == 'true'
    
    # Debug logging for music settings
    print(f"DEBUG: ENABLE_BACKGROUND_MUSIC = {ENABLE_BACKGROUND_MUSIC}")
    print(f"DEBUG: PER_CHUNK_MUSIC = {PER_CHUNK_MUSIC}")
    
    if not GOOGLE_API_KEY:
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")
    
    effective_limit = 30000
    if safe_chunk_mode:
        effective_limit = min(30000, 1800)
    
    token_count = count_tokens(chapter_text)
    
    if token_count <= effective_limit:
        print(f"Chapter size: {token_count:,} tokens - processing as single chunk")
        if custom_prompt and custom_prompt.strip():
            tts_prompt = custom_prompt.strip() + "\n\n" + chapter_text
        else:
            tts_prompt = "Use a professional, engaging audiobook narration style with appropriate pacing and emotion.\n\n" + chapter_text
        
        if not genai:
            raise ImportError("Google Genai library not available")
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        audio_data = generate_audio_with_quota_awareness(
            client,
            tts_prompt,
            NARRATOR_VOICE,
            model=model,
            max_retries=3
        )
        
        wave_file(output_file, audio_data)
        
        # Apply per-chunk music if enabled
        if ENABLE_BACKGROUND_MUSIC and PER_CHUNK_MUSIC:
            print("Per-chunk music enabled - applying music to individual chunk...")
            try:
                output_file = apply_per_chunk_music(output_file)
                print(f"Successfully applied per-chunk music to: {output_file}")
            except Exception as e:
                print(f"ERROR: Failed to apply per-chunk music: {e}")
                import traceback
                traceback.print_exc()
        elif ENABLE_BACKGROUND_MUSIC:
            print("Background music enabled but per-chunk disabled - will apply at end")
        else:
            print("Background music disabled")
        
        return output_file
    
    print(f"Chapter size: {token_count:,} tokens - splitting into chunks")
    chunks = chunk_text_smartly(chapter_text, max_tokens=effective_limit)
    print(f"Split into {len(chunks)} chunks")
    
    chunk_files = []
    base_name = output_file.replace('.wav', '')
    
    for i, chunk in enumerate(chunks, 1):
        chunk_output = f"{base_name}_chunk_{i:03d}.wav"
        chunk_tokens = count_tokens(chunk)
        print(f"Processing chunk {i}/{len(chunks)} ({chunk_tokens:,} tokens)")
        
        if custom_prompt and custom_prompt.strip():
            tts_prompt = custom_prompt.strip() + "\n\n" + chunk
        else:
            tts_prompt = "Use a professional, engaging audiobook narration style with appropriate pacing and emotion.\n\n" + chunk
        
        if not genai:
            raise ImportError("Google Genai library not available")
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        audio_data = generate_audio_with_quota_awareness(
            client,
            tts_prompt,
            NARRATOR_VOICE,
            model=model,
            max_retries=3
        )
        
        wave_file(chunk_output, audio_data)
        
        # Apply per-chunk music if enabled
        if ENABLE_BACKGROUND_MUSIC and PER_CHUNK_MUSIC:
            print(f"Per-chunk music enabled - applying music to chunk {i}...")
            try:
                chunk_output = apply_per_chunk_music(chunk_output)
                print(f"Successfully applied per-chunk music to chunk {i}: {chunk_output}")
            except Exception as e:
                print(f"ERROR: Failed to apply per-chunk music to chunk {i}: {e}")
                import traceback
                traceback.print_exc()
        elif ENABLE_BACKGROUND_MUSIC:
            print(f"Background music enabled but per-chunk disabled for chunk {i} - will apply at end")
        else:
            print(f"Background music disabled for chunk {i}")
        
        chunk_files.append(chunk_output)
    
    return combine_audio_chunks(chunk_files, output_file)

def combine_audio_chunks(chunk_files, output_file):
    """Combine multiple audio chunks into a single file using numpy + soundfile."""
    print(f"Combining {len(chunk_files)} audio chunks...")
    
    if not NUMPY_SOUNDFILE_AVAILABLE or np is None or sf is None:
        raise ImportError("numpy and soundfile are required for audio processing")
    
    combined_audio = []
    sample_rate = None
    
    for i, chunk_file in enumerate(chunk_files, 1):
        print(f"Adding chunk {i}/{len(chunk_files)}: {chunk_file}")
        
        # Read audio file
        audio_data, sr = sf.read(chunk_file)
        
        # Set sample rate from first file
        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            # Resample if needed (simple approach - could be improved)
            print(f"Warning: Sample rate mismatch in {chunk_file} ({sr} vs {sample_rate})")
        
        # Convert to stereo if mono
        if audio_data.ndim == 1:
            audio_data = np.column_stack([audio_data, audio_data])
        
        # Add to combined audio
        combined_audio.append(audio_data)
        
        # Add pause between chunks (except after last chunk)
        if i < len(chunk_files):
            pause_samples = int(0.5 * sample_rate)  # 500ms pause
            pause = np.zeros((pause_samples, 2))
            combined_audio.append(pause)
    
    # Concatenate all audio segments
    final_audio = np.concatenate(combined_audio, axis=0)
    
    # Write output file
    sf.write(output_file, final_audio, sample_rate)
    print(f"Combined chapter audio saved to {output_file}")
    
    # Clean up temporary files
    for chunk_file in chunk_files:
        try:
            os.remove(chunk_file)
            print(f"Cleaned up temporary chunk: {chunk_file}")
        except Exception as e:
            print(f"Warning: Could not clean up {chunk_file}: {e}")
    
    return output_file

# PyDub fallback functions removed - numpy/soundfile only

def combine_chapters(audio_files, output_file, enable_background_music=None):
    """Combine multiple chapter audio files into a single audiobook using numpy + soundfile."""
    print("Combining chapters into complete audiobook...")

    if not NUMPY_SOUNDFILE_AVAILABLE or np is None or sf is None:
        raise ImportError("numpy and soundfile are required for audio processing")

    combined_audio_list = []
    sample_rate = None

    for audio_file in audio_files:
        print(f"Adding {audio_file}")
        try:
            # Read audio file
            audio_data, sr = sf.read(audio_file)

            # Set sample rate from first file
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                print(f"Warning: Sample rate mismatch in {audio_file} ({sr} vs {sample_rate}) - skipping file")
                continue

            # Convert to stereo if mono
            if audio_data.ndim == 1:
                audio_data = np.column_stack([audio_data, audio_data])
            
            # Ensure it is stereo
            if audio_data.shape[1] != 2:
                print(f"Warning: Non-stereo audio in {audio_file} - skipping file")
                continue

            combined_audio_list.append(audio_data)

        except Exception as e:
            print(f"Warning: Could not process {audio_file}: {e}")
            continue

    if not combined_audio_list or sample_rate is None:
        print("Error: No valid audio files to combine or sample rate not detected.")
        return

    # Add pauses between chapters
    final_audio_segments = []
    for i, segment in enumerate(combined_audio_list):
        final_audio_segments.append(segment)
        if i < len(combined_audio_list) - 1:
            pause_samples = int(2.0 * sample_rate)
            pause = np.zeros((pause_samples, 2), dtype=segment.dtype)
            final_audio_segments.append(pause)

    # Concatenate all audio segments
    final_audio = np.concatenate(final_audio_segments, axis=0)

    # Check if background music is enabled - use direct parameter if provided, otherwise environment
    if enable_background_music is None:
        enable_background_music = os.getenv('ENABLE_BACKGROUND_MUSIC', 'false').lower() == 'true'
    
    # Check if per-chunk music is enabled
    per_chunk_music = os.getenv('PER_CHUNK_MUSIC', 'false').lower() == 'true'
    
    if enable_background_music and not per_chunk_music:
        print("Background music enabled - generating and mixing music...")
        final_audio = add_background_music_to_audiobook_numpy(final_audio, sample_rate)
    elif enable_background_music and per_chunk_music:
        print("Per-chunk music mode - skipping final music application (music already applied to individual chunks)")

    # Write output file
    sf.write(output_file, final_audio, sample_rate)
    print(f"Complete audiobook saved to {output_file}")

# PyDub fallback functions removed - numpy/soundfile only

def add_background_music_to_audiobook_numpy(audiobook_audio, sample_rate):
    """Generate and mix background music with audiobook using numpy + soundfile."""
    try:
        if not NUMPY_SOUNDFILE_AVAILABLE or np is None or sf is None:
            print("Warning: Numpy/soundfile not available - skipping background music")
            return audiobook_audio
        
        # Import music generator - use the async convenience function
        from src.music.generator import generate_background_music, MusicMood, MusicGenre
        
        # Get music settings from environment
        music_volume = float(os.getenv('BACKGROUND_MUSIC_VOLUME', '0.15'))
        music_mood = os.getenv('BACKGROUND_MUSIC_MOOD', 'ambient')
        music_genre = os.getenv('BACKGROUND_MUSIC_GENRE', 'ambient')
        
        # Calculate total duration with 3s buffer on each side (6s total)
        audiobook_duration_s = len(audiobook_audio) / sample_rate
        buffer_duration_s = 3.0  # 3 seconds
        total_music_duration_s = audiobook_duration_s + (2 * buffer_duration_s)
        
        print(f"Audiobook duration: {audiobook_duration_s:.1f}s")
        print(f"Generating background music for: {total_music_duration_s:.1f}s (with 3s buffers)")
        
        # Generate background music using the async convenience function
        import asyncio
        
        async def generate_music():
            return await generate_background_music(
                mood=MusicMood(music_mood),
                genre=MusicGenre(music_genre),
                duration_minutes=total_music_duration_s / 60,  # Convert to minutes
                api_key=os.getenv('GOOGLE_API_KEY')
            )
        
        # Run the async music generation - handle existing event loop
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If there's already a loop running, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, generate_music())
                music_file_path = future.result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            music_file_path = asyncio.run(generate_music())
        
        if not music_file_path or not os.path.exists(music_file_path):
            print("Warning: Music generation failed - continuing without background music")
            return audiobook_audio
        
        try:
            # Load the generated music file
            music_audio, music_sr = sf.read(music_file_path)
            
            # Ensure music matches audiobook sample rate
            if music_sr != sample_rate:
                print(f"Warning: Music sample rate mismatch ({music_sr} vs {sample_rate})")
                # Simple resampling approach - could be improved
                resample_ratio = sample_rate / music_sr
                new_length = int(len(music_audio) * resample_ratio)
                if music_audio.ndim == 1:
                    music_audio = np.interp(np.linspace(0, len(music_audio), new_length),
                                          np.arange(len(music_audio)), music_audio)
                else:
                    music_audio = np.array([np.interp(np.linspace(0, len(music_audio), new_length),
                                                    np.arange(len(music_audio)), music_audio[:, i])
                                          for i in range(music_audio.shape[1])]).T
            
            # Ensure music is in stereo
            if music_audio.ndim == 1:
                music_audio = np.column_stack([music_audio, music_audio])
            
            # Trim music to exact length needed
            target_samples = int(total_music_duration_s * sample_rate)
            if len(music_audio) > target_samples:
                music_audio = music_audio[:target_samples]
            elif len(music_audio) < target_samples:
                # Extend with zeros if needed
                padding = target_samples - len(music_audio)
                music_audio = np.vstack([music_audio, np.zeros((padding, 2))])
            
            # Apply fade-in and fade-out (2 second fades)
            fade_samples = int(2.0 * sample_rate)
            if len(music_audio) > 2 * fade_samples:
                # Fade in
                fade_in = np.linspace(0, 1, fade_samples)
                music_audio[:fade_samples, 0] *= fade_in
                music_audio[:fade_samples, 1] *= fade_in
                
                # Fade out
                fade_out = np.linspace(1, 0, fade_samples)
                music_audio[-fade_samples:, 0] *= fade_out
                music_audio[-fade_samples:, 1] *= fade_out
            
            # Apply volume adjustment - reduce volume significantly for background music
            music_audio = music_audio * music_volume
            
            print(f"Music volume adjusted to {music_volume*100:.1f}%")
            
            # Create silence buffers for the audiobook
            buffer_samples = int(buffer_duration_s * sample_rate)
            buffer_silence = np.zeros((buffer_samples, 2))
            
            # Add buffers to audiobook: 3s silence + audiobook + 3s silence
            buffered_audiobook = np.vstack([buffer_silence, audiobook_audio, buffer_silence])
            
            # Mix the music with the buffered audiobook
            # Ensure both arrays have the same length
            min_length = min(len(music_audio), len(buffered_audiobook))
            final_audio = music_audio[:min_length] + buffered_audiobook[:min_length]
            
            # Prevent clipping
            max_val = np.max(np.abs(final_audio))
            if max_val > 1.0:
                final_audio = final_audio / max_val * 0.95
                print(f"Applied normalization to prevent clipping (peak was {max_val:.2f})")
            
            print("✅ Background music successfully mixed with audiobook")
            print(f"Final duration: {len(final_audio)/sample_rate:.1f}s")
            
            return final_audio
            
        finally:
            # Clean up generated music file
            try:
                os.unlink(music_file_path)
                print(f"Cleaned up temporary music file: {music_file_path}")
            except Exception:
                pass
        
    except Exception as e:
        print(f"Warning: Could not add background music: {e}")
        print("Continuing without background music...")
        return audiobook_audio
def apply_per_chunk_music(audio_file):
    """Apply background music to a single audio chunk file."""
    try:
        # Import music generator
        from src.music.generator import generate_background_music, MusicMood, MusicGenre
        
        # Get music settings from environment
        music_volume = float(os.getenv('BACKGROUND_MUSIC_VOLUME', '0.15'))
        music_mood = os.getenv('BACKGROUND_MUSIC_MOOD', 'ambient')
        music_genre = os.getenv('BACKGROUND_MUSIC_GENRE', 'ambient')
        
        # Load the chunk audio to get duration using soundfile
        if not NUMPY_SOUNDFILE_AVAILABLE or sf is None:
            # Fallback using wave module to get duration
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration_seconds = frames / float(rate)
        else:
            try:
                audio_data, sample_rate = sf.read(audio_file)
                duration_seconds = len(audio_data) / sample_rate
            except Exception:
                # Fallback using wave module to get duration
                with wave.open(audio_file, 'rb') as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration_seconds = frames / float(rate)
        
        print(f"Generating background music for chunk duration: {duration_seconds:.1f}s")
        
        # Generate background music using the async convenience function
        import asyncio
        
        async def generate_music():
            return await generate_background_music(
                mood=MusicMood(music_mood),
                genre=MusicGenre(music_genre),
                duration_minutes=duration_seconds / 60,  # Convert to minutes
                api_key=os.getenv('GOOGLE_API_KEY')
            )
        
        # Run the async music generation
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, generate_music())
                music_file_path = future.result()
        except RuntimeError:
            music_file_path = asyncio.run(generate_music())
        
        if not music_file_path or not os.path.exists(music_file_path):
            print("Warning: Music generation failed - returning original chunk")
            return audio_file
        
        # Use numpy/soundfile for mixing
        if not NUMPY_SOUNDFILE_AVAILABLE or sf is None or np is None:
            print("Warning: numpy/soundfile not available - cannot apply per-chunk music")
        else:
            try:
                # Load the audio file
                audio_data, sample_rate = sf.read(audio_file)
                
                # Load the music file
                music_data, music_sample_rate = sf.read(music_file_path)
                
                # Resample music if needed
                if music_sample_rate != sample_rate:
                    try:
                        from scipy import signal
                        music_data = signal.resample(music_data, int(len(music_data) * sample_rate / music_sample_rate))
                    except ImportError:
                        print("Warning: scipy not available for resampling")
                
                # Ensure both are same length
                min_length = min(len(audio_data), len(music_data))
                audio_data = audio_data[:min_length]
                music_data = music_data[:min_length]
                
                # Ensure both have same number of channels
                if audio_data.ndim == 1 and music_data.ndim == 2:
                    audio_data = np.column_stack((audio_data, audio_data))
                elif audio_data.ndim == 2 and music_data.ndim == 1:
                    music_data = np.column_stack((music_data, music_data))
                elif audio_data.ndim == 2 and music_data.ndim == 2:
                    if audio_data.shape[1] != music_data.shape[1]:
                        if music_data.shape[1] == 1:
                            music_data = np.repeat(music_data, audio_data.shape[1], axis=1)
                        elif audio_data.shape[1] == 1:
                            audio_data = np.repeat(audio_data, music_data.shape[1], axis=1)
                
                # Mix audio with background music at specified volume
                mixed_audio = audio_data + (music_data * music_volume)
                
                # Normalize to prevent clipping
                max_val = np.max(np.abs(mixed_audio))
                if max_val > 1.0:
                    mixed_audio = mixed_audio / max_val
                
                # Save mixed audio
                sf.write(audio_file, mixed_audio, sample_rate)
                print(f"Per-chunk music applied to: {audio_file}")
                
            except Exception as e:
                print(f"Error applying per-chunk music: {e}")
        
        # Clean up music file
        try:
            if music_file_path:
                os.unlink(music_file_path)
        except Exception:
            pass
        
        return audio_file
        
    except Exception as e:
        print(f"Warning: Could not apply per-chunk music: {e}")
        return audio_file


# Old PyDub background music function removed - use numpy implementation instead

def self_test():
    """Run a self-test of the core functions."""
    print("🧪 Running self-test for core functions...")
    
    # Prerequisite check
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ Self-test failed: GOOGLE_API_KEY is not set.")
        return False

    # Test TTS Generation
    print("\n🎤 Testing TTS generation...")
    test_text = "This is a self-test of the text-to-speech audio generation function."
    tts_output_file = "self_test_tts.wav"
    try:
        generate_chapter_audio(test_text, tts_output_file)
        if os.path.exists(tts_output_file):
            print(f"✅ TTS generation successful. Output: {tts_output_file}")
            os.remove(tts_output_file)
        else:
            print("❌ TTS generation failed: Output file not created.")
            return False
    except Exception as e:
        print(f"❌ TTS generation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test Music Generation and Combination
    print("\n🎵 Testing background music combination...")
    os.environ['ENABLE_BACKGROUND_MUSIC'] = 'true'
    os.environ['BACKGROUND_MUSIC_VOLUME'] = '0.1'
    os.environ['BACKGROUND_MUSIC_MOOD'] = 'peaceful'
    os.environ['BACKGROUND_MUSIC_GENRE'] = 'ambient'
    
    # Create a dummy audio file to combine with
    dummy_tts_file = "dummy_tts_for_music_test.wav"
    try:
        # Create a 5-second silent WAV file using numpy/soundfile
        if NUMPY_SOUNDFILE_AVAILABLE and sf is not None and np is not None:
            sample_rate = 24000
            duration = 5.0
            samples = int(sample_rate * duration)
            silence = np.zeros(samples, dtype=np.float32)
            sf.write(dummy_tts_file, silence, sample_rate)
            print("✅ Created dummy TTS file for music test.")
        else:
            print("❌ numpy/soundfile not available - cannot create dummy TTS file")
            return None

        combination_output_file = "self_test_combination.wav"
        combine_chapters([dummy_tts_file], combination_output_file, enable_background_music=True)

        if os.path.exists(combination_output_file):
            print(f"✅ Music combination successful. Output: {combination_output_file}")
            # Check if file size is reasonable
            if os.path.getsize(combination_output_file) > os.path.getsize(dummy_tts_file):
                 print("✅ Final file size indicates music was added.")
            else:
                 print("⚠️ Warning: Final file size is not larger. Music may not have been added.")
            os.remove(combination_output_file)
        else:
            print("❌ Music combination failed: Output file not created.")
            os.remove(dummy_tts_file)
            return False
        
        os.remove(dummy_tts_file)

    except Exception as e:
        print(f"❌ Music combination failed with error: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(dummy_tts_file):
            os.remove(dummy_tts_file)
        return False

    print("\n🎉 Self-test for core functions passed!")
    return True

if __name__ == '__main__':
    # This block allows the script to be run standalone for testing by fixing the import paths.
    import sys
    import os
    # We need to add the project root to the path so we can import `src`
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from dotenv import load_dotenv
    
    # The .env file is in the `src` directory, which is a sibling of `core`
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment from: {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")

    self_test()