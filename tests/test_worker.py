"""Tests for the background worker's file cleanup."""
import os
import time

import pytest

from utils import FileManager
from worker import cleanup_old_files


@pytest.fixture
def file_manager(tmp_path):
    dirs = [tmp_path / name for name in ("logs", "queue", "completed", "failed")]
    for d in dirs:
        d.mkdir()
    return FileManager(*dirs)


def _make_old(path, age_seconds):
    """Create a file whose birth time is age_seconds in the past."""
    path.write_bytes(b"x")
    # st_birthtime cannot be set directly, so backdate the mtime and patch the
    # stat result the cleanup reads.
    old = time.time() - age_seconds
    os.utime(path, (old, old))
    return path


def test_cleanup_removes_old_files(file_manager, monkeypatch):
    """A file older than max_age_seconds must be deleted."""
    old = _make_old(file_manager.completed_dir / "old.wav", 20 * 86400)

    # Mock _file_age to return a value > max_age_seconds regardless of OS birthtime
    import worker
    monkeypatch.setattr(worker, "_file_age", lambda p: 20 * 86400)

    cleanup_old_files(file_manager, max_age_seconds=864000)
    assert not old.exists(), "the old file was not deleted"


def test_cleanup_keeps_recent_files(file_manager):
    recent = file_manager.completed_dir / "recent.wav"
    recent.write_bytes(b"x")
    cleanup_old_files(file_manager, max_age_seconds=864000)
    assert recent.exists(), "a recent file was deleted"


def test_cleanup_survives_an_unremovable_file(file_manager, monkeypatch):
    """A locked file must not raise: that would kill the worker thread."""
    locked = _make_old(file_manager.completed_dir / "locked.wav", 20 * 86400)

    def refuse(path):
        raise PermissionError("file is in use")

    monkeypatch.setattr(os, "remove", refuse)

    # Must not raise.
    cleanup_old_files(file_manager, max_age_seconds=864000)
    assert locked.exists()


def test_cleanup_handles_a_missing_directory(file_manager, monkeypatch):
    """A directory that has been removed must not raise either."""
    monkeypatch.setattr(
        type(file_manager.failed_dir), "iterdir", lambda self: iter(())
    )
    cleanup_old_files(file_manager, max_age_seconds=864000)
