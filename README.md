# AI Audiobook Generator v2.1.0

A professional-grade text-to-speech audiobook generator using Google's Gemini 2.5 TTS API and Lyria RealTime music generation.

## Features

### 🎤 Text-to-Speech Generation
- **High-Quality Audio**: Uses Google's Gemini 2.5 TTS with multiple voice options
- **Smart Text Chunking**: Intelligent text splitting with token counting for optimal generation
- **Resume Functionality**: Continue interrupted audiobook generation from where you left off
- **Multiple Input Formats**: Support for .txt, .md, and .epub files

### 🎵 Background Music
- **AI-Generated Music**: Optional background music using Google's Lyria RealTime API
- **Ambient Soundscapes**: Create immersive audiobook experiences
- **Configurable Volume**: Adjustable background music levels

### 🔍 Quality Assurance
- **Audio Corruption Detection**: Optional statistical analysis to detect corrupted TTS output
- **Automatic Retry**: Smart retry logic for failed API calls
- **Progress Tracking**: Real-time progress updates and state management

### 🖥️ User Interface
- **Modern GUI**: Built with CustomTkinter for a professional appearance
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Easy Configuration**: Intuitive interface for all settings

## Quick Start

### Option 1: Download Pre-built Release (Recommended)

**Choose your platform:**

- **🐧 Linux Binary**: [AI-Audiobook-Generator-v2.1.0-Linux.zip](https://github.com/wowitsjack/audiobook-maker/releases/download/v2.1.0/AI-Audiobook-Generator-v2.1.0-Linux.zip) - Standalone executable (300MB)
- **🪟 Windows Easy-Launcher**: [AI-Audiobook-Generator-v2.1.0-Windows-Easy-Launcher.zip](https://github.com/wowitsjack/audiobook-maker/releases/download/v2.1.0/AI-Audiobook-Generator-v2.1.0-Windows-Easy-Launcher.zip) - Source + launcher
- **🍎 macOS Easy-Launcher**: [AI-Audiobook-Generator-v2.1.0-macOS-Easy-Launcher.zip](https://github.com/wowitsjack/audiobook-maker/releases/download/v2.1.0/AI-Audiobook-Generator-v2.1.0-macOS-Easy-Launcher.zip) - Source + launcher
- **🐧 Linux Easy-Launcher**: [AI-Audiobook-Generator-v2.1.0-Linux-Easy-Launcher.zip](https://github.com/wowitsjack/audiobook-maker/releases/download/v2.1.0/AI-Audiobook-Generator-v2.1.0-Linux-Easy-Launcher.zip) - Source + launcher

**Installation:**
1. Download the appropriate file for your platform
2. Extract the zip file
3. Run `START-HERE` script (`.bat` for Windows, `.command` for macOS, `.sh` for Linux)
4. Enter your Google Gemini API key when prompted

### Option 2: Install from Source
```bash
git clone https://github.com/wowitsjacks/audiobook-maker.git
cd audiobook-maker/audiobook_maker
pip install -r requirements.txt
python audiobook_gui_launcher.py
```

### Option 3: Build Your Own Binary
```bash
cd audiobook_maker
python utils/build_release.py --all
```

## Setup

### 1. Get API Keys
- **Gemini API Key**: Get from [Google AI Studio](https://ai.google.dev/)
- **Lyria API Key** (optional): For background music generation

### 2. First Run
1. Launch the application
2. Enter your API key in the GUI
3. Select your text file
4. Choose output directory
5. Configure settings (voice, model, etc.)
6. Click "Generate Audiobook"

## Usage Guide

### Basic Workflow
1. **Load Text**: Click "Browse" to select your text file
2. **Configure Settings**:
   - Choose voice and TTS model
   - Adjust chunk size if needed
   - Enable background music (optional)
   - Enable quality detection (optional)
3. **Set Output**: Choose where to save your audiobook
4. **Generate**: Click "Generate Audiobook" and wait for completion

### Advanced Features

#### Background Music
- Enable in settings to add ambient music to your audiobook
- Configurable volume levels
- AI-generated soundscapes that complement your content

#### Quality Detection
- Optional feature to detect corrupted audio output
- Uses statistical analysis of audio properties
- Automatically retries failed generations

#### Resume Functionality
- Automatically saves progress during generation
- Resume interrupted sessions from the last successful chunk
- State management preserves all settings

## Supported Formats

### Input
- **Text Files**: `.txt`, `.md`
- **E-books**: `.epub`
- **Encoding**: UTF-8, UTF-16, Latin-1 (auto-detected)

### Output
- **Audio Format**: `.wav` (high-quality, uncompressed)
- **Sample Rate**: 24kHz
- **Bit Depth**: 16-bit

## System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **RAM**: 4GB (8GB recommended for large files)
- **Storage**: 1GB free space + space for output files
- **Internet**: Stable connection for API calls

### Recommended
- **RAM**: 8GB or more
- **CPU**: Multi-core processor
- **Storage**: SSD for faster processing

## Development

### Project Structure
```
audiobook_maker/
├── core/           # Core audiobook generation logic
├── gui/            # User interface components
├── tts/            # Text-to-speech integration
├── music/          # Background music generation
├── quality/        # Audio quality detection
├── state/          # State management and resume
├── utils/          # Utilities and build scripts
└── requirements.txt
```

### Building Releases
The project includes a comprehensive build system:

```bash
# Build for current platform
python utils/build_release.py

# Build for all platforms (if supported)
python utils/build_release.py --all

# Install to ~/.local/bin (Linux)
python utils/build_release.py --install-local
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

#### API Errors
- **Solution**: Check your Gemini API key and internet connection
- **Rate Limits**: The app includes built-in rate limiting and retry logic

#### Large Files
- **Issue**: Very large text files may cause memory issues
- **Solution**: Use smaller chunk sizes (adjust in settings)

#### Audio Quality
- **Issue**: Poor audio quality or artifacts
- **Solution**: Enable quality detection to automatically retry failed generations

#### Performance
- **Issue**: Slow generation on older hardware
- **Solution**: Close other applications, use smaller chunk sizes

### Getting Help
- **Issues**: Report bugs on [GitHub Issues](https://github.com/wowitsjacks/audiobook-maker/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/wowitsjacks/audiobook-maker/discussions)

## Changelog

### v2.1.0 (Latest)
- **Major Reorganization**: Complete codebase restructure into professional package
- **New Build System**: Automated multi-platform build and release system
- **Enhanced GUI**: Self-contained application with all dependencies embedded
- **Improved Quality Detection**: Enhanced audio corruption detection algorithms
- **Better Error Handling**: More robust error handling and retry logic
- **Cross-Platform Binaries**: Pre-built executables for Windows, macOS, and Linux

### v2.0.3 (Previous)
- Added background music generation
- Improved audio quality detection
- Enhanced resume functionality
- GUI improvements and bug fixes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Google AI**: For providing Gemini 2.5 TTS and Lyria RealTime APIs
- **CustomTkinter**: For the modern GUI framework
- **PyInstaller**: For cross-platform binary generation
- **Open Source Community**: For the many libraries that make this project possible

---

**Built with ❤️ by the open source community**

[![GitHub stars](https://img.shields.io/github/stars/wowitsjacks/audiobook-maker?style=social)](https://github.com/wowitsjacks/audiobook-maker/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/wowitsjacks/audiobook-maker)](https://github.com/wowitsjacks/audiobook-maker/issues)
[![GitHub license](https://img.shields.io/github/license/wowitsjacks/audiobook-maker)](https://github.com/wowitsjacks/audiobook-maker/blob/main/LICENSE)