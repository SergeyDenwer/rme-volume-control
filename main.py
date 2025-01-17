import socket
import json
import sys
import logging

SOCKET_FILE = "/tmp/rme_volumecontrol.sock"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def send_command(direction):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        cmd = {"action": "volume", "direction": direction}
        sock.sendto(json.dumps(cmd).encode(), SOCKET_FILE)
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("up", "down"):
        logger.error("Usage: python main.py <up|down>")
        sys.exit(1)

    send_command(sys.argv[1])