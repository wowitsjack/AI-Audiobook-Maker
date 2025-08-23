#!/usr/bin/env python3
"""
GUI launcher for AI Audiobook Generator.

Simple launcher script that starts the CustomTkinter GUI application.
"""

import sys
import os

def main():
    """Launch the GUI application"""
    try:
        # Add the parent directory to the path so we can import audiobook_maker
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Import and run the GUI
        from audiobook_maker.gui.application import main as gui_main
        
        print("🚀 Starting AI Audiobook Generator GUI...")
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