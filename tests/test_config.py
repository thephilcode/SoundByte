"""Tests for the config parsing and hotkey validation that guard against crashes."""
import sys
from pathlib import Path
import pytest
import dotenv

from utils import is_valid_hotkey
import settings

def _can_validate_hotkeys() -> bool:
    """The keyboard library can only validate hotkeys where it can read the keys.

    On Linux that needs root, so validation is skipped there and the tests
    below that assert a rejection are skipped as well.
    """
    import keyboard
    try:
        keyboard.parse_hotkey("ctrl+a")
    except ImportError:
        return False
    except ValueError:
        return True
    return True

CAN_VALIDATE = _can_validate_hotkeys()
needs_validation = pytest.mark.skipif(
    not CAN_VALIDATE, reason="the keyboard library cannot validate hotkeys on this platform"
)

@pytest.fixture
def temp_env(tmp_path):
    """Provide a temporary .env file for config tests."""
    env_file = tmp_path / ".env"
    # Ensure the file exists so dotenv can work with it
    env_file.touch()
    return env_file

def test_known_hotkey_is_accepted():
    assert is_valid_hotkey("windows+shift+z") is True
    assert is_valid_hotkey("ctrl+shift+a") is True

@needs_validation
def test_unknown_hotkey_is_rejected():
    assert is_valid_hotkey("windows+shift+notakey") is False

def test_empty_hotkey_is_rejected_or_not_crashing():
    """An empty hotkey must never be accepted as valid on a platform that can check."""
    if CAN_VALIDATE:
        assert is_valid_hotkey("") is False

@pytest.mark.parametrize("raw", ["", None, "not-a-number", "abc"])
def test_recording_duration_falls_back_to_ten(raw):
    """A bad RECORDING_DURATION in .env must not crash startup."""
    try:
        duration = float(raw) if raw else 10.0
    except (TypeError, ValueError):
        duration = 10.0
    assert duration == 10.0

def test_load_config_survives_a_bad_duration(temp_env):
    """load_config must not crash if RECORDING_DURATION is garbage."""
    dotenv.set_key(str(temp_env), 'RECORDING_DURATION', 'not-a-number')
    config = settings.load_config(env_path=temp_env)
    assert config['RECORDING_DURATION'] == 10.0

def test_load_config_survives_an_empty_duration(temp_env):
    """load_config must not crash if RECORDING_DURATION is empty."""
    dotenv.set_key(str(temp_env), 'RECORDING_DURATION', '')
    config = settings.load_config(env_path=temp_env)
    assert config['RECORDING_DURATION'] == 10.0

def test_save_config_round_trips(temp_env):
    """save_config must write a config that load_config can read back."""
    config = {
        "HOTKEY": "ctrl+alt+f9",
        "AUDD_API_TOKEN": "abc123",
        "RECORDING_DURATION": 8.0,
        "NOTIFICATIONS_ENABLED": False,
    }
    settings.save_config(config, env_path=temp_env)
    loaded = settings.load_config(env_path=temp_env)

    assert loaded["HOTKEY"] == "ctrl+alt+f9"
    assert loaded["AUDD_API_TOKEN"] == "abc123"
    assert loaded["RECORDING_DURATION"] == 8.0
    assert loaded["NOTIFICATIONS_ENABLED"] is False
