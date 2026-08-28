import dotenv
import keyboard
from network import is_online, send_to_api
from recording import record_audio
from threading import Thread
from tray import run_tray_app
from utils import app_state, FileManager, get_data_dirs, new_file_event, setup_logging
from worker import sync_worker

def main():
    """Main entry point for the SoundByte application."""
    dur = dotenv.get_key('.env', 'RECORDING_DURATION')
    RECORDING_DURATION = float(dur) if dur is not None else 10.0
    HOTKEY = dotenv.get_key('.env', 'HOTKEY') or 'ctrl+shift+m'
    paths = get_data_dirs()
    file_manager = FileManager(*paths)
    logger = setup_logging(file_manager.log_dir)
    logger.info("App starting...")
    if is_online(): 
        app_state.is_online = True
    worker_thread = Thread(target=sync_worker, args=(file_manager, send_to_api, is_online), daemon=True)
    worker_thread.start()
    
    def record_audio_callback():
        """Callback function for the hotkey to record audio."""
        record_audio(RECORDING_DURATION, file_manager, new_file_event)
    
    current_hotkey = HOTKEY
    keyboard.add_hotkey(current_hotkey, record_audio_callback)
    
    def update_hotkey(new_hotkey):
        """Update the global hotkey with a new value."""
        nonlocal current_hotkey
        keyboard.remove_hotkey(current_hotkey)
        current_hotkey = new_hotkey
        keyboard.add_hotkey(current_hotkey, record_audio_callback)
    
    run_tray_app(file_manager, update_hotkey)

if __name__ == "__main__":
    main()