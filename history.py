import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import json
import webbrowser
from utils import load_history

def copy_to_clipboard(text):
    """Copy text to the clipboard."""
    root = tk.Tk()
    root.withdraw()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()  # Now it stays on the clipboard after the window is closed
    root.destroy()

def open_url(url):
    """Open a URL in the default web browser."""
    if url:
        webbrowser.open(url)

def show_history(parent=None):
    """
    Show the history dialog.
    
    Args:
        parent: The parent window (optional).
    """
    # Load history data
    history_data = load_history()
    
    # Create dialog window
    dialog = tk.Toplevel(parent) if parent else tk.Tk()
    dialog.title("SoundByte Recognition History")
    dialog.resizable(True, True)
    dialog.transient(parent)  # Set to be on top of the parent window
    # Note: We don't use grab_set() here to allow the user to interact with the main app if needed,
    # but we'll make it modal by setting transient and waiting for the window to destroy.
    # Alternatively, we can use grab_set to make it strictly modal.
    # Let's make it modal for simplicity.
    dialog.grab_set()
    
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
                   tags=(entry.get('song_link', ''),))  # Store the song link in the tags
    
    # Create a frame for buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=(tk.E, tk.W))
    
    def on_copy():
        """Copy the selected item's information to the clipboard."""
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select an item to copy.")
            return
        values = tree.item(selected_item, "values")
        if values:
            text = f"Title: {values[1]}\nArtist: {values[2]}\nAlbum: {values[3]}"
            copy_to_clipboard(text)
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
    ttk.Button(button_frame, text="Close", command=dialog.destroy).grid(row=0, column=3, padx=5)
    
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
    
    # Wait for the window to be destroyed before returning
    dialog.wait_window()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    show_history()
    root.mainloop()