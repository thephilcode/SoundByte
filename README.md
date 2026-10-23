# SoundByte

## A minimal music recognition app for Windows

I got sick of the fact that Shazam isn't available on Windows, so I decided to build my own. SoundByte is a system tray application that records system audio being played on your Windows PC, sends it to a music recognition API (AudD), and returns the song title, artist, and album information—just like Shazam, but native to Windows.

### Features

- System tray application with dynamic status indicator (online/offline, pending count)
- Global hotkey (configurable via .env file or Settings UI) to trigger audio recording
- Automatic system audio recording using WASAPI loopback (Windows only) - captures what you hear through speakers/headphones
- Offline queuing of recordings when internet is unavailable
- Automatic retry with exponential backoff when offline
- Integration with AudD music recognition API for accurate song identification
- Desktop notifications for recognition results and app status
- Configurable audio token and hotkey via environment variables or Settings UI
- Comprehensive logging to file and console for debugging
- Recognition history (accessible via system tray) to view past recognitions
- Settings UI (accessible via system tray) to modify hotkey, API token, recording duration, and notification preferences

### Prerequisites

- Windows 10/11
- Python 3.13+ (or specify the version from .python-version)
- Uv package manager

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd SoundByte
   ```
2. Install dependencies:
   - Using uv: `uv sync` (if you have uv installed)
   - Using pip: `pip install -r requirements.txt`
3. Create a `.env` file based on `.env.example` and fill in your AudD API token and preferred hotkey:
   ```dotenv
   AUDD_API_TOKEN=your_audd_api_token_here
   HOTKEY=windows+shift+z
   ```

### Usage

1. Run the application:
   ```bash
   python main.py
   ```
2. Use the configured hotkey (default: windows+shift+z) to start recording.
3. Right-click the tray icon to access the menu:
   - Toggle online/offline status indicator
   - Retry now (force retry of pending recordings)
   - Pause/Resume syncing
   - Open recordings folder
   - View logs
   - View History
   - Settings
   - Quit application

### Configuration

The application can be configured via the `.env` file or through the Settings UI (accessible from the tray menu).

#### Environment Variables

- `AUDD_API_TOKEN`: Your AudD API token (get from https://audd.io/)
- `HOTKEY`: Keyboard shortcut to trigger recording (e.g., `windows+shift+z`)
- `RECORDING_DURATION`: Recording duration in seconds (default: 10.0, max: 12.0)
- `NOTIFICATIONS_ENABLED`: Whether to show desktop notifications (default: true)

#### Settings UI

The Settings UI allows you to modify:

- Global hotkey
- AudD API token
- Recording duration (seconds)
- Show notifications (on/off)

Changes made in the Settings UI are saved to the `.env` file and applied immediately (where possible, such as hotkey changes) or on restart.

### Building from Source

The PyInstaller spec file is checked in, so the build is reproducible:

```bash
pyinstaller SoundByte.spec
```

Note: Update `SoundByte.spec` if you need to add hidden imports for tkinter, dotenv, pystray, etc.

### Running the tests

```bash
uv sync --group dev
uv run pytest
```

The GUI tests need a display. On Linux, run them headlessly with `xvfb-run -a uv run pytest`; on Windows they run as-is.

### Troubleshooting

- **Audio recording issues**: Ensure the application has access to your system audio and that WASAPI loopback is available (Windows only)
- **API token invalid**: Check your AudD API token in the .env file
- **Internet connectivity**: The app works offline and will retry when online
- **Logs**: Find logs at `%APPDATA%\SoundByte\logs\`
- **History**: View recognition history via the tray menu -> View History
- **Settings or History window will not open**: These windows need a visible parent, and the app's root window is hidden by design. If a dialog is stuck, use the tray menu to open it again.

### Contributing

If you wish to contribute to SoundByte:

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a pull request.

Please ensure your code follows the existing style and includes appropriate tests.

### License

This project is licensed under the MIT License - see the LICENSE file for details.
