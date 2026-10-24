import logging
from notifypy import Notify
import os
from pathlib import Path
import sys
import time
from datetime import datetime
from threading import Event
from typing import Any, Tuple
from utils import app_state, FileManager, get_logo, new_file_event, paused_event, resume_event, retry_event, shutdown_event, save_history_entry

logger = logging.getLogger(__name__)

class Backoff:
    def __init__(self, initial=10, maximum=300):
        self.initial = initial
        self.maximum = maximum
        self.current = initial
        
    def wait(self):
        time.sleep(self.current)
        self.current = (min(self.current * 2, self.maximum))
        
    def reset(self):
        self.current = self.initial


def _file_age(file: Path) -> float:
    """Seconds since the file was created.

    st_birthtime is only available on Windows; fall back to the modification
    time, which is the same for the recordings this app creates.
    """
    stat = file.stat()
    created = getattr(stat, 'st_birthtime', stat.st_mtime)
    return time.time() - created


def cleanup_old_files(file_manager: FileManager, max_age_seconds: int = 864000) -> None:
    """Delete processed recordings older than max_age_seconds.

    Also cleans up orphaned .wav.tmp files that may be left behind if recording
    is interrupted.

    A file that cannot be removed (locked by Explorer or antivirus) is logged
    and skipped: raising here would take the worker thread down.
    """
    # Clean up completed and failed directories
    for directory in (file_manager.completed_dir, file_manager.failed_dir):
        for file in directory.iterdir():
            if _file_age(file) > max_age_seconds:
                logger.info(f"Deleting old file: {file}")
                try:
                    os.remove(file)
                except OSError as e:
                    logger.warning(f"Could not delete old file {file}: {e}")

    # Clean up orphaned .wav.tmp files in queue directory
    for tmp_file in file_manager.queue_dir.glob('*.wav.tmp'):
        if _file_age(tmp_file) > max_age_seconds:
            logger.info(f"Deleting orphaned temp file: {tmp_file}")
            try:
                os.remove(tmp_file)
            except OSError as e:
                logger.warning(f"Could not delete orphaned temp file {tmp_file}: {e}")


def sync_worker(file_manager: FileManager, send_to_recognition, is_online, event: Event = new_file_event):
    """A state-driven worker that sits in the background and processes audio files one by one."""

    def handle_pause():
        """ Helper to handle paused state and wait for resume signal """
        logger.info("Syncing paused. Waiting for resume signal")
        resume_event.wait()
        logger.info("Resume signal received. Continuing sync")
        resume_event.clear()
        paused_event.clear()
                
    logger.info("Thread started. Waiting for recorded files...")
    
    backoff = Backoff()
    last_cleanup_time = 0
    CLEANUP_INTERVAL = 86400
    
    while not shutdown_event.is_set():
        if paused_event.is_set():
            shutdown_event.wait(timeout=1)
            continue
        while not paused_event.is_set():
            event.wait(timeout=60)
            event.clear()
            pending_files = file_manager.get_pending_files()
            pending_files.sort(key=lambda p: p.stat().st_mtime)
            app_state.pending_files = len(pending_files)
            
            # Check actual online status and update app_state regardless of pending files
            currently_online = is_online()
            if currently_online != app_state.is_online:
                app_state.is_online = currently_online
                # Trigger tray menu refresh
                retry_event.set()
                if app_state.is_online:
                    backoff.reset()
                    logger.info("App is now online")
                else:
                    # Just went offline
                    # We only notify once per offline transition
                    if not any(p.stat().st_mtime > time.time() - 60 for p in file_manager.get_pending_files()) and app_state.NOTIFICATIONS_ENABLED:
                        # Use a simple flag or just check if we just transitioned
                        pass
                    # The original code had 'count=0' here, but 'count' was local to the inner loop.
                    # Let's handle the notification properly.
                    notification = Notify()
                    notification.application_name = "SoundByte"
                    notification.title = "App Offline"
                    notification.message = "Your recording is saved for recognition when you go back online.\nWe'll notify you of the results"
                    notification.icon = get_logo()
                    notification.send(block=False)
                    logger.info("App is now offline")

            current_time = time.time()
            if current_time - last_cleanup_time > CLEANUP_INTERVAL:
                cleanup_old_files(file_manager)
                last_cleanup_time = current_time

            if not pending_files:
                continue
            
            if paused_event.is_set():
                handle_pause()
            
            logger.info(f"Sync signal received. Processing {len(pending_files)} audio recording(s)")

            count=0
            while not shutdown_event.is_set() and not paused_event.is_set():
                if is_online():
                    break
                if retry_event.is_set():
                    retry_event.clear()
                    logger.info("Retry signal received: Retrying connection...")
                    backoff.current = backoff.initial
                # Check actual online status and update app_state if changed
                currently_online = is_online()
                if currently_online != app_state.is_online:
                    app_state.is_online = currently_online
                    # Trigger tray menu refresh
                    retry_event.set()
                    if app_state.is_online:
                        backoff.reset()
                        logger.info("App is now online")
                    else:
                        # Just went offline
                        if app_state.NOTIFICATIONS_ENABLED:
                            notification = Notify()
                            notification.application_name = "SoundByte"
                            notification.title = "App Offline"
                            notification.message = "Your recording is saved for recognition when you go back online.\nWe'll notify you of the results"
                            notification.icon = get_logo()
                            notification.send(block=False)
                        logger.info("App is now offline")
                elif not app_state.is_online:
                    # Still offline, continue with backoff
                    logger.info(f"App is offline. Retrying connection in {backoff.current} seconds")
                    backoff.wait()

            if shutdown_event.is_set():
                continue
            elif paused_event.is_set():
                handle_pause()
            elif is_online():
                backoff.reset()
                app_state.is_online = True
                for file in pending_files:
                    results: Tuple[bool, Any] | None = send_to_recognition(file)
                        
                    count = 0
                    while results is None or results[0] is False:
                        if count < 3:
                            results = send_to_recognition(file)
                            count += 1
                        else:
                            break

                    response = results[1] if results and isinstance(results[1], dict) else {}
                    match_fields = (
                        "title",
                        "artist",
                        "album",
                        "release_date",
                        "label",
                        "song_link",
                    )
                    has_match = any(
                        response.get(field) is not None
                        and str(response.get(field)).strip().lower() not in ("", "unknown")
                        for field in match_fields
                    )

                    if results and results[0] is True and has_match:
                         file_manager.move_to_completed(file)
                         app_state.pending_files -= 1
                         notification = Notify()
                         notification.application_name = "SoundByte"
                         notification.title = "Song Match Found!"
                         notification.message = f"Title: {str(response.get('title', 'Unknown'))}\nArtist: {str(response.get('artist', 'Unknown'))}"
                         notification.icon = get_logo()
                         notification.send(block=False)
                         # Save to history
                         entry = {
                             "timestamp": datetime.now().isoformat(),
                             "title": str(response.get('title', '')),
                             "artist": str(response.get('artist', '')),
                             "album": str(response.get('album', '')),
                             "song_link": str(response.get('song_link', ''))
                         }
                         save_history_entry(entry)
                    else:
                        file_manager.move_to_failed(file)
                        app_state.pending_files -= 1
                        notification = Notify()
                        notification.application_name = "SoundByte"
                        notification.title = "Song Not Recognised"
                        notification.message = "The song was not recognised"
                        notification.icon = get_logo()
                        notification.send(block=False)
                # End of for file in pending_files loop
            # End of elif is_online() block
        # End of while not paused_event.is_set() loop
    # End of while not shutdown_event.is_set() loop



