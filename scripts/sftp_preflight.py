#!/usr/bin/env python3
"""Read-only SFTP preflight. Never uploads, deletes or changes remote files."""
import os
import sys
import paramiko

host = os.environ["IONOS_SFTP_HOST"]
user = os.environ["IONOS_SFTP_USER"]
password = os.environ["IONOS_SFTP_PASSWORD"]
fingerprint = os.environ["IONOS_SFTP_HOSTKEY_SHA256"]
port = int(os.getenv("IONOS_SFTP_PORT", "22"))

transport = paramiko.Transport((host, port))
try:
    transport.start_client(timeout=20)
    key = transport.get_remote_server_key()
    import base64, hashlib
    actual = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
    if actual != fingerprint:
        raise RuntimeError("Host-Key stimmt nicht mit dem hinterlegten Fingerprint überein")
    transport.auth_password(user, password)
    if not transport.is_authenticated():
        raise RuntimeError("SFTP-Authentifizierung fehlgeschlagen")
    with paramiko.SFTPClient.from_transport(transport) as sftp:
        print("SFTP-Anmeldung erfolgreich. Kein Upload durchgeführt.")
        print("Remote-Verzeichnis /nachrichten vorhanden:", bool(sftp.stat("/nachrichten")))
finally:
    transport.close()
