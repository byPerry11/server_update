import os
import socket
import threading
from PySide6.QtCore import QObject, Signal
from config_manager import ConfigManager
from file_utils import generate_manifest
import network_protocol as protocol

class FileClient(QObject):
    log_message = Signal(str)
    connection_status = Signal(bool)
    progress_update = Signal(int, int) # current, total
    sync_finished = Signal()

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config = config_manager
        self.socket = None
        self.running = False
        self.thread = None

    def start_sync(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._sync_process)
        self.thread.start()

    def stop_sync(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def _sync_process(self):
        ip = self.config.get("server_ip")
        port = self.config.get("server_port")
        local_folder = self.config.get("shared_folder")

        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

        try:
            self.log_message.emit(f"Connecting to {ip}:{port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, port))
            self.connection_status.emit(True)
            self.log_message.emit("Connected.")

            # Handshake
            protocol.send_message(self.socket, protocol.CMD_HELLO)
            cmd, data = protocol.receive_message(self.socket)
            if cmd != protocol.CMD_HELLO:
                self.log_message.emit("Handshake failed.")
                return

            # Request Manifest
            self.log_message.emit("Requesting file list...")
            protocol.send_message(self.socket, protocol.CMD_LIST)
            cmd, server_manifest = protocol.receive_message(self.socket)
            
            if cmd != protocol.CMD_LIST:
                self.log_message.emit("Failed to get file list.")
                return

            # Compare Manifests
            self.log_message.emit("Comparing files...")
            local_manifest = generate_manifest(local_folder)
            files_to_download = []

            for rel_path, meta in server_manifest.items():
                if rel_path not in local_manifest or local_manifest[rel_path]['hash'] != meta['hash']:
                    files_to_download.append(rel_path)

            total_files = len(files_to_download)
            if total_files == 0:
                self.log_message.emit("Folder is up to date.")
                self.sync_finished.emit()
                return

            self.log_message.emit(f"Found {total_files} new/modified files.")
            
            for i, filename in enumerate(files_to_download):
                if not self.running:
                    break
                
                self.log_message.emit(f"Downloading {filename}...")
                self._download_file(filename, local_folder)
                self.progress_update.emit(i + 1, total_files)

            self.log_message.emit("Sync completed.")
            self.sync_finished.emit()

        except Exception as e:
            self.log_message.emit(f"Sync error: {e}")
        finally:
            self.connection_status.emit(False)
            if self.socket:
                self.socket.close()
            self.running = False

    def _download_file(self, filename, local_folder):
        protocol.send_message(self.socket, protocol.CMD_GET, {"filename": filename})
        
        # Wait for FSTART
        cmd, data = protocol.receive_message(self.socket)
        if cmd != protocol.CMD_FILE_START:
            self.log_message.emit(f"Error starting download for {filename}")
            return

        full_path = os.path.join(local_folder, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'wb') as f:
            while True:
                cmd, data = protocol.receive_message(self.socket)
                if cmd == protocol.CMD_FILE_DATA:
                    f.write(data.encode('latin1')) # Decode latin1 back to bytes
                elif cmd == protocol.CMD_FILE_END:
                    break
                elif cmd == protocol.CMD_ERROR:
                    self.log_message.emit(f"Server error: {data}")
                    break
                else:
                    break
