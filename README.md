# gemini-2-tts

AI-Powered Podcast Generator: A Python-based tool that converts text scripts into realistic audio podcasts using Google's Generative AI API. This project leverages advanced text-to-speech technology to create dynamic, multi-speaker conversations with customizable voices.

[![Create Unlimited Podcast Audio with Python and Google’s AI: A Step-by-Step Guide](https://img.youtube.com/vi/cu-56pBQSEM/maxresdefault.jpg)](https://www.youtube.com/watch?v=cu-56pBQSEM)

Features:

- Text-to-speech conversion using Google's Generative AI
- Support for multiple speakers with distinct voices
- Automatic audio file generation and combination
- Customizable voice selection
- Robust error handling and retry mechanisms
  
Prerequisites:

- Python 3.8 or higher
- FFmpeg installed and accessible in system PATH
- Google API key for Generative AI services
  
System Dependencies:

Windows:

- Microsoft Visual C++ 14.0 or greater
- FFmpeg
  
Linux:

```bash
sudo apt-get install portaudio19-dev python3-dev ffmpeg
```

macOS:

```bash
brew install portaudio ffmpeg
```

Installation:

1) Clone the repository:
```bash
git clone https://github.com/agituts/gemini-2-tts.git
cd gemini-2-tts
```
2) Create and activate virtual environment:

For Windows:
```bash
python -m venv venv
.\venv\Scripts\activate
```
For Linux/MacOS:
```bash
python3 -m venv venv
source venv/bin/activate
```
3) Install required Python packages:
```bash
pip install -r requirements.txt
```
4) Create a .env file in the project root:
```bash
GOOGLE_API_KEY=your_google_api_key_here
VOICE_A=Puck    # Optional: Default is Puck; Current options are Puck, Charon, Kore, Fenrir, Aoede
VOICE_B=Kore    # Optional: Default is Kore; Current options are Puck, Charon, Kore, Fenrir, Aoede
```
Note: To deactivate the virtual environment when you're done, simply run:
```bash
deactivate
```

Project Structure:

  podcast_script.txt: Contains the conversation script in the format:
```text
Speaker A: Welcome to our podcast! Today we'll be discussing...
Speaker B: Thanks for having me! I'm excited to...
Speaker A: Let's start with...
Speaker B: That's an interesting point...
```
  system_instructions.txt: Contains system-level instructions for voice generation in the format:
```text
You are a real-time energetic and enthusiastic narrator for a podcast.
The entire podcast script is provided below this instruction.
Your job is to narrate only the specific dialogue line provided to you in subsequent messages, responding immediately as if in real-time, using a natural, friendly, and engaging tone.
When narrating, use the context of the entire podcast script to inform your delivery.
Speak smoothly and conversationally, not like you are reading off a script.
Pause naturally at commas, periods, and question marks.
Vary your pacing slightly as a person would in real conversation.
Do not narrate anything assigned to other speakers or identify which speaker is talking.
Only narrate the specific dialogues provided to you.
Do not introduce yourself or any other speaker; simply speak the dialogues as you receive them, as if they were being spoken in that moment.
The script is designed for a podcast and contains conversational exchanges between speakers.
Do not add any additional information unless asked.
Remember, you must receive and acknowledge the full script first before you begin receiving and narrating individual dialogue lines.
```
  .env: Environment variables configuration
  requirements.txt: Python package dependencies

Usage:

1) Prepare your conversation script in podcast_script.txt
2) Run the generator:
```bash
python app.py
```
3) Find the generated podcast as final_podcast.wav

Environment Variables:

Create a .env file with the following variables:
```text
GOOGLE_API_KEY=your_google_api_key_here
VOICE_A=Puck    # Optional: Default is Puck; Current options are Puck, Charon, Kore, Fenrir, Aoede
VOICE_B=Kore    # Optional: Default is Kore; Current options are Puck, Charon, Kore, Fenrir, Aoede
```

Error Handling:

  The system automatically retries on connection failures
  Maximum retry attempts: 3
  Temporary files are automatically cleaned up
  
Output:

  Individual speaker audio files are generated temporarily
  Final output is combined into final_podcast.wav
  All temporary files are automatically cleaned up
  
License:

MIT License

Contributing:

1) Fork the repository
2) Create your feature branch
3) Commit your changes
4) Push to the branch
5) Create a new Pull Request
