import logging
from pathlib import Path
import sys
import threading
import time
import os
import json
from threading import Lock
from typing import Any, Tuple, List, Dict, Optional

new_file_event = threading.Event()
paused_event   = threading.Event()
resume_event   = threading.Event()
retry_event    = threading.Event()
shutdown_event = threading.Event()

class AppState:
    def __init__(self):
        self.is_online: bool = False
        self.is_recording: bool = False
        self.pending_files: int = 0
        
app_state = AppState()

        
class FileManager:
    def __init__(self, log_dir: Path, queue_dir: Path, processing_dir: Path, completed_dir: Path, failed_dir: Path):
        self.log_dir = log_dir
        self.queue_dir = queue_dir
        self.processing_dir = processing_dir
        self.completed_dir = completed_dir
        self.failed_dir = failed_dir
    
    def move_to_processing(self, filename: Path):
        """Move a file from queue to processing directory"""
        dst = self.processing_dir / filename.name
        filename.rename(dst)
    
    def move_to_completed(self, filename: Path) :
        """Move a file from processing to completed directory"""
        dst = self.completed_dir / filename.name
        filename.rename(dst)

    def move_to_failed(self, filename: Path):
        """Move a file from processing to failed directory"""
        dst = self.failed_dir / filename.name
        filename.rename(dst)

    def get_pending_files(self) -> list[Path]:
        """Get list of pending files in queue"""
        return [Path(p) for p in self.queue_dir.iterdir() if p.is_file() and p.suffix == '.wav']


def _get_app_base_dir() -> Path:
    """Get the base directory for the app data.
    
    Returns:
        Path: The base directory for app data (e.g., %APPDATA%\\SoundByte on Windows)
    """
    app_name = 'SoundByte'
    
    if os.name == 'nt':
        base_dir: str | None = os.getenv('APPDATA')
        if base_dir is None:
            raise EnvironmentError("APPDATA environment variable is not set")
        home_dir: Path = Path(base_dir) / app_name
    else:
        raise OSError(f"Unsupported platform: {os.name}")
    
    return home_dir


def get_data_dirs():
    """Get data directories for the app, creating them if they don't exist.
    
    Returns:
        log_dir: _Directory where the log file will be saved_
        queue_dir: _Directory where audio files will be saved while pending processing_
        processing_dir: _Directory where audio files will be moved while being processed_
        completed_dir: _Directory where audio files will be moved after processing_
        failed_dir: _Directory where audio files will be moved after failure to process them_
    """
    home_dir = _get_app_base_dir()
    log_dir: Path = Path(home_dir) / 'logs'
    queue_dir: Path = Path(home_dir) / 'pending'
    processing_dir: Path = Path(home_dir) / 'processing'
    completed_dir: Path = Path(home_dir) / 'completed'
    failed_dir: Path = Path(home_dir) / 'failed'
    dirs = (log_dir, queue_dir, processing_dir, completed_dir, failed_dir)
    # Create directories if they don't exist
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)
    
    return dirs


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_logo():
    return resource_path("logo.png")

def get_icon():
    return resource_path("logo.ico")


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure logging to both file and stdout.

    Args:
        log_dir: Directory where log file will be created.
        level: Logging level (default: INFO).

    Returns:
        Configured logger instance.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"soundbyte_{time.strftime("%Y_%m_%d")}.log"

    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("soundbyte")


# History management
HISTORY_FILE_NAME = "history.json"
_history_lock = Lock()


def get_history_dir() -> Path:
    """Get the directory where the history file is stored, creating it if necessary."""
    home_dir = _get_app_base_dir()
    history_dir = home_dir
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def get_history_file() -> Path:
    """Get the full path to the history file."""
    return get_history_dir() / HISTORY_FILE_NAME

def open_history_file(mode: str = 'r'):
    """Context manager for opening the history file with proper directory creation."""
    history_file = get_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)
    return open(history_file, mode, encoding='utf-8')

def load_history() -> List[Dict]:
    """Load the recognition history from the JSON file.
    Returns an empty list if the file does not exist or is invalid."""
    history_file = get_history_file()
    if not history_file.exists():
        return []
    try:
        with open_history_file('r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def save_history_entry(entry: Dict) -> None:
    """Append a single entry to the history file in a thread-safe manner."""
    with _history_lock:
        history = load_history()
        history.append(entry)
        with open_history_file('w') as f:
            json.dump(history, f, indent=2)

