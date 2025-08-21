# Gemini 2.5 Audiobook Generator

AI-Powered Audiobook Generator: A Python-based tool that converts written book chapters into professional audiobook narration using Google's Gemini 2.5 Pro TTS API. This project leverages advanced text-to-speech technology to create engaging, single-narrator audiobooks with customizable voices and natural storytelling delivery.

## Features

- **Professional Audiobook Narration**: Single narrator with consistent voice throughout
- **Chapter-Based Processing**: Automatically processes multiple chapters and combines them
- **30 Voice Options**: Choose from a wide variety of narrator voices with different characteristics
- **Smart Audio Combining**: Automatically combines chapters with appropriate pauses
- **Customizable Narration Style**: Professional audiobook delivery with proper pacing and emotion
- **Individual Chapter Output**: Access individual chapter audio files for editing

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed and accessible in system PATH
- Google API key for Generative AI services

## System Dependencies

**Linux:**
```bash
sudo apt-get install portaudio19-dev python3-dev ffmpeg
```

**macOS:**
```bash
brew install portaudio ffmpeg
```

**Windows:**
- Microsoft Visual C++ 14.0 or greater
- FFmpeg

## Installation

1) **Clone the repository:**
```bash
git clone https://github.com/agituts/gemini-2-tts.git
cd gemini-2-tts
```

2) **Create and activate virtual environment:**

*For Windows:*
```bash
python -m venv venv
.\venv\Scripts\activate
```

*For Linux/MacOS:*
```bash
python3 -m venv venv
source venv/bin/activate
```

3) **Install required Python packages:**
```bash
pip install -r requirements.txt
```

4) **Create a .env file in the project root:**
```bash
GOOGLE_API_KEY=your_google_api_key_here
NARRATOR_VOICE=Charon    # Choose your preferred narrator voice
```

## Project Structure

```
gemini-2-tts/
├── chapters/           # Directory for chapter text files
│   ├── chapter_01.txt
│   ├── chapter_02.txt
│   └── ...
├── output/            # Individual chapter audio files (auto-created)
├── system_instructions.txt  # Narrator guidance and style instructions
├── .env              # Configuration file
└── app.py            # Main application
```

## Available Narrator Voices

Choose from 30 professional voices with different characteristics:

- **Bright**: Zephyr, Autonoe
- **Upbeat**: Puck, Laomedeia  
- **Informative**: Charon, Rasalgethi
- **Firm**: Kore, Orus, Alnilam
- **Excitable**: Fenrir
- **Youthful**: Leda
- **Breezy**: Aoede
- **Easy-going**: Callirrhoe, Umbriel
- **Breathy**: Enceladus
- **Clear**: Iapetus, Erinome
- **Smooth**: Algieba, Despina
- **Gravelly**: Algenib
- **Soft**: Achernar
- **Even**: Schedar
- **Mature**: Gacrux
- **Forward**: Pulcherrima
- **Friendly**: Achird
- **Gentle**: Vindemiatrix
- **Lively**: Sadachbia
- **Casual**: Zubenelgenubi
- **Knowledgeable**: Sadaltager
- **Warm**: Sulafat

## Usage

1) **Prepare your book chapters:**
   - Create chapter files in the `chapters/` directory
   - Name them sequentially: `chapter_01.txt`, `chapter_02.txt`, etc.
   - Include chapter titles and content in plain text

2) **Configure narration style:**
   - Edit `system_instructions.txt` to customize the narrator's delivery style
   - Choose your preferred voice in the `.env` file

3) **Generate your audiobook:**
```bash
source venv/bin/activate  # Linux/MacOS
python app.py
```

4) **Access your audiobook:**
   - **Complete audiobook**: `complete_audiobook.wav`
   - **Individual chapters**: `output/chapter_XX.wav`

## Configuration

**Environment Variables (.env):**
```bash
GOOGLE_API_KEY=your_google_api_key_here
NARRATOR_VOICE=Charon  # Recommended: Charon (informative), Kore (firm), Algieba (smooth)
```

**Chapter Format:**
```text
Chapter 1: The Beginning

Your chapter content here. The narrator will read this with professional 
audiobook delivery, including proper pacing, emotion, and clarity.

Dialogue will be handled naturally, and the narrator will adjust tone 
appropriately for different scenes and emotions.
```

## Output

- **Individual Chapter Files**: Each chapter is saved as a separate WAV file in the `output/` directory
- **Complete Audiobook**: All chapters are combined with appropriate pauses into `complete_audiobook.wav`
- **Professional Quality**: 24kHz, stereo audio suitable for distribution

## Supported Languages

The TTS models automatically detect language and support 24 languages including:
English, Spanish, French, German, Italian, Portuguese, Japanese, Korean, Chinese, Hindi, Arabic, and more.

## Error Handling

- Automatic retry mechanisms for API calls
- Graceful handling of missing chapter files
- Clear error messages and progress indicators
- Temporary file cleanup

## License

MIT License

## Contributing

1) Fork the repository
2) Create your feature branch
3) Commit your changes
4) Push to the branch
5) Create a new Pull Request

---

**Note**: This project uses Google's Gemini 2.5 Pro TTS API for high-quality, natural-sounding audiobook narration. Ensure you have a valid Google AI API key before use.