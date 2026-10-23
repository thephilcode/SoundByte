"""Regression tests for the Settings and History dialogs.

The root window is withdrawn (main.py does this), so the dialogs must not be
made transient to it: Tk refuses to map a transient whose container is not
mapped, which left the dialogs invisible while still holding a global grab.
"""
import sys
from unittest.mock import MagicMock
sys.modules['pyaudiowpatch'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

import pytest

pytest.importorskip("tkinter")

import history
import settings


@pytest.fixture(autouse=True)
def _reset_dialogs(monkeypatch):
    """The dialog modules keep a module-level reference; clear it between tests."""
    # messagebox.showerror opens a modal loop and would block the test run.
    monkeypatch.setattr(settings.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(history.messagebox, "showerror", lambda *a, **k: None)
    settings._settings_dialog = None
    history._history_dialog = None
    yield
    for module, name in ((settings, "_settings_dialog"), (history, "_history_dialog")):
        dialog = getattr(module, name)
        if dialog is not None:
            try:
                dialog.destroy()
            except Exception:
                pass
        setattr(module, name, None)


def test_settings_dialog_is_visible_with_withdrawn_parent(tk_root, app_dirs):
    """The settings window must actually be on screen.

    This fails on the unfixed code: the Toplevel is created but stays
    withdrawn because it was made transient to the hidden root.
    """
    settings.show_settings(parent=tk_root, on_save_callback=None, wait=False)
    dialog = settings._settings_dialog

    assert dialog is not None, "show_settings did not create a dialog"
    assert dialog.winfo_ismapped(), "settings dialog was never mapped"
    assert dialog.winfo_viewable(), "settings dialog is not viewable"
    assert dialog.state() == "normal", f"settings dialog state is {dialog.state()!r}"


def test_history_dialog_is_visible_with_withdrawn_parent(tk_root, app_dirs):
    """The history window must actually be on screen."""
    history.show_history(parent=tk_root, wait=False)
    dialog = history._history_dialog

    assert dialog is not None, "show_history did not create a dialog"
    assert dialog.winfo_ismapped(), "history dialog was never mapped"
    assert dialog.winfo_viewable(), "history dialog is not viewable"
    assert dialog.state() == "normal", f"history dialog state is {dialog.state()!r}"


def test_settings_dialog_focuses_the_hotkey_entry(tk_root, app_dirs):
    """The hotkey field must take the caret, so the user can type straight away.

    The root window is hidden, so the OS never assigns focus to a field.
    """
    settings.show_settings(parent=tk_root, on_save_callback=None, wait=False)
    dialog = settings._settings_dialog

    # Find the hotkey entry: it is the first ttk.Entry in the dialog.
    entries = []

    def walk(widget):
        for child in widget.winfo_children():
            if child.winfo_class() == "TEntry":
                entries.append(child)
            walk(child)

    walk(dialog)
    assert entries, "the settings dialog has no entry fields"
    assert entries[0].focus_get() is entries[0], (
        "the hotkey entry does not have the caret"
    )


def test_dialog_grab_is_released_when_destroyed(tk_root, app_dirs):
    """Closing a dialog must release the global grab, or the app stays frozen."""
    # Use wait=False so the test doesn't block, then manually grab
    settings.show_settings(parent=tk_root, on_save_callback=None, wait=False)
    dialog = settings._settings_dialog
    dialog.grab_set()

    assert dialog.grab_current() is not None, "expected the dialog to hold the grab"

    dialog.destroy()
    settings._settings_dialog = None
    tk_root.update_idletasks()

    assert tk_root.grab_current() is None, "the grab outlived the dialog"


def test_error_path_does_not_leak_a_grabbing_dialog(tk_root, app_dirs, monkeypatch):
    """A failure while building the dialog must not leave an invisible grab behind."""

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(settings.ttk, "Frame", boom)

    settings.show_settings(parent=tk_root, on_save_callback=None, wait=False)

    assert settings._settings_dialog is None, "the failed dialog was left referenced"
    assert tk_root.grab_current() is None, "the failed dialog still holds the grab"
    assert tk_root.winfo_children() == [], "the failed dialog was left on screen"
