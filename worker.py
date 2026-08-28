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
            
            current_time = time.time()
            if current_time - last_cleanup_time > CLEANUP_INTERVAL:
                completed_files = list(file_manager.completed_dir.iterdir())
                failed_files = list(file_manager.failed_dir.iterdir())
                file_list = (completed_files, failed_files)
                
                for _ in file_list:
                    for file in _:
                        age = file.stat().st_birthtime
                        diff = current_time - age
                        if diff > 864000:
                            logger.info(f"Deleting old file: {file}")
                            os.remove(file)
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
                if not app_state.is_online:
                    app_state.is_online = False
                shutdown_event.wait(timeout=backoff.current)
                if shutdown_event.is_set():
                    logger.info("Shutdown signal received. Ending loop")
                    sys.exit(0)
                backoff.current = (min(backoff.current * 2, backoff.maximum))
                if count==0:
                    notification = Notify()
                    notification.application_name = "SoundByte"
                    notification.title = "App Offline"
                    notification.message = "Your recording is saved for recognition when you go back online.\nWe'll notify you of the results"
                    notification.send(block=False)
                    count+=1
                logger.info(f"App is offline. Retrying connection in {backoff.current} seconds")
            
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
                            file_manager.move_to_failed(file)
                            notification = Notify()
                            notification.title = "Song Not Recognised"
                            notification.message = "The song was not recognised"
                            notification.icon = get_logo()
                            notification.send(block=False)
                            break

                    if results and results[0] is True:
                         file_manager.move_to_completed(file)
                         notification = Notify()
                         notification.title = "Song Match Found!"
                         notification.message = f"Title: {str(results[1]['title'])}\nArtist: {str(results[1]['artist'])}"
                         notification.icon = get_logo()
                         notification.send(block=False)
                         # Save to history
                         entry = {
                             "timestamp": datetime.now().isoformat(),
                             "title": str(results[1].get('title', '')),
                             "artist": str(results[1].get('artist', '')),
                             "album": str(results[1].get('album', '')),
                             "song_link": str(results[1].get('song_link', ''))
                         }
                         save_history_entry(entry)
                # End of for file in pending_files loop
            # End of elif is_online() block
        # End of while not paused_event.is_set() loop
    # End of while not shutdown_event.is_set() loop



