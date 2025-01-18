# RME ADI-2 Volume Control

A simple volume-control daemon for RME ADI-2 DAC/Pro on macOS using MIDI.  
Allows you to adjust volume via command line (or keyboard shortcuts) and keep the software state in sync with the device.

## Features

- Control RME ADI-2 volume from the command line  
- Automatically launches as a system daemon  
- Periodically polls the device to track hardware-based volume changes  
- Ensures volume remains within a safe range (−114.5 to 6.0 dB)

## Requirements

- macOS  
- **Python 3** (must be installed by the user)  
- RME ADI-2 DAC/Pro/Pro SE connected via USB

## Installation

1. **Clone** this repository:
   ```bash
   git clone https://github.com/SergeyDenwer/rme-volume-control
   cd rme-volume-control
   ```

2. **Run setup script**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   This will:
   - Install required Python packages (using `pip install -r requirements.txt`)
   - Create a `.env` file if it doesn't exist
   - Create and load the `launchd` service
   - Symlink `main.py` to `/usr/local/bin/rme-volume`

3. **Adjust `.env`** if needed:
   ```bash
   cp .env.example .env
   ```
   - `RME_DEVICE_ID` (`0x71` = ADI-2 DAC, `0x72` = ADI-2 Pro, `0x73` = ADI-2/4 Pro SE)
   - `RME_VOLUME_STEP` (step in dB, default `1.0`)
   - `RME_DEVICE_PORT` (the MIDI port name; you can list available ports with `sendmidi list` or another tool)

## Usage

After installation, you can run:
```bash
rme-volume up
rme-volume down
```
The daemon runs in the background and keeps the MIDI connection open for fast response.

### How It Works

1. **Daemon** (`daemon.py`) runs continuously under macOS `launchd`, keeps the MIDI device open, and **periodically polls** the device:
   - Reads current active output (Line Out or Phones).
   - Reads the actual volume levels for each output.
   - If you change volume physically on the RME device, the daemon will pick it up within a few seconds and update its internal state.
2. **CLI** (`main.py`) sends simple commands (“up” or “down”) to the daemon via a Unix domain socket. The daemon then updates volume without delay, respecting the last known state from device polling.

## Troubleshooting

- **Check service status**:
  ```bash
  launchctl list | grep rme
  ```
- **Logs**:
  ```bash
  tail -f ~/Library/Logs/rme_volumecontrol.log
  tail -f ~/Library/Logs/rme_volumecontrol.error.log
  ```
- **Restart service**:
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
  launchctl load ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
  ```

## Uninstallation

1. Unload and remove the launchd service:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
   rm ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
   ```
2. Remove any shortcuts or aliases that call `rme-volume`.

## License

[MIT](https://choosealicense.com/licenses/mit/)
