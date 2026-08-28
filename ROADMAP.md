# Soundbyte Roadmap

## Completed
- [x] tray app
- [x] global hotkey
- [x] automatic system-audio recognition
- [x] save recordings offline and automatically identify when back online, then notify of results
- [x] recognition history (view past recognitions within the app)
- [x] settings UI (to change hotkey, API token, recording duration, and notification preferences without editing .env)

## In Progress / Planned
- [ ] Recognition history search (search past recognitions by song title, artist, or album)
- [ ] Settings UI enhancements:
    - [ ] Audio input device selection (if multiple are available)
    - [ ] Logging level configuration (INFO, DEBUG, etc.)
    - [ ] Offline retry interval and backoff multiplier configuration
    - [ ] Option to automatically start with Windows
- [ ] Multiple API fallbacks (e.g., AcoustID as a secondary option)
- [ ] Optional: Offline fingerprinting (generate local fingerprints for faster matching when online)
- [ ] Improve offline retry logic (configurable backoff, max retries)
- [ ] Option to disable notifications or customize notification sounds

## Notes
- Browser extension support is redundant since the app listens to whatever is playing on the speakers, regardless of source.
- Consider splitting the roadmap into near-term and long-term if appropriate.