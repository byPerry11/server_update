import json
import os

CONFIG_FILE = "config.txt"

DEFAULT_CONFIG = {
    "mode": "client",  # client or server
    "server_ip": "127.0.0.1",
    "server_port": 5000,
    "shared_folder": os.path.join(os.getcwd(), "shared_downloads"),
    "mode_configured": False
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except (json.JSONDecodeError, IOError):
                print("Error loading config, using defaults.")
        else:
            self.save_config()

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
