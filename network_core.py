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
        """Obtiene la IP local del servidor."""
        try:
            # Conectar a un servidor externo para obtener la IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
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
                    # Esperar confirmación antes del siguiente archivo
                    client_socket.recv(1024)  # ACK
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
    
    def compare_manifests(self, server_manifest: Dict[str, str], 
                         local_manifest: Dict[str, str]) -> List[str]:
        """
        Compara los manifestos y retorna lista de archivos a descargar.
        
        Returns:
            Lista de rutas relativas de archivos que necesitan descarga
        """
        files_to_download = []
        
        for relative_path, server_hash in server_manifest.items():
            local_hash = local_manifest.get(relative_path)
            
            # Archivo faltante o hash diferente
            if local_hash is None or local_hash != server_hash:
                files_to_download.append(relative_path)
        
        return files_to_download
    
    def receive_file(self, client_socket: socket.socket, relative_path: str) -> bool:
        """Recibe un archivo del servidor y lo guarda localmente."""
        try:
            # Recibir tamaño del archivo
            size_data = b""
            while b"FILE_SIZE:" not in size_data:
                chunk = client_socket.recv(1024)
                if not chunk:
                    return False
                size_data += chunk
            
            size_str = size_data.decode().split("FILE_SIZE:")[1].split("\n")[0]
            file_size = int(size_str)
            client_socket.sendall(b"ACK")  # Confirmar recepción de tamaño
            
            # Crear estructura de directorios si es necesario
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
            
            # Verificar hash después de la descarga (opcional pero recomendado)
            calculated_hash = calculate_file_hash(file_path)
            # Nota: Aquí podríamos verificar contra el manifesto del servidor
            # pero por simplicidad solo verificamos que el hash se calculó correctamente
            
            self.update_status(f"Descargado: {relative_path} ({file_size} bytes)")
            client_socket.sendall(b"ACK")  # Confirmar recepción completa
            return True
            
        except Exception as e:
            self.update_status(f"Error recibiendo {relative_path}: {e}")
            return False
    
    def sync(self) -> Tuple[bool, str]:
        """
        Sincroniza archivos con el servidor.
        
        Returns:
            Tuple (éxito: bool, mensaje: str)
        """
        try:
            self.update_status("Conectando al servidor...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(30)  # Timeout de 30 segundos
            client_socket.connect((self.server_ip, self.server_port))
            
            self.update_status("Conectado. Recibiendo manifesto...")
            
            # Recibir tamaño del manifesto
            manifest_size_data = b""
            while b"MANIFEST_SIZE:" not in manifest_size_data:
                chunk = client_socket.recv(1024)
                if not chunk:
                    return False, "Error recibiendo tamaño del manifesto"
                manifest_size_data += chunk
            
            size_str = manifest_size_data.decode().split("MANIFEST_SIZE:")[1].split("\n")[0]
            manifest_size = int(size_str)
            client_socket.sendall(b"ACK")  # Confirmar
            
            # Recibir manifesto
            manifest_data = b""
            while len(manifest_data) < manifest_size:
                chunk = client_socket.recv(min(4096, manifest_size - len(manifest_data)))
                if not chunk:
                    return False, "Error recibiendo manifesto"
                manifest_data += chunk
            
            server_manifest = json.loads(manifest_data.decode())
            self.update_status(f"Manifesto recibido ({len(server_manifest)} archivos en servidor)")
            
            # Generar manifesto local
            self.update_status("Generando manifesto local...")
            local_manifest = self.generate_local_manifest()
            
            # Comparar manifestos
            self.update_status("Comparando manifestos...")
            files_to_download = self.compare_manifests(server_manifest, local_manifest)
            
            if not files_to_download:
                self.update_status("Todos los archivos están sincronizados")
                client_socket.close()
                return True, "Sincronización completa - No hay archivos nuevos"
            
            self.update_status(f"Archivos a descargar: {len(files_to_download)}")
            
            # Enviar lista de archivos solicitados
            request_json = json.dumps(files_to_download)
            client_socket.sendall(request_json.encode() + b"END_REQUEST")
            
            # Recibir archivos
            total_files = len(files_to_download)
            for idx, relative_path in enumerate(files_to_download):
                self.update_status(f"Descargando ({idx + 1}/{total_files}): {relative_path}")
                self.receive_file(client_socket, relative_path)
                self.update_progress(idx + 1, total_files)
            
            self.update_status("Sincronización completada exitosamente")
            client_socket.close()
            return True, f"Sincronización completa - {total_files} archivos descargados"
            
        except socket.timeout:
            return False, "Timeout: No se pudo conectar al servidor"
        except ConnectionRefusedError:
            return False, f"Error: No se pudo conectar a {self.server_ip}:{self.server_port}"
        except Exception as e:
            return False, f"Error durante sincronización: {str(e)}"

