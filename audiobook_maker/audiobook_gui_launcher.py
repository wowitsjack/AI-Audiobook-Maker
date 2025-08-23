#!/usr/bin/env python3
"""
Standalone GUI launcher for AI Audiobook Generator.
This script ensures the GUI can be launched even if the package isn't properly installed.
"""

import sys
import os

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """Launch the GUI application"""
    try:
        print("🚀 Starting AI Audiobook Generator GUI...")
        
        # Import and run the GUI
        from gui.application import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"❌ Error importing GUI application: {e}")
        print("💡 Please ensure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()