import socket
import json
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple
import threading


def calculate_file_hash(filepath: Path) -> str:
    """Calcula el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculando hash de {filepath}: {e}")
        return ""


def generate_manifest(folder_path: Path) -> Dict[str, str]:
    """
    Genera un manifesto (diccionario) con rutas relativas y hashes SHA-256.
    
    Args:
        folder_path: Ruta del directorio a escanear
        
    Returns:
        Dict con formato {ruta_relativa: hash_sha256}
    """
    manifest = {}
    
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        return manifest
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = Path(root) / file
            try:
                relative_path = file_path.relative_to(folder_path)
                # Usar barras normales para compatibilidad multiplataforma
                relative_path_str = str(relative_path).replace("\\", "/")
                file_hash = calculate_file_hash(file_path)
                if file_hash:
                    manifest[relative_path_str] = file_hash
            except Exception as e:
                print(f"Error procesando {file_path}: {e}")
    
    return manifest


class FileServer:
    """Servidor que comparte archivos y maneja sincronización inteligente."""
    
    def __init__(self, folder_path: str, port: int = 65432, log_callback=None):
        self.folder_path = Path(folder_path)
        self.port = port
        self.log_callback = log_callback
        self.server_socket = None
        self.is_running = False
        self.server_thread = None
        
        # Crear directorio si no existe
        self.folder_path.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str):
        """Registra un mensaje usando el callback si está disponible."""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)
    
    def get_local_ip(self) -> str:
        """Obtiene la IP local del servidor, priorizando métodos offline."""
        try:
            # Método 1: Iterar sobre las IPs asociadas al hostname
            hostname = socket.gethostname()
            addrs = socket.gethostbyname_ex(hostname)[2]
            for ip in addrs:
                if not ip.startswith("127."):
                    return ip
        except Exception:
            pass # Continuar al siguiente método si este falla

        try:
            # Método 2: Conectar a un servidor externo (fallback)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1" # Fallback final
    
    def generate_manifest(self) -> Dict[str, str]:
        """Genera el manifesto del servidor."""
        return generate_manifest(self.folder_path)
    
    def send_file(self, client_socket: socket.socket, relative_path: str):
        """Envía un archivo al cliente por chunks."""
        file_path = self.folder_path / relative_path
        
        if not file_path.exists():
            self.log(f"Error: Archivo no encontrado: {relative_path}")
            client_socket.sendall(b"FILE_NOT_FOUND")
            return
        
        try:
            # Enviar tamaño del archivo primero
            file_size = file_path.stat().st_size
            client_socket.sendall(f"FILE_SIZE:{file_size}".encode())
            client_socket.recv(1024)  # ACK
            
            # Enviar archivo por chunks
            with open(file_path, "rb") as f:
                sent = 0
                while sent < file_size:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    client_socket.sendall(chunk)
                    sent += len(chunk)
            
            self.log(f"Archivo enviado: {relative_path} ({file_size} bytes)")
        except Exception as e:
            self.log(f"Error enviando {relative_path}: {e}")
    
    def handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Maneja la conexión de un cliente."""
        self.log(f"Conexión recibida de {address[0]}:{address[1]}")
        
        try:
            # Generar y enviar manifesto
            manifest = self.generate_manifest()
            manifest_json = json.dumps(manifest)
            manifest_size = len(manifest_json.encode())
            
            # Enviar tamaño del manifesto
            client_socket.sendall(f"MANIFEST_SIZE:{manifest_size}".encode())
            client_socket.recv(1024)  # ACK
            
            # Enviar manifesto
            client_socket.sendall(manifest_json.encode())
            self.log(f"Manifesto enviado ({len(manifest)} archivos)")
            
            # Recibir lista de archivos solicitados
            request_data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                if b"END_REQUEST" in request_data:
                    break
            
            request_str = request_data.decode().replace("END_REQUEST", "")
            if request_str.strip():
                requested_files = json.loads(request_str)
                self.log(f"Archivos solicitados: {len(requested_files)}")
                
                # Enviar cada archivo solicitado
                for relative_path in requested_files:
                    self.send_file(client_socket, relative_path)
                    # Esperar ACK/NACK del cliente
                    ack = client_socket.recv(1024)
                    if ack == b"NACK":
                        self.log(f"Fallo en cliente al recibir: {relative_path} (hash incorrecto)")

            else:
                self.log("No hay archivos para sincronizar")
            
            self.log(f"Conexión con {address[0]} completada")
            
        except Exception as e:
            self.log(f"Error manejando cliente {address}: {e}")
        finally:
            client_socket.close()
    
    def start(self):
        """Inicia el servidor en un hilo separado."""
        if self.is_running:
            return
        
        def server_loop():
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                self.server_socket.bind(("0.0.0.0", self.port))
                self.server_socket.listen(5)
                self.is_running = True
                self.log(f"Servidor iniciado en puerto {self.port}")
                
                while self.is_running:
                    try:
                        client_socket, address = self.server_socket.accept()
                        # Manejar cada cliente en un hilo separado
                        client_thread = threading.Thread(
                            target=self.handle_client,
                            args=(client_socket, address),
                            daemon=True
                        )
                        client_thread.start()
                    except Exception as e:
                        if self.is_running:
                            self.log(f"Error aceptando conexión: {e}")
            except Exception as e:
                self.log(f"Error iniciando servidor: {e}")
                self.is_running = False
        
        self.server_thread = threading.Thread(target=server_loop, daemon=True)
        self.server_thread.start()
    
    def stop(self):
        """Detiene el servidor."""
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.log("Servidor detenido")


