from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTextEdit, QProgressBar, QFileDialog)
from PySide6.QtCore import Qt, Slot

class ServerWidget(QWidget):
    def __init__(self, server_backend, parent=None):
        super().__init__(parent)
        self.backend = server_backend
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Server is Offline")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
        layout.addWidget(self.status_label)

        self.toggle_btn = QPushButton("Go Online")
        layout.addWidget(self.toggle_btn)

        # Folder Selection UI
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel(f"Shared: {self.backend.config.get('shared_folder')}")
        self.folder_label.setWordWrap(True)
        folder_layout.addWidget(self.folder_label)
        
        self.select_folder_btn = QPushButton("Change Folder")
        folder_layout.addWidget(self.select_folder_btn)
        layout.addLayout(folder_layout)

        layout.addWidget(QLabel("Connection Logs:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def connect_signals(self):
        self.toggle_btn.clicked.connect(self.toggle_server)
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.backend.log_message.connect(self.append_log)
        self.backend.server_status.connect(self.update_status)

    @Slot()
    def select_folder(self):
        current_folder = self.backend.config.get("shared_folder")
        folder = QFileDialog.getExistingDirectory(self, "Select Shared Folder", current_folder)
        if folder:
            self.backend.config.set("shared_folder", folder)
            self.folder_label.setText(f"Shared: {folder}")
            self.append_log(f"Shared folder updated to: {folder}")

    @Slot()
    def toggle_server(self):
        if self.backend.running:
            self.backend.stop_server()
        else:
            self.backend.start_server()

    @Slot(bool)
    def update_status(self, is_running):
        if is_running:
            self.status_label.setText("Server is Online")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: green;")
            self.toggle_btn.setText("Go Offline")
        else:
            self.status_label.setText("Server is Offline")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
            self.toggle_btn.setText("Go Online")

    @Slot(str)
    def append_log(self, message):
        self.log_area.append(message)


class ClientWidget(QWidget):
    def __init__(self, client_backend, parent=None):
        super().__init__(parent)
        self.backend = client_backend
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel("Ready to connect")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.sync_btn = QPushButton("Download / Sync Files")
        layout.addWidget(self.sync_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("Activity Logs:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def connect_signals(self):
        self.sync_btn.clicked.connect(self.start_sync)
        self.backend.log_message.connect(self.append_log)
        self.backend.connection_status.connect(self.update_connection_status)
        self.backend.progress_update.connect(self.update_progress)
        self.backend.sync_finished.connect(self.on_sync_finished)

    @Slot()
    def start_sync(self):
        self.sync_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.backend.start_sync()

    @Slot(bool)
    def update_connection_status(self, connected):
        if connected:
            self.status_label.setText("Connected to Server")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: black;")
            self.sync_btn.setEnabled(True)

    @Slot(int, int)
    def update_progress(self, current, total):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.status_label.setText(f"Downloading file {current} of {total}")

    @Slot()
    def on_sync_finished(self):
        self.status_label.setText("Sync Completed")
        self.sync_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        
        # Open the folder
        folder = self.backend.config.get("shared_folder")
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    @Slot(str)
    def append_log(self, message):
        self.log_area.append(message)
