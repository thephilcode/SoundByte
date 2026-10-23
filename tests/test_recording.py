"""Tests for the recording entry point.

record_audio() runs as a keyboard hotkey callback, on the keyboard library's
own thread. Raising SystemExit there kills that thread and silently breaks the
hotkey, so the failure paths must return instead.
"""
import sys
import types

import pytest


@pytest.fixture
def pyaudio_stub(monkeypatch):
    """Stub pyaudiowpatch, which is Windows-only."""
    paw = types.ModuleType("pyaudiowpatch")
    paw.paInt16 = 8

    class FakePyAudio:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_default_wasapi_loopback(self):
            raise OSError("no WASAPI here")

    paw.PyAudio = FakePyAudio
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", paw)
    return paw


def test_missing_wasapi_does_not_exit_the_process(pyaudio_stub, tmp_path):
    """A missing WASAPI device must not raise SystemExit.

    SystemExit here would kill the keyboard library's callback thread, so the
    hotkey would stop working for the rest of the session.
    """
    import recording
    from utils import FileManager

    dirs = [tmp_path / n for n in ("logs", "queue", "completed", "failed")]
    for d in dirs:
        d.mkdir()
    file_manager = FileManager(*dirs)

    import threading
    event = threading.Event()

    # Must return normally instead of raising SystemExit.
    recording.record_audio(10.0, file_manager, event)


def test_missing_loopback_device_does_not_exit_the_process(monkeypatch, tmp_path):
    """A missing loopback device must not raise SystemExit either."""
    import recording
    from utils import FileManager

    paw = types.ModuleType("pyaudiowpatch")
    paw.paInt16 = 8

    class FakePyAudio:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_default_wasapi_loopback(self):
            raise LookupError("no loopback device")

    paw.PyAudio = FakePyAudio
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", paw)

    dirs = [tmp_path / n for n in ("logs", "queue", "completed", "failed")]
    for d in dirs:
        d.mkdir()
    file_manager = FileManager(*dirs)

    import threading
    event = threading.Event()

    recording.record_audio(10.0, file_manager, event)
