import struct
import json

# Protocol Constants
CMD_HELLO = "HELLO"
CMD_LIST = "LIST"
CMD_GET = "GET"
CMD_ERROR = "ERROR"
CMD_FILE_START = "FSTART"
CMD_FILE_DATA = "FDATA"
CMD_FILE_END = "FEND"

def send_message(socket, command, payload=None):
    """
    Sends a framed message: [Length (4 bytes)][Command (UTF-8)][Payload (JSON UTF-8)]
    """
    msg = {
        "cmd": command,
        "data": payload
    }
    json_bytes = json.dumps(msg).encode('utf-8')
    # Prefix with length (4 bytes big-endian)
    length_prefix = struct.pack('>I', len(json_bytes))
    socket.sendall(length_prefix + json_bytes)

def receive_message(socket):
    """
    Receives a framed message. Returns (command, payload) or (None, None) on disconnect.
    """
    # Read length prefix
    length_bytes = _recv_all(socket, 4)
    if not length_bytes:
        return None, None
    
    msg_len = struct.unpack('>I', length_bytes)[0]
    
    # Read payload
    payload_bytes = _recv_all(socket, msg_len)
    if not payload_bytes:
        return None, None
        
    try:
        msg = json.loads(payload_bytes.decode('utf-8'))
        return msg.get("cmd"), msg.get("data")
    except json.JSONDecodeError:
        return None, None

def _recv_all(socket, n):
    """Helper to receive exactly n bytes."""
    data = b''
    while len(data) < n:
        packet = socket.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data
