# Sistema de Actualización LAN Inteligente

Sistema de distribución de archivos/actualizaciones por red LAN con sincronización inteligente basada en hashes SHA-256.

## 🚀 Características

- **Modo Servidor**: Comparte archivos desde `server_folder/`
- **Modo Cliente**: Sincroniza archivos desde el servidor a `client_updates/`
- **Sincronización Inteligente**: Solo transfiere archivos nuevos o modificados usando hashes SHA-256
- **Interfaz Gráfica Moderna**: UI desarrollada con Flet
- **Barras de Progreso**: Visualización del progreso de descarga

## 📋 Requisitos

- Python 3.x
- Flet (se instala automáticamente con requirements.txt)

## 🔧 Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## 🎮 Uso

### Iniciar la Aplicación

```bash
python main.py
```

### Modo Servidor

1. Seleccionar "Modo Servidor" en la interfaz
2. Hacer clic en "Iniciar Servidor"
3. El servidor escuchará en el puerto **65432**
4. La IP local se mostrará en la interfaz
5. Los archivos a compartir deben estar en la carpeta `server_folder/`

### Modo Cliente

1. Seleccionar "Modo Cliente" en la interfaz
2. Configurar la IP del servidor:
   - Editar el campo "IP del Servidor"
   - Hacer clic en "Guardar Configuración"
   - O editar directamente el archivo `Config.txt` con el formato: `SERVER_IP=192.168.1.50`
3. Hacer clic en "Sincronizar / Descargar"
4. El sistema comparará los manifestos y descargará solo los archivos necesarios
5. Los archivos se guardarán en `client_updates/`

## 📁 Estructura del Proyecto

```
server_update/
├── main.py              # Interfaz gráfica Flet y lógica principal
├── network_core.py      # Clases FileServer y FileClient
├── Config.txt           # Configuración del cliente (IP del servidor)
├── requirements.txt     # Dependencias Python
├── server_folder/       # Directorio compartido por el servidor
└── client_updates/      # Directorio donde el cliente guarda archivos
```

## 🔐 Funcionamiento de la Sincronización

1. **Generación de Manifesto**: El servidor genera un JSON con rutas relativas y hashes SHA-256 de todos los archivos
2. **Comparación**: El cliente compara su manifesto local con el del servidor
3. **Detección de Cambios**:
   - Archivos **faltantes** localmente → Se descargan
   - Archivos con **hash diferente** → Se descargan (actualización)
   - Archivos con **mismo hash** → Se ignoran (ya están actualizados)
4. **Transferencia**: Solo se transfieren los archivos necesarios

## 📝 Notas

- El servidor escucha en `0.0.0.0:65432` (todas las interfaces)
- El cliente se conecta al puerto **65432** por defecto
- Los archivos se transfieren en chunks de 8KB
- Se verifica el hash después de cada descarga para garantizar integridad
- El sistema maneja múltiples clientes simultáneamente (cada uno en su propio hilo)

## 🐛 Solución de Problemas

- **Error de conexión**: Verificar que el servidor esté activo y la IP sea correcta
- **Puerto ocupado**: Cambiar el puerto en `network_core.py` si el 65432 está en uso
- **Archivos no se sincronizan**: Verificar permisos de escritura en `client_updates/`

