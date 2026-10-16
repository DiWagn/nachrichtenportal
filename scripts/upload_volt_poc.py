import base64
import hashlib
import os
from pathlib import Path
from urllib.request import urlopen
import paramiko

host = os.environ["IONOS_SFTP_HOST"]
user = os.environ["IONOS_SFTP_USER"]
target = "/nachrichten/VoltPOC"
payload = Path("generated/index.php").read_bytes()
if not payload.startswith(b"<?php") or b"<!doctype html>" not in payload.lower():
    raise RuntimeError("PHP-Seite fehlt oder ist nicht vollstaendig")

connection = paramiko.Transport((host, 22))
try:
    connection.get_security_options().key_types = ("ssh-ed25519",)
    connection.start_client(timeout=20)
    actual = "SHA256:" + base64.b64encode(hashlib.sha256(connection.get_remote_server_key().asbytes()).digest()).decode().rstrip("=")
    if actual != os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:
        raise RuntimeError("Server-Fingerprint passt nicht")
    connection.auth_password(user, os.environ["IONOS_SFTP_PASSWORD"])
    with paramiko.SFTPClient.from_transport(connection) as sftp:
        try:
            sftp.mkdir(target)
        except OSError:
            sftp.stat(target)
        probe = target + "/php-check.php"
        with sftp.open(probe, "wb") as f:
            f.write(b"<?php header('Content-Type: text/plain'); echo 'PHP_OK_91734'; ?>")
        try:
            with urlopen("https://dirkwagner.de/nachrichten/VoltPOC/php-check.php", timeout=20) as response:
                if response.read().strip() != b"PHP_OK_91734":
                    raise RuntimeError("PHP wird auf IONOS nicht ausgefuehrt")
        finally:
            sftp.remove(probe)
        with sftp.open(target + "/index.php", "wb") as f:
            f.write(payload)
        with sftp.open(target + "/index.php", "rb") as f:
            if f.read() != payload:
                raise RuntimeError("Ruecklesekontrolle fehlgeschlagen")
    print("VoltPOC: PHP-Seite mit Passwortabfrage uebertragen")
finally:
    connection.close()
