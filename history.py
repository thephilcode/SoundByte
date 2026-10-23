import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import webbrowser
from utils import load_history

# Global to track the history dialog instance to prevent multiple instances
_history_dialog = None

def copy_to_clipboard(root, text):
    """Copy text to the clipboard."""
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()  # Now it stays on the clipboard after the window is closed

def open_url(url):
    """Open a URL in the default web browser."""
    if url:
        webbrowser.open(url)

def show_history(parent=None, wait=True) -> None:
    """
    Show the history dialog.
    
    Args:
        parent: The parent window (should be the root Tk window).
        wait: If True, wait for the dialog to be destroyed before returning (modal behavior).
    """
    global _history_dialog
    # If a history dialog already exists and is still alive, lift it and return
    if _history_dialog is not None and _history_dialog.winfo_exists():
        _history_dialog.lift()
        return

    try:
        # Load history data
        history_data = load_history()

        # Create dialog window
        dialog = tk.Toplevel(parent)
        _history_dialog = dialog  # Set the global reference
        dialog.title("SoundByte Recognition History")
        dialog.resizable(True, True)
        # Only make the dialog transient to a mapped parent: Tk refuses to map a
        # transient whose container is not mapped, and the root window is withdrawn.
        if parent is not None and parent.winfo_ismapped():
            dialog.transient(parent)
        # Only make the dialog modal if we're waiting for it
        if wait:
            dialog.grab_set()  # Make it modal
        dialog.lift()
        dialog.focus_force()

        # Handle the window close button (X)
        def on_closing():
            on_close()
        dialog.protocol("WM_DELETE_WINDOW", on_closing)

        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create a Treeview to display the history
        tree = ttk.Treeview(main_frame, columns=("timestamp", "title", "artist", "album"), show="headings")
        tree.heading("timestamp", text="Timestamp")
        tree.heading("title", text="Title")
        tree.heading("artist", text="Artist")
        tree.heading("album", text="Album")
        
        # Set column widths
        tree.column("timestamp", width=150)
        tree.column("title", width=200)
        tree.column("artist", width=150)
        tree.column("album", width=150)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid the tree and scrollbar
        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Populate the tree with history data (newest first)
        for entry in reversed(history_data):  # Show newest first
            timestamp = entry.get('timestamp', '')
            # Format timestamp to be more readable if possible
            try:
                # If the timestamp is in ISO format, we can parse it and format it nicely
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_time = timestamp
            tree.insert("", tk.END, values=(formatted_time, 
                                            entry.get('title', ''), 
                                            entry.get('artist', ''), 
                                            entry.get('album', '')),
                       tags=(entry.get('song_link', ''),))
        
        # Create a frame for buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=(tk.E, tk.W))
        
        def on_close():
            global _history_dialog
            if _history_dialog is dialog:
                _history_dialog = None
            dialog.destroy()
        
        def on_copy():
            """Copy the selected item's information to the clipboard."""
            selected_item = tree.focus()
            if not selected_item:
                messagebox.showwarning("No Selection", "Please select an item to copy.")
                return
            values = tree.item(selected_item, "values")
            if values:
                text = f"Title: {values[1]}\nArtist: {values[2]}\nAlbum: {values[3]}"
                copy_to_clipboard(parent, text)
                messagebox.showinfo("Copied", "Song information copied to clipboard.")
        
        def on_open():
            """Open the selected song's link in the web browser."""
            selected_item = tree.focus()
            if not selected_item:
                messagebox.showwarning("No Selection", "Please select an item to open.")
                return
            # The song link is stored in the tags
            tags = tree.item(selected_item, "tags")
            if tags and tags[0]:
                url = tags[0]
                open_url(url)
            else:
                messagebox.showinfo("No Link", "No song link available for this entry.")
        
        def on_refresh():
            """Refresh the list from the history file."""
            # Clear the tree
            for item in tree.get_children():
                tree.delete(item)
            # Reload the data
            nonlocal history_data
            history_data = load_history()
            for entry in reversed(history_data):
                timestamp = entry.get('timestamp', '')
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp)
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    formatted_time = timestamp
                tree.insert("", tk.END, values=(formatted_time, 
                                                entry.get('title', ''), 
                                                entry.get('artist', ''), 
                                                entry.get('album', '')),
                           tags=(entry.get('song_link', ''),))
        
        # Buttons
        ttk.Button(button_frame, text="Copy Selected", command=on_copy).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Open Link", command=on_open).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Refresh", command=on_refresh).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Close", command=on_close).grid(row=0, column=3, padx=5)
        
        # Center the dialog on the screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Wait for the window to be destroyed before returning
        if wait:
            dialog.wait_window()
    except Exception as e:
        # Destroy the half-built dialog: left alive it would keep holding a
        # global grab while invisible, and the error dialog could never be dismissed.
        if _history_dialog is not None:
            _history_dialog.destroy()
        _history_dialog = None
        messagebox.showerror("Error", f"Failed to open history dialog: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    show_history(root)
    root.mainloop()