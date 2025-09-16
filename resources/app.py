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
    # Fallback for different import structure
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
        """Fallback load_dotenv function"""
        pass

try:
    from pydub import AudioSegment  # type: ignore
except ImportError:
    # Create a placeholder class for AudioSegment when not available
    class AudioSegment:  # type: ignore
        @staticmethod
        def empty():
            raise ImportError("Pydub library not available. Please install pydub package.")
        
        @staticmethod
        def from_wav(file_path):
            raise ImportError("Pydub library not available. Please install pydub package.")
        
        @staticmethod
        def silent(duration):
            raise ImportError("Pydub library not available. Please install pydub package.")
from project_state import ProjectStateManager
from api_retry_handler import ServiceUnavailableError, MaxRetriesExceededError, HTTPAPIError

# Import audio quality detection
try:
    from audio_quality_detector import AudioQualityDetector, quick_corruption_check
    AUDIO_QUALITY_DETECTION_AVAILABLE = True
except ImportError:
    AUDIO_QUALITY_DETECTION_AVAILABLE = False
    # Create fallback function
    def quick_corruption_check(file_path: str) -> bool:
        return False
    print("⚠️ Audio quality detection not available - install requirements: pip install librosa scipy soundfile")

# Import background music generation
try:
    from music_generator import MusicGenerator, MusicMood, MusicGenre, MusicConfig
    BACKGROUND_MUSIC_AVAILABLE = True
except ImportError:
    BACKGROUND_MUSIC_AVAILABLE = False
    MusicGenerator = None
    MusicMood = None
    MusicGenre = None
    MusicConfig = None
    print("⚠️ Background music generation not available - check google-genai package")

# Configuration for corruption detection
ENABLE_CORRUPTION_DETECTION = os.getenv('ENABLE_CORRUPTION_DETECTION', 'true').lower() == 'true'
CORRUPTION_RETRY_ATTEMPTS = int(os.getenv('CORRUPTION_RETRY_ATTEMPTS', '2'))
CORRUPTION_AUTO_SPLIT = os.getenv('CORRUPTION_AUTO_SPLIT', 'true').lower() == 'true'

# Configuration for background music
ENABLE_BACKGROUND_MUSIC = os.getenv('ENABLE_BACKGROUND_MUSIC', 'false').lower() == 'true'
BACKGROUND_MUSIC_VOLUME = float(os.getenv('BACKGROUND_MUSIC_VOLUME', '0.2'))
BACKGROUND_MUSIC_MOOD = os.getenv('BACKGROUND_MUSIC_MOOD', 'ambient')
BACKGROUND_MUSIC_GENRE = os.getenv('BACKGROUND_MUSIC_GENRE', 'ambient')
BACKGROUND_MUSIC_BPM = int(os.getenv('BACKGROUND_MUSIC_BPM', '80'))
BACKGROUND_MUSIC_DENSITY = float(os.getenv('BACKGROUND_MUSIC_DENSITY', '0.3'))
BACKGROUND_MUSIC_BRIGHTNESS = float(os.getenv('BACKGROUND_MUSIC_BRIGHTNESS', '0.4'))
BACKGROUND_MUSIC_GUIDANCE = float(os.getenv('BACKGROUND_MUSIC_GUIDANCE', '4.0'))
BACKGROUND_MUSIC_TEMPERATURE = float(os.getenv('BACKGROUND_MUSIC_TEMPERATURE', '1.0'))
BACKGROUND_MUSIC_CUSTOM_PROMPTS = [p.strip() for p in os.getenv('BACKGROUND_MUSIC_CUSTOM_PROMPTS', '').split(',') if p.strip()]
BACKGROUND_MUSIC_CONTINUOUS = os.getenv('BACKGROUND_MUSIC_CONTINUOUS', 'true').lower() == 'true'
BACKGROUND_MUSIC_FADE_DURATION = float(os.getenv('BACKGROUND_MUSIC_FADE_DURATION', '2.0'))
BACKGROUND_MUSIC_SEGMENT_LENGTH = float(os.getenv('BACKGROUND_MUSIC_SEGMENT_LENGTH', '10.0'))

