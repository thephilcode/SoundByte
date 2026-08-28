import tkinter as tk
from tkinter import ttk, messagebox
import os
from pathlib import Path
import dotenv

def load_config():
    """Load configuration from .env file."""
    env_path = Path('.env')
    if not env_path.exists():
        # Create a default .env if it doesn't exist
        dotenv.set_key(env_path, 'AUDD_API_TOKEN', '')
        dotenv.set_key(env_path, 'HOTKEY', 'ctrl+shift+m')
        dotenv.set_key(env_path, 'RECORDING_DURATION', '10.0')
        dotenv.set_key(env_path, 'NOTIFICATIONS_ENABLED', 'True')
    config = dotenv.dotenv_values(env_path)
    # Convert types
    config['RECORDING_DURATION'] = float(config.get('RECORDING_DURATION', 10.0))
    config['NOTIFICATIONS_ENABLED'] = config.get('NOTIFICATIONS_ENABLED', 'True').lower() in ('true', '1', 'yes')
    return config

def save_config(config):
    """Save configuration to .env file."""
    env_path = Path('.env')
    for key, value in config.items():
        if isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)
        dotenv.set_key(env_path, key, value)

def show_settings(parent=None, on_save_callback=None):
    """
    Show the settings dialog.
    
    Args:
        parent: The parent window (optional).
        on_save_callback: A function to call with the new config when the user saves.
    """
    # Load current config
    config = load_config()
    
    # Create dialog window
    dialog = tk.Toplevel(parent) if parent else tk.Tk()
    dialog.title("SoundByte Settings")
    dialog.resizable(False, False)
    dialog.transient(parent)  # Set to be on top of the parent window
    dialog.grab_set()  # Make it modal
    
    # Create main frame
    main_frame = ttk.Frame(dialog, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.W, tk.N, tk.E, tk.N, tk.S))
    
    # Hotkey
    ttk.Label(main_frame, text="Global Hotkey:").grid(row=0, column=0, sticky=tk.W, pady=5)
    hotkey_var = tk.StringVar(value=config.get('HOTKEY', 'ctrl+shift+m'))
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
    duration_spinbox = ttk.Spinbox(main_frame, from_=1.0, to=60.0, increment=0.5, textvariable=duration_var, width=10)
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
        new_config = {
            'HOTKEY': hotkey_var.get().strip(),
            'AUDD_API_TOKEN': api_token_var.get().strip(),
            'RECORDING_DURATION': duration_var.get(),
            'NOTIFICATIONS_ENABLED': notifications_var.get()
        }
        save_config(new_config)
        if on_save_callback:
            on_save_callback(new_config)
        dialog.destroy()
    
    def on_cancel():
        dialog.destroy()
    
    ttk.Button(button_frame, text="Save", command=on_save).grid(row=0, column=0, padx=5)
    ttk.Button(button_frame, text="Cancel", command=on_cancel).grid(row=0, column=1, padx=5)
    
    # Center the dialog on the parent window
    if parent:
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    else:
        # Center on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    show_settings()
    root.mainloop()