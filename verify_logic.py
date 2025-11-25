import os
import time
import shutil
import threading
from config_manager import ConfigManager
from server_backend import FileServer
from client_backend import FileClient

# Mock Config
class MockConfig(ConfigManager):
    def __init__(self, data):
        self.config = data

    def get(self, key):
        return self.config.get(key)
    
    def set(self, key, value):
        self.config[key] = value

def test_sync():
    print("Setting up test environment...")
    base_dir = os.getcwd()
    server_dir = os.path.join(base_dir, "test_server_share")
    client_dir = os.path.join(base_dir, "test_client_share")

    if os.path.exists(server_dir): shutil.rmtree(server_dir)
    if os.path.exists(client_dir): shutil.rmtree(client_dir)
    os.makedirs(server_dir)
    os.makedirs(client_dir)

    # Create a test file
    with open(os.path.join(server_dir, "test_file.txt"), "w") as f:
        f.write("Hello World from Server!")

    server_config = MockConfig({
        "server_ip": "127.0.0.1",
        "server_port": 5001,
        "shared_folder": server_dir
    })

    client_config = MockConfig({
        "server_ip": "127.0.0.1",
        "server_port": 5001,
        "shared_folder": client_dir
    })

    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication([])

    print("Starting Server...")
    server = FileServer(server_config)
    server.log_message.connect(lambda msg: print(f"[SERVER] {msg}"))
    server.start_server()
    
    # Wait for server start
    time.sleep(1)

    print("Starting Client Sync...")
    client = FileClient(client_config)
    client.log_message.connect(lambda msg: print(f"[CLIENT] {msg}"))
    
    # Run sync directly
    client.running = True
    try:
        client._sync_process()
    except Exception as e:
        print(f"Client error: {e}")

    print("Sync finished. Verifying...")
    
    dest_file = os.path.join(client_dir, "test_file.txt")
    if os.path.exists(dest_file):
        with open(dest_file, "r") as f:
            content = f.read()
        if content == "Hello World from Server!":
            print("SUCCESS: File synced correctly.")
        else:
            print(f"FAILURE: Content mismatch. Got '{content}'")
    else:
        print("FAILURE: File not found in client folder.")

    print("Cleaning up...")
    server.stop_server()
    # shutil.rmtree(server_dir)
    # shutil.rmtree(client_dir)

if __name__ == "__main__":
    test_sync()
