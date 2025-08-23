#!/usr/bin/env python3
"""
Command-line interface for the AI Audiobook Generator.

Provides a simple CLI interface for generating audiobooks from text files.
"""

import argparse
import sys
import os
from pathlib import Path

from .core.config import load_config, get_default_config, save_config_to_env
from .core.engine import AudiobookEngine


def create_sample_config():
    """Create a sample .env configuration file"""
    try:
        config = get_default_config()
        success = save_config_to_env(config, '.env.sample')
        if success:
            print("✅ Sample configuration created: .env.sample")
            print("📝 Please copy this to .env and update with your API key:")
            print("   cp .env.sample .env")
            print("   # Edit .env with your GOOGLE_API_KEY")
        else:
            print("❌ Failed to create sample configuration")
    except Exception as e:
        print(f"❌ Error creating sample config: {e}")


def validate_chapters_directory(chapters_dir: str) -> bool:
    """Validate that chapters directory exists and contains chapter files"""
    if not os.path.exists(chapters_dir):
        print(f"❌ Chapters directory not found: {chapters_dir}")
        return False
    
    chapter_files = list(Path(chapters_dir).glob("chapter_*.txt"))
    if not chapter_files:
        print(f"❌ No chapter files found in {chapters_dir}")
        print("📝 Chapter files should be named: chapter_01.txt, chapter_02.txt, etc.")
        return False
    
    print(f"✅ Found {len(chapter_files)} chapter files in {chapters_dir}")
    return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI Audiobook Generator - Convert text to high-quality audiobooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate audiobook from chapters directory
  audiobook-maker generate --chapters ./chapters --output ./output

  # Generate with custom narration style
  audiobook-maker generate --chapters ./chapters --prompt "Narrate in a dramatic style"

  # Generate with background music
  audiobook-maker generate --chapters ./chapters --music

  # Create sample configuration
  audiobook-maker config --sample

  # Check project status
  audiobook-maker status --chapters ./chapters
        """
    )
    
    # Global options
    parser.add_argument('--config', help='Path to configuration file', default='.env')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate audiobook')
    generate_parser.add_argument('--chapters', required=True, help='Path to chapters directory')
    generate_parser.add_argument('--output', default='output', help='Output directory for audio files')
    generate_parser.add_argument('--prompt', help='Custom narration prompt')
    generate_parser.add_argument('--no-combine', action='store_true', 
                                help='Don\'t combine chapters into single audiobook')
    generate_parser.add_argument('--safe-mode', action='store_true', 
                                help='Enable safe chunk mode for better reliability')
    generate_parser.add_argument('--music', action='store_true', 
                                help='Enable background music generation')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('--sample', action='store_true', 
                              help='Create sample configuration file')
    config_parser.add_argument('--validate', action='store_true', 
                              help='Validate current configuration')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check project status')
    status_parser.add_argument('--chapters', required=True, help='Path to chapters directory')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset project state')
    reset_parser.add_argument('--chapters', required=True, help='Path to chapters directory')
    reset_parser.add_argument('--confirm', action='store_true', 
                             help='Confirm reset without prompting')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle config command
    if args.command == 'config':
        if args.sample:
            create_sample_config()
            return 0
        elif args.validate:
            try:
                config = load_config()
                print("✅ Configuration is valid")
                print(f"   - API Key: {'Set' if config.tts.api_key != 'your_api_key_here' else 'Not set'}")
                print(f"   - Narrator Voice: {config.tts.narrator_voice}")
                print(f"   - Corruption Detection: {'Enabled' if config.corruption_detection.enabled else 'Disabled'}")
                print(f"   - Background Music: {'Enabled' if config.background_music.enabled else 'Disabled'}")
                return 0
            except Exception as e:
                print(f"❌ Configuration error: {e}")
                return 1
        else:
            config_parser.print_help()
            return 1
    
    # Load configuration for other commands
    try:
        config = load_config()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Try: audiobook-maker config --sample")
        return 1
    
    # Apply command-line overrides to config
    if hasattr(args, 'safe_mode') and args.safe_mode:
        config.tts.safe_chunk_mode = True
    if hasattr(args, 'music') and args.music:
        config.background_music.enabled = True
    
    # Initialize engine
    try:
        engine = AudiobookEngine(config)
    except Exception as e:
        print(f"❌ Failed to initialize audiobook engine: {e}")
        return 1
    
    # Handle status command
    if args.command == 'status':
        if not validate_chapters_directory(args.chapters):
            return 1
        
        try:
            status = engine.get_project_status(args.chapters)
            print(f"\n📊 Project Status:")
            print(f"   - Project ID: {status['project_id']}")
            print(f"   - Total Chapters: {status['total_chapters']}")
            print(f"   - Completed: {status['completed_chapters']}")
            print(f"   - Progress: {status['progress_percentage']:.1f}%")
            print(f"   - Can Resume: {'Yes' if status['can_resume'] else 'No'}")
            
            if status['completed_files']:
                print(f"\n✅ Completed Files:")
                for file in status['completed_files']:
                    print(f"   - {file}")
            
            return 0
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return 1
    
    # Handle reset command
    elif args.command == 'reset':
        if not validate_chapters_directory(args.chapters):
            return 1
        
        if not args.confirm:
            response = input("⚠️ This will reset all progress. Continue? (y/N): ")
            if response.lower() != 'y':
                print("Reset cancelled.")
                return 0
        
        try:
            engine.reset_project(args.chapters)
            print("✅ Project state reset successfully")
            return 0
        except Exception as e:
            print(f"❌ Error resetting project: {e}")
            return 1
    
    # Handle generate command
    elif args.command == 'generate':
        if not validate_chapters_directory(args.chapters):
            return 1
        
        # Set up progress callback
        def progress_callback(message):
            if args.verbose:
                print(f"🔄 {message}")
        
        def chapter_callback(current, total, chapter_name):
            print(f"📖 Processing chapter {current}/{total}: {chapter_name}")
        
        engine.set_progress_callback(progress_callback)
        engine.set_chapter_callback(chapter_callback)
        
        print(f"🚀 Starting audiobook generation...")
        print(f"   - Chapters: {args.chapters}")
        print(f"   - Output: {args.output}")
        print(f"   - Safe mode: {'Yes' if config.tts.safe_chunk_mode else 'No'}")
        print(f"   - Background music: {'Yes' if config.background_music.enabled else 'No'}")
        if args.prompt:
            print(f"   - Custom prompt: {args.prompt}")
        
        try:
            results = engine.generate_audiobook(
                chapters_dir=args.chapters,
                output_dir=args.output,
                custom_prompt=args.prompt,
                combine_chapters=not args.no_combine
            )
            
            if results['success']:
                print(f"\n🎉 Audiobook generation complete!")
                print(f"   - Chapters processed: {results['chapters_processed']}")
                print(f"   - Individual files: {args.output}/")
                if results.get('combined_file'):
                    print(f"   - Combined audiobook: {results['combined_file']}")
                if results.get('background_music_enabled'):
                    print(f"   - Background music: Included")
            else:
                print(f"❌ Audiobook generation failed: {results.get('error', 'Unknown error')}")
                return 1
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Generation interrupted by user")
            return 1
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return 1
        finally:
            engine.cleanup()
        
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())