import os
import wave
import glob
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
NARRATOR_VOICE = os.getenv('NARRATOR_VOICE', 'Charon')

if not GOOGLE_API_KEY:
    raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")

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

def get_chapter_files():
    """Get all chapter files sorted by name."""
    chapter_files = glob.glob('chapters/chapter_*.txt')
    return sorted(chapter_files)

def generate_chapter_audio(chapter_text, system_instructions, output_file):
    """Generate TTS audio for a single chapter using Gemini 2.5 Pro TTS."""
    
    # Create client with API key
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # Create the narration prompt
    prompt = f"""Using a professional, engaging, and captivating voice:

{system_instructions}

Please narrate the following chapter with professional charm, appropriate pacing, and compelling delivery. Make every word feel meaningful and engaging:

{chapter_text}"""
    
    response = client.models.generate_content(
        model="gemini-2.5-pro-preview-tts",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=NARRATOR_VOICE,
                    )
                )
            )
        )
    )
    
    # Extract audio data
    data = response.candidates[0].content.parts[0].inline_data.data
    
    # Save to wave file
    wave_file(output_file, data)
    print(f"Chapter audio saved to {output_file}")
    return output_file

def combine_chapters(audio_files, output_file):
    """Combine multiple chapter audio files into a single audiobook."""
    print("Combining chapters into complete audiobook...")
    combined = AudioSegment.empty()
    
    for audio_file in audio_files:
        print(f"Adding {audio_file}")
        audio = AudioSegment.from_wav(audio_file)
        
        # Ensure stereo
        if audio.channels == 1:
            audio = audio.set_channels(2)
            
        # Add the chapter audio
        combined += audio
        
        # Add a brief pause between chapters (2 seconds)
        pause = AudioSegment.silent(duration=2000)
        combined += pause
    
    combined.export(output_file, format="wav")
    print(f"Complete audiobook saved to {output_file}")

def main():
    try:
        # Read system instructions
        system_instructions = read_file_content('system_instructions.txt')
        
        # Get all chapter files
        chapter_files = get_chapter_files()
        
        if not chapter_files:
            print("No chapter files found in chapters/ directory!")
            print("Please add chapter files named like: chapter_01.txt, chapter_02.txt, etc.")
            return
        
        print(f"Found {len(chapter_files)} chapters to process")
        print(f"Using narrator voice: {NARRATOR_VOICE}")
        
        # Create output directory for individual chapters
        os.makedirs('output', exist_ok=True)
        
        generated_files = []
        
        # Process each chapter
        for chapter_file in chapter_files:
            chapter_name = os.path.basename(chapter_file).replace('.txt', '')
            output_file = f"output/{chapter_name}.wav"
            
            print(f"\nProcessing {chapter_file}...")
            
            # Read chapter content
            chapter_text = read_file_content(chapter_file)
            
            # Generate audio for this chapter
            generate_chapter_audio(chapter_text, system_instructions, output_file)
            generated_files.append(output_file)
        
        # Combine all chapters into a complete audiobook
        if len(generated_files) > 1:
            print(f"\nCombining {len(generated_files)} chapters...")
            combine_chapters(generated_files, "complete_audiobook.wav")
        else:
            # If only one chapter, just copy it as the complete audiobook
            print("Single chapter detected, creating audiobook...")
            audio = AudioSegment.from_wav(generated_files[0])
            audio.export("complete_audiobook.wav", format="wav")
        
        print(f"\n✅ Audiobook generation complete!")
        print(f"📚 Individual chapters: output/")
        print(f"🎧 Complete audiobook: complete_audiobook.wav")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()