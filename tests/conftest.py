"""Shared fixtures for the SoundByte test suite."""
import sys
from pathlib import Path

import pytest

# The app modules import each other by top-level name.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """Keep tests from creating a .env in the repository.

    settings.load_config() creates a .env in the working directory when it is
    missing, so every test runs from a temp directory instead.
    """
    monkeypatch.chdir(tmp_path)
    yield


@pytest.fixture
def tk_root():
    """A hidden Tk root window, matching how main.py creates it."""
    tkinter = pytest.importorskip("tkinter")
    try:
        root = tkinter.Tk()
    except tkinter.TclError as e:
        pytest.skip(f"No display available for Tk: {e}")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tkinter.TclError:
        pass


@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """Run in a temp directory with a .env file, and point the app at it."""
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text(
        'AUDD_API_TOKEN="test-token"\n'
        'HOTKEY="windows+shift+z"\n'
        'RECORDING_DURATION=10.0\n'
        'NOTIFICATIONS_ENABLED="True"\n'
    )
    return env_file


@pytest.fixture
def app_dirs(tmp_path, monkeypatch):
    """Point the app's data/history directories at a temp folder.

    The real implementation resolves %APPDATA% and is Windows-only, so the
    tests stub it out rather than requiring a Windows environment.
    """
    import utils

    data_dir = tmp_path / "appdata"
    data_dir.mkdir()
    monkeypatch.setattr(utils, "_get_app_base_dir", lambda: data_dir)
    return data_dir
