# 🎧 AI Audiobook Generator - Release Assets

Welcome to the AI Audiobook Generator! This folder contains cross-platform executables and launchers for easy installation and use.

## 📦 Available Versions

### 🐧 Linux (Ubuntu/Debian/Fedora/etc.)
**File:** `AI-Audiobook-Generator-Linux`
- **Type:** Standalone executable binary
- **Requirements:** None (all dependencies bundled)
- **Installation:**
  1. Download the `AI-Audiobook-Generator-Linux` file
  2. Make it executable: `chmod +x AI-Audiobook-Generator-Linux`
  3. Run: `./AI-Audiobook-Generator-Linux`

### 🍎 macOS (Intel & Apple Silicon)
**File:** `AI-Audiobook-Generator-macOS.command`
- **Type:** Shell script launcher
- **Requirements:** Python 3.8+ (automatically installs dependencies)
- **Installation:**
  1. Download the `AI-Audiobook-Generator-macOS.command` file
  2. Double-click to run, or use Terminal: `./AI-Audiobook-Generator-macOS.command`
  3. First run will automatically set up the virtual environment

### 🪟 Windows (10/11)
**File:** `AI-Audiobook-Generator-Windows.bat`
- **Type:** Batch script launcher
- **Requirements:** Python 3.8+ (automatically installs dependencies)
- **Installation:**
  1. Download the `AI-Audiobook-Generator-Windows.bat` file
  2. Double-click to run
  3. First run will automatically set up the virtual environment

## 🚀 Quick Start

1. **Get a Google API Key:**
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key
   - Save it securely

2. **Download and Run:**
   - Choose your platform-specific file above
   - Follow the installation steps
   - Enter your API key when prompted

3. **Start Creating Audiobooks:**
   - Add text/markdown files to the `chapters` folder
   - Choose your narrator voice (30 options available!)
   - Customize narration style with preset prompts
   - Generate professional audiobooks with one click

## ✨ Key Features

### 🎭 **30 Professional Narrator Voices**
Choose from a diverse range of voices including:
- **Kore** - Firm & Confident
- **Puck** - Upbeat & Energetic
- **Enceladus** - Breathy & Intimate
- **Aoede** - Breezy & Natural
- And 26 more unique voices!

### 📝 **Smart Text Processing**
- **File Support:** `.txt` and `.md` (Markdown) files
- **Intelligent Chunking:** Automatically splits large files at paragraph boundaries
- **Chunk Editor:** Preview and manually edit text chunks before generation
- **Word Count Tracking:** Real-time word count for optimal processing

### 🎨 **Customizable Narration Styles**
- **Professional:** Clear, engaging business/educational content
- **Dramatic:** Theatrical delivery with heightened emotion
- **Relaxing:** Calm, soothing style perfect for meditation
- **Expressive:** Varied emotion with captivating delivery
- **Custom Prompts:** Write your own narration instructions

### 🖥️ **Modern Interface**
- **HiDPI Support:** Crystal clear on high-resolution displays
- **Dark Theme:** Easy on the eyes for long sessions
- **Progress Tracking:** Real-time status updates and progress bars
- **File Management:** Built-in output folder and playback integration

### ⚡ **Advanced Features**
- **Chunk Preview & Editing:** See exactly how files will be split and edit as needed
- **Merge/Split Tools:** Manually adjust chunk boundaries for perfect pacing
- **Multiple Format Support:** Handles both plain text and Markdown formatting
- **Batch Processing:** Generate multiple chapters automatically
- **Audio Combining:** Automatically creates complete audiobook files

## 🔧 Configuration

### Environment Setup
Create a `.env` file in the project directory:
```
GOOGLE_API_KEY=your_google_api_key_here
NARRATOR_VOICE=Kore
```

### Chapter Organization
```
chapters/
├── chapter_01.txt
├── chapter_02.md
├── introduction.txt
└── conclusion.md
```

### Output Structure
```
output/
├── chapter_01.wav
├── chapter_02_part_01.wav
├── chapter_02_part_02.wav
└── complete_audiobook.wav
```

## 📋 System Requirements

### All Platforms
- **Internet Connection:** Required for API calls to Google's TTS service
- **Storage:** ~100MB for application + space for generated audio files
- **RAM:** 2GB minimum, 4GB recommended for large files

### Platform-Specific Requirements

#### Linux
- **OS:** Ubuntu 18.04+, Debian 10+, Fedora 30+, or equivalent
- **Architecture:** x86_64 (64-bit)
- **Dependencies:** All bundled in executable

#### macOS
- **OS:** macOS 10.14 (Mojave) or later
- **Python:** 3.8+ (install from [python.org](https://python.org))
- **Architecture:** Intel and Apple Silicon supported

#### Windows
- **OS:** Windows 10 or Windows 11
- **Python:** 3.8+ (install from [python.org](https://python.org))
- **Architecture:** 64-bit recommended

## 🆘 Troubleshooting

### Common Issues

**"Python not found" (Windows/macOS)**
- Install Python from [python.org](https://python.org)
- Make sure to check "Add Python to PATH" during installation

**"Permission denied" (Linux/macOS)**
- Make the file executable: `chmod +x filename`
- Check file permissions and ownership

**"API Key Invalid"**
- Verify your Google API key is correct
- Ensure the Generative AI API is enabled in your Google Cloud project
- Check for any billing or quota restrictions

**"Audio generation fails"**
- Check internet connection
- Verify API key has proper permissions
- Try with smaller text chunks first

### Getting Help
- **Issues:** Report problems on the [GitHub Issues page](https://github.com/wowitsjack/AI-Audiobook-Maker/issues)
- **Documentation:** Full guides available in the main repository
- **Community:** Join discussions in the repository's discussion section

## 📄 License & Credits

This project is built with:
- **Google Gemini 2.5 Pro TTS** - Advanced text-to-speech AI
- **CustomTkinter** - Modern Python GUI framework
- **PyInstaller** - Python application packaging
- **Python Libraries** - Various audio and GUI libraries

Created with ❤️ for audiobook enthusiasts and content creators worldwide.

---

**🎧 Happy Audiobook Creating! 🎧**