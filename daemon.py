import socket
import os
import mido
import logging
import json
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

SOCKET_FILE = "/tmp/rme_volumecontrol.sock"
DEVICE_PORT = os.getenv('RME_DEVICE_PORT', '')
DEVICE_ID = int(os.getenv('RME_DEVICE_ID', '0x71'), 16)
VOLUME_STEP = float(os.getenv('RME_VOLUME_STEP', '1.0'))
VOLUME_FILE = os.path.join(os.path.dirname(__file__), "volume_state.txt")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def load_volume():
    try:
        with open(VOLUME_FILE, "r") as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 20.0


def save_volume(volume):
    with open(VOLUME_FILE, "w") as f:
        f.write(f"{volume}")


def generate_channel_command(channel_address, parameter_index, parameter_value):
    if not (0 <= channel_address <= 15 and 0 <= parameter_index <= 31 and -2048 <= parameter_value <= 2047):
        raise ValueError("Invalid command parameter values")

    byte1 = (channel_address << 3) | (parameter_index >> 2)
    byte2 = ((parameter_index & 0x03) << 5) | ((parameter_value >> 7) & 0x1F)
    byte3 = parameter_value & 0x7F
    return [byte1, byte2, byte3]


def send_volume_command(volume_db, outport):
    volume_value = int(volume_db * 10)
    if not (-1145 <= volume_value <= 60):
        raise ValueError("The volume should be in the range from -114.5 to 6.0 dB")

    channel = 3
    parameter = 12
    command = generate_channel_command(channel, parameter, volume_value)
    sysex_message = [0x00, 0x20, 0x0D, DEVICE_ID, 0x02] + command

    outport.send(mido.Message('sysex', data=sysex_message))


def change_volume(direction, outport):
    step = 1.0
    current_volume = load_volume()

    if direction == "up":
        current_volume += step
    elif direction == "down":
        current_volume -= step
    else:
        logger.error("Unknown command!")
        return

    current_volume = max(-114.5, min(6.0, current_volume))
    send_volume_command(current_volume, outport)
    save_volume(current_volume)
    logger.info(f"Volume changed to: {current_volume}")


def cleanup(_signum, _frame):
    logger.info("Terminating the daemon...")
    try:
        os.unlink(SOCKET_FILE)
    except OSError:
        pass
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    logger.info("Starting volume control daemon...")

    try:
        outport = mido.open_output(DEVICE_PORT)
        logger.info("MIDI port opened successfully")
    except Exception as e:
        logger.error(f"Error opening MIDI port: {e}")
        return

    try:
        os.unlink(SOCKET_FILE)
    except OSError:
        pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(SOCKET_FILE)
    logger.info("Socket created successfully")

    while True:
        try:
            data = sock.recv(1024)
            cmd = json.loads(data.decode())
            if cmd["action"] == "volume":
                change_volume(cmd["direction"], outport)
        except Exception as e:
            logger.error(f"Error processing command: {e}")


if __name__ == "__main__":
    main()