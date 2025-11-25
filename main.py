import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QDialog, QVBoxLayout, 
                               QPushButton, QLabel, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from config_manager import ConfigManager
from server_backend import FileServer
from client_backend import FileClient
from gui_components import ServerWidget, ClientWidget

class ModeSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Mode")
        self.selected_mode = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose application mode:"))
        
        server_btn = QPushButton("Server (Admin)")
        server_btn.clicked.connect(lambda: self.set_mode("server"))
        layout.addWidget(server_btn)

        client_btn = QPushButton("Client")
        client_btn.clicked.connect(lambda: self.set_mode("client"))
        layout.addWidget(client_btn)

    def set_mode(self, mode):
        self.selected_mode = mode
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.setWindowTitle("LAN File Sharer")
        self.resize(400, 300) # Small window
        
        self.init_mode()

    def init_mode(self):
        mode = self.config_manager.get("mode")
        
        # If mode is not set or invalid (e.g. default "client" but maybe we want to force choice first time? 
        # The config_manager defaults to "client". 
        # Requirement: "la primera vez que defines el modo (Cliente/Servidor) se mantiene".
        # So I should probably check if it was explicitly set? 
        # My config_manager sets default. I should probably change config_manager to not have a default mode or check if config file existed.
        # For now, let's assume if config file didn't exist, we might want to ask.
        # But config_manager.load_config() creates it if missing.
        # Let's check if we should ask. 
        # Actually, let's just ask if the user wants to change it? No, "se mantiene".
        # I'll implement a logic: If config.txt exists, use it. If not (or first run), ask.
        # Since config_manager creates it, I can't easily tell.
        # I'll modify this logic: I will check if "mode_set" flag is in config? 
        # Or just rely on the user editing config.txt as per requirements?
        # Requirement: "Esta ip debe estar configurada en un archivo config.txt... En este mismo archivo se tambien se debe asignar la ruta..."
        # It implies manual config for IP/Folder.
        # But for Mode: "la primera vez que defines el modo... se mantiene". This implies UI selection.
        
        # I'll check if I can force a selection if it's the "default" default. 
        # I'll add a specific check.
        pass 

        # Let's just show the dialog if we want to be safe, or maybe add a "Reset" feature.
        # For this implementation, I will assume "client" default is fine, BUT I will add a check:
        # If the config file was just created (I can't tell easily).
        # I'll just add a "mode_configured": false to default config.
        
        if not self.config_manager.get("mode_configured"):
            dialog = ModeSelectionDialog(self)
            if dialog.exec():
                mode = dialog.selected_mode
                self.config_manager.set("mode", mode)
                self.config_manager.set("mode_configured", True)
            else:
                sys.exit() # User closed dialog

        self.setup_ui(mode)

    def setup_ui(self, mode):
        if mode == "server":
            self.setWindowTitle("LAN File Sharer - Server")
            self.backend = FileServer(self.config_manager)
            self.central_widget = ServerWidget(self.backend)
        else:
            self.setWindowTitle("LAN File Sharer - Client")
            self.backend = FileClient(self.config_manager)
            self.central_widget = ClientWidget(self.backend)
        
        self.setCentralWidget(self.central_widget)

    def closeEvent(self, event):
        if hasattr(self, 'backend'):
            if isinstance(self.backend, FileServer):
                self.backend.stop_server()
            elif isinstance(self.backend, FileClient):
                self.backend.stop_sync()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
