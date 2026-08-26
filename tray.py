from functools import partial
import logging
import os
import sys
import subprocess
from pystray import Icon, MenuItem, Menu
from PIL import Image
from utils import app_state, FileManager, get_icon, new_file_event, paused_event, resume_event, retry_event, shutdown_event

# Import settings and history modules
try:
    from settings import show_settings
except ImportError:
    # Fallback if settings module is not available (should not happen in normal operation)
    def show_settings(parent=None, on_save_callback=None):
        pass

try:
    from history import show_history
except ImportError:
    # Fallback if history module is not available
    def show_history(parent=None):
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
    """ Set new file event to trigger sync worker loop 
    
    Args:
        icon: The Icon instance for this tray app
        item: The Menuitem that was clicked
    """
    retry_event.set()

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

def run_tray_app(file_manager: FileManager, update_hotkey_callback=None):
    """ Main function to setup and run the tray app 
    
    Args:
        file_manager: FileManager instance for getting directory paths
        update_hotkey: Optional function to call when the hotkey is changed via settings
    """
    logger.info("Configuring tray menu and icon")
    
    # Define the settings menu item callback
    def settings_on_clicked(icon, item):
        def on_settings_save(new_config):
            # If the hotkey changed and we have an update_hotkey function, call it
            if 'HOTKEY' in new_config and update_hotkey_callback is not None:
                update_hotkey_callback(new_config['HOTKEY'])
        # Show the settings dialog
        show_settings(parent=None, on_save_callback=on_settings_save)
    
    # Define the history menu item callback
    def history_on_clicked(icon, item):
        show_history(parent=None)
    
    menu = Menu(
        MenuItem(lambda item: f"{'○ Offline' if not app_state.is_online else '● Online'} - {app_state.pending_files} pending files", None),
        Menu.SEPARATOR,
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
    icon.run()