class FileClient:
    """Cliente que se conecta al servidor y sincroniza archivos."""
    
    def __init__(self, server_ip: str, server_port: int = 65432, 
                 local_folder: str = "client_updates", 
                 progress_callback=None, status_callback=None):
        self.server_ip = server_ip
        self.server_port = server_port
        self.local_folder = Path(local_folder)
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        
        # Crear directorio local si no existe
        self.local_folder.mkdir(parents=True, exist_ok=True)
    
    def update_status(self, message: str):
        """Actualiza el estado usando el callback si está disponible."""
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)
    
    def update_progress(self, current: int, total: int):
        """Actualiza el progreso usando el callback si está disponible."""
        if self.progress_callback:
            self.progress_callback(current, total)
    
    def generate_local_manifest(self) -> Dict[str, str]:
        """Genera el manifesto local del cliente."""
        return generate_manifest(self.local_folder)
    
    def get_sync_actions(self, server_manifest: Dict[str, str], 
                         local_manifest: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """
        Compara manifestos y retorna listas de acciones (descargar, eliminar).
        
        Returns:
            Tuple (files_to_download, files_to_delete)
        """
        files_to_download = []
        server_files = set(server_manifest.keys())
        local_files = set(local_manifest.keys())

        # Archivos a descargar (nuevos o modificados)
        for relative_path, server_hash in server_manifest.items():
            local_hash = local_manifest.get(relative_path)
            if local_hash is None or local_hash != server_hash:
                files_to_download.append(relative_path)
        
        # Archivos a eliminar (existen localmente pero no en el servidor)
        files_to_delete = list(local_files - server_files)
        
        return files_to_download, files_to_delete
    
    def receive_file(self, client_socket: socket.socket, relative_path: str, expected_hash: str) -> bool:
        """Recibe un archivo del servidor, lo guarda y verifica su hash."""
        try:
            # Recibir tamaño del archivo
            size_data = b""
            while b"FILE_SIZE:" not in size_data:
                chunk = client_socket.recv(1024)
                if not chunk:
                    self.update_status(f"Error: Conexión cerrada al recibir tamaño de {relative_path}")
                    return False
                size_data += chunk
            
            size_str = size_data.decode().split("FILE_SIZE:")[1].split("\n")[0]
            file_size = int(size_str)
            client_socket.sendall(b"ACK")  # Confirmar recepción de tamaño
            
            # Crear estructura de directorios
            file_path = self.local_folder / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Recibir archivo por chunks
            received = 0
            with open(file_path, "wb") as f:
                while received < file_size:
                    chunk = client_socket.recv(min(8192, file_size - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            
            if received < file_size:
                self.update_status(f"Error: Transferencia incompleta para {relative_path}")
                file_path.unlink() # Eliminar archivo incompleto
                return False

            # Verificar hash después de la descarga
            calculated_hash = calculate_file_hash(file_path)
            if calculated_hash != expected_hash:
                self.update_status(f"Error: Hash incorrecto para {relative_path}. Archivo corrupto.")
                file_path.unlink()  # Eliminar archivo corrupto
                client_socket.sendall(b"NACK") # Notificar al servidor del fallo
                return False
            
            self.update_status(f"Verificado: {relative_path}")
            client_socket.sendall(b"ACK")  # Confirmar recepción completa y correcta
            return True
            
        except Exception as e:
            self.update_status(f"Error recibiendo {relative_path}: {e}")
            # Intentar eliminar el archivo si algo falló
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
            return False
    
    def sync(self) -> Tuple[bool, str]:
        """
        Sincroniza archivos con el servidor, incluyendo descargas y eliminaciones.
        
        Returns:
            Tuple (éxito: bool, mensaje: str)
        """
        try:
            self.update_status("Conectando al servidor...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(30)
            client_socket.connect((self.server_ip, self.server_port))
            
            self.update_status("Conectado. Recibiendo manifesto...")
            
            # Recibir manifesto del servidor
            manifest_size_data = b""
            while b"MANIFEST_SIZE:" not in manifest_size_data:
                chunk = client_socket.recv(1024)
                if not chunk: return False, "Error recibiendo tamaño del manifesto"
                manifest_size_data += chunk
            
            size_str = manifest_size_data.decode().split("MANIFEST_SIZE:")[1].split("\n")[0]
            manifest_size = int(size_str)
            client_socket.sendall(b"ACK")
            
            manifest_data = b""
            while len(manifest_data) < manifest_size:
                chunk = client_socket.recv(min(4096, manifest_size - len(manifest_data)))
                if not chunk: return False, "Error recibiendo manifesto"
                manifest_data += chunk
            
            server_manifest = json.loads(manifest_data.decode())
            self.update_status(f"Manifesto recibido ({len(server_manifest)} archivos en servidor)")
            
            # Generar y comparar manifestos
            local_manifest = self.generate_local_manifest()
            files_to_download, files_to_delete = self.get_sync_actions(server_manifest, local_manifest)
            
            # Eliminar archivos obsoletos
            deleted_count = 0
            if files_to_delete:
                self.update_status(f"Eliminando {len(files_to_delete)} archivos obsoletos...")
                for relative_path in files_to_delete:
                    file_path = self.local_folder / relative_path
                    try:
                        if file_path.exists():
                            file_path.unlink()
                            self.update_status(f"Eliminado: {relative_path}")
                            deleted_count += 1
                    except Exception as e:
                        self.update_status(f"Error eliminando {relative_path}: {e}")

            # Descargar archivos nuevos o modificados
            downloaded_count = 0
            if files_to_download:
                self.update_status(f"Archivos a descargar: {len(files_to_download)}")
                request_json = json.dumps(files_to_download)
                client_socket.sendall(request_json.encode() + b"END_REQUEST")
                
                total_files = len(files_to_download)
                for idx, relative_path in enumerate(files_to_download):
                    self.update_status(f"Descargando ({idx + 1}/{total_files}): {relative_path}")
                    expected_hash = server_manifest[relative_path]
                    if self.receive_file(client_socket, relative_path, expected_hash):
                        downloaded_count += 1
                    self.update_progress(idx + 1, total_files)
            else:
                client_socket.sendall(b"END_REQUEST")

            # Mensaje final
            summary = []
            if downloaded_count > 0:
                summary.append(f"{downloaded_count} archivos descargados")
            if deleted_count > 0:
                summary.append(f"{deleted_count} archivos eliminados")
            
            if not summary:
                message = "Sincronización completa - No hay cambios"
            else:
                message = f"Sincronización completa - {', '.join(summary)}"

            success = downloaded_count == len(files_to_download)
            self.update_status(f"{'✓' if success else '✗'} {message}")
            client_socket.close()
            return success, message
            
        except socket.timeout:
            return False, "Timeout: No se pudo conectar al servidor"
        except ConnectionRefusedError:
            return False, f"Error: No se pudo conectar a {self.server_ip}:{self.server_port}"
        except Exception as e:
            return False, f"Error durante sincronización: {str(e)}"

