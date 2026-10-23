from functools import partial
import logging
import os
import sys
import subprocess
from typing import Any, Callable
from pystray import Icon, MenuItem, Menu
from PIL import Image
from utils import app_state, FileManager, get_icon, new_file_event, paused_event, resume_event, retry_event, shutdown_event

# Import settings and history modules
try:
    from settings import show_settings
except ImportError:
    # Fallback if settings module is not available (should not happen in normal operation)
    def show_settings(
        parent: Any = None,
        on_save_callback: Callable[..., Any] | None = None,
    ) -> None:
        pass

try:
    from history import show_history
except ImportError:
    # Fallback if history module is not available
    def show_history(parent: Any = None) -> None:
        pass

logger = logging.getLogger(__name__)

def create_default_icon():
    """ Helper function to generate the app icon """
    img = Image.open(get_icon())
    img.load()
    return img

def pause_on_clicked(icon, item: MenuItem):
    """ Toggle paused status of the app 
    
    Args:
        icon: The Icon instance for this tray app
        item: The Menuitem that was clicked
    """
    if paused_event.is_set():
        logger.info("Resume signal sent")
        resume_event.set()
        paused_event.clear()
    else:
        resume_event.clear()
        paused_event.set()
        logger.info("Pause signal sent")
    icon.update_menu()

def retry_on_clicked(icon, item: MenuItem):
    """ Set new file event to trigger sync worker loop immediately for retry

    Args:
        icon: The Icon instance for this tray app
        item: The Menuitem that was clicked
    """
    logger.info("Retry Now clicked - triggering immediate connection retry")
    new_file_event.set()

def open_folder_on_clicked(file_manager: FileManager, icon, item: MenuItem):
    """ Open folder when triggered 
    
    Args:
        file_manager: FileManager instance for getting directory paths
        icon: The Icon instance for this tray app
        item: The Menuitem that was clicked
    """
    if str(item.text) == "Open Recordings Folder":
        path = str(file_manager.queue_dir)
    elif str(item.text) == "View Logs":
        path = str(file_manager.log_dir)
    else:
        return

    if os.name == 'nt':
        os.startfile(path)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, path])

def on_quit(icon, item: MenuItem):
    """ Callback function to quit the app

    Args:
        icon: The Icon instance for this tray app
        item: The Menuitem that was clicked
    """
    shutdown_event.set()
    new_file_event.set()
    logger.info("Quitting app")
    icon.stop()
    # Stop the Tk mainloop too, otherwise the process lingers with no tray icon.
    root = getattr(icon, "root", None)
    if root is not None:
        root.after(0, root.quit)

def run_tray_app(file_manager: FileManager, update_hotkey_callback=None, root=None):
    """ Main function to setup and run the tray app 
    
    Args:
        file_manager: FileManager instance for getting directory paths
        update_hotkey_callback: Optional function to call when the hotkey is changed via settings
        root: The Tkinter root window (used to schedule dialogs in the main thread)
    """
    logger.info("Configuring tray menu and icon")
    
    # Define the settings menu item callback
    def settings_on_clicked(icon, item):
        def on_settings_save(new_config):
            # If the hotkey changed and we have an update_hotkey function, call it
            if 'HOTKEY' in new_config and update_hotkey_callback is not None:
                update_hotkey_callback(new_config['HOTKEY'])
        # Show the settings dialog in the main thread
        try:
            if root:
                root.after(0, lambda: show_settings(parent=root, on_save_callback=on_settings_save, wait=False))
            else:
                show_settings(parent=None, on_save_callback=on_settings_save, wait=False)
        except Exception as e:
            logger.error(f"Failed to show settings dialog: {e}", exc_info=True)
    
    # Define the history menu item callback
    def history_on_clicked(icon, item):
        def on_history_save():
            pass  # Placeholder for consistency with settings callback signature
        # Show the history dialog in the main thread
        try:
            if root:
                root.after(0, lambda: show_history(parent=root, wait=False))
            else:
                show_history(parent=None, wait=False)
        except Exception as e:
            logger.error(f"Failed to show history dialog: {e}", exc_info=True)

    def manual_record_on_clicked(icon, item):
        from recording import record_audio
        # We need the file_manager and new_file_event
        # Since we are in run_tray_app, we have file_manager
        # and new_file_event is imported from utils
        from utils import new_file_event
        logger.info("Manual record clicked")
        # Recording duration is now in app_state
        record_audio(app_state.recording_duration, file_manager, new_file_event)

    menu = Menu(
        MenuItem(lambda item: f"{'○ Offline' if not app_state.is_online else '● Online'} - {app_state.pending_files} pending files", None),
        Menu.SEPARATOR,
        MenuItem("Manual Record", manual_record_on_clicked),
        MenuItem("Retry Now", retry_on_clicked),
        MenuItem("Pause syncing", pause_on_clicked, checked=lambda item: paused_event.is_set()),
        Menu.SEPARATOR,
        MenuItem("Open Recordings Folder", partial(open_folder_on_clicked, file_manager)),
        MenuItem("View Logs", partial(open_folder_on_clicked, file_manager)),
        Menu.SEPARATOR,
        MenuItem("Settings", settings_on_clicked),
        MenuItem("View History", history_on_clicked),
        Menu.SEPARATOR,
        MenuItem("Quit", on_quit)
    )
    icon = Icon(
        name="tray_icon",
        icon=create_default_icon(),
        title="SoundByte",
        menu=menu
    )
    setattr(icon, "root", root)
    icon.run()
