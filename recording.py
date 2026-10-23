from datetime import datetime
import dotenv
import logging
from notifypy import Notify
from pathlib import Path
import pyaudiowpatch as pyaudio
import threading
from typing import Union
from utils import app_state, FileManager, get_logo
import wave

logger = logging.getLogger(__name__)

def record_audio(duration: float, file_manager: FileManager, new_file_event: threading.Event):
    loopback_device: dict[str, Union[str, int, float, bool]] = dict()
    with pyaudio.PyAudio() as p:
        try:
            loopback_device = p.get_default_wasapi_loopback()
        except OSError:
            # Runs on the keyboard library's callback thread: raising SystemExit
            # here would kill that thread and silently break the hotkey.
            logger.error("WASAPI driver is not available on this system. This happens if the Windows Audio service is disabled or if you are on a non-Windows OS (WASAPI is Windows-only).")
            return
        except LookupError:
            logger.error("Could not find a WASAPI loopback device. Check if you have an active output device (speakers or headphones plugged in/enabled).")
            return
        
        logger.info(f"Recording audio from: {loopback_device['name']}")
        notification = Notify()
        notification.application_name = "SoundByte"
        notification.title = "Listening..."
        notification.message = f"Recording audio from {loopback_device['name']}"
        notification.icon = get_logo()
        notification.send(block=False)
        
        app_state.is_recording = True
        try:
            with p.open(
                rate=int(loopback_device["defaultSampleRate"]),
                channels=int(loopback_device["maxInputChannels"]),
                format=pyaudio.paInt16,
                input=True,
                input_device_index=int(loopback_device["index"]),
                frames_per_buffer=1024
            ) as stream:
                logger.info(f"Recording {duration} seconds of audio...")
                num_frames = int(int(loopback_device["defaultSampleRate"]) / 1024 * (duration + 1))

                filename = f"recording_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.wav"
                tmp_path = file_manager.queue_dir / (filename + '.tmp')
                final_path = file_manager.queue_dir / filename

                # Write to temp file first so worker cannot pick up a partial file
                with wave.open(str(tmp_path), 'wb') as wf:
                    wf.setnchannels(int(loopback_device["maxInputChannels"]))
                    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(int(loopback_device["defaultSampleRate"]))
                    for _ in range(num_frames):
                        frame = stream.read(1024, exception_on_overflow=False)
                        wf.writeframes(frame)

                # Atomic rename makes the complete file visible to the worker
                tmp_path.replace(final_path)
                logger.info(f"Saved recording to {final_path}")
        finally:
            app_state.is_recording = False
        new_file_event.set()


