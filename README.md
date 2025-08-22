# 🎧 wowitsjack's Audiobook Maker v2.0.3

![wowitsjack's Audiobook Maker](https://github.com/wowitsjack/AI-Audiobook-Maker/releases/download/v2.0.3/image.png)

**Professional AI-Powered Audiobook Generator** - Transform your written content into high-quality audiobooks using Google's advanced Gemini 2.5 TTS technology. Features a modern GUI, intelligent chunking, and 30 professional narrator voices.

## 🎯 **Quick Start - No Coding Required!**

### 📦 **Download Ready-to-Use Packages**

Choose your platform and start creating audiobooks in minutes:

- 🐧 **[Linux Standalone](https://github.com/wowitsjack/AI-Audiobook-Maker/releases/download/v2.0.3/wowitsjacks-Audiobook-Maker-v2.0.3-Linux-Standalone.zip)** - Zero dependencies, just run!
- 🪟 **[Windows Complete](https://github.com/wowitsjack/AI-Audiobook-Maker/releases/download/v2.0.3/wowitsjacks-Audiobook-Maker-v2.0.3-Windows-Standalone.zip)** - Auto-setup launcher
- 🍎 **[macOS Complete](https://github.com/wowitsjack/AI-Audiobook-Maker/releases/download/v2.0.3/wowitsjacks-Audiobook-Maker-v2.0.3-macOS-Standalone.zip)** - Intel & Apple Silicon

Each package includes everything you need with clear instructions!

## 🆕 **What's New in v2.0.3**

### 🔧 **Major Bug Fixes & Code Quality**
- ✅ **Fixed all Pylance static analysis errors** for cleaner, more reliable code
- ✅ **Enhanced security** with comprehensive `.gitignore` protecting API keys
- ✅ **Improved platform compatibility** with better Windows/macOS/Linux support
- ✅ **Enhanced error handling** with proper type checking throughout

### 🎯 **Enhanced User Experience** 
- ✅ **Smart UI Controls** - Manual sliders automatically disable when Smart Chunking is enabled
- ✅ **Better Visual Feedback** - Greyed-out controls clearly show automatic operation
- ✅ **Updated Branding** - Now officially "wowitsjack's Audiobook Maker"

### 🔍 **Advanced Debugging & Logging**
- ✅ **Comprehensive API Logging** - Full network request/response logging in terminal
- ✅ **Enhanced Error Reporting** - Detailed debugging information for troubleshooting
- ✅ **Real-time Status Updates** - Timestamped logs with detailed API call information

### 🛡️ **Smart Chunking Improvements**
- ✅ **Fixed Chunk Distribution** - Safe mode now properly creates multiple chunks
- ✅ **Automatic Control Management** - Smart chunking disables manual controls for cleaner UX
- ✅ **Better Token Management** - Enhanced 1800-token safe mode for optimal TTS performance

## ✨ **Key Features**

### 🎭 **30 Professional Narrator Voices**
Choose from a diverse range of voices including:
- **Kore** - Firm & Confident
- **Puck** - Upbeat & Energetic  
- **Enceladus** - Breathy & Intimate
- **Aoede** - Breezy & Natural
- **Charon** - Informative & Clear
- And 25 more unique voices!

### 🤖 **Dual TTS Model Support**
- **Gemini 2.5 Pro TTS** - Highest quality, premium voice generation
- **Gemini 2.5 Flash TTS** - Faster processing, efficient for large projects

### 📝 **Smart Text Processing**
- **File Support**: `.txt` and `.md` (Markdown) files
- **Intelligent Chunking**: Automatically splits large files at paragraph boundaries
- **Safe Chunk Mode**: 1800-token limit for optimal TTS performance (enabled by default)
- **Chunk Editor**: Preview and manually edit text chunks before generation
- **Word Count Tracking**: Real-time word count for optimal processing

### 🎨 **Customizable Narration Styles**
- **Professional**: Clear, engaging business/educational content
- **Dramatic**: Theatrical delivery with heightened emotion
- **Relaxing**: Calm, soothing style perfect for meditation
- **Expressive**: Varied emotion with captivating delivery
- **Custom Prompts**: Write your own narration instructions

### 🖥️ **Modern GUI Interface**
- **HiDPI Support**: Crystal clear on high-resolution displays
- **Dark Theme**: Easy on the eyes for long sessions
- **Smart UI Controls**: Manual sliders automatically disable when smart chunking is enabled
- **Enhanced Visual Feedback**: Greyed-out controls show automatic operation
- **Progress Tracking**: Real-time status updates and progress bars
- **Comprehensive Logging**: Full API call debugging in terminal section

### ⚡ **Advanced Features**
- **Chunk Preview & Editing**: See exactly how files will be split and edit as needed
- **Merge/Split Tools**: Manually adjust chunk boundaries for perfect pacing
- **Multiple Format Support**: Handles both plain text and Markdown formatting
- **Batch Processing**: Generate multiple chapters automatically
- **Audio Combining**: Automatically creates complete audiobook files
- **Project Resume**: Smart resume functionality for interrupted sessions
- **Audio Format Support**: WAV, MP3, M4B with customizable bitrates

## 🚀 **Getting Started**

### Option 1: Download Ready-Made Packages (Recommended)
1. **Get a Google API Key**: Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **Download your platform package** from the links above
3. **Extract and run** - follow the included README for your platform
4. **Enter your API key** when prompted
5. **Start creating audiobooks!**

### Option 2: Install from Source (Developers)
1. **Clone the repository:**
   ```bash
   git clone https://github.com/wowitsjack/AI-Audiobook-Maker.git
   cd AI-Audiobook-Maker
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate
   # Linux/macOS: source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file:**
   ```bash
   GOOGLE_API_KEY=your_google_api_key_here
   NARRATOR_VOICE=Kore
   TTS_MODEL=gemini-2.5-pro-preview-tts
   ```

5. **Run the GUI:**
   ```bash
   python audiobook_gui.py
   ```

## 📂 **Usage**

1. **Prepare Your Content:**
   - Add text files to the `chapters` folder (created automatically)
   - Supports `.txt` and `.md` files
   - Name files sequentially: `chapter_01.txt`, `chapter_02.txt`, etc.

2. **Configure Settings:**
   - Choose your narrator voice (30 options available)
   - Select narration style preset or create custom prompts
   - Adjust chunking settings if needed

3. **Generate Audiobook:**
   - Click "Generate Audiobook"
   - Monitor progress in real-time
   - Access individual chapter files and complete audiobook

4. **Output Files:**
   ```
   output/
   ├── chapter_01.wav
   ├── chapter_02.wav
   ├── ...
   └── complete_audiobook.wav
   ```

## 🔧 **Configuration**

### Environment Variables (.env)
```bash
GOOGLE_API_KEY=your_google_api_key_here
NARRATOR_VOICE=Kore
TTS_MODEL=gemini-2.5-pro-preview-tts
```

### Chapter Format
```text
Chapter 1: The Beginning

Your chapter content here. The narrator will read this with professional 
audiobook delivery, including proper pacing, emotion, and clarity.

Dialogue will be handled naturally, and the narrator will adjust tone 
appropriately for different scenes and emotions.
```

## 📋 **System Requirements**

### All Platforms
- **Internet Connection**: Required for API calls to Google's TTS service
- **Storage**: ~100MB for application + space for generated audio files
- **RAM**: 2GB minimum, 4GB recommended for large files

### Platform-Specific Requirements

#### Linux (Standalone Package)
- **OS**: Ubuntu 18.04+, Debian 10+, Fedora 30+, or equivalent
- **Architecture**: x86_64 (64-bit)
- **Dependencies**: None (all bundled in executable)

#### Windows (Auto-Setup Package)
- **OS**: Windows 10 or Windows 11
- **Python**: 3.8+ (script will help install if needed)
- **Architecture**: 64-bit recommended

#### macOS (Auto-Setup Package)
- **OS**: macOS 10.14 (Mojave) or later
- **Python**: 3.8+ (install from [python.org](https://python.org))
- **Architecture**: Intel and Apple Silicon supported

## 🆘 **Troubleshooting**

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
- Check the terminal section for detailed debugging logs

**"Chunking issues"**
- Enable Safe Chunk Mode for optimal performance
- Use Smart Chunking for automatic management
- Check the chunking preview before generation

### Debugging Features
- **Terminal Logging**: Enable terminal view for comprehensive API call logs
- **Debug Information**: Detailed request/response data for troubleshooting
- **Progress Tracking**: Real-time status updates with timestamps

## 🔗 **Support & Community**

- **Issues**: [Report problems](https://github.com/wowitsjack/AI-Audiobook-Maker/issues)
- **Releases**: [Download latest versions](https://github.com/wowitsjack/AI-Audiobook-Maker/releases)
- **Documentation**: Full guides available in this repository
- **Community**: Join discussions in the repository's discussion section

## 📝 **Version History**

### v2.0.3 (Latest) - Major Bug Fixes & Newbie-Friendly Packages
- 🔧 Fixed all Pylance static analysis errors
- 🛡️ Enhanced security with comprehensive .gitignore
- 🎯 Smart UI controls with visual feedback
- 🔍 Comprehensive API/network logging
- 📦 Cross-platform standalone packages

### v2.0.2 - Safe Chunking & Enhanced Controls
- 🛡️ Safe Chunk Mode with 1800-token limit
- 🧠 Smart chunking improvements
- 🎨 Enhanced GUI controls

### v2.0.1 - Dual Models & Custom Prompts
- 🤖 Dual TTS model support (Pro vs Flash)
- ✍️ Custom prompt functionality
- 📊 Enhanced chunk management

### v2.0.0 - Complete Rewrite
- 🎨 Modern GUI interface
- 🧠 Intelligent chunking system
- 💾 Project state management

## 📄 **Credits & License**

This project is built with:
- **Google Gemini 2.5 Pro/Flash TTS** - Advanced text-to-speech AI
- **CustomTkinter** - Modern Python GUI framework
- **PyInstaller** - Python application packaging
- **Python Libraries** - Various audio and GUI libraries

**MIT License** - Created with ❤️ by wowitsjack for audiobook enthusiasts and content creators worldwide.

---

## 🎧 **Happy Audiobook Creating!** 🎧

Transform your written content into professional audiobooks with just a few clicks. Whether you're an author, educator, or content creator, wowitsjack's Audiobook Maker makes high-quality text-to-speech conversion accessible to everyone.

**[Download v2.0.3 Now →](https://github.com/wowitsjack/AI-Audiobook-Maker/releases/latest)**