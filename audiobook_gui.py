import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import glob
from pathlib import Path
import webbrowser
from PIL import Image
import subprocess
import sys
import json
import queue

# Import our audiobook generation logic
from app import generate_chapter_audio, combine_chapters, read_file_content, load_config
from dotenv import load_dotenv
from project_state import ProjectStateManager
from api_retry_handler import ServiceUnavailableError, MaxRetriesExceededError, HTTPAPIError
from rate_limiter import generate_audio_with_quota_awareness, QuotaExhaustedError

# Load configuration using the same logic as app.py
load_config()

# Set the appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

# Configure HiDPI scaling
try:
    from ctk_scaling import configure_scaling
    configure_scaling()
except:
    # Fallback HiDPI support
    import platform
    if platform.system() == "Windows":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

class AudiobookGeneratorGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🎧 wowitsjack's Audiobook Maker")
        
        # Set up working directory and initialize paths
        self.setup_working_directory()
        
        # HiDPI and scaling support
        self.setup_scaling()
        
        # Better proportions - wider and taller to accommodate all chunking controls and new features
        self.root.geometry("1600x1300")
        self.root.minsize(1400, 1200)
        self.root.resizable(True, True)
        
        # Configure grid weight
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Variables
        self.api_key = tk.StringVar(value=os.getenv('GOOGLE_API_KEY', ''))
        self.narrator_voice = tk.StringVar(value=os.getenv('NARRATOR_VOICE', 'Kore'))
        self.tts_model = tk.StringVar(value=os.getenv('TTS_MODEL', 'gemini-2.5-pro-preview-tts'))
        self.chapters_path = tk.StringVar(value=self.default_chapters_path)
        self.output_path = tk.StringVar(value=self.default_output_path)
        self.custom_prompt = tk.StringVar(value='Use a professional, engaging audiobook narration style with appropriate pacing and emotion.')
        self.is_generating = False
        self.file_chunks = {}  # Initialize chunk storage
        self.chunk_order = []  # Track order of chunks
        self.resume_point = tk.StringVar(value="from_beginning")  # Resume point selection
        self.state_manager = ProjectStateManager(self.working_dir)
        self.project_id = None
        
        # Audio encoding options
        self.output_format = tk.StringVar(value="WAV")
        self.mp3_bitrate = tk.StringVar(value="192")
        self.m4b_chapters = tk.BooleanVar(value=True)
        
        # Chunking options
        self.enable_chunking = tk.BooleanVar(value=True)
        self.chunk_word_threshold = tk.IntVar(value=800)  # Words before chunking
        self.target_chunk_count = tk.IntVar(value=3)      # Target number of chunks
        self.chunk_overlap = tk.IntVar(value=50)          # Overlap between chunks
        self.min_chunk_size = tk.IntVar(value=200)        # Minimum chunk size
        self.safe_chunk_mode = tk.BooleanVar(value=True)  # Safe chunk mode for Flash model
        
        # Terminal variables
        self.terminal_visible = False
        self.terminal_queue = queue.Queue()
        
        # Load saved prompts and settings
        self.load_saved_settings()
        
        # Voice options with descriptions
        self.voice_options = {
            'Kore': 'Kore (Firm & Confident)',
            'Puck': 'Puck (Upbeat & Energetic)',
            'Charon': 'Charon (Informative & Clear)',
            'Algieba': 'Algieba (Smooth & Polished)',
            'Enceladus': 'Enceladus (Breathy & Intimate)',
            'Zephyr': 'Zephyr (Bright & Vibrant)',
            'Aoede': 'Aoede (Breezy & Natural)',
            'Callirrhoe': 'Callirrhoe (Easy-going & Relaxed)',
            'Despina': 'Despina (Smooth & Professional)',
            'Achernar': 'Achernar (Soft & Gentle)',
            'Vindemiatrix': 'Vindemiatrix (Gentle & Warm)',
            'Sulafat': 'Sulafat (Warm & Inviting)',
            'Leda': 'Leda (Youthful & Fresh)',
            'Fenrir': 'Fenrir (Excitable & Dynamic)',
            'Autonoe': 'Autonoe (Bright & Clear)',
            'Umbriel': 'Umbriel (Easy-going & Calm)',
            'Iapetus': 'Iapetus (Clear & Precise)',
            'Erinome': 'Erinome (Clear & Articulate)',
            'Algenib': 'Algenib (Deep & Distinctive)',
            'Schedar': 'Schedar (Even & Balanced)',
            'Gacrux': 'Gacrux (Mature & Authoritative)',
            'Pulcherrima': 'Pulcherrima (Forward & Confident)',
            'Achird': 'Achird (Friendly & Approachable)',
            'Sadachbia': 'Sadachbia (Lively & Spirited)',
            'Zubenelgenubi': 'Zubenelgenubi (Casual & Natural)',
            'Sadaltager': 'Sadaltager (Knowledgeable & Wise)',
            'Laomedeia': 'Laomedeia (Upbeat & Cheerful)',
            'Rasalgethi': 'Rasalgethi (Informative & Professional)',
            'Orus': 'Orus (Firm & Strong)',
            'Alnilam': 'Alnilam (Firm & Steady)'
        }
        
        # TTS Model options with descriptions
        self.tts_model_options = {
            'gemini-2.5-pro-preview-tts': '2.5 Pro TTS (Highest Quality)',
            'gemini-2.5-flash-preview-tts': '2.5 Flash TTS (Faster & Efficient)'
        }
        
        self.create_widgets()
    
    def load_saved_settings(self):
        """Load saved settings and prompts from config file"""
        settings_file = os.path.join(self.config_dir, 'settings.json')
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                # Load last used prompt
                if 'last_prompt' in settings:
                    self.custom_prompt.set(settings['last_prompt'])
                    
                # Load audio encoding preferences
                if 'output_format' in settings:
                    self.output_format.set(settings['output_format'])
                if 'mp3_bitrate' in settings:
                    self.mp3_bitrate.set(settings['mp3_bitrate'])
                if 'm4b_chapters' in settings:
                    self.m4b_chapters.set(settings['m4b_chapters'])
                
                # Load chunking preferences
                if 'enable_chunking' in settings:
                    self.enable_chunking.set(settings['enable_chunking'])
                if 'chunk_word_threshold' in settings:
                    self.chunk_word_threshold.set(settings['chunk_word_threshold'])
                if 'target_chunk_count' in settings:
                    self.target_chunk_count.set(settings['target_chunk_count'])
                if 'chunk_overlap' in settings:
                    self.chunk_overlap.set(settings['chunk_overlap'])
                if 'min_chunk_size' in settings:
                    self.min_chunk_size.set(settings['min_chunk_size'])
                if 'safe_chunk_mode' in settings:
                    self.safe_chunk_mode.set(settings['safe_chunk_mode'])
                
                # Load last used chapters folder
                if 'last_chapters_folder' in settings:
                    self.chapters_path.set(settings['last_chapters_folder'])
                
                # Load TTS model preference
                if 'tts_model' in settings:
                    self.tts_model.set(settings['tts_model'])
                    
                # Load saved custom prompts
                self.saved_prompts = settings.get('saved_prompts', [])
            else:
                self.saved_prompts = []
        except Exception as e:
            print(f"Could not load settings: {e}")
            self.saved_prompts = []
    
    def save_settings(self):
        """Save current settings and prompts to config file"""
        settings_file = os.path.join(self.config_dir, 'settings.json')
        try:
            settings = {
                'last_prompt': self.custom_prompt.get(),
                'output_format': self.output_format.get(),
                'mp3_bitrate': self.mp3_bitrate.get(),
                'm4b_chapters': self.m4b_chapters.get(),
                'enable_chunking': self.enable_chunking.get(),
                'chunk_word_threshold': self.chunk_word_threshold.get(),
                'target_chunk_count': self.target_chunk_count.get(),
                'chunk_overlap': self.chunk_overlap.get(),
                'min_chunk_size': self.min_chunk_size.get(),
                'safe_chunk_mode': self.safe_chunk_mode.get(),
                'last_chapters_folder': self.chapters_path.get(),
                'tts_model': self.tts_model.get(),
                'saved_prompts': getattr(self, 'saved_prompts', [])
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Could not save settings: {e}")
    
    def setup_working_directory(self):
        """Set up working directory in home folder for the audiobook generator"""
        self.working_dir = os.path.expanduser('~/AI-Audiobook-Generator')
        self.config_dir = os.path.expanduser('~/.config/ai-audiobook-generator')
        
        # Create working directories
        os.makedirs(self.working_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Set default paths
        self.default_chapters_path = os.path.join(self.working_dir, 'chapters')
        self.default_output_path = os.path.join(self.working_dir, 'output')
        
        # Create subdirectories
        os.makedirs(self.default_chapters_path, exist_ok=True)
        os.makedirs(self.default_output_path, exist_ok=True)
        
        # Create README file if it doesn't exist
        readme_file = os.path.join(self.working_dir, 'README.txt')
        
        if not os.path.exists(readme_file):
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write("""🎧 AI Audiobook Generator - Working Directory

This directory contains your audiobook projects and generated content.

Folder Structure:
📁 chapters/     - Place your .txt and .md chapter files here
📁 output/      - Generated audio files are saved here
📄 README.txt   - This file

Getting Started:
1. Add your book chapters to the chapters/ folder
2. Launch the AI Audiobook Generator application
3. Configure your Google AI API key
4. Generate professional audiobooks!

For more information, visit the project on GitHub:
https://github.com/wowitsjack/AI-Audiobook-Maker

Created with ❤️ for audiobook enthusiasts""")
        
        # Copy configuration files if they exist
        env_source = os.path.expanduser('~/.config/ai-audiobook-generator/.env')
        if os.path.exists(env_source):
            # Configuration already exists, we're good
            pass
        elif os.path.exists('.env'):
            # Copy from current directory if available
            import shutil
            shutil.copy2('.env', env_source)
        
        # Change working directory to our app directory
        os.chdir(self.working_dir)
        
    def setup_scaling(self):
        """Configure HiDPI scaling"""
        try:
            # Auto-detect system scaling
            import platform
            if platform.system() == "Windows":
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    dpi = user32.GetDpiForSystem()
                    scale_factor = dpi / 96.0
                except:
                    scale_factor = 1.0
            else:
                # For Linux/Mac, try to detect scaling
                scale_factor = 1.2  # Default higher scaling for better visibility
                
            # Apply scaling (clamp between reasonable values)
            scale_factor = max(1.0, min(scale_factor, 2.0))
            ctk.set_widget_scaling(scale_factor)
            ctk.set_window_scaling(scale_factor)
            
        except Exception as e:
            # Fallback to default scaling
            ctk.set_widget_scaling(1.2)
            ctk.set_window_scaling(1.0)
        
    def create_widgets(self):
        # Title with gradient effect
        title_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        title_frame.grid(row=0, column=0, columnspan=2, pady=(15, 20), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            title_frame,
            text="🎧 wowitsjack's Audiobook Maker 🚀",
            font=ctk.CTkFont(size=36, weight="bold", family="Segoe UI")
        )
        title_label.grid(row=0, column=0, sticky="ew")

        # Add a subtle progress indicator
        self.progress_indicator = ctk.CTkLabel(
            title_frame,
            text="📊 Ready to generate",
            font=ctk.CTkFont(size=12, slant="italic")
        )
        self.progress_indicator.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        # Left Column - Configuration and Chapters
        left_frame = ctk.CTkFrame(self.root)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(15, 8), pady=(0, 15))
        left_frame.grid_columnconfigure(1, weight=1)
        left_frame.grid_rowconfigure(4, weight=1)
        
        # Configuration Section
        ctk.CTkLabel(left_frame, text="🔧 Configuration", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(15, 10), sticky="w", padx=15
        )
        
        # API Key
        ctk.CTkLabel(left_frame, text="Google API Key:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=15, pady=5
        )
        api_entry = ctk.CTkEntry(
            left_frame, 
            textvariable=self.api_key, 
            placeholder_text="Enter your Google AI API key", 
            show="*",
            height=30,
            font=ctk.CTkFont(size=11)
        )
        api_entry.grid(row=1, column=1, sticky="ew", padx=(10, 15), pady=5)
        
        # Voice Selection Row
        voice_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        voice_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=5)
        voice_frame.grid_columnconfigure(1, weight=1)
        voice_frame.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(voice_frame, text="Voice:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=5
        )
        voice_menu = ctk.CTkOptionMenu(
            voice_frame,
            variable=self.narrator_voice,
            values=list(self.voice_options.keys()),
            command=self.on_voice_change,
            height=30,
            font=ctk.CTkFont(size=11),
            width=150
        )
        voice_menu.grid(row=0, column=1, sticky="w", pady=5)
        
        # TTS Model selection
        ctk.CTkLabel(voice_frame, text="Model:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=2, sticky="w", padx=(20, 10), pady=5
        )
        model_menu = ctk.CTkOptionMenu(
            voice_frame,
            variable=self.tts_model,
            values=list(self.tts_model_options.keys()),
            command=self.on_model_change,
            height=30,
            font=ctk.CTkFont(size=11),
            width=150
        )
        model_menu.grid(row=0, column=3, sticky="w", pady=5)
        
        # Move chapters to next row
        ctk.CTkLabel(voice_frame, text="Chapters:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=5
        )
        path_entry = ctk.CTkEntry(
            voice_frame,
            textvariable=self.chapters_path,
            height=30,
            font=ctk.CTkFont(size=11),
            width=200
        )
        path_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)
        
        browse_btn = ctk.CTkButton(
            voice_frame,
            text="📁",
            command=self.browse_chapters_folder,
            width=30,
            height=30,
            font=ctk.CTkFont(size=12)
        )
        browse_btn.grid(row=1, column=3, padx=(5, 0), pady=5)
        
        # Advanced Chunking Options
        chunking_main_frame = ctk.CTkFrame(left_frame)
        chunking_main_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(5, 10))
        chunking_main_frame.grid_columnconfigure(0, weight=1)
        
        # Chunking header
        chunking_header = ctk.CTkFrame(chunking_main_frame, fg_color="transparent")
        chunking_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        chunking_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(chunking_header, text="🔧 Smart Chunking Options", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        
        # Enable/disable chunking
        chunking_options_frame = ctk.CTkFrame(chunking_header, fg_color="transparent")
        chunking_options_frame.grid(row=0, column=1, sticky="e", padx=(10, 0))
        
        self.chunking_checkbox = ctk.CTkCheckBox(
            chunking_options_frame,
            text="Enable Smart Chunking",
            variable=self.enable_chunking,
            font=ctk.CTkFont(size=12),
            command=self.on_chunking_toggle
        )
        self.chunking_checkbox.grid(row=0, column=0, sticky="e", padx=(0, 10))
        
        # Safe chunk mode checkbox
        self.safe_chunk_checkbox = ctk.CTkCheckBox(
            chunking_options_frame,
            text="Safe Mode (1800 tokens)",
            variable=self.safe_chunk_mode,
            font=ctk.CTkFont(size=11),
            command=self.on_safe_chunk_toggle
        )
        self.safe_chunk_checkbox.grid(row=0, column=1, sticky="e")
        
        # Chunking controls frame
        self.chunking_controls = ctk.CTkFrame(chunking_main_frame, fg_color="transparent")
        self.chunking_controls.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.chunking_controls.grid_columnconfigure((0, 1), weight=1)
        
        # Word threshold slider
        threshold_frame = ctk.CTkFrame(self.chunking_controls, fg_color="transparent")
        threshold_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=5)
        threshold_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(threshold_frame, text="📏 Chunking Threshold:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        
        self.threshold_slider = ctk.CTkSlider(
            threshold_frame,
            from_=200,
            to=5000,
            number_of_steps=48,
            variable=self.chunk_word_threshold,
            command=self.on_chunking_setting_change
        )
        self.threshold_slider.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.threshold_label = ctk.CTkLabel(
            threshold_frame,
            text=f"{self.chunk_word_threshold.get()} words",
            font=ctk.CTkFont(size=10),
            width=80
        )
        self.threshold_label.grid(row=0, column=2, padx=(5, 0))
        
        # Target chunk count slider
        target_frame = ctk.CTkFrame(self.chunking_controls, fg_color="transparent")
        target_frame.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=5)
        target_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(target_frame, text="🎯 Target Chunk Count:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        
        self.target_slider = ctk.CTkSlider(
            target_frame,
            from_=2,
            to=20,
            number_of_steps=18,
            variable=self.target_chunk_count,
            command=self.on_chunking_setting_change
        )
        self.target_slider.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.target_label = ctk.CTkLabel(
            target_frame,
            text=f"{self.target_chunk_count.get()} chunks",
            font=ctk.CTkFont(size=10),
            width=80
        )
        self.target_label.grid(row=0, column=2, padx=(5, 0))
        
        # Overlap and minimum size sliders
        advanced_frame = ctk.CTkFrame(self.chunking_controls, fg_color="transparent")
        advanced_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        advanced_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Overlap slider
        overlap_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        overlap_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        overlap_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(overlap_frame, text="🔗 Overlap:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        
        self.overlap_slider = ctk.CTkSlider(
            overlap_frame,
            from_=0,
            to=500,
            number_of_steps=25,
            variable=self.chunk_overlap,
            command=self.on_chunking_setting_change
        )
        self.overlap_slider.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.overlap_label = ctk.CTkLabel(
            overlap_frame,
            text=f"{self.chunk_overlap.get()} words",
            font=ctk.CTkFont(size=10),
            width=80
        )
        self.overlap_label.grid(row=0, column=2, padx=(5, 0))
        
        # Minimum size slider
        min_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        min_frame.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        min_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(min_frame, text="📐 Min Size:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        
        self.min_size_slider = ctk.CTkSlider(
            min_frame,
            from_=50,
            to=1000,
            number_of_steps=38,
            variable=self.min_chunk_size,
            command=self.on_chunking_setting_change
        )
        self.min_size_slider.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.min_size_label = ctk.CTkLabel(
            min_frame,
            text=f"{self.min_chunk_size.get()} words",
            font=ctk.CTkFont(size=10),
            width=80
        )
        self.min_size_label.grid(row=0, column=2, padx=(5, 0))
        
        # Chunking info and statistics
        self.chunking_info = ctk.CTkLabel(
            chunking_main_frame,
            text="💡 Files larger than threshold are automatically split using these settings",
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray40")
        )
        self.chunking_info.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Safe chunk mode info
        self.safe_chunk_info = ctk.CTkLabel(
            chunking_main_frame,
            text="🛡️ Safe Mode: Limits chunks to 1800 tokens for all models - ensures optimal performance and reliability",
            font=ctk.CTkFont(size=10),
            text_color=("blue", "lightblue")
        )
        self.safe_chunk_info.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Resume point selection
        resume_frame = ctk.CTkFrame(left_frame)
        resume_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 5))
        resume_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(resume_frame, text="🎯 Resume Options", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )
        
        resume_options_frame = ctk.CTkFrame(resume_frame, fg_color="transparent")
        resume_options_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        resume_options_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.resume_from_beginning = ctk.CTkRadioButton(
            resume_options_frame,
            text="From Beginning",
            variable=self.resume_point,
            value="from_beginning",
            font=ctk.CTkFont(size=11)
        )
        self.resume_from_beginning.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        
        self.resume_from_incomplete = ctk.CTkRadioButton(
            resume_options_frame,
            text="Skip Completed",
            variable=self.resume_point,
            value="skip_completed",
            font=ctk.CTkFont(size=11)
        )
        self.resume_from_incomplete.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        self.resume_from_selected = ctk.CTkRadioButton(
            resume_options_frame,
            text="From Selected",
            variable=self.resume_point,
            value="from_selected",
            font=ctk.CTkFont(size=11)
        )
        self.resume_from_selected.grid(row=0, column=2, sticky="w", padx=5, pady=2)
        
        # Chapter list with advanced management
        chapter_list_frame = ctk.CTkFrame(left_frame)
        chapter_list_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=15, pady=(5, 15))
        chapter_list_frame.grid_columnconfigure(0, weight=1)
        chapter_list_frame.grid_rowconfigure(2, weight=1)
        
        list_header = ctk.CTkFrame(chapter_list_frame, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        list_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(list_header, text="📚 Chapters & Chunks", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        
        # Management buttons
        mgmt_buttons = ctk.CTkFrame(list_header, fg_color="transparent")
        mgmt_buttons.grid(row=0, column=1, sticky="e")
        
        refresh_btn = ctk.CTkButton(
            mgmt_buttons,
            text="🔄",
            command=self.refresh_chapters,
            width=30,
            height=25,
            font=ctk.CTkFont(size=11)
        )
        refresh_btn.grid(row=0, column=0, padx=(0, 2))
        
        self.remove_btn = ctk.CTkButton(
            mgmt_buttons,
            text="🗑️",
            command=self.remove_selected_chunk,
            width=30,
            height=25,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.remove_btn.grid(row=0, column=1, padx=2)
        
        self.move_up_btn = ctk.CTkButton(
            mgmt_buttons,
            text="⬆️",
            command=self.move_chunk_up,
            width=30,
            height=25,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.move_up_btn.grid(row=0, column=2, padx=2)
        
        self.move_down_btn = ctk.CTkButton(
            mgmt_buttons,
            text="⬇️",
            command=self.move_chunk_down,
            width=30,
            height=25,
            font=ctk.CTkFont(size=11),
            state="disabled"
        )
        self.move_down_btn.grid(row=0, column=3, padx=(2, 0))
        
        # Instruction label
        ctk.CTkLabel(
            chapter_list_frame,
            text="💡 Select chunks to manage • Drag to reorder • Right-click for options",
            font=ctk.CTkFont(size=10),
            text_color=("gray60", "gray40")
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Enhanced chapter listbox with drag & drop support
        listbox_frame = ctk.CTkFrame(chapter_list_frame, fg_color="transparent")
        listbox_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        listbox_frame.grid_columnconfigure(0, weight=1)
        listbox_frame.grid_rowconfigure(0, weight=1)
        
        self.chapter_listbox = tk.Listbox(
            listbox_frame,
            height=8,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f6aa5",
            font=("Segoe UI", 10),
            selectmode=tk.EXTENDED  # Allow multiple selection
        )
        self.chapter_listbox.grid(row=0, column=0, sticky="nsew")
        self.chapter_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        self.chapter_listbox.bind('<Button-3>', self.show_chunk_context_menu)  # Right-click
        self.chapter_listbox.bind('<Button-1>', self.on_drag_start)
        self.chapter_listbox.bind('<B1-Motion>', self.on_drag_motion)
        self.chapter_listbox.bind('<ButtonRelease-1>', self.on_drag_end)
        
        # Add scrollbar
        chapter_scrollbar = ctk.CTkScrollbar(listbox_frame, command=self.chapter_listbox.yview)
        chapter_scrollbar.grid(row=0, column=1, sticky="ns")
        self.chapter_listbox.configure(yscrollcommand=chapter_scrollbar.set)
        
        # Drag and drop state variables
        self.drag_start_index = None
        self.drag_data = None
        
        # Right Column - Custom Prompt and Generation
        right_frame = ctk.CTkFrame(self.root)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 15), pady=(0, 15))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(2, weight=1)
        right_frame.grid_rowconfigure(4, weight=1)
        
        # Custom Prompt Section
        prompt_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        prompt_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        prompt_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(prompt_header, text="✏️ Custom Narration Style", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        
        # Prompt management buttons
        prompt_mgmt_frame = ctk.CTkFrame(prompt_header, fg_color="transparent")
        prompt_mgmt_frame.grid(row=0, column=1, sticky="e")
        
        save_prompt_btn = ctk.CTkButton(
            prompt_mgmt_frame,
            text="💾 Save",
            command=self.save_current_prompt,
            width=60,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        save_prompt_btn.grid(row=0, column=0, padx=(0, 5))
        
        load_prompt_btn = ctk.CTkButton(
            prompt_mgmt_frame,
            text="📂 Load",
            command=self.load_saved_prompt,
            width=60,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        load_prompt_btn.grid(row=0, column=1)
        
        self.prompt_textbox = ctk.CTkTextbox(
            right_frame,
            height=80,
            font=ctk.CTkFont(size=11)
        )
        self.prompt_textbox.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.prompt_textbox.insert("1.0", self.custom_prompt.get())
        
        # Preset prompt buttons
        preset_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        preset_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        preset_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        presets = [
            ("📚 Professional", "Use a professional, clear audiobook narration style with appropriate pacing and emotion."),
            ("🎭 Dramatic", "Use a dramatic, theatrical narration style with heightened emotion and dynamic delivery."),
            ("😌 Relaxing", "Use a calm, soothing narration style perfect for relaxation and bedtime listening."),
            ("🎪 Expressive", "Use an expressive, engaging narration style with varied emotion and captivating delivery.")
        ]
        
        for i, (name, prompt) in enumerate(presets):
            btn = ctk.CTkButton(
                preset_frame,
                text=name,
                command=lambda p=prompt: self.set_preset_prompt(p),
                height=25,
                font=ctk.CTkFont(size=10)
            )
            btn.grid(row=0, column=i, padx=2, pady=5, sticky="ew")
        
        # Generation Section
        generation_frame = ctk.CTkFrame(right_frame)
        generation_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        generation_frame.grid_columnconfigure(0, weight=1)
        generation_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(generation_frame, text="🎵 Generation", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(10, 8), sticky="w", padx=10
        )
        
        self.generate_btn = ctk.CTkButton(
            generation_frame, 
            text="🎧 Generate Audiobook", 
            command=self.start_generation,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45
        )
        self.generate_btn.grid(row=1, column=0, padx=(10, 5), pady=(0, 10), sticky="ew")
        
        preview_edit_frame = ctk.CTkFrame(generation_frame, fg_color="transparent")
        preview_edit_frame.grid(row=1, column=1, padx=(5, 10), pady=(0, 10), sticky="ew")
        preview_edit_frame.grid_columnconfigure(0, weight=1)
        preview_edit_frame.grid_columnconfigure(1, weight=1)
        
        self.preview_btn = ctk.CTkButton(
            preview_edit_frame,
            text="👁️ Preview Chunk Text",
            command=self.preview_chapter,
            height=45,
            font=ctk.CTkFont(size=11)
        )
        self.preview_btn.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        
        self.edit_chunks_btn = ctk.CTkButton(
            preview_edit_frame,
            text="✂️ Edit Chunks",
            command=self.edit_chunks,
            height=45,
            font=ctk.CTkFont(size=11)
        )
        self.edit_chunks_btn.grid(row=0, column=1, padx=(2, 0), sticky="ew")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(generation_frame, variable=self.progress_var, height=15)
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        
        # Audio Encoding Options Section
        encoding_frame = ctk.CTkFrame(right_frame)
        encoding_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 10))
        encoding_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ctk.CTkLabel(encoding_frame, text="🎵 Audio Encoding Options", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, pady=(10, 8), sticky="w", padx=10
        )
        
        # Output format selection
        ctk.CTkLabel(encoding_frame, text="Format:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        format_menu = ctk.CTkOptionMenu(
            encoding_frame,
            variable=self.output_format,
            values=["WAV", "MP3", "M4B"],
            command=self.on_format_change,
            height=30,
            font=ctk.CTkFont(size=11),
            width=80
        )
        format_menu.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # MP3 bitrate (only visible when MP3/M4B selected)
        self.bitrate_label = ctk.CTkLabel(encoding_frame, text="Bitrate:", font=ctk.CTkFont(size=12))
        self.bitrate_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        
        self.bitrate_menu = ctk.CTkOptionMenu(
            encoding_frame,
            variable=self.mp3_bitrate,
            values=["128", "192", "256", "320"],
            height=30,
            font=ctk.CTkFont(size=11),
            width=80
        )
        self.bitrate_menu.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # M4B chapter support
        self.chapters_checkbox = ctk.CTkCheckBox(
            encoding_frame,
            text="Include chapter markers (M4B)",
            variable=self.m4b_chapters,
            font=ctk.CTkFont(size=11)
        )
        self.chapters_checkbox.grid(row=2, column=2, sticky="w", padx=10, pady=5)
        
        # Update visibility based on initial format
        self.on_format_change(self.output_format.get())

        # Add project reset confirmation
        self.reset_confirmation = None
        
        # Status and log area
        self.status_text = ctk.CTkTextbox(
            right_frame,
            height=120,
            font=ctk.CTkFont(size=10)
        )
        self.status_text.grid(row=5, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # Bottom buttons
        bottom_frame = ctk.CTkFrame(self.root)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)
        bottom_frame.grid_columnconfigure(2, weight=1)
        bottom_frame.grid_columnconfigure(3, weight=1)
        bottom_frame.grid_columnconfigure(4, weight=1)

        open_output_btn = ctk.CTkButton(
            bottom_frame,
            text="📂 Open Output Folder",
            command=self.open_output_folder,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        open_output_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        play_btn = ctk.CTkButton(
            bottom_frame,
            text="▶️ Play Audiobook",
            command=self.play_audiobook,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        play_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.reset_btn = ctk.CTkButton(
            bottom_frame,
            text="🔄 Reset Project",
            command=self.reset_project,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.reset_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        terminal_btn = ctk.CTkButton(
            bottom_frame,
            text="💻 Terminal",
            command=self.toggle_terminal,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        terminal_btn.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        about_btn = ctk.CTkButton(
            bottom_frame,
            text="ℹ️ About",
            command=self.show_about,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        about_btn.grid(row=0, column=4, padx=10, pady=10, sticky="ew")
        
        # Terminal frame (initially hidden)
        self.terminal_frame = ctk.CTkFrame(self.root)
        self.terminal_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=15, pady=(0, 15))
        self.terminal_frame.grid_columnconfigure(0, weight=1)
        self.terminal_frame.grid_rowconfigure(1, weight=1)
        self.terminal_frame.grid_remove()  # Hide by default
        
        # Terminal header
        terminal_header = ctk.CTkFrame(self.terminal_frame, fg_color="transparent")
        terminal_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        terminal_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(terminal_header, text="💻 Terminal Output", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        
        clear_btn = ctk.CTkButton(
            terminal_header,
            text="🗑️ Clear",
            command=self.clear_terminal,
            width=60,
            height=25,
            font=ctk.CTkFont(size=10)
        )
        clear_btn.grid(row=0, column=1, padx=(0, 10))
        
        # Terminal text area
        self.terminal_text = ctk.CTkTextbox(
            self.terminal_frame,
            height=150,
            font=ctk.CTkFont(size=10, family="Consolas")
        )
        self.terminal_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Redirect print statements to terminal
        import sys
        from io import StringIO
        
        class TerminalRedirect:
            def __init__(self, gui_instance):
                self.gui = gui_instance
                
            def write(self, text):
                self.gui.terminal_queue.put(text)
                self.gui.process_terminal_queue()
                
            def flush(self):
                pass
                
        sys.stdout = TerminalRedirect(self)
        sys.stderr = TerminalRedirect(self)
        
        # Initialize chunking controls visibility
        self.on_chunking_toggle()
        
        # Initialize safe chunk mode visibility
        self.on_safe_chunk_toggle()
        
        # Initialize
        self.refresh_chapters()
        self.log_message("🎧 AI Audiobook Generator ready!")
        self.log_message("💡 Add chapters to folder and customize your narration style!")
        
    def set_preset_prompt(self, prompt):
        """Set a preset prompt"""
        self.prompt_textbox.delete("1.0", "end")
        self.prompt_textbox.insert("1.0", prompt)
        
    def save_current_prompt(self):
        """Save current prompt to saved prompts list"""
        current_prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
        if not current_prompt:
            messagebox.showwarning("Warning", "No prompt to save!")
            return
            
        # Get name for the prompt
        dialog = ctk.CTkInputDialog(text="Enter name for this prompt:", title="Save Prompt")
        prompt_name = dialog.get_input()
        
        if prompt_name:
            if not hasattr(self, 'saved_prompts'):
                self.saved_prompts = []
                
            # Check if name already exists
            existing_names = [p['name'] for p in self.saved_prompts]
            if prompt_name in existing_names:
                result = messagebox.askyesno("Confirm", f"A prompt named '{prompt_name}' already exists. Replace it?")
                if result:
                    # Remove existing prompt with same name
                    self.saved_prompts = [p for p in self.saved_prompts if p['name'] != prompt_name]
                else:
                    return
            
            # Add new prompt
            self.saved_prompts.append({
                'name': prompt_name,
                'prompt': current_prompt
            })
            
            # Save to file
            self.save_settings()
            self.log_message(f"💾 Saved prompt: {prompt_name}")
            messagebox.showinfo("Success", f"Prompt '{prompt_name}' saved successfully!")
    
    def load_saved_prompt(self):
        """Load a saved prompt"""
        if not hasattr(self, 'saved_prompts') or not self.saved_prompts:
            messagebox.showinfo("Info", "No saved prompts found.")
            return
            
        # Create selection window
        selection_window = ctk.CTkToplevel(self.root)
        selection_window.title("Load Saved Prompt")
        selection_window.geometry("600x400")
        selection_window.transient(self.root)
        selection_window.grab_set()
        
        # Center the window
        selection_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        ctk.CTkLabel(selection_window, text="📂 Saved Prompts", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Create listbox for prompts
        prompt_frame = ctk.CTkFrame(selection_window)
        prompt_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.prompt_listbox = tk.Listbox(
            prompt_frame,
            height=10,
            bg="#2b2b2b",
            fg="white",
            selectbackground="#1f6aa5",
            font=("Segoe UI", 11)
        )
        self.prompt_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Populate listbox
        for prompt_info in self.saved_prompts:
            self.prompt_listbox.insert(tk.END, prompt_info['name'])
        
        # Preview area
        preview_label = ctk.CTkLabel(selection_window, text="Preview:", font=ctk.CTkFont(size=12, weight="bold"))
        preview_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.prompt_preview = ctk.CTkTextbox(selection_window, height=80, font=ctk.CTkFont(size=10))
        self.prompt_preview.pack(fill="x", padx=20, pady=(0, 10))
        
        # Bind selection event
        def on_prompt_select(event):
            selection = self.prompt_listbox.curselection()
            if selection:
                prompt_info = self.saved_prompts[selection[0]]
                self.prompt_preview.delete("1.0", "end")
                self.prompt_preview.insert("1.0", prompt_info['prompt'])
        
        self.prompt_listbox.bind('<<ListboxSelect>>', on_prompt_select)
        
        # Buttons
        button_frame = ctk.CTkFrame(selection_window, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)
        
        def load_selected():
            selection = self.prompt_listbox.curselection()
            if selection:
                prompt_info = self.saved_prompts[selection[0]]
                self.prompt_textbox.delete("1.0", "end")
                self.prompt_textbox.insert("1.0", prompt_info['prompt'])
                self.log_message(f"📂 Loaded prompt: {prompt_info['name']}")
                selection_window.destroy()
            else:
                messagebox.showwarning("Warning", "Please select a prompt to load.")
        
        def delete_selected():
            selection = self.prompt_listbox.curselection()
            if selection:
                prompt_info = self.saved_prompts[selection[0]]
                result = messagebox.askyesno("Confirm", f"Delete prompt '{prompt_info['name']}'?")
                if result:
                    del self.saved_prompts[selection[0]]
                    self.save_settings()
                    self.prompt_listbox.delete(selection[0])
                    self.prompt_preview.delete("1.0", "end")
                    self.log_message(f"🗑️ Deleted prompt: {prompt_info['name']}")
            else:
                messagebox.showwarning("Warning", "Please select a prompt to delete.")
        
        load_btn = ctk.CTkButton(button_frame, text="📂 Load", command=load_selected, width=100)
        load_btn.pack(side="left", padx=(0, 10))
        
        delete_btn = ctk.CTkButton(button_frame, text="🗑️ Delete", command=delete_selected, width=100)
        delete_btn.pack(side="left", padx=(0, 10))
        
        cancel_btn = ctk.CTkButton(button_frame, text="❌ Cancel", command=selection_window.destroy, width=100)
        cancel_btn.pack(side="right")
    
    def on_format_change(self, format_choice):
        """Handle audio format selection changes"""
        if format_choice == "WAV":
            # Hide MP3/M4B specific options
            self.bitrate_label.grid_remove()
            self.bitrate_menu.grid_remove()
            self.chapters_checkbox.grid_remove()
        elif format_choice == "MP3":
            # Show bitrate, hide chapters
            self.bitrate_label.grid()
            self.bitrate_menu.grid()
            self.chapters_checkbox.grid_remove()
        elif format_choice == "M4B":
            # Show both bitrate and chapters
            self.bitrate_label.grid()
            self.bitrate_menu.grid()
            self.chapters_checkbox.grid()
        
        # Save current settings
        self.save_settings()
        
    def on_voice_change(self, voice):
        """Update voice description when voice changes"""
        # Could add a status message here if needed
        pass
    
    def on_model_change(self, model):
        """Handle TTS model selection changes"""
        model_description = self.tts_model_options.get(model, model)
        self.log_message(f"🤖 TTS Model changed to: {model_description}")
        
        # Save settings immediately
        self.save_settings()
        
    def on_chunking_toggle(self):
        """Handle chunking toggle changes"""
        if self.enable_chunking.get():
            # Show chunking controls but disable manual sliders for automatic chunking
            self.chunking_controls.grid()
            
            # Disable and grey out manual sliders when smart chunking is enabled
            self.threshold_slider.configure(state="disabled", fg_color="gray60", progress_color="gray40")
            self.target_slider.configure(state="disabled", fg_color="gray60", progress_color="gray40")
            self.overlap_slider.configure(state="disabled", fg_color="gray60", progress_color="gray40")
            self.min_size_slider.configure(state="disabled", fg_color="gray60", progress_color="gray40")
            
            # Also grey out the labels to show they're disabled
            self.threshold_label.configure(text_color="gray60")
            self.target_label.configure(text_color="gray60")
            self.overlap_label.configure(text_color="gray60")
            self.min_size_label.configure(text_color="gray60")
            
            threshold = self.chunk_word_threshold.get()
            self.chunking_info.configure(text=f"💡 Smart Chunking enabled - automatic intelligent splitting (manual controls disabled)")
            self.log_message("🔧 Smart Chunking enabled - automatic intelligent splitting with manual controls disabled")
            self.log_message("🎛️ DEBUG: Manual sliders disabled and greyed out for smart chunking mode")
        else:
            # Hide chunking controls
            self.chunking_controls.grid_remove()
            
            # Re-enable and restore colors for manual sliders when smart chunking is disabled
            self.threshold_slider.configure(state="normal", fg_color=("gray78", "gray23"), progress_color=("gray81", "gray19"))
            self.target_slider.configure(state="normal", fg_color=("gray78", "gray23"), progress_color=("gray81", "gray19"))
            self.overlap_slider.configure(state="normal", fg_color=("gray78", "gray23"), progress_color=("gray81", "gray19"))
            self.min_size_slider.configure(state="normal", fg_color=("gray78", "gray23"), progress_color=("gray81", "gray19"))
            
            # Restore label colors
            self.threshold_label.configure(text_color=("gray10", "gray90"))
            self.target_label.configure(text_color=("gray10", "gray90"))
            self.overlap_label.configure(text_color=("gray10", "gray90"))
            self.min_size_label.configure(text_color=("gray10", "gray90"))
            
            self.chunking_info.configure(text="⚠️ Chunking disabled - all files processed as single pieces")
            self.log_message("🔧 Smart Chunking disabled - files will be processed as complete pieces")
            self.log_message("🎛️ DEBUG: Manual sliders re-enabled and colors restored")
        
        # Save settings immediately
        self.save_settings()
        
        # Refresh chapters to reflect chunking changes
        self.refresh_chapters()
    
    def on_safe_chunk_toggle(self):
        """Handle safe chunk mode toggle changes"""
        if self.safe_chunk_mode.get():
            self.log_message("🛡️ Safe Chunk Mode enabled - chunks limited to 1800 tokens (~1350 words)")
            self.safe_chunk_info.configure(
                text="🛡️ Safe Mode: Active - chunks limited to 1800 tokens (~1350 words) for optimal performance"
            )
        else:
            self.log_message("🛡️ Safe Chunk Mode disabled - using standard token limits")
            self.safe_chunk_info.configure(
                text="🛡️ Safe Mode: Inactive - using standard token limits for all models"
            )
        
        # Save settings immediately
        self.save_settings()
        
        # Refresh chapters to reflect safe mode changes
        self.refresh_chapters()
    
    def on_chunking_setting_change(self, value):
        """Handle chunking slider changes"""
        # Update labels
        self.threshold_label.configure(text=f"{self.chunk_word_threshold.get()} words")
        self.target_label.configure(text=f"{self.target_chunk_count.get()} chunks")
        self.overlap_label.configure(text=f"{self.chunk_overlap.get()} words")
        self.min_size_label.configure(text=f"{self.min_chunk_size.get()} words")
        
        # Update info text
        if self.enable_chunking.get():
            threshold = self.chunk_word_threshold.get()
            self.chunking_info.configure(text=f"💡 Files >{threshold} words are automatically split using these settings")
        
        # Save settings
        self.save_settings()
        
        # Refresh chapters if needed (debounced)
        if hasattr(self, '_refresh_timer'):
            self.root.after_cancel(self._refresh_timer)
        self._refresh_timer = self.root.after(500, self.refresh_chapters)  # 500ms delay
        
    def browse_chapters_folder(self):
        """Browse for chapters folder and remember location"""
        folder = filedialog.askdirectory(
            title="Select Chapters Folder",
            initialdir=self.chapters_path.get() if os.path.exists(self.chapters_path.get()) else None
        )
        if folder:
            self.chapters_path.set(folder)
            self.save_settings()  # Save the new folder location immediately
            self.refresh_chapters()
            self.log_message(f"📁 Chapters folder updated: {folder}")
    
    def count_words(self, text):
        """Count words in text"""
        return len(text.split())
    
    def intelligent_chunk_text_with_settings(self, text):
        """Intelligent text chunking with user-defined settings, respecting paragraphs and safe mode"""
        target_count = self.target_chunk_count.get()
        overlap_words = self.chunk_overlap.get()
        min_size = self.min_chunk_size.get()
        
        # Apply safe mode limits if enabled
        if self.safe_chunk_mode.get():
            # Convert 1800 tokens to approximate words (tokens * 0.75)
            safe_word_limit = int(1800 * 0.75)  # ~1350 words
            min_size = min(min_size, safe_word_limit)
        
        # Split text into paragraphs, preserving empty lines
        paragraphs = text.split('\n\n')
        if not paragraphs:
            return [text]
        
        # Calculate word counts for each paragraph
        paragraph_info = []
        total_words = 0
        for para in paragraphs:
            word_count = len(para.split()) if para.strip() else 0
            paragraph_info.append({
                'text': para,
                'words': word_count,
                'is_empty': not para.strip()
            })
            total_words += word_count
        
        # If text is small enough, return as single chunk
        if total_words <= min_size or target_count <= 1:
            return [text]
        
        # Calculate target words per chunk, considering safe mode
        target_words_per_chunk = max(min_size, total_words // target_count)
        if self.safe_chunk_mode.get():
            safe_word_limit = int(1800 * 0.75)  # ~1350 words
            target_words_per_chunk = min(target_words_per_chunk, safe_word_limit)
        
        chunks = []
        current_chunk_text = []
        current_word_count = 0
        chunks_created = 0
        
        # In safe mode, we ignore target count and create as many chunks as needed
        use_target_limit = not self.safe_chunk_mode.get()
        
        i = 0
        while i < len(paragraph_info):
            para_info = paragraph_info[i]
            para_text = para_info['text']
            para_words = para_info['words']
            
            # For the last chunk when using target count (not in safe mode), include remaining paragraphs
            if (use_target_limit and chunks_created == target_count - 1 and
                i == len(paragraph_info) - 1):
                # Add final paragraph to complete the target count
                current_chunk_text.append(para_text)
                current_word_count += para_words
                break
            
            # Check if adding this paragraph would exceed limits
            would_exceed_target = current_word_count + para_words > target_words_per_chunk
            would_exceed_safe = (self.safe_chunk_mode.get() and
                               current_word_count + para_words > int(1800 * 0.75))
            
            if ((would_exceed_target or would_exceed_safe) and
                current_word_count >= min_size and
                current_chunk_text):
                
                # Finalize current chunk
                chunk_text = '\n\n'.join(current_chunk_text)
                chunks.append(chunk_text)
                chunks_created += 1
                
                # Start new chunk with overlap if specified
                if overlap_words > 0 and current_chunk_text:
                    # Try to include some overlap from the previous chunk
                    last_para = current_chunk_text[-1]
                    last_para_words = last_para.split()
                    if len(last_para_words) > overlap_words:
                        # Take last N words as overlap
                        overlap_text = ' '.join(last_para_words[-overlap_words:])
                        current_chunk_text = [overlap_text]
                        current_word_count = overlap_words
                    else:
                        # Take whole last paragraph as overlap
                        current_chunk_text = [last_para]
                        current_word_count = len(last_para_words)
                else:
                    current_chunk_text = []
                    current_word_count = 0
                
                # Check if we've reached target count limit (only when not in safe mode)
                if use_target_limit and chunks_created >= target_count:
                    # Force remaining content into final chunk
                    remaining_paras = [p['text'] for p in paragraph_info[i:]]
                    current_chunk_text.extend(remaining_paras)
                    break
            
            # Add current paragraph to chunk
            current_chunk_text.append(para_text)
            current_word_count += para_words
            i += 1
        
        # Add final chunk if there's content
        if current_chunk_text:
            chunk_text = '\n\n'.join(current_chunk_text)
            chunks.append(chunk_text)
        
        # If we ended up with only one chunk, try to split the largest paragraph
        if len(chunks) == 1 and target_count > 1:
            return self._split_large_paragraph(text, target_count, min_size)
        
        return chunks
    
    def _split_large_paragraph(self, text, target_count, min_size):
        """Split a large paragraph when paragraph-based chunking isn't sufficient"""
        sentences = self._split_into_sentences(text)
        if len(sentences) <= target_count:
            return sentences
        
        chunks = []
        current_chunk = []
        current_words = 0
        target_words = len(text.split()) // target_count
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            if (current_words + sentence_words > target_words and
                current_words >= min_size and
                current_chunk and
                len(chunks) < target_count - 1):
                
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_words = sentence_words
            else:
                current_chunk.append(sentence)
                current_words += sentence_words
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_into_sentences(self, text):
        """Split text into sentences, preserving structure"""
        import re
        
        # Split on sentence boundaries but keep the punctuation
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # Recombine sentences with their punctuation
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence.strip())
        
        return result if result else [text]
    
    def process_file_with_chunking(self, filepath):
        """Process a file and return list of chunks with metadata"""
        try:
            content = read_file_content(filepath)
            filename = os.path.basename(filepath)
            name_without_ext = os.path.splitext(filename)[0]

            # Remove markdown headers and formatting for word counting
            clean_content = content
            if filepath.endswith('.md'):
                # Basic markdown cleanup for word counting
                import re
                clean_content = re.sub(r'^#+\s+', '', clean_content, flags=re.MULTILINE)  # Remove headers
                clean_content = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_content)  # Remove bold
                clean_content = re.sub(r'\*(.*?)\*', r'\1', clean_content)  # Remove italic
                clean_content = re.sub(r'`(.*?)`', r'\1', clean_content)  # Remove code

            word_count = self.count_words(clean_content)
            
            # Determine chunking threshold based on safe mode
            threshold = self.chunk_word_threshold.get()
            if self.safe_chunk_mode.get():
                # Convert 1800 tokens to approximate words (tokens * 0.75)
                safe_word_limit = int(1800 * 0.75)  # ~1350 words
                threshold = min(threshold, safe_word_limit)

            # Check if chunking is disabled or file is small enough
            if not self.enable_chunking.get() or word_count <= threshold:
                if not self.enable_chunking.get() and word_count > threshold:
                    return [(filename, content, f"{name_without_ext} (Complete - {word_count} words)")]
                else:
                    return [(filename, content, f"{name_without_ext} ({word_count} words)")]
            else:
                # Use the user-configurable intelligent chunking with safe mode consideration
                chunks = self.intelligent_chunk_text_with_settings(clean_content)
                chunk_info = []
                for i, chunk in enumerate(chunks):
                    chunk_words = self.count_words(chunk)
                    chunk_filename = f"{name_without_ext}_part_{i+1:02d}.txt"
                    chunk_display = f"{name_without_ext} Part {i+1}/{len(chunks)} ({chunk_words} words)"
                    chunk_info.append((chunk_filename, chunk, chunk_display))
                return chunk_info

        except Exception as e:
            self.log_message(f"❌ Error processing {filepath}: {str(e)}")
            return []

    def refresh_chapters(self):
        """Refresh the chapter list with visual feedback"""
        self.chapter_listbox.delete(0, tk.END)
        chapters_dir = self.chapters_path.get()

        if os.path.exists(chapters_dir):
            # Look for both .txt and .md files
            txt_files = glob.glob(os.path.join(chapters_dir, '*.txt'))
            md_files = glob.glob(os.path.join(chapters_dir, '*.md'))
            all_files = sorted(txt_files + md_files)

            total_chunks = 0
            completed_count = 0
            self.file_chunks = {}  # Store chunk information

            # Generate project ID
            self.project_id = self.state_manager.get_project_id(chapters_dir)

            # Check for existing project state
            project_state = self.state_manager.load_project_state(self.project_id)
            completed_chunks = self.state_manager.get_completed_chunks(self.project_id)

            if completed_chunks:
                self.log_message(f"📋 Resuming project - {len(completed_chunks)} chunks already completed")
            else:
                self.log_message("📋 Starting new project")

            for file_path in all_files:
                chunks = self.process_file_with_chunking(file_path)
                if chunks:
                    for chunk_filename, chunk_content, display_name in chunks:
                        # Check if this chunk is already completed
                        output_file = os.path.join(self.output_path.get(), chunk_filename.replace('.txt', '.wav'))
                        if output_file in completed_chunks:
                            display_name = f"✅ {display_name} (completed)"
                            self.chapter_listbox.insert(tk.END, display_name)
                            self.chapter_listbox.itemconfig(tk.END, {'fg': 'green', 'bg': '#2d3a2d'})
                            completed_count += 1
                        else:
                            self.chapter_listbox.insert(tk.END, display_name)
                            self.chapter_listbox.itemconfig(tk.END, {'fg': 'white', 'bg': '#2b2b2b'})

                        self.file_chunks[display_name] = {
                            'original_file': file_path,
                            'chunk_filename': chunk_filename,
                            'content': chunk_content,
                            'completed': output_file in completed_chunks
                        }
                        total_chunks += 1

            # Add visual summary
            if total_chunks > 0:
                progress_percent = (completed_count / total_chunks) * 100
                progress_bar = '▓' * int(progress_percent / 10) + '░' * (10 - int(progress_percent / 10))
                self.log_message(f"📊 Project Progress: {progress_bar} {progress_percent:.1f}%")

            self.log_message(f"📚 Found {len(all_files)} files, {total_chunks} chunks")
            self.log_message(f"🎯 Completed: {completed_count}/{total_chunks} chunks")

            if any(self.count_words(read_file_content(f)) > 800 for f in all_files):
                if self.enable_chunking.get():
                    self.log_message("📄 Large files automatically split into chunks")
                else:
                    self.log_message("📄 Large files will be processed as complete pieces (chunking disabled)")
        else:
            self.log_message(f"❌ Chapters folder not found: {chapters_dir}")
            self.file_chunks = {}
            
    def on_drag_start(self, event):
        """Handle start of drag operation"""
        index = self.chapter_listbox.nearest(event.y)
        if index >= 0 and index < self.chapter_listbox.size():
            self.drag_start_index = index
            self.drag_data = self.chapter_listbox.get(index)
    
    def on_drag_motion(self, event):
        """Handle drag motion"""
        if self.drag_start_index is not None:
            current_index = self.chapter_listbox.nearest(event.y)
            if current_index != self.drag_start_index and 0 <= current_index < self.chapter_listbox.size():
                # Visual feedback for drag operation
                self.chapter_listbox.selection_clear(0, tk.END)
                self.chapter_listbox.selection_set(current_index)
    
    def on_drag_end(self, event):
        """Handle end of drag operation"""
        if self.drag_start_index is not None:
            end_index = self.chapter_listbox.nearest(event.y)
            if (end_index != self.drag_start_index and
                0 <= end_index < self.chapter_listbox.size()):
                self.move_chunk_to_position(self.drag_start_index, end_index)
        
        self.drag_start_index = None
        self.drag_data = None
    
    def move_chunk_to_position(self, from_index, to_index):
        """Move chunk from one position to another"""
        try:
            # Get the item data
            item_text = self.chapter_listbox.get(from_index)
            
            # Find the corresponding chunk in our data
            chunk_key = None
            for key in self.file_chunks:
                display_name = key.split(' (')[0] if ' (' in key else key
                if item_text.startswith(display_name) or item_text.startswith(f"✅ {display_name}"):
                    chunk_key = key
                    break
            
            if chunk_key:
                # Update the order
                if chunk_key in self.chunk_order:
                    self.chunk_order.remove(chunk_key)
                self.chunk_order.insert(to_index, chunk_key)
                
                # Refresh the display
                self.refresh_chapter_display()
                self.log_message(f"📝 Moved chunk to position {to_index + 1}")
                
        except Exception as e:
            self.log_message(f"❌ Error moving chunk: {str(e)}")
    
    def remove_selected_chunk(self):
        """Remove selected chunks from the list"""
        selection = self.chapter_listbox.curselection()
        if not selection:
            return
        
        # Confirm removal
        if len(selection) == 1:
            item_text = self.chapter_listbox.get(selection[0])
            message = f"Remove this chunk?\n\n{item_text}"
        else:
            message = f"Remove {len(selection)} selected chunks?"
        
        if messagebox.askyesno("Confirm Removal", message):
            # Get the keys to remove
            keys_to_remove = []
            for index in selection:
                item_text = self.chapter_listbox.get(index)
                for key in self.file_chunks:
                    display_name = key.split(' (')[0] if ' (' in key else key
                    if item_text.startswith(display_name) or item_text.startswith(f"✅ {display_name}"):
                        keys_to_remove.append(key)
                        break
            
            # Remove from data structures
            for key in keys_to_remove:
                if key in self.file_chunks:
                    del self.file_chunks[key]
                if key in self.chunk_order:
                    self.chunk_order.remove(key)
            
            # Refresh display
            self.refresh_chapter_display()
            self.log_message(f"🗑️ Removed {len(keys_to_remove)} chunk(s)")
    
    def move_chunk_up(self):
        """Move selected chunk up in the list"""
        selection = self.chapter_listbox.curselection()
        if len(selection) == 1 and selection[0] > 0:
            self.move_chunk_to_position(selection[0], selection[0] - 1)
    
    def move_chunk_down(self):
        """Move selected chunk down in the list"""
        selection = self.chapter_listbox.curselection()
        if len(selection) == 1 and selection[0] < self.chapter_listbox.size() - 1:
            self.move_chunk_to_position(selection[0], selection[0] + 1)
    
    def show_chunk_context_menu(self, event):
        """Show context menu for chunk management"""
        index = self.chapter_listbox.nearest(event.y)
        if index >= 0 and index < self.chapter_listbox.size():
            # Select the item
            self.chapter_listbox.selection_clear(0, tk.END)
            self.chapter_listbox.selection_set(index)
            
            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            
            item_text = self.chapter_listbox.get(index)
            is_completed = item_text.startswith("✅")
            
            context_menu.add_command(
                label="👁️ Preview",
                command=self.preview_chapter
            )
            context_menu.add_separator()
            
            if index > 0:
                context_menu.add_command(
                    label="⬆️ Move Up",
                    command=self.move_chunk_up
                )
            
            if index < self.chapter_listbox.size() - 1:
                context_menu.add_command(
                    label="⬇️ Move Down",
                    command=self.move_chunk_down
                )
            
            context_menu.add_separator()
            context_menu.add_command(
                label="🗑️ Remove",
                command=self.remove_selected_chunk
            )
            
            if is_completed:
                context_menu.add_separator()
                context_menu.add_command(
                    label="🔄 Mark as Incomplete",
                    command=lambda: self.toggle_chunk_completion(index)
                )
            else:
                context_menu.add_separator()
                context_menu.add_command(
                    label="✅ Mark as Complete",
                    command=lambda: self.toggle_chunk_completion(index)
                )
            
            # Show menu
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def toggle_chunk_completion(self, index):
        """Toggle completion status of a chunk"""
        try:
            item_text = self.chapter_listbox.get(index)
            
            # Find the chunk key
            chunk_key = None
            for key in self.file_chunks:
                display_name = key.split(' (')[0] if ' (' in key else key
                if item_text.startswith(display_name) or item_text.startswith(f"✅ {display_name}"):
                    chunk_key = key
                    break
            
            if chunk_key and chunk_key in self.file_chunks:
                # Toggle completion status
                current_status = self.file_chunks[chunk_key].get('completed', False)
                self.file_chunks[chunk_key]['completed'] = not current_status
                
                # Update project state
                if self.project_id:
                    chunk_info = self.file_chunks[chunk_key]
                    output_file = os.path.join(self.output_path.get(),
                                             chunk_info['chunk_filename'].replace('.txt', '.wav'))
                    
                    if not current_status:  # Now completed
                        self.state_manager.mark_chunk_completed(self.project_id, output_file)
                        self.log_message(f"✅ Marked as completed: {chunk_key}")
                    else:  # Now incomplete
                        # Remove from completed chunks
                        completed_chunks = self.state_manager.get_completed_chunks(self.project_id)
                        if output_file in completed_chunks:
                            completed_chunks.remove(output_file)
                            # Save updated state
                            self.state_manager.project_states[self.project_id]['completed_chunks'] = completed_chunks
                            self.state_manager.save_project_state(self.project_id, self.state_manager.project_states[self.project_id])
                        self.log_message(f"🔄 Marked as incomplete: {chunk_key}")
                
                # Refresh display
                self.refresh_chapter_display()
                
        except Exception as e:
            self.log_message(f"❌ Error toggling completion: {str(e)}")
    
    def refresh_chapter_display(self):
        """Refresh the chapter display maintaining current order"""
        self.chapter_listbox.delete(0, tk.END)
        
        # Use chunk_order if available, otherwise use file_chunks keys
        if self.chunk_order:
            display_order = [key for key in self.chunk_order if key in self.file_chunks]
            # Add any new chunks not in the order
            for key in self.file_chunks:
                if key not in display_order:
                    display_order.append(key)
        else:
            display_order = list(self.file_chunks.keys())
        
        # Update chunk_order to match current state
        self.chunk_order = display_order.copy()
        
        for display_name in display_order:
            if display_name in self.file_chunks:
                chunk_info = self.file_chunks[display_name]
                if chunk_info.get('completed', False):
                    self.chapter_listbox.insert(tk.END, f"✅ {display_name}")
                    self.chapter_listbox.itemconfig(tk.END, {'fg': 'green', 'bg': '#2d3a2d'})
                else:
                    self.chapter_listbox.insert(tk.END, display_name)
                    self.chapter_listbox.itemconfig(tk.END, {'fg': 'white', 'bg': '#2b2b2b'})

    def on_chapter_select(self, event):
        """Handle chapter selection"""
        selection = self.chapter_listbox.curselection()
        if selection:
            self.preview_btn.configure(state="normal")
            self.remove_btn.configure(state="normal")
            # Enable move buttons based on position
            if len(selection) == 1:  # Only enable move for single selection
                index = selection[0]
                self.move_up_btn.configure(state="normal" if index > 0 else "disabled")
                self.move_down_btn.configure(state="normal" if index < self.chapter_listbox.size() - 1 else "disabled")
            else:
                self.move_up_btn.configure(state="disabled")
                self.move_down_btn.configure(state="disabled")
        else:
            self.preview_btn.configure(state="disabled")
            self.remove_btn.configure(state="disabled")
            self.move_up_btn.configure(state="disabled")
            self.move_down_btn.configure(state="disabled")
            
    def preview_chapter(self):
        """Preview selected chapter content"""
        selection = self.chapter_listbox.curselection()
        if not selection:
            return
            
        display_name = self.chapter_listbox.get(selection[0])
        
        try:
            # Get content from chunk data
            chunk_key = None
            
            # Find the correct chunk key by matching display names
            for key in self.file_chunks:
                if display_name.startswith("✅ "):
                    clean_display = display_name[2:].strip()  # Remove ✅ prefix
                else:
                    clean_display = display_name
                
                # Match by base name (without word count part)
                key_base = key.split(' (')[0] if ' (' in key else key
                display_base = clean_display.split(' (')[0] if ' (' in clean_display else clean_display
                
                if key_base == display_base or clean_display == key:
                    chunk_key = key
                    break
            
            if chunk_key and chunk_key in self.file_chunks:
                content = self.file_chunks[chunk_key]['content']
                title = f"Preview: {chunk_key}"
            else:
                # Fallback to first chunk if exact match not found
                if self.file_chunks:
                    first_key = list(self.file_chunks.keys())[0]
                    content = self.file_chunks[first_key]['content']
                    title = f"Preview: {first_key} (fallback)"
                else:
                    raise Exception("No chunk content available")
            
            # Create preview window
            preview_window = ctk.CTkToplevel(self.root)
            preview_window.title(title)
            preview_window.geometry("700x500")
            
            text_widget = ctk.CTkTextbox(preview_window, font=ctk.CTkFont(size=12))
            text_widget.pack(fill="both", expand=True, padx=20, pady=20)
            text_widget.insert("1.0", content)
            text_widget.configure(state="disabled")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not preview chapter: {str(e)}")

    def edit_chunks(self):
        """Open chunk editor window to preview and edit file chunks"""
        if not hasattr(self, 'file_chunks') or not self.file_chunks:
            messagebox.showinfo("Info", "No files with chunks found. Load some files first!")
            return

        # Group chunks by original file
        files_with_chunks = {}
        for display_name, chunk_info in self.file_chunks.items():
            original_file = chunk_info['original_file']
            if original_file not in files_with_chunks:
                files_with_chunks[original_file] = []
            files_with_chunks[original_file].append((display_name, chunk_info))

        # Create chunk editor window
        self.chunk_editor = ctk.CTkToplevel(self.root)
        self.chunk_editor.title("✂️ Chunk Editor")
        self.chunk_editor.geometry("1200x800")
        self.chunk_editor.minsize(1000, 600)
        
        # Configure grid
        self.chunk_editor.grid_columnconfigure(0, weight=1)
        self.chunk_editor.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self.chunk_editor)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="✂️ Chunk Editor",
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=10)

        total_files = len(files_with_chunks)
        total_chunks = len(self.file_chunks)
        ctk.CTkLabel(
            header_frame,
            text=f"📊 {total_files} files, {total_chunks} chunks",
            font=ctk.CTkFont(size=14)
        ).grid(row=0, column=1, sticky="e", padx=15, pady=10)

        # Main content area
        main_frame = ctk.CTkFrame(self.chunk_editor)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=3)
        main_frame.grid_rowconfigure(0, weight=1)

        # Left panel - File and chunk list
        left_panel = ctk.CTkFrame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left_panel,
            text="📚 Files & Chunks",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        # Chunk tree/list
        self.chunk_tree_frame = ctk.CTkScrollableFrame(left_panel)
        self.chunk_tree_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.chunk_tree_frame.grid_columnconfigure(0, weight=1)

        # Right panel - Chunk content editor
        right_panel = ctk.CTkFrame(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        # Editor header
        editor_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        editor_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        editor_header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            editor_header,
            text="✏️ Chunk Editor",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        self.chunk_info_label = ctk.CTkLabel(
            editor_header,
            text="Select a chunk to edit",
            font=ctk.CTkFont(size=12)
        )
        self.chunk_info_label.grid(row=0, column=1, sticky="e")

        # Chunk content editor
        self.chunk_editor_text = ctk.CTkTextbox(
            right_panel,
            font=ctk.CTkFont(size=11),
            wrap="word"
        )
        self.chunk_editor_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

        # Editor buttons
        editor_buttons = ctk.CTkFrame(right_panel, fg_color="transparent")
        editor_buttons.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        editor_buttons.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.save_chunk_btn = ctk.CTkButton(
            editor_buttons,
            text="💾 Save Chunk",
            command=self.save_current_chunk,
            state="disabled"
        )
        self.save_chunk_btn.grid(row=0, column=0, padx=2, sticky="ew")

        self.split_chunk_btn = ctk.CTkButton(
            editor_buttons,
            text="✂️ Split Here",
            command=self.split_current_chunk,
            state="disabled"
        )
        self.split_chunk_btn.grid(row=0, column=1, padx=2, sticky="ew")

        self.merge_chunk_btn = ctk.CTkButton(
            editor_buttons,
            text="🔗 Merge Next",
            command=self.merge_with_next_chunk,
            state="disabled"
        )
        self.merge_chunk_btn.grid(row=0, column=2, padx=2, sticky="ew")

        self.reset_chunks_btn = ctk.CTkButton(
            editor_buttons,
            text="🔄 Reset File",
            command=self.reset_file_chunks,
            state="disabled"
        )
        self.reset_chunks_btn.grid(row=0, column=3, padx=2, sticky="ew")

        # Bottom buttons
        bottom_frame = ctk.CTkFrame(self.chunk_editor)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        bottom_frame.grid_columnconfigure((0, 1), weight=1)

        apply_btn = ctk.CTkButton(
            bottom_frame,
            text="✅ Apply Changes",
            command=self.apply_chunk_changes,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        apply_btn.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

        cancel_btn = ctk.CTkButton(
            bottom_frame,
            text="❌ Cancel",
            command=self.chunk_editor.destroy,
            font=ctk.CTkFont(size=14),
            height=40
        )
        cancel_btn.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="ew")

        # Populate the chunk tree
        self.populate_chunk_tree(files_with_chunks)
        
        # Store original chunks for reset functionality
        self.original_chunks = self.file_chunks.copy()
        self.current_chunk_key = None

    def populate_chunk_tree(self, files_with_chunks):
        """Populate the chunk tree with files and their chunks"""
        row = 0
        self.chunk_buttons = {}
        
        for file_path, chunks in files_with_chunks.items():
            file_name = os.path.basename(file_path)
            
            # File header
            file_frame = ctk.CTkFrame(self.chunk_tree_frame)
            file_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
            file_frame.grid_columnconfigure(0, weight=1)
            
            # File info
            total_words = sum(self.count_words(chunk_info['content']) for _, chunk_info in chunks)
            file_label = ctk.CTkLabel(
                file_frame,
                text=f"📄 {file_name}",
                font=ctk.CTkFont(size=13, weight="bold")
            )
            file_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
            
            stats_label = ctk.CTkLabel(
                file_frame,
                text=f"{len(chunks)} chunks, {total_words} words total",
                font=ctk.CTkFont(size=10)
            )
            stats_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 5))
            
            row += 1
            
            # Chunk buttons for this file
            for i, (display_name, chunk_info) in enumerate(chunks):
                chunk_words = self.count_words(chunk_info['content'])
                
                chunk_btn = ctk.CTkButton(
                    self.chunk_tree_frame,
                    text=f"   📝 Part {i+1} ({chunk_words} words)",
                    command=lambda key=display_name: self.select_chunk_for_editing(key),
                    anchor="w",
                    height=30,
                    font=ctk.CTkFont(size=11)
                )
                chunk_btn.grid(row=row, column=0, sticky="ew", pady=1, padx=(20, 0))
                self.chunk_buttons[display_name] = chunk_btn
                row += 1
            
            # Spacing between files
            row += 1

    def select_chunk_for_editing(self, chunk_key):
        """Select a chunk for editing"""
        if chunk_key not in self.file_chunks:
            return
            
        # Save current chunk if one was being edited
        if self.current_chunk_key and self.current_chunk_key in self.file_chunks:
            self.save_current_chunk()
        
        self.current_chunk_key = chunk_key
        chunk_info = self.file_chunks[chunk_key]
        
        # Update UI
        self.chunk_editor_text.delete("1.0", "end")
        self.chunk_editor_text.insert("1.0", chunk_info['content'])
        
        # Update info label
        word_count = self.count_words(chunk_info['content'])
        self.chunk_info_label.configure(text=f"Editing: {chunk_key} ({word_count} words)")
        
        # Enable buttons
        self.save_chunk_btn.configure(state="normal")
        self.split_chunk_btn.configure(state="normal")
        self.reset_chunks_btn.configure(state="normal")
        
        # Check if merge is possible (has next chunk from same file)
        original_file = chunk_info['original_file']
        file_chunks = [k for k, v in self.file_chunks.items() if v['original_file'] == original_file]
        current_index = file_chunks.index(chunk_key)
        if current_index < len(file_chunks) - 1:
            self.merge_chunk_btn.configure(state="normal")
        else:
            self.merge_chunk_btn.configure(state="disabled")
        
        # Highlight selected chunk button
        for key, btn in self.chunk_buttons.items():
            if key == chunk_key:
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5"))
            else:
                btn.configure(fg_color=("gray75", "gray25"))

    def save_current_chunk(self):
        """Save the currently edited chunk"""
        if not self.current_chunk_key:
            return
            
        new_content = self.chunk_editor_text.get("1.0", "end-1c")
        self.file_chunks[self.current_chunk_key]['content'] = new_content
        
        # Update word count display
        word_count = self.count_words(new_content)
        self.chunk_info_label.configure(text=f"Editing: {self.current_chunk_key} ({word_count} words)")

    def split_current_chunk(self):
        """Split current chunk at cursor position"""
        if not self.current_chunk_key:
            return
            
        # Get cursor position
        cursor_pos = self.chunk_editor_text.index(tk.INSERT)
        
        # Get content before and after cursor
        all_content = self.chunk_editor_text.get("1.0", "end-1c")
        before_cursor = self.chunk_editor_text.get("1.0", cursor_pos)
        after_cursor = self.chunk_editor_text.get(cursor_pos, "end-1c")
        
        if not before_cursor.strip() or not after_cursor.strip():
            messagebox.showwarning("Warning", "Cannot split at this position - both parts must have content.")
            return
        
        # Create new chunk info
        original_info = self.file_chunks[self.current_chunk_key]
        original_file = original_info['original_file']
        
        # Find all chunks from the same file and their order
        file_chunks = [(k, v) for k, v in self.file_chunks.items() if v['original_file'] == original_file]
        file_chunks.sort(key=lambda x: x[0])  # Sort by display name
        
        current_index = next(i for i, (k, v) in enumerate(file_chunks) if k == self.current_chunk_key)
        
        # Generate new chunk names
        base_name = os.path.splitext(os.path.basename(original_file))[0]
        new_chunk1_name = f"{base_name} Part {current_index + 1}A ({self.count_words(before_cursor)} words)"
        new_chunk2_name = f"{base_name} Part {current_index + 1}B ({self.count_words(after_cursor)} words)"
        
        # Update current chunk
        self.file_chunks[self.current_chunk_key]['content'] = before_cursor
        
        # Create new chunk
        new_chunk_info = {
            'original_file': original_file,
            'chunk_filename': f"{base_name}_part_{current_index + 1}B.txt",
            'content': after_cursor
        }
        self.file_chunks[new_chunk2_name] = new_chunk_info
        
        # Refresh the tree
        self.refresh_chunk_tree()
        
        messagebox.showinfo("Success", "Chunk split successfully!")

    def merge_with_next_chunk(self):
        """Merge current chunk with the next chunk from the same file"""
        if not self.current_chunk_key:
            return
            
        current_info = self.file_chunks[self.current_chunk_key]
        original_file = current_info['original_file']
        
        # Find next chunk from same file
        file_chunks = [k for k, v in self.file_chunks.items() if v['original_file'] == original_file]
        current_index = file_chunks.index(self.current_chunk_key)
        
        if current_index >= len(file_chunks) - 1:
            messagebox.showwarning("Warning", "No next chunk to merge with.")
            return
        
        next_chunk_key = file_chunks[current_index + 1]
        next_info = self.file_chunks[next_chunk_key]
        
        # Merge content
        current_content = self.chunk_editor_text.get("1.0", "end-1c")
        merged_content = current_content + "\n\n" + next_info['content']
        
        # Update current chunk
        self.file_chunks[self.current_chunk_key]['content'] = merged_content
        self.chunk_editor_text.delete("1.0", "end")
        self.chunk_editor_text.insert("1.0", merged_content)
        
        # Remove next chunk
        del self.file_chunks[next_chunk_key]
        
        # Refresh the tree
        self.refresh_chunk_tree()
        
        messagebox.showinfo("Success", "Chunks merged successfully!")

    def reset_file_chunks(self):
        """Reset chunks for the current file back to original"""
        if not self.current_chunk_key:
            return
            
        current_info = self.file_chunks[self.current_chunk_key]
        original_file = current_info['original_file']
        
        result = messagebox.askyesno(
            "Confirm Reset",
            f"Reset all chunks for {os.path.basename(original_file)} back to original splits?"
        )
        
        if result:
            # Remove all chunks for this file
            keys_to_remove = [k for k, v in self.file_chunks.items() if v['original_file'] == original_file]
            for key in keys_to_remove:
                del self.file_chunks[key]
            
            # Regenerate original chunks
            original_chunks = self.process_file_with_chunking(original_file)
            for chunk_filename, chunk_content, display_name in original_chunks:
                self.file_chunks[display_name] = {
                    'original_file': original_file,
                    'chunk_filename': chunk_filename,
                    'content': chunk_content
                }
            
            # Refresh the tree
            self.refresh_chunk_tree()
            
            # Clear editor
            self.current_chunk_key = None
            self.chunk_editor_text.delete("1.0", "end")
            self.chunk_info_label.configure(text="Select a chunk to edit")
            self.save_chunk_btn.configure(state="disabled")
            self.split_chunk_btn.configure(state="disabled")
            self.merge_chunk_btn.configure(state="disabled")
            self.reset_chunks_btn.configure(state="disabled")

    def refresh_chunk_tree(self):
        """Refresh the chunk tree display"""
        # Clear existing tree
        for widget in self.chunk_tree_frame.winfo_children():
            widget.destroy()
        
        # Regroup chunks by file
        files_with_chunks = {}
        for display_name, chunk_info in self.file_chunks.items():
            original_file = chunk_info['original_file']
            if original_file not in files_with_chunks:
                files_with_chunks[original_file] = []
            files_with_chunks[original_file].append((display_name, chunk_info))
        
        # Repopulate
        self.populate_chunk_tree(files_with_chunks)

    def apply_chunk_changes(self):
        """Apply all chunk changes and close the editor"""
        # Save current chunk if being edited
        if self.current_chunk_key:
            self.save_current_chunk()
        
        # Refresh the main chapter list
        self.refresh_chapters()
        
        # Close editor
        self.chunk_editor.destroy()
        
        self.log_message("✅ Chunk changes applied successfully!")
        messagebox.showinfo("Success", "All chunk changes have been applied!")
            
    def log_message(self, message):
        """Add message to status log with visual flair"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Add some emoji and color enhancements
        if "✅" in message or "Completed" in message:
            message = f"🟢 {message}"
        elif "❌" in message or "Error" in message or "Warning" in message:
            message = f"🔴 {message}"
        elif "📋" in message or "Resuming" in message:
            message = f"🔵 {message}"
        elif "🎧" in message or "Starting" in message:
            message = f"🟡 {message}"
        elif "DEBUG" in message or "API" in message or "Network" in message:
            message = f"🔍 {message}"

        formatted_message = f"[{timestamp}] {message}"
        self.status_text.insert("end", f"{formatted_message}\n")
        self.status_text.see("end")
        
        # Also log to terminal if it exists
        if hasattr(self, 'terminal_text'):
            self.terminal_text.insert("end", f"{formatted_message}\n")
            self.terminal_text.see("end")
        
        self.root.update_idletasks()
        
    def start_generation(self):
        """Start audiobook generation in a separate thread"""
        if self.is_generating:
            return

        # Validate inputs
        if not self.api_key.get().strip():
            messagebox.showerror("Error", "Please enter your Google API Key")
            return

        # Update environment
        os.environ['GOOGLE_API_KEY'] = self.api_key.get().strip()
        os.environ['NARRATOR_VOICE'] = self.narrator_voice.get()
        os.environ['TTS_MODEL'] = self.tts_model.get()

        # Get custom prompt
        custom_prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
        if not custom_prompt:
            custom_prompt = "Use a professional audiobook narration style."

        self.is_generating = True
        self.generate_btn.configure(text="🔄 Generating...", state="disabled")
        self.log_message("🚀 Launching audiobook generation...")

        # Start generation in separate thread
        thread = threading.Thread(target=self.generate_audiobook, args=(custom_prompt,))
        thread.daemon = True
        thread.start()
        
    def generate_audiobook(self, custom_prompt):
        """Generate audiobook (runs in separate thread)"""
        try:
            self.log_message("🎧 Starting audiobook generation...")
    
            # Update progress indicator
            self.progress_indicator.configure(text="🚀 Generating audiobook...")

            # Get chunks from the listbox
            if not hasattr(self, 'file_chunks') or not self.file_chunks:
                self.log_message("❌ No files or chunks found!")
                return

            # Determine which chunks to process based on resume option
            resume_option = self.resume_point.get()
            all_chunks = list(self.file_chunks.keys())
            completed_chunks = []  # Initialize completed_chunks for all branches
            
            if resume_option == "from_beginning":
                # Process all chunks, mark all as incomplete first
                chunks_to_process = all_chunks
                for chunk_key in self.file_chunks:
                    self.file_chunks[chunk_key]['completed'] = False
                self.log_message("🔄 Resume from beginning - processing all chunks")
                
            elif resume_option == "from_selected":
                # Start from selected chunk
                selection = self.chapter_listbox.curselection()
                if not selection:
                    self.log_message("❌ No chunk selected! Please select a chunk to start from.")
                    return
                
                selected_index = selection[0]
                selected_item = self.chapter_listbox.get(selected_index)
                
                # Find selected chunk key
                selected_chunk_key = None
                for key in self.file_chunks:
                    display_name = key.split(' (')[0] if ' (' in key else key
                    if selected_item.startswith(display_name) or selected_item.startswith(f"✅ {display_name}"):
                        selected_chunk_key = key
                        break
                
                if selected_chunk_key:
                    # Get chunks from selected position onward
                    if self.chunk_order:
                        try:
                            start_index = self.chunk_order.index(selected_chunk_key)
                            chunks_to_process = self.chunk_order[start_index:]
                        except ValueError:
                            chunks_to_process = [selected_chunk_key]
                    else:
                        # Use listbox order
                        chunks_to_process = []
                        start_found = False
                        for i in range(self.chapter_listbox.size()):
                            item = self.chapter_listbox.get(i)
                            for key in self.file_chunks:
                                display_name = key.split(' (')[0] if ' (' in key else key
                                if item.startswith(display_name) or item.startswith(f"✅ {display_name}"):
                                    if start_found or key == selected_chunk_key:
                                        chunks_to_process.append(key)
                                        start_found = True
                                    break
                    
                    self.log_message(f"🎯 Resume from selected: {selected_chunk_key}")
                    self.log_message(f"📚 Processing {len(chunks_to_process)} chunks from selection onward")
                else:
                    self.log_message("❌ Could not find selected chunk!")
                    return
                    
            else:  # skip_completed (default behavior)
                chunks_to_process = [k for k, v in self.file_chunks.items() if not v.get('completed', False)]
                completed_chunks = [k for k, v in self.file_chunks.items() if v.get('completed', False)]
                self.log_message(f"📚 Processing {len(chunks_to_process)} incomplete chunks...")
                if completed_chunks:
                    self.log_message(f"📋 {len(completed_chunks)} chunks already completed")

            if not chunks_to_process:
                self.log_message("✅ All chunks are already completed!")
                return

            # Create output directory
            output_dir = self.output_path.get()
            os.makedirs(output_dir, exist_ok=True)

            # Read system instructions from multiple possible locations
            system_instructions_files = [
                'system_instructions.txt',  # Current directory
                os.path.expanduser('~/.config/ai-audiobook-generator/system_instructions.txt'),  # System config
            ]

            system_instructions = "Use a professional audiobook narration style."  # Default
            for sys_file in system_instructions_files:
                if os.path.exists(sys_file):
                    system_instructions = read_file_content(sys_file)
                    break

            combined_instructions = f"{custom_prompt}\n\n{system_instructions}"

            generated_files = []

            # Add already completed files
            for display_name in completed_chunks:
                chunk_info = self.file_chunks[display_name]
                chunk_filename = chunk_info['chunk_filename']
                output_file = os.path.join(output_dir, chunk_filename.replace('.txt', '.wav'))
                if os.path.exists(output_file):
                    generated_files.append(output_file)

            # Process each new chunk
            for i, display_name in enumerate(chunks_to_process):
                chunk_info = self.file_chunks[display_name]
                chunk_filename = chunk_info['chunk_filename']
                chunk_content = chunk_info['content']

                output_file = os.path.join(output_dir, chunk_filename.replace('.txt', '.wav'))

                self.log_message(f"🎵 Generating audio for {display_name}...")

                # Generate audio with custom prompt
                actual_output_file = self.generate_chapter_with_custom_prompt(
                    chunk_content, combined_instructions, output_file, custom_prompt
                )
                generated_files.append(actual_output_file)

                # Mark as completed
                self.file_chunks[display_name]['completed'] = True
                self.state_manager.mark_chunk_completed(self.project_id, output_file)

                # Update progress
                progress = (i + 1) / len(chunks_to_process) * 0.8  # 80% for individual chunks
                self.progress_var.set(progress)
                self.root.update_idletasks()
    
                # Update visual feedback in chapter list
                for idx in range(self.chapter_listbox.size()):
                    item = self.chapter_listbox.get(idx)
                    if item.startswith(display_name.split(' (')[0]) or display_name.startswith(item.split(' (')[0]):
                        # Update the listbox item to show completion
                        if not item.startswith("✅"):
                            completed_item = f"✅ {item}"
                            self.chapter_listbox.delete(idx)
                            self.chapter_listbox.insert(idx, completed_item)
                            self.chapter_listbox.itemconfig(idx, {'fg': 'green', 'bg': '#2d3a2d'})
                        break
    
                self.log_message(f"✅ Completed {display_name}")

            # Combine chapters and convert to final format
            if len(generated_files) > 1:
                self.log_message("🎼 Combining chunks into complete audiobook...")
                combine_chapters(generated_files, "complete_audiobook.wav")
            else:
                self.log_message("📖 Single chunk, creating audiobook...")
                # Copy single file as complete audiobook
                import shutil
                shutil.copy2(generated_files[0], "complete_audiobook.wav")

            # Save file information for change detection
            self.state_manager.save_file_info(self.project_id, 'chapters')

            # Convert to final format if needed
            self.progress_var.set(0.9)
            final_file = self.convert_to_final_format("complete_audiobook.wav")

            self.progress_var.set(1.0)
            self.log_message("🎉 Audiobook generation complete!")
            self.log_message("📂 Individual chunks: output/")
            self.log_message(f"🎧 Complete audiobook: {final_file}")
    
            # Update progress indicator
            self.progress_indicator.configure(text="🎉 Generation complete!")

        except QuotaExhaustedError as e:
            self.log_message(f"🚦 Quota Exhausted: {str(e)}")
            self.log_message("⏳ API quota limits reached. Consider waiting or upgrading your API plan.")
            messagebox.showerror("Quota Exhausted",
                                f"API quota limits have been reached.\n\nPlease wait a few minutes before trying again, or consider upgrading your Google AI API plan.\n\nDetails: {str(e)}")
        except ServiceUnavailableError as e:
            self.log_message(f"🚫 Service Unavailable: {str(e)}")
            self.log_message("❌ Google AI service is currently unavailable. Please try again later.")
            messagebox.showerror("Service Unavailable",
                                f"Google AI service is currently unavailable (503).\n\nPlease try again later.\n\nDetails: {str(e)}")
        except MaxRetriesExceededError as e:
            self.log_message(f"❌ Maximum Retries Exceeded: {str(e)}")
            self.log_message("💡 Multiple server errors occurred. Try again later or check your connection.")
            messagebox.showerror("Connection Issues",
                                f"Multiple server errors occurred during generation.\n\nPlease try again later or check your internet connection.\n\nDetails: {str(e)}")
        except HTTPAPIError as e:
            self.log_message(f"❌ API Error: {str(e)}")
            messagebox.showerror("API Error", f"API call failed: {str(e)}")
        except Exception as e:
            self.log_message(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Generation failed: {str(e)}")

        finally:
            self.is_generating = False
            self.generate_btn.configure(text="🎧 Generate Audiobook", state="normal")
            self.progress_indicator.configure(text="📊 Ready to generate")
            
    def generate_chapter_with_custom_prompt(self, chapter_text, system_instructions, output_file, custom_prompt):
        """Generate audio with custom prompt using the app.py generation functions with safe chunk mode"""
        from app import generate_chapter_audio
        
        # Use the app.py generation function with safe chunk mode
        try:
            actual_output_file = generate_chapter_audio(
                chapter_text=chapter_text,
                output_file=output_file,
                model=self.tts_model.get(),
                custom_prompt=custom_prompt,
                safe_chunk_mode=self.safe_chunk_mode.get()
            )
            return actual_output_file

        except QuotaExhaustedError as e:
            error_msg = f"🚦 Quota exhausted: {str(e)}"
            self.log_message(error_msg)
            self.log_message("⏳ API quota limits reached. Please wait before continuing or try again later.")
            raise
        except ServiceUnavailableError as e:
            error_msg = f"🚫 Service unavailable: {str(e)}"
            self.log_message(error_msg)
            self.log_message("❌ Stopping generation due to service unavailability. Please try again later.")
            raise
        except MaxRetriesExceededError as e:
            error_msg = f"❌ Maximum retries exceeded: {str(e)}"
            self.log_message(error_msg)
            self.log_message("💡 Try again later or check your internet connection.")
            raise
        except HTTPAPIError as e:
            error_msg = f"❌ API Error: {str(e)}"
            self.log_message(error_msg)
            raise
        except Exception as e:
            error_msg = f"❌ Unexpected error during audio generation: {str(e)}"
            self.log_message(error_msg)
            raise
    
    def convert_to_final_format(self, wav_file):
        """Convert WAV file to final output format"""
        output_format = self.output_format.get()
        
        if output_format == "WAV":
            return wav_file
        
        # Determine output filename
        base_name = os.path.splitext(wav_file)[0]
        if output_format == "MP3":
            output_file = f"{base_name}.mp3"
        elif output_format == "M4B":
            output_file = f"{base_name}.m4b"
        else:
            return wav_file
        
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_message("⚠️ FFmpeg not found. Install FFmpeg for audio conversion.")
            self.log_message("📄 Keeping WAV format.")
            return wav_file
        
        try:
            self.log_message(f"🔄 Converting to {output_format}...")
            
            # Build ffmpeg command
            cmd = ['ffmpeg', '-i', wav_file, '-y']  # -y to overwrite output file
            
            if output_format == "MP3":
                bitrate = self.mp3_bitrate.get()
                cmd.extend(['-codec:a', 'libmp3lame', '-b:a', f'{bitrate}k'])
            elif output_format == "M4B":
                bitrate = self.mp3_bitrate.get()
                cmd.extend(['-codec:a', 'aac', '-b:a', f'{bitrate}k'])
                
                # Add chapter markers if enabled
                if self.m4b_chapters.get() and hasattr(self, 'file_chunks'):
                    # Create chapter metadata for M4B
                    chapter_file = "chapters.txt"
                    self.create_chapter_metadata(chapter_file)
                    cmd.extend(['-f', 'mp4'])
            
            cmd.append(output_file)
            
            # Run conversion
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_message(f"✅ Converted to {output_format}")
                # Remove original WAV file if conversion successful
                if os.path.exists(output_file):
                    os.remove(wav_file)
                return output_file
            else:
                self.log_message(f"❌ Conversion failed: {result.stderr}")
                return wav_file
                
        except Exception as e:
            self.log_message(f"❌ Conversion error: {str(e)}")
            return wav_file
    
    def create_chapter_metadata(self, chapter_file):
        """Create chapter metadata file for M4B format"""
        try:
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(";FFMETADATA1\n")
                
                if hasattr(self, 'file_chunks'):
                    # Estimate chapter durations (this is approximate)
                    # In a real implementation, you'd track actual audio durations
                    current_time = 0
                    for i, (display_name, chunk_info) in enumerate(self.file_chunks.items()):
                        # Rough estimate: 150 words per minute, converted to milliseconds
                        word_count = self.count_words(chunk_info['content'])
                        duration_ms = int((word_count / 150) * 60 * 1000)
                        
                        f.write(f"\n[CHAPTER]\n")
                        f.write(f"TIMEBASE=1/1000\n")
                        f.write(f"START={current_time}\n")
                        f.write(f"END={current_time + duration_ms}\n")
                        f.write(f"title=Chapter {i+1}\n")
                        
                        current_time += duration_ms
                        
        except Exception as e:
            self.log_message(f"Warning: Could not create chapter metadata: {e}")
        
    def open_output_folder(self):
        """Open output folder in file manager"""
        output_dir = self.output_path.get()
        if os.path.exists(output_dir):
            if sys.platform.startswith('linux'):
                subprocess.run(['xdg-open', output_dir])
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', output_dir])
            elif sys.platform.startswith('win'):
                subprocess.run(['explorer', output_dir])
        else:
            messagebox.showinfo("Info", "Output folder doesn't exist yet. Generate an audiobook first!")
            
    def play_audiobook(self):
        """Play the latest generated audiobook"""
        audiobook_file = "complete_audiobook.wav"
        if os.path.exists(audiobook_file):
            if sys.platform.startswith('linux'):
                subprocess.run(['xdg-open', audiobook_file])
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', audiobook_file])
            elif sys.platform.startswith('win'):
                subprocess.run(['start', audiobook_file], shell=True)
        else:
            messagebox.showinfo("Info", "No audiobook found. Generate one first!")
            
    def show_about(self):
        """Show about dialog"""
        about_text = """🎧 AI Audiobook Generator

A sophisticated AI-powered audiobook generator using Google's Gemini 2.5 Pro TTS.

Features:
• 30 different narrator voices with unique characteristics
• Fully customizable narration prompts and styles
• Professional audiobook generation with chapter support
• Modern, HiDPI-compatible interface
• Preset styles: Professional, Dramatic, Relaxing, Passionate

Built with:
• CustomTkinter for modern, scalable UI
• Google Generative AI for high-quality TTS
• Python audio processing libraries

Perfect for:
• Converting written books to audiobooks
• Creating personalized narration styles
• Professional audiobook production
• Creative storytelling projects

Created with ❤️ for audiobook enthusiasts and content creators"""

        messagebox.showinfo("About", about_text)
    
    def reset_project(self):
        """Reset the current project state"""
        if not self.project_id:
            messagebox.showinfo("Info", "No active project to reset.")
            return

        if self.is_generating:
            messagebox.showwarning("Warning", "Cannot reset project while generation is in progress.")
            return

        # Confirm reset
        result = messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset the current project?\n\nThis will remove all progress and allow you to start fresh."
        )

        if result:
            # Reset project state
            self.state_manager.reset_project_state(self.project_id)
            self.log_message("🔄 Project state reset successfully")

            # Refresh chapters to show all as incomplete
            self.refresh_chapters()

            messagebox.showinfo("Success", "Project reset complete. You can now start fresh!")

    def toggle_terminal(self):
        """Toggle the terminal visibility"""
        if self.terminal_visible:
            self.terminal_frame.grid_remove()
            self.terminal_visible = False
        else:
            self.terminal_frame.grid()
            self.terminal_visible = True
            # Scroll to end when showing
            self.terminal_text.see("end")
    
    def clear_terminal(self):
        """Clear the terminal text"""
        self.terminal_text.delete("1.0", "end")
    
    def process_terminal_queue(self):
        """Process messages in the terminal queue"""
        try:
            while True:
                message = self.terminal_queue.get_nowait()
                if message:
                    self.terminal_text.insert("end", message)
                    self.terminal_text.see("end")
        except queue.Empty:
            pass
    
    def run(self):
        """Start the GUI application"""
        # Set up protocol to save settings on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Handle application closing - save current settings"""
        try:
            # Save current prompt from textbox
            current_prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
            if current_prompt:
                self.custom_prompt.set(current_prompt)
            
            # Save all settings
            self.save_settings()
        except Exception as e:
            print(f"Error saving settings on close: {e}")
        
        # Close the application
        self.root.destroy()

def main():
    app = AudiobookGeneratorGUI()
    app.run()

if __name__ == "__main__":
    main()