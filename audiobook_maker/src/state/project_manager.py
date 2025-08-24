import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class ProjectStateManager:
    """Manages project state for resume support, intelligent handling, and collision fixing"""
    
    def __init__(self, project_dir: Optional[str] = None):
        if project_dir is None:
            project_dir = os.path.expanduser('~/AI-Audiobook-Generator')
        self.project_dir = Path(project_dir)
        self.state_dir = self.project_dir / '.audiobook_state'
        self.state_dir.mkdir(exist_ok=True)
        
    def get_file_hash(self, file_path: str) -> str:
        """Generate a hash for a file to detect changes"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def get_project_id(self, chapters_dir: str) -> str:
        """Generate a unique project ID based on the chapters directory"""
        files = []
        for file_path in Path(chapters_dir).glob('*'):
            if file_path.is_file() and file_path.suffix in ['.txt', '.md']:
                files.append(str(file_path))
        
        files.sort()
        
        hash_input = ""
        for file_path in files:
            hash_input += f"{file_path}:{self.get_file_hash(file_path)};"
        
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def save_project_state(self, project_id: str, state_data: Dict[str, Any]) -> None:
        """Save project state to file"""
        state_file = self.state_dir / f"{project_id}.json"
        state_data['last_updated'] = datetime.now().isoformat()
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save project state: {e}")
    
    def load_project_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load project state from file"""
        state_file = self.state_dir / f"{project_id}.json"
        
        if not state_file.exists():
            return None
            
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load project state: {e}")
            return None
    
    def get_completed_chunks(self, project_id: str) -> List[str]:
        """Get list of completed chunk filenames for a project"""
        state = self.load_project_state(project_id)
        if state and 'completed_chunks' in state:
            return state['completed_chunks']
        return []
    
    def mark_chunk_completed(self, project_id: str, chunk_filename: str) -> None:
        """Mark a chunk as completed in the project state"""
        state = self.load_project_state(project_id)
        if state is None:
            state = {'completed_chunks': []}

        if 'completed_chunks' not in state:
            state['completed_chunks'] = []

        if chunk_filename not in state['completed_chunks']:
            state['completed_chunks'].append(chunk_filename)
            self.save_project_state(project_id, state)

    def get_available_filename(self, base_path: str) -> str:
        """Generate a unique filename to avoid collisions"""
        if not os.path.exists(base_path):
            return base_path

        directory = os.path.dirname(base_path)
        basename = os.path.basename(base_path)
        name, ext = os.path.splitext(basename)

        counter = 1
        new_path = base_path
        while os.path.exists(new_path):
            new_path = os.path.join(directory, f"{name}_{counter}{ext}")
            counter += 1

        return new_path

    def handle_file_collision(self, original_path: str) -> str:
        """Handle file collisions by finding an available filename"""
        return self.get_available_filename(original_path)

    def reset_project_state(self, project_id: str) -> None:
        """Reset project state (for starting fresh)"""
        state_file = self.state_dir / f"{project_id}.json"
        if state_file.exists():
            try:
                state_file.unlink()
            except Exception as e:
                print(f"Warning: Could not reset project state: {e}")
    
    def save_file_info(self, project_id: str, chapters_dir: str) -> None:
        """Save current file information for change detection"""
        state = self.load_project_state(project_id)
        if state is None:
            state = {}
        
        file_info = {}
        for file_path in Path(chapters_dir).glob('*'):
            if file_path.is_file() and file_path.suffix in ['.txt', '.md']:
                try:
                    stat = os.stat(file_path)
                    file_info[str(file_path)] = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'hash': self.get_file_hash(str(file_path))
                    }
                except Exception:
                    pass
        
        state['file_info'] = file_info
        self.save_project_state(project_id, state)