"""
Core audiobook generation engine.

This module contains the main AudiobookEngine class that orchestrates
the entire audiobook generation process, including TTS, background music,
corruption detection, and project management.
"""

import os
import glob
import threading
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from .config import Config
from ..utils.text_processing import TextProcessor
from ..tts.generator import TTSGenerator
from ..music.generator import MusicGenerator
from ..quality.detector import QualityDetector
from ..state.manager import StateManager


class AudiobookEngine:
    """
    Main engine for audiobook generation.
    
    Coordinates all aspects of audiobook creation including:
    - Text processing and chunking
    - TTS generation with retry logic
    - Background music generation and mixing
    - Audio quality detection
    - Project state management
    """
    
    def __init__(self, config: Config):
        """
        Initialize the audiobook engine.
        
        Args:
            config: Configuration object with all settings
        """
        self.config = config
        self.text_processor = TextProcessor()
        self.tts_generator = TTSGenerator(config.tts)
        self.quality_detector = QualityDetector(config.corruption_detection) if config.corruption_detection.enabled else None
        self.state_manager = StateManager(config.project_directory)
        
        # Initialize music generator if enabled
        self.music_generator = None
        self.music_thread = None
        if config.background_music.enabled:
            try:
                self.music_generator = MusicGenerator(config.tts.api_key, config.background_music)
                print(f"🎵 Background music enabled: {config.background_music.mood} {config.background_music.genre}")
            except Exception as e:
                print(f"⚠️ Failed to initialize background music: {e}")
        
        # Progress callbacks
        self.progress_callback: Optional[Callable[[str], None]] = None
        self.chapter_callback: Optional[Callable[[int, int, str], None]] = None
        
    def set_progress_callback(self, callback: Callable[[str], None]):
        """Set callback for progress updates"""
        self.progress_callback = callback
        
    def set_chapter_callback(self, callback: Callable[[int, int, str], None]):
        """Set callback for chapter progress updates"""
        self.chapter_callback = callback
    
    def _notify_progress(self, message: str):
        """Send progress notification"""
        if self.progress_callback:
            self.progress_callback(message)
        print(message)
    
    def _notify_chapter_progress(self, current: int, total: int, chapter_name: str):
        """Send chapter progress notification"""
        if self.chapter_callback:
            self.chapter_callback(current, total, chapter_name)
    
    def get_chapter_files(self, chapters_dir: str = "chapters") -> List[str]:
        """
        Get all chapter files sorted by name.
        
        Args:
            chapters_dir: Directory containing chapter files
            
        Returns:
            List of chapter file paths
        """
        chapter_pattern = os.path.join(chapters_dir, "chapter_*.txt")
        chapter_files = glob.glob(chapter_pattern)
        return sorted(chapter_files)
    
    def start_background_music(self) -> bool:
        """
        Start background music generation in a separate thread.
        
        Returns:
            bool: True if started successfully
        """
        if not self.music_generator:
            return False
            
        try:
            import asyncio
            
            def start_music_generation():
                async def music_task():
                    try:
                        if hasattr(self.music_generator, 'start_generation'):
                            await self.music_generator.start_generation()
                            print(f"🎵 Background music generation started successfully")
                    except Exception as e:
                        print(f"⚠️ Failed to start background music: {e}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(music_task())
            
            # Start music generation in background thread
            self.music_thread = threading.Thread(target=start_music_generation, daemon=True)
            self.music_thread.start()
            
            # Give music generator time to start
            import time
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to start background music thread: {e}")
            return False
    
    def stop_background_music(self):
        """Stop background music generation"""
        if self.music_generator:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.music_generator.stop())
                print(f"🎵 Background music generation stopped")
            except Exception as e:
                print(f"⚠️ Failed to stop background music: {e}")
    
    def generate_chapter_audio(self, chapter_text: str, output_file: str, 
                             custom_prompt: Optional[str] = None) -> str:
        """
        Generate audio for a single chapter.
        
        Args:
            chapter_text: Text content of the chapter
            output_file: Output file path
            custom_prompt: Optional custom narration prompt
            
        Returns:
            str: Path to generated audio file
        """
        self._notify_progress(f"Processing chapter: {os.path.basename(output_file)}")
        
        # Use TTS generator to create audio
        actual_output = self.tts_generator.generate_chapter_audio(
            chapter_text=chapter_text,
            output_file=output_file,
            custom_prompt=custom_prompt,
            quality_detector=self.quality_detector,
            music_generator=self.music_generator,
            progress_callback=self._notify_progress
        )
        
        return actual_output
    
    def generate_audiobook(self, chapters_dir: str = "chapters", 
                          output_dir: str = "output",
                          custom_prompt: Optional[str] = None,
                          combine_chapters: bool = True) -> Dict[str, Any]:
        """
        Generate complete audiobook from chapter files.
        
        Args:
            chapters_dir: Directory containing chapter text files
            output_dir: Directory for output audio files
            custom_prompt: Optional custom narration prompt
            combine_chapters: Whether to combine into single audiobook file
            
        Returns:
            dict: Generation results with file paths and statistics
        """
        try:
            # Ensure we're in the right directory
            if not os.path.exists(chapters_dir):
                working_dir = self.config.project_directory
                os.makedirs(working_dir, exist_ok=True)
                os.chdir(working_dir)
                
                # Check again
                if not os.path.exists(chapters_dir):
                    raise FileNotFoundError(f"Chapters directory not found: {chapters_dir}")
            
            # Get chapter files
            chapter_files = self.get_chapter_files(chapters_dir)
            if not chapter_files:
                raise FileNotFoundError(f"No chapter files found in {chapters_dir}")
            
            self._notify_progress(f"Found {len(chapter_files)} chapters to process")
            self._notify_progress(f"Using narrator voice: {self.config.tts.narrator_voice}")
            
            # Initialize project state
            project_id = self.state_manager.get_project_id(chapters_dir)
            completed_chunks = self.state_manager.get_completed_chunks(project_id)
            
            if completed_chunks:
                self._notify_progress(f"📋 Resuming project - {len(completed_chunks)} chunks already completed")
            else:
                self._notify_progress("📋 Starting new project")
            
            # Start background music if enabled
            music_started = False
            if self.config.background_music.enabled:
                music_started = self.start_background_music()
                if music_started:
                    self._notify_progress("🎵 Background music generation started")
                else:
                    self._notify_progress("🎵 Background music enabled but failed to start")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each chapter
            generated_files = []
            for i, chapter_file in enumerate(chapter_files, 1):
                chapter_name = os.path.basename(chapter_file).replace('.txt', '')
                output_file = os.path.join(output_dir, f"{chapter_name}.wav")
                
                # Notify chapter progress
                self._notify_chapter_progress(i, len(chapter_files), chapter_name)
                
                # Check if already completed
                if output_file in completed_chunks:
                    self._notify_progress(f"✅ Skipping already completed: {chapter_file}")
                    generated_files.append(output_file)
                    continue
                
                # Read chapter content
                with open(chapter_file, 'r', encoding='utf-8') as f:
                    chapter_text = f.read()
                
                # Generate audio
                actual_output = self.generate_chapter_audio(
                    chapter_text=chapter_text,
                    output_file=output_file,
                    custom_prompt=custom_prompt
                )
                
                generated_files.append(actual_output)
                
                # Mark as completed
                self.state_manager.mark_chunk_completed(project_id, actual_output)
            
            # Combine chapters if requested
            final_audiobook_path = None
            if combine_chapters and generated_files:
                if len(generated_files) > 1:
                    self._notify_progress(f"Combining {len(generated_files)} chapters...")
                    final_audiobook_path = self._combine_chapters(generated_files, "complete_audiobook.wav")
                else:
                    # Single chapter - copy as complete audiobook
                    self._notify_progress("Single chapter detected, creating audiobook...")
                    final_audiobook_path = self._copy_single_chapter(generated_files[0], "complete_audiobook.wav")
            
            # Stop background music
            if music_started:
                self.stop_background_music()
            
            # Save file information for change detection
            self.state_manager.save_file_info(project_id, chapters_dir)
            
            # Prepare results
            results = {
                'success': True,
                'project_id': project_id,
                'chapters_processed': len(generated_files),
                'individual_files': generated_files,
                'combined_file': final_audiobook_path,
                'output_directory': output_dir,
                'background_music_enabled': self.config.background_music.enabled and music_started
            }
            
            self._notify_progress("✅ Audiobook generation complete!")
            return results
            
        except Exception as e:
            # Ensure music is stopped on error
            if hasattr(self, 'music_generator') and self.music_generator:
                try:
                    self.stop_background_music()
                except:
                    pass
            
            error_msg = f"❌ Error during audiobook generation: {e}"
            self._notify_progress(error_msg)
            return {
                'success': False,
                'error': str(e),
                'chapters_processed': 0
            }
    
    def _combine_chapters(self, audio_files: List[str], output_file: str) -> str:
        """Combine multiple chapter audio files into one"""
        try:
            from pydub import AudioSegment
            
            combined = AudioSegment.empty()
            
            for audio_file in audio_files:
                audio = AudioSegment.from_wav(audio_file)
                
                # Ensure stereo
                if audio.channels == 1:
                    audio = audio.set_channels(2)
                
                combined += audio
                
                # Add pause between chapters (2 seconds)
                pause = AudioSegment.silent(duration=2000)
                combined += pause
            
            # Handle file collisions
            final_output = self.state_manager.handle_file_collision(output_file)
            combined.export(final_output, format="wav")
            
            self._notify_progress(f"Combined audiobook saved to {final_output}")
            return final_output
            
        except ImportError:
            # Fallback if pydub not available
            import shutil
            final_output = self.state_manager.handle_file_collision(output_file)
            shutil.copy2(audio_files[0], final_output)
            self._notify_progress(f"Single file copied to {final_output}")
            return final_output
    
    def _copy_single_chapter(self, source_file: str, output_file: str) -> str:
        """Copy single chapter as complete audiobook"""
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_wav(source_file)
            final_output = self.state_manager.handle_file_collision(output_file)
            audio.export(final_output, format="wav")
            
            return final_output
            
        except ImportError:
            import shutil
            final_output = self.state_manager.handle_file_collision(output_file)
            shutil.copy2(source_file, final_output)
            return final_output
    
    def get_project_status(self, chapters_dir: str = "chapters") -> Dict[str, Any]:
        """
        Get current project status and progress.
        
        Args:
            chapters_dir: Directory containing chapter files
            
        Returns:
            dict: Project status information
        """
        chapter_files = self.get_chapter_files(chapters_dir)
        project_id = self.state_manager.get_project_id(chapters_dir) if chapter_files else None
        completed_chunks = self.state_manager.get_completed_chunks(project_id) if project_id else []
        
        return {
            'project_id': project_id,
            'total_chapters': len(chapter_files),
            'completed_chapters': len(completed_chunks),
            'progress_percentage': (len(completed_chunks) / len(chapter_files) * 100) if chapter_files else 0,
            'chapter_files': chapter_files,
            'completed_files': completed_chunks,
            'can_resume': len(completed_chunks) > 0
        }
    
    def reset_project(self, chapters_dir: str = "chapters"):
        """Reset project state to start fresh"""
        chapter_files = self.get_chapter_files(chapters_dir)
        if chapter_files:
            project_id = self.state_manager.get_project_id(chapters_dir)
            self.state_manager.reset_project_state(project_id)
            self._notify_progress("🔄 Project state reset - starting fresh")
        else:
            self._notify_progress("⚠️ No chapters found to reset")
    
    def cleanup(self):
        """Clean up resources"""
        if self.music_generator:
            self.stop_background_music()