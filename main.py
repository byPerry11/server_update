import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QDialog, QVBoxLayout, 
                               QPushButton, QLabel, QWidget, QMessageBox, QComboBox, QHBoxLayout, QFrame)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from config_manager import ConfigManager
from server_backend import FileServer
from client_backend import FileClient
from gui_components import ServerWidget, ClientWidget

# Stylesheet
STYLESHEET = """
QMainWindow {
    background-color: white;
}
QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    color: #333;
}
QPushButton {
    background-color: #0078D7;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #005A9E;
}
QPushButton:pressed {
    background-color: #004578;
}
QPushButton:disabled {
    background-color: #CCCCCC;
    color: #666;
}
QLabel {
    color: #333;
}
QComboBox {
    border: 1px solid #0078D7;
    border-radius: 4px;
    padding: 4px;
    min-width: 100px;
}
QProgressBar {
    border: 1px solid #0078D7;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #0078D7;
}
QTextEdit {
    border: 1px solid #DDD;
    background-color: #F9F9F9;
    border-radius: 4px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.setWindowTitle("LAN File Sharer")
        self.resize(500, 400)
        
        # Set Icon
        if os.path.exists("assets/Icon_app.ico"):
            self.setWindowIcon(QIcon("assets/Icon_app.ico"))
        
        # Apply Theme
        self.setStyleSheet(STYLESHEET)
        
        self.backend = None
        self.central_widget = None
        
        self.setup_main_layout()
        self.init_mode()

    def setup_main_layout(self):
        # Main container
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        self.main_layout = QVBoxLayout(self.main_container)
        
        # Header (Mode Selector)
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Mode:"))
        
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Client", "Server"])
        self.mode_selector.currentIndexChanged.connect(self.change_mode)
        header_layout.addWidget(self.mode_selector)
        header_layout.addStretch()
        
        self.main_layout.addLayout(header_layout)
        
        # Content Area (Placeholder)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_area)
        
        # Footer (Logo)
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        logo_label = QLabel()
        if os.path.exists("assets/TPV_logo.png"):
            pixmap = QPixmap("assets/TPV_logo.png")
            if not pixmap.isNull():
                logo_label.setPixmap(pixmap.scaled(100, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        footer_layout.addWidget(logo_label)
        
        self.main_layout.addLayout(footer_layout)

    def init_mode(self):
        mode = self.config_manager.get("mode")
        # Default to Client if invalid
        if mode not in ["client", "server"]:
            mode = "client"
            
        # Set selector without triggering signal initially
        self.mode_selector.blockSignals(True)
        self.mode_selector.setCurrentText(mode.capitalize())
        self.mode_selector.blockSignals(False)
        
        self.load_mode_ui(mode)

    def change_mode(self, index):
        mode = self.mode_selector.currentText().lower()
        
        # Confirm change if backend is running? 
        # For simplicity, we just stop and switch.
        if self.backend:
            if isinstance(self.backend, FileServer):
                self.backend.stop_server()
            elif isinstance(self.backend, FileClient):
                self.backend.stop_sync()
        
        self.config_manager.set("mode", mode)
        self.load_mode_ui(mode)

    def load_mode_ui(self, mode):
        # Clear current content
        if self.central_widget:
            self.central_widget.setParent(None)
            self.central_widget.deleteLater()
            self.backend = None

        if mode == "server":
            self.setWindowTitle("LAN File Sharer - Server")
            self.backend = FileServer(self.config_manager)
            self.central_widget = ServerWidget(self.backend)
        else:
            self.setWindowTitle("LAN File Sharer - Client")
            self.backend = FileClient(self.config_manager)
            self.central_widget = ClientWidget(self.backend)
        
        self.content_layout.addWidget(self.central_widget)

    def closeEvent(self, event):
        if hasattr(self, 'backend') and self.backend:
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
