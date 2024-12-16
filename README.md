# gemini-2-tts

AI-Powered Podcast Generator: A Python-based tool that converts text scripts into realistic audio podcasts using Google's Generative AI API. This project leverages advanced text-to-speech technology to create dynamic, multi-speaker conversations with customizable voices.

Features

Text-to-speech conversion using Google's Generative AI
Support for multiple speakers with distinct voices
Automatic audio file generation and combination
Customizable voice selection
Robust error handling and retry mechanisms
Prerequisites
Python 3.8 or higher
FFmpeg installed and accessible in system PATH
Google API key for Generative AI services
System Dependencies
Windows:
Microsoft Visual C++ 14.0 or greater
FFmpeg
Linux:
bash
sudo apt-get install portaudio19-dev python3-dev ffmpeg
macOS:
bash
brew install portaudio ffmpeg
Installation
Clone the repository:
bash
git clone https://github.com/agituts/gemini-2-tts.git
cd gemini-2-tts
Install required Python packages:
bash
pip install -r requirements.txt
Create a .env file in the project root:
bash
GOOGLE_API_KEY=your_google_api_key_here
VOICE_A=Puck
VOICE_B=Kore
Project Structure
podcast_script.txt: Contains the conversation script in the format:
text
Speaker A: Your text here
Speaker B: Response text here
system_instructions.txt: Contains system-level instructions for voice generation
.env: Environment variables configuration
requirements.txt: Python package dependencies
Usage
Prepare your conversation script in podcast_script.txt
Run the generator:
bash
python main.py
Find the generated podcast as final_podcast.wav
Environment Variables
Create a .env file with the following variables:
text
GOOGLE_API_KEY=your_google_api_key_here
VOICE_A=Puck    # Optional: Default is Puck
VOICE_B=Kore    # Optional: Default is Kore
Error Handling
The system automatically retries on connection failures
Maximum retry attempts: 3
Temporary files are automatically cleaned up
Output
Individual speaker audio files are generated temporarily
Final output is combined into final_podcast.wav
All temporary files are automatically cleaned up
License
MIT License
Contributing
Fork the repository
Create your feature branch
Commit your changes
Push to the branch
Create a new Pull Request