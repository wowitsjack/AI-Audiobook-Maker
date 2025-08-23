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

try:
    from pydub import AudioSegment  # type: ignore
except ImportError:
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
    from ..utils.rate_limiter import generate_audio_with_quota_awareness
    
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    NARRATOR_VOICE = os.getenv('NARRATOR_VOICE', 'Charon')
    
    if not GOOGLE_API_KEY:
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")
    
    effective_limit = 30000
    if safe_chunk_mode:
        effective_limit = min(30000, 1800)
    
    token_count = count_tokens(chapter_text)
    
    if token_count <= effective_limit:
        print(f"Chapter size: {token_count:,} tokens - processing as single chunk")
        if custom_prompt and custom_prompt.strip():
            tts_prompt = f"{custom_prompt.strip()}: {chapter_text}"
        else:
            tts_prompt = f"Narrate this audiobook chapter in a professional, engaging style: {chapter_text}"
        
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
            tts_prompt = f"{custom_prompt.strip()}: {chunk}"
        else:
            tts_prompt = f"Narrate this audiobook chapter in a professional, engaging style: {chunk}"
        
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
        chunk_files.append(chunk_output)
    
    return combine_audio_chunks(chunk_files, output_file)

def combine_audio_chunks(chunk_files, output_file):
    """Combine multiple audio chunks into a single file."""
    print(f"Combining {len(chunk_files)} audio chunks...")
    combined = AudioSegment.empty()
    
    for i, chunk_file in enumerate(chunk_files, 1):
        print(f"Adding chunk {i}/{len(chunk_files)}: {chunk_file}")
        audio = AudioSegment.from_wav(chunk_file)
        
        if audio.channels == 1:
            audio = audio.set_channels(2)
        
        combined += audio
        
        if i < len(chunk_files):
            pause = AudioSegment.silent(duration=500)
            combined += pause
    
    combined.export(output_file, format="wav")
    print(f"Combined chapter audio saved to {output_file}")
    
    for chunk_file in chunk_files:
        try:
            os.remove(chunk_file)
            print(f"Cleaned up temporary chunk: {chunk_file}")
        except Exception as e:
            print(f"Warning: Could not clean up {chunk_file}: {e}")
    
    return output_file

def combine_chapters(audio_files, output_file):
    """Combine multiple chapter audio files into a single audiobook."""
    print("Combining chapters into complete audiobook...")
    combined = AudioSegment.empty()
    
    for audio_file in audio_files:
        print(f"Adding {audio_file}")
        audio = AudioSegment.from_wav(audio_file)
        
        if audio.channels == 1:
            audio = audio.set_channels(2)
            
        combined += audio
        
        pause = AudioSegment.silent(duration=2000)
        combined += pause
    
    combined.export(output_file, format="wav")
    print(f"Complete audiobook saved to {output_file}")