# Load environment variables from multiple possible locations
def load_config():
    """Load configuration from .env files in order of priority."""
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
        print("No .env file found. Trying environment variables...")

load_config()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
NARRATOR_VOICE = os.getenv('NARRATOR_VOICE', 'Charon')

# Adaptive chunking - starts at 30k, reduces on server errors
CURRENT_CHUNK_LIMIT = 30000
CHUNK_REDUCTION_STEPS = [25000, 20000, 15000, 10000, 5000]
CHUNK_STEP_INDEX = 0

if not GOOGLE_API_KEY:
    config_dir = os.path.expanduser('~/.config/ai-audiobook-generator')
    raise EnvironmentError(f"""GOOGLE_API_KEY not found in environment variables.

Please set up your API key by either:
1. Creating a .env file in the current directory
2. Creating {config_dir}/.env
3. Setting the GOOGLE_API_KEY environment variable

Example .env file content:
GOOGLE_API_KEY=your_gemini_api_key_here
NARRATOR_VOICE=Charon""")

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM data to a wave file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def read_file_content(file_path):
    """Read file content."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Initialize tokenizer globally
try:
    if tiktoken:
        tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    else:
        tokenizer = None
except Exception:
    # Fallback to a rough estimate if tiktoken fails
    tokenizer = None

def count_tokens(text: str) -> int:
    """Count actual tokens in text using tiktoken."""
    if tokenizer is None:
        # Fallback to rough estimate
        return max(1, len(text) // 4)
    
    try:
        return len(tokenizer.encode(text))
    except Exception:
        # Fallback to rough estimate if encoding fails
        return max(1, len(text) // 4)

def chunk_text_smartly(text: str, max_tokens: int = 30000) -> list[str]:
    """Split text into chunks that stay under the token limit, breaking at natural boundaries."""
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first (double newlines)
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # Check if adding this paragraph would exceed the limit
        test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph
        
        if count_tokens(test_chunk) <= max_tokens:
            # Safe to add this paragraph
            current_chunk = test_chunk
        else:
            # Adding this paragraph would exceed limit
            if current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk.strip())
                # Check if single paragraph exceeds limit
                if count_tokens(paragraph) > max_tokens:
                    # Force split oversized paragraph
                    para_chunks = chunk_text_smartly(paragraph, max_tokens)
                    chunks.extend(para_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                # Single paragraph is too large, split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                temp_chunk = ""
                
                for sentence in sentences:
                    test_sentence_chunk = temp_chunk + (' ' if temp_chunk else '') + sentence
                    
                    if count_tokens(test_sentence_chunk) <= max_tokens:
                        temp_chunk = test_sentence_chunk
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            # Check if single sentence exceeds limit
                            if count_tokens(sentence) > max_tokens:
                                # Force split oversized sentence
                                sent_chunks = chunk_text_smartly(sentence, max_tokens)
                                chunks.extend(sent_chunks)
                                temp_chunk = ""
                            else:
                                temp_chunk = sentence
                        else:
                            # Single sentence is too large, force split by words
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
                                        # Single word is too large - force split by characters
                                        if count_tokens(word) > max_tokens:
                                            # Split oversized word by characters
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
                                                        # Single character over limit (impossible with normal text)
                                                        chunks.append(char)
                                            if char_chunk:
                                                word_chunk = char_chunk
                                        else:
                                            word_chunk = word
                            
                            if word_chunk:
                                temp_chunk = word_chunk
                
                if temp_chunk:
                    current_chunk = temp_chunk
    
    # Add the last chunk if it exists with final safety check
    if current_chunk:
        if count_tokens(current_chunk) > max_tokens:
            # Force split if final chunk is still too large
            final_chunks = chunk_text_smartly(current_chunk, max_tokens)
            chunks.extend(final_chunks)
        else:
            chunks.append(current_chunk.strip())
    
    # Final verification pass - guarantee no chunk exceeds limit
    verified_chunks = []
    for chunk in chunks:
        if chunk.strip():
            if count_tokens(chunk) > max_tokens:
                # Emergency character-level splitting
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

def get_chapter_files():
    """Get all chapter files sorted by name."""
    chapter_files = glob.glob('chapters/chapter_*.txt')
    return sorted(chapter_files)

def get_narration_system_instruction():
    """Built-in system instruction for professional audiobook narration."""
    return """You are a professional audiobook narrator with a captivating, engaging voice. Narrate the provided text with:

- A warm, professional tone that draws listeners in
- Clear, well-modulated delivery with perfect pacing
- Appropriate character voices for dialogue
- Smooth transitions and natural rhythm
- Emotional depth that enhances the story

Focus only on narrating the content provided. Do not read any instructions or meta-commentary."""

def reduce_chunk_limit():
    """Reduce the global chunk limit when server errors occur."""
    global CURRENT_CHUNK_LIMIT, CHUNK_STEP_INDEX
    
    if CHUNK_STEP_INDEX < len(CHUNK_REDUCTION_STEPS):
        old_limit = CURRENT_CHUNK_LIMIT
        CURRENT_CHUNK_LIMIT = CHUNK_REDUCTION_STEPS[CHUNK_STEP_INDEX]
        CHUNK_STEP_INDEX += 1
        print(f"🔧 Reducing chunk limit from {old_limit:,} to {CURRENT_CHUNK_LIMIT:,} tokens due to server errors")
        return True
    return False

def generate_chunk_audio(chunk_text, chunk_output_file, model="gemini-2.5-flash-preview-tts", custom_prompt=None, safe_chunk_mode=False, _retry_count=0):
    """Generate TTS audio for a single text chunk using REST API with proper TTS prompting."""
    global CURRENT_CHUNK_LIMIT
    
    # Enhanced debugging output
    print(f"🔍 DEBUG: Starting chunk audio generation")
    print(f"🔍 DEBUG: Model: {model}")
    print(f"🔍 DEBUG: Output file: {chunk_output_file}")
    print(f"🔍 DEBUG: Safe chunk mode: {safe_chunk_mode}")
    print(f"🔍 DEBUG: Custom prompt provided: {bool(custom_prompt and custom_prompt.strip())}")
    print(f"🔍 DEBUG: Chunk length: {len(chunk_text)} characters")
    print(f"🔍 DEBUG: Chunk tokens: {count_tokens(chunk_text):,}")
    print(f"🔍 DEBUG: API Key present: {'***' + GOOGLE_API_KEY[-4:] if GOOGLE_API_KEY and len(GOOGLE_API_KEY) > 4 else 'Yes' if GOOGLE_API_KEY else 'No'}")
    print(f"🔍 DEBUG: Narrator voice: {NARRATOR_VOICE}")
    
    # Determine effective chunk limit based on safe mode
    effective_limit = CURRENT_CHUNK_LIMIT
    if safe_chunk_mode:
        # Use 1800 token limit for all models in safe mode
        effective_limit = min(CURRENT_CHUNK_LIMIT, 1800)
        print(f"🛡️ Safe chunk mode active: Using {effective_limit:,} token limit for optimal performance")
        print(f"🔍 DEBUG: Effective limit reduced from {CURRENT_CHUNK_LIMIT:,} to {effective_limit:,}")
    else:
        print(f"🔍 DEBUG: Using standard limit: {effective_limit:,} tokens")
    
    # Check if chunk exceeds effective limit
    if count_tokens(chunk_text) > effective_limit:
        print(f"⚠️ Chunk ({count_tokens(chunk_text):,} tokens) exceeds effective limit ({effective_limit:,}), re-chunking...")
        print(f"🔍 DEBUG: Initiating smart re-chunking with limit {effective_limit:,}")
        # Re-chunk with effective limit
        sub_chunks = chunk_text_smartly(chunk_text, effective_limit)
        print(f"🔍 DEBUG: Split into {len(sub_chunks)} sub-chunks")
        
        # Generate audio for each sub-chunk and combine
        sub_chunk_files = []
        base_name = chunk_output_file.replace('.wav', '')
        
        for i, sub_chunk in enumerate(sub_chunks, 1):
            sub_output = f"{base_name}_sub_{i:02d}.wav"
            print(f"🔍 DEBUG: Processing sub-chunk {i}/{len(sub_chunks)}: {count_tokens(sub_chunk):,} tokens")
            sub_file = generate_chunk_audio(sub_chunk, sub_output, model, custom_prompt, safe_chunk_mode)  # Recursive call
            sub_chunk_files.append(sub_file)
        
        # Combine sub-chunks
        print(f"🔍 DEBUG: Combining {len(sub_chunk_files)} sub-chunks into final output")
        return combine_audio_chunks(sub_chunk_files, chunk_output_file)

    # Import rate limiter
    from rate_limiter import generate_audio_with_quota_awareness
    
    # Prepend the user's exact custom prompt as a style instruction before the content
    if custom_prompt and custom_prompt.strip():
        # Use the user's exact prompt text as a style instruction
        tts_prompt = f"{custom_prompt.strip()}: {chunk_text}"
        print(f"🔍 DEBUG: Applied custom prompt: '{custom_prompt[:50]}...'")
    else:
        # Default fallback if no custom prompt provided
        tts_prompt = f"Narrate this audiobook chapter in a professional, engaging style: {chunk_text}"
        print(f"🔍 DEBUG: Using default prompt format")
    
    print(f"🔍 DEBUG: Final TTS prompt length: {len(tts_prompt)} characters, {count_tokens(tts_prompt):,} tokens")

    # Define a progress callback
    def progress_callback(message):
        print(f"🎤 {message}")
        print(f"🔍 DEBUG: Progress update: {message}")

    try:
        print(f"🔍 DEBUG: Initializing Gemini client...")
        # Initialize Gemini client
        if not genai:
            raise ImportError("Google Genai library not available. Please install google-genai package.")
        client = genai.Client(api_key=GOOGLE_API_KEY)
        print(f"🔍 DEBUG: Client initialized successfully")
        
        print(f"🔍 DEBUG: Calling generate_audio_with_quota_awareness...")
        print(f"🔍 DEBUG: Voice: {NARRATOR_VOICE}, Model: {model}")
        
        # Generate audio using REST API with proper TTS prompting
        audio_data = generate_audio_with_quota_awareness(
            client,
            tts_prompt,  # Properly formatted TTS prompt
            NARRATOR_VOICE,
            model=model,
            max_retries=3,
            progress_callback=progress_callback
        )

        print(f"🔍 DEBUG: Audio generation completed, received {len(audio_data)} bytes")
        
        # Save audio to file
        print(f"🔍 DEBUG: Saving audio to file: {chunk_output_file}")
        wave_file(chunk_output_file, audio_data)
        print(f"Chunk audio saved to {chunk_output_file}")
        print(f"🔍 DEBUG: File save completed successfully")
        
        # Audio corruption detection
        if ENABLE_CORRUPTION_DETECTION and AUDIO_QUALITY_DETECTION_AVAILABLE:
            print(f"🔍 DEBUG: Running corruption detection on {chunk_output_file}")
            try:
                is_corrupted = quick_corruption_check(chunk_output_file)
                if is_corrupted:
                    print(f"🚨 CORRUPTION DETECTED in {chunk_output_file}")
                    
                    # Check if we should retry (prevent infinite recursion)
                    if _retry_count < CORRUPTION_RETRY_ATTEMPTS:
                        print(f"🔄 Regenerating due to API corruption (attempt {_retry_count + 1}/{CORRUPTION_RETRY_ATTEMPTS})...")
                        
                        # Remove corrupted file
                        try:
                            os.remove(chunk_output_file)
                            print(f"🗑️ Removed corrupted file: {chunk_output_file}")
                        except Exception as e:
                            print(f"⚠️ Could not remove corrupted file: {e}")
                        
                        # Retry with progressive fallback strategy
                        if CORRUPTION_AUTO_SPLIT and count_tokens(chunk_text) > 1000:
                            print(f"🔧 Large chunk detected, reducing size for retry...")
                            # Try with safe chunk mode if not already enabled
                            if not safe_chunk_mode:
                                print(f"🛡️ Enabling safe chunk mode for retry")
                                return generate_chunk_audio(chunk_text, chunk_output_file, model, custom_prompt, True, _retry_count + 1)
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
                                        # Reset retry count for sub-chunks
                                        sub_file = generate_chunk_audio(sub_chunk, sub_output, model, custom_prompt, safe_chunk_mode, 0)
                                        sub_chunk_files.append(sub_file)
                                    
                                    # Combine sub-chunks
                                    return combine_audio_chunks(sub_chunk_files, chunk_output_file)
                        
                        # Simple retry for smaller chunks or when auto-split is disabled
                        print(f"🔄 Retrying generation with same parameters...")
                        return generate_chunk_audio(chunk_text, chunk_output_file, model, custom_prompt, safe_chunk_mode, _retry_count + 1)
                    else:
                        print(f"❌ Maximum retry attempts ({CORRUPTION_RETRY_ATTEMPTS}) reached for {chunk_output_file}")
                        print(f"⚠️ Proceeding with potentially corrupted audio")
                else:
                    print(f"✅ Audio quality check passed for {chunk_output_file}")
            except Exception as e:
                print(f"⚠️ Audio quality check failed: {e}")
                print(f"📋 Proceeding with generated audio (detection error)")
        elif ENABLE_CORRUPTION_DETECTION:
            print(f"📋 Audio quality detection enabled but libraries not available")
        else:
            print(f"📋 Audio quality detection disabled")
        
        return chunk_output_file

    except Exception as e:
        error_str = str(e)
        print(f"🔍 DEBUG: Exception caught: {type(e).__name__}")
        print(f"🔍 DEBUG: Exception message: {error_str}")
        
        # Handle server errors with adaptive chunking
        if "500" in error_str or "502" in error_str or "timeout" in error_str.lower():
            print(f"🔧 Server error detected: {error_str}")
            print(f"🔍 DEBUG: Attempting to reduce chunk limit and retry")
            if reduce_chunk_limit():
                print(f"🔄 Retrying with smaller chunks...")
                print(f"🔍 DEBUG: Chunk limit reduced, retrying generation")
                return generate_chunk_audio(chunk_text, chunk_output_file, model, custom_prompt, safe_chunk_mode)  # Retry with new limit
            else:
                print(f"🔍 DEBUG: Cannot reduce chunk limit further")
        
        # Re-raise if not a server error or can't reduce further
        print(f"❌ API Error: {error_str}")
        print(f"🔍 DEBUG: Re-raising exception: {type(e).__name__}")
        raise

def create_background_music_generator():
    """Create and configure background music generator if enabled."""
    if not ENABLE_BACKGROUND_MUSIC or not BACKGROUND_MUSIC_AVAILABLE or MusicGenerator is None:
        return None
        
    try:
        generator = MusicGenerator(api_key=GOOGLE_API_KEY)
        
        # Convert string enums to actual enums
        mood = getattr(MusicMood, BACKGROUND_MUSIC_MOOD.upper(), MusicMood.AMBIENT)
        genre = getattr(MusicGenre, BACKGROUND_MUSIC_GENRE.upper(), MusicGenre.AMBIENT)
        
        config = MusicConfig(
            bpm=BACKGROUND_MUSIC_BPM,
            temperature=BACKGROUND_MUSIC_TEMPERATURE,
            guidance=BACKGROUND_MUSIC_GUIDANCE,
            density=BACKGROUND_MUSIC_DENSITY,
            brightness=BACKGROUND_MUSIC_BRIGHTNESS,
            volume=BACKGROUND_MUSIC_VOLUME,
            mood=mood,
            genre=genre,
            custom_prompts=BACKGROUND_MUSIC_CUSTOM_PROMPTS
        )
        
        mood_name = getattr(mood, 'value', str(mood))
        genre_name = getattr(genre, 'value', str(genre))
        print(f"🎵 Background music configured: {mood_name} {genre_name} at volume {BACKGROUND_MUSIC_VOLUME}")
        return generator, config
        
    except Exception as e:
        print(f"⚠️ Failed to initialize background music generator: {e}")
        return None

def mix_audio_with_background_music(speech_audio, music_generator, duration_seconds):
    """Mix speech audio with background music."""
    if not music_generator:
        return speech_audio
        
    try:
        # Get background music for the duration needed
        music_duration = duration_seconds + BACKGROUND_MUSIC_FADE_DURATION * 2
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
        music_audio = music_audio - (60 - int(BACKGROUND_MUSIC_VOLUME * 60))  # Convert volume to dB reduction
        
        # Trim music to match speech duration + fade time
        speech_duration_ms = len(speech_audio)
        music_audio = music_audio[:speech_duration_ms + int(BACKGROUND_MUSIC_FADE_DURATION * 2000)]
        
        # Add fade in/out to music
        fade_duration_ms = int(BACKGROUND_MUSIC_FADE_DURATION * 1000)
        if len(music_audio) > fade_duration_ms * 2:
            music_audio = music_audio.fade_in(fade_duration_ms).fade_out(fade_duration_ms)
        
        # Mix speech and music
        mixed_audio = speech_audio.overlay(music_audio[:len(speech_audio)])
        
        print(f"🎵 Mixed {duration_seconds:.1f}s of speech with background music")
        return mixed_audio
        
    except Exception as e:
        print(f"⚠️ Failed to mix background music: {e}")
        return speech_audio

def combine_audio_chunks(chunk_files, output_file, music_generator=None):
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
        if music_generator and ENABLE_BACKGROUND_MUSIC:
            duration_seconds = len(audio) / 1000.0  # Convert ms to seconds
            audio = mix_audio_with_background_music(audio, music_generator, duration_seconds)
        
        # Add the chunk audio
        combined += audio
        
        # Add a brief pause between chunks (0.5 seconds)
        if i < len(chunk_files):
            pause = AudioSegment.silent(duration=500)
            combined += pause
    
    # Handle file collisions
    state_manager = ProjectStateManager()
    final_output_file = state_manager.handle_file_collision(output_file)
    
    # Export combined audio
    combined.export(final_output_file, format="wav")
    print(f"Combined chapter audio saved to {final_output_file}")
    
    # Clean up chunk files
    for chunk_file in chunk_files:
        try:
            os.remove(chunk_file)
            print(f"Cleaned up temporary chunk: {chunk_file}")
        except Exception as e:
            print(f"Warning: Could not clean up {chunk_file}: {e}")
    
    return final_output_file

def generate_chapter_audio(chapter_text, output_file, model="gemini-2.5-flash-preview-tts", custom_prompt=None, safe_chunk_mode=False, music_generator=None):
    """Generate TTS audio for a chapter, automatically chunking if needed."""
    global CURRENT_CHUNK_LIMIT
    
    # Determine effective chunk limit based on safe mode
    effective_limit = CURRENT_CHUNK_LIMIT
    if safe_chunk_mode:
        # Use 1800 token limit for all models in safe mode
        effective_limit = min(CURRENT_CHUNK_LIMIT, 1800)
        print(f"🛡️ Safe chunk mode active: Using {effective_limit:,} token limit for optimal performance")
    
    # Check if chapter needs to be chunked
    token_count = count_tokens(chapter_text)
    
    if token_count <= effective_limit:
        # Small enough for single request
        print(f"Chapter size: {token_count:,} tokens - processing as single chunk (limit: {effective_limit:,})")
        return generate_chunk_audio(chapter_text, output_file, model, custom_prompt, safe_chunk_mode)
    
    # Chapter is too large, needs chunking
    print(f"Chapter size: {token_count:,} tokens - splitting into chunks (limit: {effective_limit:,})...")
    chunks = chunk_text_smartly(chapter_text, max_tokens=effective_limit)
    print(f"Split into {len(chunks)} chunks")
    
    # Process chunks with smart resume capability
    chunk_files = []
    base_name = output_file.replace('.wav', '')
    chunk_index = 0
    chunk_file_counter = 1  # Separate counter for consistent file naming
    
    while chunk_index < len(chunks):
        chunk = chunks[chunk_index]
        chunk_tokens = count_tokens(chunk)
        print(f"Processing chunk {chunk_index+1}/{len(chunks)} ({chunk_tokens:,} tokens)...")
        
        chunk_output = f"{base_name}_chunk_{chunk_file_counter:03d}.wav"
        
        try:
            chunk_file = generate_chunk_audio(chunk, chunk_output, model, custom_prompt, safe_chunk_mode)
            chunk_files.append(chunk_file)
            chunk_index += 1  # Success - move to next chunk
            chunk_file_counter += 1  # Increment file counter
            
        except (MaxRetriesExceededError, HTTPAPIError) as e:
            # Check if this is a server error that warrants chunk size reduction
            if ("500" in str(e) or "502" in str(e) or "timeout" in str(e).lower()):
                if reduce_chunk_limit():
                    print(f"🔧 Server error on chunk {chunk_index+1}, reducing limit to {CURRENT_CHUNK_LIMIT:,} tokens")
                    
                    # Update effective limit after reduction
                    new_effective_limit = CURRENT_CHUNK_LIMIT
                    if safe_chunk_mode:
                        new_effective_limit = min(CURRENT_CHUNK_LIMIT, 1800)
                    
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
    return combine_audio_chunks(chunk_files, output_file, music_generator)

def combine_chapters(audio_files, output_file):
    """Combine multiple chapter audio files into a single audiobook."""
    print("Combining chapters into complete audiobook...")
    combined = AudioSegment.empty()
    
    for audio_file in audio_files:
        print(f"Adding {audio_file}")
        audio = AudioSegment.from_wav(audio_file)  # type: ignore
        
        # Ensure stereo
        if audio.channels == 1:
            audio = audio.set_channels(2)
            
        # Add the chapter audio
        combined += audio
        
        # Add a brief pause between chapters (2 seconds)
        pause = AudioSegment.silent(duration=2000)  # type: ignore
        combined += pause
    
    combined.export(output_file, format="wav")
    print(f"Complete audiobook saved to {output_file}")

def main():
    music_generator = None  # Initialize at function start
    
    try:
        # Check if chapters exist in current directory first
        current_dir = os.getcwd()
        current_chapters = get_chapter_files()
        
        if current_chapters:
            # Use current directory if chapters are found here
            working_dir = current_dir
            print(f"Found chapters in current directory: {working_dir}")
        else:
            # Fall back to the default directory
            working_dir = os.path.expanduser('~/AI-Audiobook-Generator')
            os.makedirs(working_dir, exist_ok=True)
            os.chdir(working_dir)
            print(f"Using default working directory: {working_dir}")

        # Initialize project state manager
        state_manager = ProjectStateManager(working_dir)

        # Get all chapter files
        chapter_files = get_chapter_files()

        if not chapter_files:
            print("No chapter files found in chapters/ directory!")
            print("Please add chapter files named like: chapter_01.txt, chapter_02.txt, etc.")
            print(f"Working directory: {working_dir}")
            return

        print(f"Found {len(chapter_files)} chapters to process")
        print(f"Using narrator voice: {NARRATOR_VOICE}")
        print(f"Working directory: {working_dir}")

        # Initialize background music generator if enabled
        music_result = create_background_music_generator()
        music_config = None
        
        if music_result:
            music_generator, music_config = music_result
            print(f"🎵 Background music enabled for audiobook generation")
            
            # Start background music generation asynchronously
            try:
                import asyncio
                import threading
                
                def start_music_generation():
                    async def music_task():
                        try:
                            if music_generator and hasattr(music_generator, 'start_generation'):
                                await music_generator.start_generation(music_config)
                                print(f"🎵 Background music generation started successfully")
                        except Exception as e:
                            print(f"⚠️ Failed to start background music: {e}")
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(music_task())
                
                # Start music generation in background thread
                music_thread = threading.Thread(target=start_music_generation, daemon=True)
                music_thread.start()
                
                # Give music generator time to start
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Failed to start background music thread: {e}")
                music_generator = None
        else:
            if ENABLE_BACKGROUND_MUSIC:
                print(f"🎵 Background music enabled but not available (check dependencies)")
            else:
                print(f"🎵 Background music disabled")

        # Generate project ID based on chapters
        project_id = state_manager.get_project_id('chapters')
        print(f"Project ID: {project_id}")

        # Check for existing project state
        project_state = state_manager.load_project_state(project_id)
        completed_chunks = state_manager.get_completed_chunks(project_id)

        if completed_chunks:
            print(f"📋 Resuming project - {len(completed_chunks)} chunks already completed")
        else:
            print("📋 Starting new project")

        # Create output directory for individual chapters
        os.makedirs('output', exist_ok=True)

        generated_files = []

        # Process each chapter
        for chapter_file in chapter_files:
            chapter_name = os.path.basename(chapter_file).replace('.txt', '')
            output_file = f"output/{chapter_name}.wav"

            # Check if this chapter is already completed
            if output_file in completed_chunks:
                print(f"✅ Skipping already completed: {chapter_file}")
                generated_files.append(output_file)
                continue

            print(f"\nProcessing {chapter_file}...")

            # Read chapter content
            chapter_text = read_file_content(chapter_file)

            # Generate audio for this chapter (using default model and prompt)
            actual_output_file = generate_chapter_audio(chapter_text, output_file, music_generator=music_generator)
            generated_files.append(actual_output_file)

            # Mark as completed
            state_manager.mark_chunk_completed(project_id, actual_output_file)

        # Combine all chapters into a complete audiobook
        if len(generated_files) > 1:
            print(f"\nCombining {len(generated_files)} chapters...")
            combine_chapters(generated_files, "complete_audiobook.wav")
        else:
            # If only one chapter, just copy it as the complete audiobook
            print("Single chapter detected, creating audiobook...")
            try:
                audio = AudioSegment.from_wav(generated_files[0])
                audio.export("complete_audiobook.wav", format="wav")
            except ImportError:
                # Just copy the file if AudioSegment is not available
                import shutil
                shutil.copy2(generated_files[0], "complete_audiobook.wav")

        # Stop background music generation
        if music_generator:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(music_generator.stop())
                print(f"🎵 Background music generation stopped")
            except Exception as e:
                print(f"⚠️ Failed to stop background music: {e}")

        # Save file information for change detection
        state_manager.save_file_info(project_id, 'chapters')

        print(f"\n✅ Audiobook generation complete!")
        print(f"📚 Individual chapters: output/")
        print(f"🎧 Complete audiobook: complete_audiobook.wav")
        if music_generator:
            print(f"🎵 Generated with background music: {BACKGROUND_MUSIC_MOOD} {BACKGROUND_MUSIC_GENRE}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # Ensure music generator is stopped in case of error
        try:
            if music_generator:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(music_generator.stop())
        except:
            pass

if __name__ == "__main__":
    main()