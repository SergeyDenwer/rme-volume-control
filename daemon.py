#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import os
import mido
import logging
import json
import signal
import sys
import time
from dotenv import load_dotenv

# Step 1. Load environment variables
load_dotenv()

# Constants for socket path, MIDI port, and so on
SOCKET_FILE = "/tmp/rme_volumecontrol.sock"
DEVICE_PORT = os.getenv('RME_DEVICE_PORT', '')
DEVICE_ID = int(os.getenv('RME_DEVICE_ID', '0x71'), 16)
VOLUME_STEP = float(os.getenv('RME_VOLUME_STEP', '1.0'))
STATE_FILE = os.path.join(os.path.dirname(__file__), "rme_device_state.json")

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# SysEx prefix for RME and message codes
RME_SYSEX_PREFIX = [0x00, 0x20, 0x0D]
GET_STATUS_CODE = 0x07
GET_PARAMETER_CODE = 0x03
SET_PARAMETER_CODE = 0x02
RME_RESPONSE_CODE = 0x01
PARAMETER_VOLUME_INDEX = 12

# Global state to store active outputs and volumes
current_state = {
    "active_outputs": [],
    "volumes": {3: None, 6: None, 9: None}
}

# Will store the MIDI port opened in main()
outport = None

# A flag to control the main loop
run_main_loop = True


def generate_status_request_command():
    """
    Builds a SysEx message to request device status (active output).
    """
    return RME_SYSEX_PREFIX + [DEVICE_ID, GET_STATUS_CODE]


def generate_get_parameter_command():
    """
    Builds a SysEx message to request parameters (volume, etc.).
    """
    return RME_SYSEX_PREFIX + [DEVICE_ID, GET_PARAMETER_CODE, 0x09]


def generate_channel_command(channel_address, parameter_index, parameter_value):
    """
    Generates the 3-byte command to set a certain parameter for a channel.
    """
    if not (0 <= channel_address <= 15 and 0 <= parameter_index <= 31 and -2048 <= parameter_value <= 2047):
        raise ValueError("Invalid command parameters.")

    byte1 = (channel_address << 3) | (parameter_index >> 2)
    byte2 = ((parameter_index & 0x03) << 5) | ((parameter_value >> 7) & 0x1F)
    byte3 = parameter_value & 0x7F
    return [byte1, byte2, byte3]


def check_active_output():
    """
    Sends a SysEx status request to find which output is active (Line Out or Phones).
    Returns [3] or [6, 9], or an empty list if no response.
    """
    if not outport:
        return []

    # Clear pending messages
    for _ in outport.iter_pending():
        pass

    msg_req = generate_status_request_command()
    outport.send(mido.Message('sysex', data=msg_req))

    start_time = time.time()
    while (time.time() - start_time) < 0.3:
        msg = outport.receive(block=False)
        if msg and msg.type == "sysex":
            data = msg.data
            if len(data) >= 6 and list(data[0:3]) == RME_SYSEX_PREFIX and data[3] == DEVICE_ID:
                status_data = data[5:]
                if len(status_data) >= 1:
                    if status_data[0] == 8:
                        return [3]  # Line Out
                    elif status_data[0] == 9:
                        return [6, 9]  # Phones 1/2 and Phones 3/4
        time.sleep(0.01)

    return []


def check_volume_values():
    """
    Sends a SysEx request to get volumes of Line Out (3), Phones 1/2 (6), and Phones 3/4 (9).
    Returns a dict like:
      {
        3: {'volume': -20.0},
        6: {'volume': -18.5},
        9: {'volume': None}
      }
    """
    if not outport:
        return {}

    for _ in outport.iter_pending():
        pass

    msg_req = generate_get_parameter_command()
    outport.send(mido.Message('sysex', data=msg_req))

    outputs = {
        3: {'volume': None},
        6: {'volume': None},
        9: {'volume': None}
    }

    start_time = time.time()
    while (time.time() - start_time) < 0.3:
        msg = outport.receive(block=False)
        if msg and msg.type == "sysex":
            data = msg.data
            if len(data) >= 6 and list(data[0:3]) == RME_SYSEX_PREFIX and data[3] == DEVICE_ID:
                if data[4] == RME_RESPONSE_CODE:
                    i = 5
                    while i < (len(data) - 1):
                        address = data[i] >> 3
                        index = ((data[i] & 0x07) << 2) | (data[i + 1] >> 5)
                        value = ((data[i + 1] & 0x1F) << 7) | data[i + 2]
                        if value >= 2048:
                            value -= 4096

                        if index == PARAMETER_VOLUME_INDEX and address in outputs:
                            outputs[address]['volume'] = value / 10.0
                        i += 3
        time.sleep(0.01)

    return outputs


