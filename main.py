import dotenv
import keyboard
import threading
import tkinter as tk
from network import is_online, send_to_api
from recording import record_audio
from tray import run_tray_app
from utils import app_state, DEFAULT_HOTKEY, DEFAULT_RECORDING_DURATION, FileManager, get_data_dirs, new_file_event, setup_logging, shutdown_event
from worker import sync_worker

def main():
    """Main entry point for the SoundByte application."""
    # Create the hidden root Tk window
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    paths = get_data_dirs()
    file_manager = FileManager(*paths)
    logger = setup_logging(file_manager.log_dir)
    logger.info("App starting...")

    dur = dotenv.get_key('.env', 'RECORDING_DURATION')
    try:
        RECORDING_DURATION = float(dur) if dur else DEFAULT_RECORDING_DURATION
    except (TypeError, ValueError):
        logger.warning(f"Invalid RECORDING_DURATION in .env ({dur!r}); using {DEFAULT_RECORDING_DURATION}")
        RECORDING_DURATION = DEFAULT_RECORDING_DURATION
    HOTKEY = dotenv.get_key('.env', 'HOTKEY') or DEFAULT_HOTKEY
    if is_online(): 
        app_state.is_online = True
    worker_thread = threading.Thread(target=sync_worker, args=(file_manager, send_to_api, is_online), daemon=True)
    worker_thread.start()

    def record_audio_callback():
        """Callback function for the hotkey to record audio."""
        record_audio(RECORDING_DURATION, file_manager, new_file_event)

    current_hotkey = HOTKEY
    try:
        keyboard.add_hotkey(current_hotkey, record_audio_callback)
    except ValueError as e:
        logger.error(f"Invalid HOTKEY in .env ({current_hotkey!r}): {e}")
        logger.warning(f"Falling back to the default hotkey {DEFAULT_HOTKEY!r}")
        current_hotkey = DEFAULT_HOTKEY
        keyboard.add_hotkey(current_hotkey, record_audio_callback)

    def update_hotkey(new_hotkey):
        """Update the global hotkey with a new value."""
        nonlocal current_hotkey
        if new_hotkey == current_hotkey:
            return
        # Register the new hotkey before removing the old one, so a failure
        # leaves the app with a working hotkey instead of none.
        try:
            keyboard.add_hotkey(new_hotkey, record_audio_callback)
        except ValueError as e:
            logger.error(f"Could not register hotkey {new_hotkey!r}: {e}")
            return
        keyboard.remove_hotkey(current_hotkey)
        current_hotkey = new_hotkey

    # Start the tray icon in a separate thread
    tray_thread = threading.Thread(target=run_tray_app, args=(file_manager, update_hotkey, root), daemon=True)
    tray_thread.start()

    # Start the Tkinter mainloop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
        shutdown_event.set()
        new_file_event.set()
        root.quit()
    finally:
        shutdown_event.set()
        new_file_event.set()
        try:
            root.destroy()
        except Exception:
            pass
        logger.info("App shut down")

if __name__ == "__main__":
    main()