import os
import hashlib

def generate_manifest(folder_path):
    """
    Scans the folder and returns a dictionary of files with their metadata.
    Format: { 'relative/path/to/file': {'hash': 'md5...', 'size': 1234, 'mtime': 123456.7} }
    """
    manifest = {}
    if not os.path.exists(folder_path):
        return manifest

    for root, _, files in os.walk(folder_path):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                rel_path = os.path.relpath(full_path, folder_path).replace("\\", "/")
                stat = os.stat(full_path)
                
                # Calculate hash (MD5 for simplicity/speed in this context)
                hasher = hashlib.md5()
                with open(full_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()

                manifest[rel_path] = {
                    'hash': file_hash,
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                }
            except OSError:
                continue # Skip files we can't read
    return manifest

def is_safe_path(base_path, target_path):
    """
    Checks if the target_path is safely within the base_path to prevent traversal attacks.
    """
    # Resolve absolute paths
    base_abs = os.path.abspath(base_path)
    target_abs = os.path.abspath(target_path)
    return os.path.commonpath([base_abs, target_abs]) == base_abs
