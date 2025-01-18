#!/bin/bash

pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from example. Edit it if needed."
fi

cat > ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.rme.volumecontrol</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python)</string>
        <string>$(pwd)/daemon.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>~/Library/Logs/rme_volumecontrol.log</string>
    <key>StandardErrorPath</key>
    <string>~/Library/Logs/rme_volumecontrol.error.log</string>
</dict>
</plist>
EOF

launchctl unload ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.user.rme.volumecontrol.plist

echo "Installation complete!"
echo "1. Edit .env file if needed"
echo "2. Use commands:"
echo "   main.py up"
echo "   main.py down"