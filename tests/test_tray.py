"""Tests for the tray menu wiring."""
import pytest

import tray
from utils import shutdown_event


@pytest.fixture(autouse=True)
def _reset_events():
    shutdown_event.clear()
    yield
    shutdown_event.clear()


def test_on_quit_stops_the_tk_mainloop(tk_root):
    """Quit must stop the Tk mainloop, or the process lingers headless."""
    stopped = []

    class FakeIcon:
        pass

    icon = FakeIcon()
    icon.root = tk_root
    icon.stop = lambda: None

    real_quit = tk_root.quit
    tk_root.quit = lambda: (stopped.append(True), real_quit())

    # The quit is scheduled on the Tk thread, so the mainloop has to be
    # running for the callback to fire.
    def run_and_check():
        tray.on_quit(icon, None)
        tk_root.after(200, real_quit)

    tk_root.after(0, run_and_check)
    tk_root.mainloop()

    assert shutdown_event.is_set(), "shutdown_event was not set"
    assert stopped, "the Tk mainloop was never told to quit"


def test_on_quit_without_a_root_does_not_raise():
    """A missing root must not stop the tray from quitting."""
    class FakeIcon:
        pass

    icon = FakeIcon()
    icon.stop = lambda: None

    tray.on_quit(icon, None)
    assert shutdown_event.is_set()
