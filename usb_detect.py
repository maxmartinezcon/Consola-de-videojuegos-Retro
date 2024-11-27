import os
import pyudev
import hashlib
import sqlite3
import subprocess as sp
import time


command = "sudo systemctl restart xinit.service"
emulator_name = "xmame"
# Directorios
ROM_DIR = "/home/han/xmame-arm-sdl/roms"  # Carpeta local para guardar las ROMs
DB_FILE = "/home/han/xmame-arm-sdl/roms/roms.db"  # Base de datos para almacenar los hashes

# Funciones
def initialize_database():
    """Crea la base de datos SQLite si no existe."""
    if not os.path.exists(ROM_DIR):
        os.makedirs(ROM_DIR)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            md5_hash TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def calculate_md5(file_path):
    """Calcula el hash MD5 de un archivo."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def rom_exists(md5_hash):
    """Verifica si una ROM ya está registrada en la base de datos."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM roms WHERE md5_hash = ?", (md5_hash,))
    exists = cursor.fetchone()[0] > 0
    conn.close()
    return exists

def add_rom_to_database(file_name, md5_hash):
    """Registra una ROM en la base de datos."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO roms (name, md5_hash) VALUES (?, ?)", (file_name, md5_hash))
    conn.commit()
    conn.close()

def copy_roms(source_dir):
    """Copia archivos .zip del dispositivo USB a la carpeta local de ROMs evitando duplicados."""
    for file in os.listdir(source_dir):
        if file.endswith(".zip"):
            file_path = os.path.join(source_dir, file)
            md5_hash = calculate_md5(file_path)
            if rom_exists(md5_hash):
                print(f"ROM duplicada encontrada: {file}. Saltando.")
            else:
                dest_path = os.path.join(ROM_DIR, file)
                sp.run(["sudo", "cp", file_path, dest_path])
                add_rom_to_database(file, md5_hash)
                print(f"ROM copiada: {file}")

def auto_mount(path):
    """Monta automáticamente el dispositivo USB."""
    args = ["sudo", "udisksctl", "mount", "-b", path]
    sp.run(args)

def get_mount_point(path):
    """Obtiene el punto de montaje de un dispositivo."""
    args = ["sudo", "findmnt", "-unl", "-S", path]
    cp = sp.run(args, capture_output=True, text=True)
    out = cp.stdout.strip()
    if out:
        mount_point = out.split()[0]
        return mount_point
    return None

def print_dev_stats(path):
    roms = []
    vaild_extensions = [".zip"]
    try:
        for file in os.listdir(path):
            if any(file.endswith(ext) for ext in valid_extensions):
                roms.append(file)
        print(f"{path} contiene {len(roms)} ROMs:")
        for rom in roms:
            print(f"  - {roms}")
    except PermissionError:
        print(f"Error: No se tienen permisos para acceder al contenido de {path}.")
    except FileNotFoundError:
        print(f"Error: El directorio {path} no existe.")
    except Exception as e:
        print(f"Ocurrio un error al analizar {path}: {e}")

# Inicialización de la base de datos
initialize_database()

# Configuración de pyudev
context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by(subsystem="block", device_type="partition")

print("Esperando dispositivos USB...")

while True:
    action, device = monitor.receive_device()
    if action != "add":
        continue
    print(f"Dispositivo detectado: {device.sys_name}")
    auto_mount("/dev/" + device.sys_name)
    mount_point = get_mount_point("/dev/" + device.sys_name)
    if not mount_point or not os.path.exists(mount_point):
        print(f"Error: No se pudo encontrar el punto de montaje para {device.sys_name}")
    else:
        print(f"Mount point: {mount_point}")
        print_dev_stats(mount_point)
    if mount_point:
        print(f"Punto de montaje: {mount_point}")
        copy_roms(mount_point)
        try:
            env = os.environ.copy()
            #if "XDG_RUNTIME_DIR" not in os.environ:
            #    os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
            sp.run(["sudo","pkill", "xinit"], check=True, env=env)
            sp.run(["/usr/local/bin/attract", "--config", "/home/han/.attract/", "--build-romlist", emulator_name, "--output", "xmame"], check=True, env=env)
            #key_press()
           # show_loading_screen()
            sp.run(["sudo", "-u", "han", "xinit"], check=True, env=env)
           # sp.run(["sudo", "systemctl", "restart", "xinit.service"], check=True, env=env)
        except sp.CalledProcessError as e:
            print(f"Error al ejecutar el comando: {e}")
        print("Proceso completado. Esperando otro dispositivo USB...")
