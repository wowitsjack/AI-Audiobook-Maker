import tempfile
import asyncio
import base64
import json
import os
import wave
from websockets.asyncio.client import connect
import websockets
import pyaudio
from dotenv import load_dotenv
import sys
from pydub import AudioSegment

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
VOICE_A = os.getenv('VOICE_A', 'Puck')
VOICE_B = os.getenv('VOICE_B', 'Kore')

if sys.version_info < (3, 11):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

class AudioGenerator:
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.ws = None
        self.ws_semaphore = asyncio.Semaphore(1)
        
        # Audio configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.SAMPLE_RATE = 24000
        self.CHUNK_SIZE = 512
        
        # WebSocket configuration
        self.ws_options = {
            'ping_interval': 20,
            'ping_timeout': 10,
            'close_timeout': 5
        }
        
        # API configuration
        self.host = 'generativelanguage.googleapis.com'
        self.model = "gemini-2.0-flash-exp"
        self.uri = f"wss://{self.host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={GOOGLE_API_KEY}"
        
        # Store complete audio data
        self.complete_audio = bytearray()

    async def startup(self, voice):
        async with self.ws_semaphore:
            setup_msg = {
                "setup": {
                    "model": f"models/{self.model}",
                    "generation_config": {
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": voice
                                }
                            }
                        }
                    }
                }
            }
            await self.ws.send(json.dumps(setup_msg))
            response = await self.ws.recv()

    async def send_text(self, text, voice):
        async with self.ws_semaphore:
            msg = {
                "client_content": {
                    "turn_complete": True,
                    "turns": [
                        {"role": "user", "parts": [{"text": text}]}
                    ]
                }
            }
            await self.ws.send(json.dumps(msg))

    async def receive_audio(self, output_file):
        async with self.ws_semaphore:
            self.complete_audio.clear()
            await asyncio.sleep(0.1)
            
            try:
                async for raw_response in self.ws:
                    response = json.loads(raw_response)
                    
                    # Process audio data
                    try:
                        parts = response["serverContent"]["modelTurn"]["parts"]
                        for part in parts:
                            if "inlineData" in part:
                                b64data = part["inlineData"]["data"]
                                pcm_data = base64.b64decode(b64data)
                                self.complete_audio.extend(pcm_data)
                                self.audio_in_queue.put_nowait(pcm_data)
                    except KeyError:
                        pass

                    # Check for completion
                    try:
                        if response["serverContent"].get("turnComplete", False):
                            self.save_wav_file(output_file)
                            while not self.audio_in_queue.empty():
                                self.audio_in_queue.get_nowait()
                            break
                    except KeyError:
                        pass
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"Connection closed: {e}")
                raise

    def save_wav_file(self, filename):
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(self.CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.SAMPLE_RATE)
            wav_file.writeframes(self.complete_audio)
        print(f"Audio saved to {filename}")

    async def run(self, dialogues, output_files, voices, max_retries=3):
        last_exception = None
        for attempt in range(max_retries):
            try:
                async with await connect(self.uri, **self.ws_options) as ws:
                    self.ws = ws
                    await self.startup(voices[0])
                    
                    # Process dialogues sequentially
                    for i in range(len(dialogues)):
                        await self.send_text(dialogues[i], voices[i])
                        await self.receive_audio(output_files[i])
                    return
                    
            except websockets.exceptions.ConnectionClosedError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    print(f"Connection lost. Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(5)
                else:
                    print("Max retries reached. Unable to reconnect.")
                    raise last_exception

def parse_conversation(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    lines = content.strip().split('\n')
    speaker_a_lines = []
    speaker_b_lines = []
    
    for line in lines:
        if line.strip():
            if line.startswith("Speaker A:"):
                speaker_a_lines.append(line.replace("Speaker A:", "").strip())
            elif line.startswith("Speaker B:"):
                speaker_b_lines.append(line.replace("Speaker B:", "").strip())
    
    return speaker_a_lines, speaker_b_lines

def combine_audio_files(file_list, output_file):
    combined = AudioSegment.empty()
    for file in file_list:
        audio = AudioSegment.from_wav(file)
        combined += audio
    combined.export(output_file, format="wav")

def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

async def setup_environment():
    if not os.getenv('GOOGLE_API_KEY'):
        raise EnvironmentError("GOOGLE_API_KEY not found in environment variables")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return script_dir

def read_and_parse_inputs():
    system_instructions = read_file_content('system_instructions.txt')
    full_script = read_file_content('podcast_script.txt')
    speaker_a_lines, speaker_b_lines = parse_conversation('podcast_script.txt')
    return system_instructions, full_script, speaker_a_lines, speaker_b_lines

def prepare_speaker_dialogues(system_instructions, full_script, speaker_lines, voice, temp_dir):
    dialogues = [system_instructions + "\n\n" + full_script]
    voices = [voice]
    output_files = [os.path.join(temp_dir, f"speaker_{voice}_initial.wav")]

    for i, line in enumerate(speaker_lines):
        dialogues.append(line)
        voices.append(voice)
        output_files.append(os.path.join(temp_dir, f"speaker_{voice}_{i}.wav"))

    return dialogues, voices, output_files

async def process_speaker(generator, dialogues, output_files, voices):
    await generator.run(dialogues, output_files, voices)

def interleave_output_files(speaker_a_files, speaker_b_files):
    all_output_files = []
    min_length = min(len(speaker_a_files), len(speaker_b_files))

    for i in range(min_length):
        all_output_files.extend([speaker_a_files[i], speaker_b_files[i]])

    all_output_files.extend(speaker_a_files[min_length:])
    all_output_files.extend(speaker_b_files[min_length:])

    return all_output_files

async def main():
    script_dir = await setup_environment()

    with tempfile.TemporaryDirectory(dir=script_dir) as temp_dir:
        system_instructions, full_script, speaker_a_lines, speaker_b_lines = read_and_parse_inputs()

        dialogues_a, voices_a, output_files_a = prepare_speaker_dialogues(
            system_instructions, full_script, speaker_a_lines, VOICE_A, temp_dir)
        dialogues_b, voices_b, output_files_b = prepare_speaker_dialogues(
            system_instructions, full_script, speaker_b_lines, VOICE_B, temp_dir)

        generator = AudioGenerator()
        await process_speaker(generator, dialogues_a, output_files_a, voices_a)
        await process_speaker(generator, dialogues_b, output_files_b, voices_b)

        all_output_files = interleave_output_files(output_files_a[1:], output_files_b[1:])
        final_output = "final_podcast.wav"
        combine_audio_files(all_output_files, final_output)
        print(f"Final podcast audio created: {final_output}")

    print("Temporary files cleaned up")

if __name__ == "__main__":
    asyncio.run(main())
