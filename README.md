# RME ADI-2 Volume Control

Simple volume control daemon for RME ADI-2 DAC/Pro on macOS using MIDI.
You need this if you want to control the volume from the keyboard.

## Features

- Control RME ADI-2 volume using command line
- Runs as a system daemon

## Requirements

- macOS
- Python 3
- RME ADI-2 DAC/Pro/Pro SE connected via USB

## Installation

1. Clone repository:
```bash
git clone https://github.com/SergeyDenwer/rme-volume-control
cd rme-volume-control
```

2. Run setup script:
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Install required Python packages
- Create .env file from example if it doesn't exist
- Create and load the launchd service

## Configuration

Copy `.env.example` to `.env` and edit if needed:

```bash
cp .env.example .env
```

Available settings:
- `RME_DEVICE_ID` - MIDI device ID in hex format:
  - `0x71` - ADI-2 DAC (default)
  - `0x72` - ADI-2 Pro
  - `0x73` - ADI-2/4 Pro SE
- `RME_VOLUME_STEP` - Volume change step in dB (default: 1.0)
- `RME_DEVICE_PORT` - Device port. Search using:
```bash
brew install sendmidi
sendmidi list
```
## Usage

After installation, you can use:
```bash
main.py up
main.py down
```

The daemon will:
- Start automatically on system boot
- Keep the MIDI connection open for fast response
- Store volume state between sessions
- Ensure volume stays within safe range (-114.5 to 6.0 dB)

### Setting up Keyboard Shortcuts in macOS

1. Open "Shortcuts" app (Apple Shortcuts)
2. Click "+" to create a new shortcut
3. Select "Run Shell Script" as the action
4. In the script field, enter:
```bash
cd /path/to/rme-volume-control && /path/to/python main.py up
```

To get correct paths:
- Your python path: run `which python` in terminal
- Project path: use `pwd` in project directory

Create two shortcuts:
- One for volume up with the command above
- One for volume down (replace `up` with `down` in the command)

Then in Shortcuts preferences:

- Add keyboard shortcuts for both commands
- Make sure shortcuts don't conflict with system or other app shortcuts

## Troubleshooting

Check service status:
```bash
launchctl list | grep rme
```

View logs:
```bash
tail -f ~/Library/Logs/rme_volumecontrol.log
tail -f ~/Library/Logs/rme_volumecontrol.error.log
```

Restart service:
```bash
launchctl unload ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
launchctl load ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
```

## Uninstallation

1. Stop and remove service:
```bash
launchctl unload ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
rm ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist
```

2. Remove Apple Shortcuts and Keyboard Shortcuts

## Technical Details

The system consists of two parts:
1. A daemon that maintains MIDI connection (`daemon.py`)
2. A command line interface for sending volume commands (`main.py`)

Communication between them is done via Unix Domain Socket.

## Contributing

Pull requests are welcome! Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)