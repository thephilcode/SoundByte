import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import dotenv
from utils import DEFAULT_HOTKEY, DEFAULT_RECORDING_DURATION, is_valid_hotkey

# Global to track the settings dialog instance to prevent multiple instances
_settings_dialog = None

def load_config(env_path=None):
    """Load configuration from .env file."""
    if env_path is None:
        env_path = Path('.env')
    else:
        env_path = Path(env_path)
    if not env_path.exists():
        # Create a default .env if it doesn't exist
        dotenv.set_key(env_path, 'AUDD_API_TOKEN', '')
        dotenv.set_key(env_path, 'HOTKEY', DEFAULT_HOTKEY)
        dotenv.set_key(env_path, 'RECORDING_DURATION', str(DEFAULT_RECORDING_DURATION))
        dotenv.set_key(env_path, 'NOTIFICATIONS_ENABLED', 'True')
    raw_config = dotenv.dotenv_values(env_path)
    try:
        duration = float(raw_config.get('RECORDING_DURATION') or DEFAULT_RECORDING_DURATION)
    except (TypeError, ValueError):
        duration = DEFAULT_RECORDING_DURATION
    config = {
        'AUDD_API_TOKEN': raw_config.get('AUDD_API_TOKEN') or '',
        'HOTKEY': raw_config.get('HOTKEY') or DEFAULT_HOTKEY,
        'RECORDING_DURATION': duration,
        'NOTIFICATIONS_ENABLED': (raw_config.get('NOTIFICATIONS_ENABLED') or 'True').lower() in ('true', '1', 'yes'),
    }
    # Update global app state with notification setting
    from utils import app_state
    app_state.NOTIFICATIONS_ENABLED = config['NOTIFICATIONS_ENABLED']
    return config

def save_config(config, env_path=None):
    """Save configuration to .env file."""
    if env_path is None:
        env_path = Path('.env')
    else:
        env_path = Path(env_path)
    for key, value in config.items():
        if isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)
        dotenv.set_key(env_path, key, value)

def show_settings(parent=None, on_save_callback=None, wait=True) -> None:
    """
    Show the settings dialog.
    
    Args:
        parent: The parent window (should be the root Tk window).
        on_save_callback: A function to call with the new config when the user saves.
        wait: If True, wait for the dialog to be destroyed before returning (modal behavior).
    """
    global _settings_dialog
    # If a settings dialog already exists and is still alive, lift it and return
    if _settings_dialog is not None and _settings_dialog.winfo_exists():
        _settings_dialog.lift()
        return

    try:
        # Load current config
        config = load_config()

        # Create dialog window
        dialog = tk.Toplevel(parent)
        _settings_dialog = dialog  # Set the global reference
        dialog.title("SoundByte Settings")
        dialog.resizable(False, False)
        # Only make the dialog transient to a mapped parent: Tk refuses to map a
        # transient whose container is not mapped, and the root window is withdrawn.
        if parent is not None and parent.winfo_ismapped():
            dialog.transient(parent)
        # Only make the dialog modal if we're waiting for it
        if wait:
            dialog.grab_set()  # Make it modal
        dialog.lift()
        dialog.focus_force()

        # Handle the window close button (X) by treating it as Cancel
        def on_closing():
            on_cancel()
        dialog.protocol("WM_DELETE_WINDOW", on_closing)

        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Hotkey
        ttk.Label(main_frame, text="Global Hotkey:").grid(row=0, column=0, sticky=tk.W, pady=5)
        hotkey_var = tk.StringVar(value=config.get('HOTKEY', DEFAULT_HOTKEY))
        hotkey_entry = ttk.Entry(main_frame, textvariable=hotkey_var, width=20)
        hotkey_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        # API Token
        ttk.Label(main_frame, text="AudD API Token:").grid(row=1, column=0, sticky=tk.W, pady=5)
        api_token_var = tk.StringVar(value=config.get('AUDD_API_TOKEN', ''))
        api_entry = ttk.Entry(main_frame, textvariable=api_token_var, width=30, show="*")
        api_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)

        # Recording Duration
        ttk.Label(main_frame, text="Recording Duration (seconds):").grid(row=2, column=0, sticky=tk.W, pady=5)
        duration_var = tk.DoubleVar(value=config.get('RECORDING_DURATION', 10.0))
        duration_spinbox = ttk.Spinbox(main_frame, from_=5.0, to=12.0, increment=0.5, textvariable=duration_var, width=10)
        duration_spinbox.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)

        # Notifications Enabled
        ttk.Label(main_frame, text="Show Notifications:").grid(row=3, column=0, sticky=tk.W, pady=5)
        notifications_var = tk.BooleanVar(value=config.get('NOTIFICATIONS_ENABLED', True))
        notifications_check = ttk.Checkbutton(main_frame, variable=notifications_var)
        notifications_check.grid(row=3, column=1, sticky=tk.W, pady=5)

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        def on_save():
            # Gather values from the UI
            hotkey = hotkey_var.get().strip()
            if not is_valid_hotkey(hotkey):
                messagebox.showerror(
                    "Invalid hotkey",
                    f"'{hotkey}' is not a known key combination.\n"
                    "The previous hotkey is still active."
                )
                return
            try:
                duration = duration_var.get()
            except tk.TclError:
                messagebox.showerror(
                    "Invalid recording duration",
                    "Recording duration must be a number between 5 and 12 seconds."
                )
                return
            new_config = {
                'HOTKEY': hotkey,
                'AUDD_API_TOKEN': api_token_var.get().strip(),
                'RECORDING_DURATION': duration,
                'NOTIFICATIONS_ENABLED': notifications_var.get()
            }
            save_config(new_config)
            if on_save_callback:
                on_save_callback(new_config)
            on_cancel()  # This will destroy the dialog and clear the global

        def on_cancel():
            global _settings_dialog
            if _settings_dialog is dialog:
                _settings_dialog = None
            dialog.destroy()

        ttk.Button(button_frame, text="Save", command=on_save).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).grid(row=0, column=1, padx=5)

        # Center the dialog on the screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # The root window is hidden, so the OS gives no field the caret. Focus
        # the hotkey entry last, otherwise the dialog-level focus_force() above
        # would take the caret back.
        dialog.update_idletasks()
        hotkey_entry.focus_set()

        # Wait for the window to be destroyed before returning
        if wait:
            dialog.wait_window()
    except Exception as e:
        # Destroy the half-built dialog: left alive it would keep holding a
        # global grab while invisible, and the error dialog could never be dismissed.
        if _settings_dialog is not None:
            _settings_dialog.destroy()
        _settings_dialog = None
        messagebox.showerror("Error", f"Failed to open settings dialog: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    show_settings(root)
    root.mainloop()