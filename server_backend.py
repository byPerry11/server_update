import os
import socket
import threading
from PySide6.QtCore import QObject, Signal, Slot
from config_manager import ConfigManager
from file_utils import generate_manifest, is_safe_path
import network_protocol as protocol

class ClientHandler(threading.Thread):
    def __init__(self, conn, addr, shared_folder, log_signal):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.shared_folder = shared_folder
        self.log_signal = log_signal
        self.running = True

    def run(self):
        self.log_signal.emit(f"Client connected: {self.addr}")
        try:
            while self.running:
                cmd, data = protocol.receive_message(self.conn)
                if not cmd:
                    break
                
                if cmd == protocol.CMD_HELLO:
                    protocol.send_message(self.conn, protocol.CMD_HELLO, "Welcome")
                
                elif cmd == protocol.CMD_LIST:
                    self.log_signal.emit(f"Sending manifest to {self.addr}")
                    manifest = generate_manifest(self.shared_folder)
                    protocol.send_message(self.conn, protocol.CMD_LIST, manifest)
                
                elif cmd == protocol.CMD_GET:
                    filename = data.get("filename")
                    self.handle_get_file(filename)
                    
        except Exception as e:
            self.log_signal.emit(f"Error with client {self.addr}: {e}")
        finally:
            self.conn.close()
            self.log_signal.emit(f"Client disconnected: {self.addr}")

    def handle_get_file(self, filename):
        full_path = os.path.join(self.shared_folder, filename)
        if not is_safe_path(self.shared_folder, full_path) or not os.path.exists(full_path):
            protocol.send_message(self.conn, protocol.CMD_ERROR, "File not found or access denied")
            return

        self.log_signal.emit(f"Sending file {filename} to {self.addr}")
        file_size = os.path.getsize(full_path)
        protocol.send_message(self.conn, protocol.CMD_FILE_START, {"filename": filename, "size": file_size})

        with open(full_path, 'rb') as f:
            while chunk := f.read(8192):
                protocol.send_message(self.conn, protocol.CMD_FILE_DATA, chunk.decode('latin1')) # Encode binary as latin1 for JSON safety or use base64. 
                # actually, JSON is bad for binary. Let's stick to the protocol but maybe we should send raw bytes for FDATA?
                # The protocol defined in network_protocol.py uses JSON. 
                # For simplicity in this "simple" app, I will encode binary chunks as latin1 string which maps 1-1 to bytes.
                # A better approach would be base64, but latin1 is faster for this hack.
        
        protocol.send_message(self.conn, protocol.CMD_FILE_END, {"filename": filename})

class FileServer(QObject):
    log_message = Signal(str)
    server_status = Signal(bool)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config = config_manager
        self.server_socket = None
        self.running = False
        self.thread = None

    def start_server(self):
        if self.running:
            return

        ip = self.config.get("server_ip")
        port = self.config.get("server_port")
        folder = self.config.get("shared_folder")

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except OSError as e:
                self.log_message.emit(f"Failed to create shared folder: {e}")
                return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((ip, port))
            self.server_socket.listen(5)
            self.running = True
            self.server_status.emit(True)
            self.log_message.emit(f"Server started on {ip}:{port}")
            self.log_message.emit(f"Sharing folder: {folder}")
            
            self.thread = threading.Thread(target=self._accept_loop)
            self.thread.start()
        except Exception as e:
            self.log_message.emit(f"Failed to start server: {e}")
            self.running = False

    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.server_status.emit(False)
        self.log_message.emit("Server stopped")

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                handler = ClientHandler(conn, addr, self.config.get("shared_folder"), self.log_message)
                handler.start()
            except OSError:
                break
