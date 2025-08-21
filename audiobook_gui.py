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

# Import our audiobook generation logic
from app import generate_chapter_audio, combine_chapters, read_file_content, load_config
from dotenv import load_dotenv

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
        self.root.title("🎧 AI Audiobook Generator")
        
        # Set up working directory and initialize paths
        self.setup_working_directory()
        
        # HiDPI and scaling support
        self.setup_scaling()
        
        # Better proportions - wider and shorter
        self.root.geometry("1600x800")
        self.root.minsize(1400, 700)
        self.root.resizable(True, True)
        
        # Configure grid weight
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Variables
        self.api_key = tk.StringVar(value=os.getenv('GOOGLE_API_KEY', ''))
        self.narrator_voice = tk.StringVar(value=os.getenv('NARRATOR_VOICE', 'Kore'))
        self.chapters_path = tk.StringVar(value=self.default_chapters_path)
        self.output_path = tk.StringVar(value=self.default_output_path)
        self.custom_prompt = tk.StringVar(value='Use a professional, engaging audiobook narration style with appropriate pacing and emotion.')
        self.is_generating = False
        self.file_chunks = {}  # Initialize chunk storage
        
        # Audio encoding options
        self.output_format = tk.StringVar(value="WAV")
        self.mp3_bitrate = tk.StringVar(value="192")
        self.m4b_chapters = tk.BooleanVar(value=True)
        
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
        # Title
        title_label = ctk.CTkLabel(
            self.root, 
            text="🎧 AI Audiobook Generator",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(15, 20), sticky="ew")
        
        # Left Column - Configuration and Chapters
        left_frame = ctk.CTkFrame(self.root)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(15, 8), pady=(0, 15))
        left_frame.grid_columnconfigure(1, weight=1)
        left_frame.grid_rowconfigure(3, weight=1)
        
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
        
        ctk.CTkLabel(voice_frame, text="Chapters:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=2, sticky="w", padx=(20, 10), pady=5
        )
        path_entry = ctk.CTkEntry(
            voice_frame, 
            textvariable=self.chapters_path,
            height=30,
            font=ctk.CTkFont(size=11),
            width=150
        )
        path_entry.grid(row=0, column=3, sticky="ew", pady=5)
        
        browse_btn = ctk.CTkButton(
            voice_frame, 
            text="📁", 
            command=self.browse_chapters_folder, 
            width=30,
            height=30,
            font=ctk.CTkFont(size=12)
        )
        browse_btn.grid(row=0, column=4, padx=(5, 0), pady=5)
        
        # Chapter list
        chapter_list_frame = ctk.CTkFrame(left_frame)
        chapter_list_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=15, pady=(10, 15))
        chapter_list_frame.grid_columnconfigure(0, weight=1)
        chapter_list_frame.grid_rowconfigure(1, weight=1)
        
        list_header = ctk.CTkFrame(chapter_list_frame, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        list_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(list_header, text="📚 Chapters Found", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        
        refresh_btn = ctk.CTkButton(
            list_header, 
            text="🔄", 
            command=self.refresh_chapters, 
            width=30,
            height=25,
            font=ctk.CTkFont(size=11)
        )
        refresh_btn.grid(row=0, column=1, sticky="e")
        
        self.chapter_listbox = tk.Listbox(
            chapter_list_frame, 
            height=8, 
            bg="#2b2b2b", 
            fg="white", 
            selectbackground="#1f6aa5",
            font=("Segoe UI", 10)
        )
        self.chapter_listbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.chapter_listbox.bind('<<ListboxSelect>>', self.on_chapter_select)
        
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
        
        about_btn = ctk.CTkButton(
            bottom_frame, 
            text="ℹ️ About", 
            command=self.show_about,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        about_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
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
        
    def browse_chapters_folder(self):
        """Browse for chapters folder"""
        folder = filedialog.askdirectory(title="Select Chapters Folder")
        if folder:
            self.chapters_path.set(folder)
            self.refresh_chapters()
    
    def count_words(self, text):
        """Count words in text"""
        return len(text.split())
    
    def intelligent_chunk_text(self, text, max_words=800):
        """Intelligently split text into chunks at paragraph boundaries"""
        if self.count_words(text) <= max_words:
            return [text]
        
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Clean up the paragraph
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Check if adding this paragraph would exceed the limit
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if self.count_words(test_chunk) <= max_words:
                current_chunk = test_chunk
            else:
                # If current chunk has content, save it and start new chunk
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    # If single paragraph is too long, split by sentences
                    sentences = paragraph.split('. ')
                    current_sentence_chunk = ""
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        
                        # Add period back if it was split
                        if not sentence.endswith('.') and sentence != sentences[-1]:
                            sentence += '.'
                        
                        test_sentence_chunk = current_sentence_chunk + " " + sentence if current_sentence_chunk else sentence
                        
                        if self.count_words(test_sentence_chunk) <= max_words:
                            current_sentence_chunk = test_sentence_chunk
                        else:
                            if current_sentence_chunk:
                                chunks.append(current_sentence_chunk)
                                current_sentence_chunk = sentence
                            else:
                                # If single sentence is too long, just add it anyway
                                chunks.append(sentence)
                                current_sentence_chunk = ""
                    
                    if current_sentence_chunk:
                        current_chunk = current_sentence_chunk
                    else:
                        current_chunk = ""
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
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
            
            if word_count <= 800:
                return [(filename, content, f"{name_without_ext} ({word_count} words)")]
            else:
                chunks = self.intelligent_chunk_text(clean_content)
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
        """Refresh the chapter list"""
        self.chapter_listbox.delete(0, tk.END)
        chapters_dir = self.chapters_path.get()
        
        if os.path.exists(chapters_dir):
            # Look for both .txt and .md files
            txt_files = glob.glob(os.path.join(chapters_dir, '*.txt'))
            md_files = glob.glob(os.path.join(chapters_dir, '*.md'))
            all_files = sorted(txt_files + md_files)
            
            total_chunks = 0
            self.file_chunks = {}  # Store chunk information
            
            for file_path in all_files:
                chunks = self.process_file_with_chunking(file_path)
                if chunks:
                    for chunk_filename, chunk_content, display_name in chunks:
                        self.chapter_listbox.insert(tk.END, display_name)
                        self.file_chunks[display_name] = {
                            'original_file': file_path,
                            'chunk_filename': chunk_filename,
                            'content': chunk_content
                        }
                        total_chunks += 1
                
            self.log_message(f"📚 Found {len(all_files)} files, {total_chunks} chunks")
            if any(self.count_words(read_file_content(f)) > 800 for f in all_files):
                self.log_message("📄 Large files automatically split into chunks")
        else:
            self.log_message(f"❌ Chapters folder not found: {chapters_dir}")
            self.file_chunks = {}
            
    def on_chapter_select(self, event):
        """Handle chapter selection"""
        selection = self.chapter_listbox.curselection()
        if selection:
            self.preview_btn.configure(state="normal")
        else:
            self.preview_btn.configure(state="disabled")
            
    def preview_chapter(self):
        """Preview selected chapter content"""
        selection = self.chapter_listbox.curselection()
        if not selection:
            return
            
        display_name = self.chapter_listbox.get(selection[0])
        
        try:
            # Get content from chunk data or fallback to file reading
            if hasattr(self, 'file_chunks') and display_name in self.file_chunks:
                content = self.file_chunks[display_name]['content']
                title = f"Preview: {display_name}"
            else:
                # Fallback for old naming convention
                filepath = os.path.join(self.chapters_path.get(), display_name)
                content = read_file_content(filepath)
                title = f"Preview: {display_name}"
            
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
        """Add message to status log"""
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
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
        
        # Get custom prompt
        custom_prompt = self.prompt_textbox.get("1.0", "end-1c").strip()
        if not custom_prompt:
            custom_prompt = "Use a professional audiobook narration style."
            
        self.is_generating = True
        self.generate_btn.configure(text="🔄 Generating...", state="disabled")
        
        # Start generation in separate thread
        thread = threading.Thread(target=self.generate_audiobook, args=(custom_prompt,))
        thread.daemon = True
        thread.start()
        
    def generate_audiobook(self, custom_prompt):
        """Generate audiobook (runs in separate thread)"""
        try:
            self.log_message("🎧 Starting audiobook generation...")
            
            # Get chunks from the listbox
            if not hasattr(self, 'file_chunks') or not self.file_chunks:
                self.log_message("❌ No files or chunks found!")
                return
                
            chunks_to_process = list(self.file_chunks.keys())
            self.log_message(f"📚 Processing {len(chunks_to_process)} chunks...")
            
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
            
            # Process each chunk
            for i, display_name in enumerate(chunks_to_process):
                chunk_info = self.file_chunks[display_name]
                chunk_filename = chunk_info['chunk_filename']
                chunk_content = chunk_info['content']
                
                output_file = os.path.join(output_dir, chunk_filename.replace('.txt', '.wav'))
                
                self.log_message(f"🎵 Generating audio for {display_name}...")
                
                # Generate audio with custom prompt
                self.generate_chapter_with_custom_prompt(
                    chunk_content, combined_instructions, output_file, custom_prompt
                )
                generated_files.append(output_file)
                
                # Update progress
                progress = (i + 1) / len(chunks_to_process) * 0.8  # 80% for individual chunks
                self.progress_var.set(progress)
                self.root.update_idletasks()
                
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
            
            # Convert to final format if needed
            self.progress_var.set(0.9)
            final_file = self.convert_to_final_format("complete_audiobook.wav")
                
            self.progress_var.set(1.0)
            self.log_message("🎉 Audiobook generation complete!")
            self.log_message("📂 Individual chunks: output/")
            self.log_message(f"🎧 Complete audiobook: {final_file}")
            
        except Exception as e:
            self.log_message(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Generation failed: {str(e)}")
            
        finally:
            self.is_generating = False
            self.generate_btn.configure(text="🎧 Generate Audiobook", state="normal")
            
    def generate_chapter_with_custom_prompt(self, chapter_text, system_instructions, output_file, custom_prompt):
        """Generate audio with custom prompt"""
        from google import genai
        from google.genai import types
        import wave
        
        def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(rate)
                wf.writeframes(pcm)
        
        client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
        
        prompt = f"""{custom_prompt}

{system_instructions}

Please narrate the following chapter:

{chapter_text}"""
        
        response = client.models.generate_content(
            model="gemini-2.5-pro-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.narrator_voice.get(),
                        )
                    )
                )
            )
        )
        
        data = response.candidates[0].content.parts[0].inline_data.data
        wave_file(output_file, data)
    
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