def send_volume_command(volume_db, active_outputs):
    """
    Sends a SysEx command to set volume_db (float) for each channel in active_outputs.
    """
    if not outport:
        return

    volume_value = int(volume_db * 10)
    if volume_value < -1145:
        volume_value = -1145
    if volume_value > 60:
        volume_value = 60

    for ch in active_outputs:
        cmd3bytes = generate_channel_command(ch, PARAMETER_VOLUME_INDEX, volume_value)
        sysex_data = RME_SYSEX_PREFIX + [DEVICE_ID, SET_PARAMETER_CODE] + cmd3bytes
        outport.send(mido.Message('sysex', data=sysex_data))


def change_volume(direction):
    """
    Handles increment/decrement of volume through the local state:
    1) Uses current_state["active_outputs"] to find channels.
    2) Gets current volume from the first channel, modifies it by VOLUME_STEP.
    3) Clamps it between -114.5 and +6 dB.
    4) Calls send_volume_command(...) and updates local state accordingly.
    """
    if not current_state["active_outputs"]:
        # If there's no known active output, try to read from device
        ao = check_active_output()
        if ao:
            current_state["active_outputs"] = ao
        else:
            logger.error("No active output found (local state is empty and device did not respond).")
            return

    first_out = current_state["active_outputs"][0]
    current_vol = current_state["volumes"].get(first_out, -20.0)
    if current_vol is None:
        current_vol = -20.0

    if direction == "up":
        current_vol += VOLUME_STEP
    elif direction == "down":
        current_vol -= VOLUME_STEP
    else:
        logger.error(f"Unknown direction for change_volume: {direction}")
        return

    current_vol = max(-114.5, min(6.0, current_vol))

    for ch in current_state["active_outputs"]:
        current_state["volumes"][ch] = current_vol

    send_volume_command(current_vol, current_state["active_outputs"])

    logger.info(f"Set volume to {current_vol} dB (active channels: {current_state['active_outputs']})")


def write_state_to_file(active_outputs, volumes_map, filename=STATE_FILE):
    """
    Saves a data structure with active outputs and volumes to a JSON file.
    The volumes_map should look like {3: {'volume': -20.0}, 6: {...}, 9: {...}}.
    """
    data_to_save = {
        "timestamp": time.time(),
        "active_outputs": active_outputs,
        "volumes": {}
    }
    for ch, info in volumes_map.items():
        data_to_save["volumes"][ch] = info["volume"]

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing JSON to file {filename}: {e}")


def poll_device_and_save(interval=1.0):
    """
    Periodically:
     1) Reads the active output from device.
     2) Reads volume values from device.
     3) Updates current_state and writes JSON to file.
     4) Waits 'interval' seconds.
    """
    ao = check_active_output()
    if ao:
        current_state["active_outputs"] = ao

    vols = check_volume_values()
    for ch, info in vols.items():
        current_state["volumes"][ch] = info["volume"]

    write_state_to_file(current_state["active_outputs"], vols)
    time.sleep(interval)


def cleanup(signum, frame):
    """
    Handler for SIGINT/SIGTERM signals: cleans up resources and stops the loop.
    """
    global run_main_loop
    run_main_loop = False
    logger.info(f"Received signal {signum}, stopping the script...")

    try:
        os.unlink(SOCKET_FILE)
    except OSError:
        pass

    if outport:
        outport.close()

    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    logger.info("Starting the volume-control daemon with periodic polling...")

    global outport
    try:
        outport = mido.open_ioport(DEVICE_PORT)
        logger.info(f"MIDI port '{DEVICE_PORT}' opened successfully.")
    except Exception as e:
        logger.error(f"Error opening MIDI port '{DEVICE_PORT}': {e}")
        sys.exit(1)

    try:
        os.unlink(SOCKET_FILE)
    except OSError:
        pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(SOCKET_FILE)
    logger.info(f"Unix socket created at {SOCKET_FILE}")

    global run_main_loop
    poll_timer = time.time()

    while run_main_loop:
        sock.settimeout(0.5)
        try:
            data = sock.recv(1024)
            cmd = json.loads(data.decode("utf-8"))
            if cmd.get("action") == "volume":
                direction = cmd.get("direction")
                change_volume(direction)
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"Error handling socket: {e}")

        if time.time() - poll_timer >= 1.0:
            poll_device_and_save(interval=0)
            poll_timer = time.time()

    cleanup(0, None)


if __name__ == "__main__":
    main()
