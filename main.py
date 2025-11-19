import flet as ft
from pathlib import Path
from network_core import FileServer, FileClient
import threading


class UpdateApp:
    """Aplicación principal de actualización LAN."""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Sistema de Actualización LAN"
        self.page.window.width = 800
        self.page.window.height = 600
        self.page.padding = 20
        
        # Estado de la aplicación
        self.file_server = None
        self.current_mode = "cliente"  # "servidor" o "cliente"
        self.config_file = Path("Config.txt")
        self.server_port = 65432  # Puerto por defecto
        
        # Crear UI
        self.setup_ui()
        
        # Cargar configuración inicial - hacerlo directamente después de setup_ui
        # Los controles ya están creados y agregados a la página
        self.load_config()
    
    def setup_ui(self):
        """Configura la interfaz de usuario."""
        # Título
        title = ft.Text(
            "Sistema de Actualización LAN",
            size=24,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER
        )
        
        # Control de modo (Segmented Button)
        self.mode_selector = ft.SegmentedButton(
            selected={"cliente"},
            segments=[
                ft.Segment(
                    value="servidor",
                    label=ft.Text("Modo Servidor"),
                    icon="dns"
                ),
                ft.Segment(
                    value="cliente",
                    label=ft.Text("Modo Cliente"),
                    icon="download"
                ),
            ],
            on_change=self.on_mode_changed
        )
        
        # Contenedor de modo servidor
        self.server_container = self.create_server_ui()
        
        # Contenedor de modo cliente
        self.client_container = self.create_client_ui()
        
        # Mostrar cliente por defecto
        self.server_container.visible = False
        
        # Layout principal
        main_column = ft.Column(
            [
                title,
                ft.Divider(height=20),
                self.mode_selector,
                ft.Divider(height=10),
                self.server_container,
                self.client_container,
            ],
            spacing=10,
            expand=True
        )
        
        self.page.add(main_column)
    
    def create_server_ui(self) -> ft.Container:
        """Crea la interfaz del modo servidor."""
        # Estado del servidor
        self.server_status_label = ft.Text(
            "Servidor Inactivo",
            size=16,
            weight=ft.FontWeight.BOLD,
            color="red"
        )
        
        self.server_ip_label = ft.Text("IP Local: -", size=14)
        self.server_port_label = ft.Text("Puerto: 65432", size=14)
        
        # Botón de inicio/detención
        self.server_toggle_btn = ft.ElevatedButton(
            "Iniciar Servidor",
            icon="play_arrow",
            on_click=self.toggle_server,
            color="white",
            bgcolor="green"
        )
        
        # Área de log
        self.server_log = ft.Column(
            [],
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
            height=300
        )
        
        self.server_log_container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Log del servidor:", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=self.server_log,
                        border=ft.border.all(1, "#9E9E9E"),
                        border_radius=5,
                        padding=10,
                        bgcolor="#F5F5F5",
                        expand=True
                    )
                ],
                spacing=5,
                expand=True
            ),
            expand=True
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    self.server_status_label,
                    self.server_ip_label,
                    self.server_port_label,
                    ft.Divider(height=10),
                    self.server_toggle_btn,
                    ft.Divider(height=10),
                    self.server_log_container,
                ],
                spacing=10,
                expand=True
            ),
            expand=True
        )
    
    def create_client_ui(self) -> ft.Container:
        """Crea la interfaz del modo cliente."""
        # Información de configuración
        self.client_config_label = ft.Text("IP del Servidor: -", size=14)
        self.client_config_port_label = ft.Text("Puerto: -", size=14)

        # Campos para editar IP y puerto
        self.client_ip_input = ft.TextField(
            label="IP del Servidor",
            hint_text="192.168.1.50",
            width=300
        )
        self.client_port_input = ft.TextField(
            label="Puerto del Servidor",
            hint_text="65432",
            width=150
        )
        
        self.client_save_config_btn = ft.ElevatedButton(
            "Guardar Configuración",
            icon="save",
            on_click=self.save_config,
            width=200
        )
        
        # Botón de sincronización
        self.client_sync_btn = ft.ElevatedButton(
            "Sincronizar / Descargar",
            icon="sync",
            on_click=self.start_sync,
            color="white",
            bgcolor="blue",
            width=300,
            height=50
        )
        
        # Estado de sincronización
        self.client_status_label = ft.Text(
            "Listo para sincronizar",
            size=14
        )
        
        # Barra de progreso
        self.client_progress_bar = ft.ProgressBar(
            value=0,
            width=600,
            height=20,
            color="blue",
            bgcolor="#E0E0E0"
        )
        
        self.client_progress_text = ft.Text(
            "0 / 0 archivos",
            size=12
        )
        
        return ft.Container(
            content=ft.Column(
                [
                    self.client_config_label,
                    self.client_config_port_label,
                    ft.Row(
                        [
                            self.client_ip_input,
                            self.client_port_input,
                            self.client_save_config_btn,
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10
                    ),
                    ft.Divider(height=20),
                    self.client_sync_btn,
                    ft.Divider(height=10),
                    self.client_status_label,
                    self.client_progress_bar,
                    self.client_progress_text,
                ],
                spacing=10,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            expand=True
        )
    
    def on_mode_changed(self, e):
        """Maneja el cambio de modo."""
        if not e.control.selected:
            return
        
        selected = list(e.control.selected)[0] if e.control.selected else "cliente"
        self.current_mode = selected
        
        if selected == "servidor":
            self.server_container.visible = True
            self.client_container.visible = False
        else:
            self.server_container.visible = False
            self.client_container.visible = True
        
        self.page.update()
    
    def add_server_log(self, message: str):
        """Añade un mensaje al log del servidor."""
        if hasattr(self, 'server_log'):
            # Limitar a los últimos 100 mensajes para evitar problemas de memoria
            if len(self.server_log.controls) > 100:
                self.server_log.controls.pop(0)
            
            self.server_log.controls.append(
                ft.Text(
                    message,
                    size=12,
                    color="#212121"
                )
            )
            self.page.update()
    
    def toggle_server(self, e):
        """Inicia o detiene el servidor."""
        if self.file_server is None or not self.file_server.is_running:
            # Iniciar servidor
            self.file_server = FileServer(
                folder_path="server_folder",
                port=self.server_port,
                log_callback=self.add_server_log
            )
            self.file_server.start()
            
            # Actualizar UI
            local_ip = self.file_server.get_local_ip()
            self.server_status_label.value = "Servidor Activo"
            self.server_status_label.color = "green"
            self.server_ip_label.value = f"IP Local: {local_ip}"
            self.server_port_label.value = f"Puerto: {self.server_port}"
            self.server_toggle_btn.text = "Detener Servidor"
            self.server_toggle_btn.bgcolor = "red"
            
            self.add_server_log(f"Servidor iniciado en {local_ip}:{self.server_port}")
        else:
            # Detener servidor
            self.file_server.stop()
            self.file_server = None
            
            # Actualizar UI
            self.server_status_label.value = "Servidor Inactivo"
            self.server_status_label.color = "red"
            self.server_ip_label.value = "IP Local: -"
            self.server_port_label.value = f"Puerto: {self.server_port}"
            self.server_toggle_btn.text = "Iniciar Servidor"
            self.server_toggle_btn.bgcolor = "green"
        
        self.page.update()
    
    def load_config(self):
        """Carga la configuración desde Config.txt."""
        server_ip = "192.168.1.50"
        server_port = 65432

        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = {line.split("=")[0].strip(): line.split("=")[1].strip() for line in f if "=" in line}
                server_ip = config.get("SERVER_IP", server_ip)
                server_port = int(config.get("SERVER_PORT", server_port))

        self.server_port = server_port
        self.client_ip_input.value = server_ip
        self.client_port_input.value = str(server_port)
        self.client_config_label.value = f"IP del Servidor: {server_ip}"
        self.client_config_port_label.value = f"Puerto: {server_port}"
        self.server_port_label.value = f"Puerto: {server_port}"

        if not self.config_file.exists():
            self.save_config(None) # Guardar valores por defecto

        self.page.update()
    
    def save_config(self, e):
        """Guarda la configuración en Config.txt."""
        server_ip = self.client_ip_input.value.strip() or "192.168.1.50"
        try:
            server_port = int(self.client_port_input.value.strip() or "65432")
            if not 1024 < server_port < 65535:
                raise ValueError("Puerto fuera de rango")
        except ValueError:
            self.client_status_label.value = "Error: El puerto debe ser un número entre 1025 y 65534"
            self.page.update()
            return

        self.server_port = server_port
        self.client_ip_input.value = server_ip
        self.client_port_input.value = str(server_port)
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write(f"SERVER_IP={server_ip}\n")
                f.write(f"SERVER_PORT={server_port}\n")
            
            self.client_config_label.value = f"IP del Servidor: {server_ip}"
            self.client_config_port_label.value = f"Puerto: {server_port}"
            self.server_port_label.value = f"Puerto: {server_port}"
            self.client_status_label.value = "Configuración guardada"
            self.page.update()
        except Exception as ex:
            self.client_status_label.value = f"Error guardando configuración: {ex}"
            self.page.update()
    
    def update_client_status(self, message: str):
        """Actualiza el estado del cliente."""
        self.client_status_label.value = message
        self.page.update()
    
    def update_client_progress(self, current: int, total: int):
        """Actualiza la barra de progreso del cliente."""
        if total > 0:
            progress = current / total
            self.client_progress_bar.value = progress
            self.client_progress_text.value = f"{current} / {total} archivos"
        else:
            self.client_progress_bar.value = 0
            self.client_progress_text.value = "0 / 0 archivos"
        
        self.page.update()
    
    def start_sync(self, e):
        """Inicia la sincronización en un hilo separado."""
        # Obtener IP del servidor
        server_ip = self.client_ip_input.value.strip()
        if not server_ip:
            self.update_client_status("Error: Debe especificar la IP del servidor")
            return
        
        # Deshabilitar botón durante sincronización
        self.client_sync_btn.disabled = True
        self.client_sync_btn.text = "Sincronizando..."
        self.update_client_status("Iniciando sincronización...")
        self.update_client_progress(0, 0)
        self.page.update()
        
        def sync_thread():
            """Hilo de sincronización."""
            client = FileClient(
                server_ip=server_ip,
                server_port=self.server_port,
                local_folder="client_updates",
                progress_callback=self.update_client_progress,
                status_callback=self.update_client_status
            )
            
            success, message = client.sync()
            
            # Restaurar botón
            self.client_sync_btn.disabled = False
            self.client_sync_btn.text = "Sincronizar / Descargar"
            
            if success:
                self.update_client_status(f"✓ {message}")
            else:
                self.update_client_status(f"✗ {message}")
            
            self.page.update()
        
        # Ejecutar en hilo separado para no bloquear UI
        thread = threading.Thread(target=sync_thread, daemon=True)
        thread.start()


def main(page: ft.Page):
    """Función principal de la aplicación."""
    app = UpdateApp(page)


if __name__ == "__main__":
    ft.app(target=main)

