#!/usr/bin/env python3
"""Upload a self-contained preview only; never touch the live homepage."""
import base64
import hashlib
import os
from pathlib import Path
import paramiko

source = Path("portal-preview.html")
payload = source.read_bytes().replace(
    b'fetch("./berichte/"+date+".json"',
    b'fetch("../berichte/"+date+".json"'
)
if b'id="positive-only"' not in payload or b'original_markdown' not in payload:
    raise RuntimeError("Preview preflight failed")
if b'fetch("../berichte/"+date+".json"' not in payload:
    raise RuntimeError("Preview JSON path not adjusted")
target_dir = "/nachrichten/vorschau"
target = target_dir + "/index.html"
t = paramiko.Transport((os.environ["IONOS_SFTP_HOST"], 22))
try:
    t.get_security_options().key_types = ("ssh-ed25519",)
    t.start_client(timeout=20)
    actual = "SHA256:" + base64.b64encode(hashlib.sha256(t.get_remote_server_key().asbytes()).digest()).decode().rstrip("=")
    if actual != os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:
        raise RuntimeError("Host key mismatch")
    t.auth_password(os.environ["IONOS_SFTP_USER"], os.environ["IONOS_SFTP_PASSWORD"])
    if not t.is_authenticated():
        raise RuntimeError("SFTP authentication failed")
    with paramiko.SFTPClient.from_transport(t) as sftp:
        try:
            sftp.mkdir(target_dir)
        except OSError:
            sftp.stat(target_dir)
        try:
            sftp.stat(target)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("Preview already exists: refusing to overwrite")
        temporary = target_dir + "/.index-upload.tmp"
        try:
            sftp.stat(temporary)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("Stale temporary file exists")
        with sftp.open(temporary, "wb") as f:
            f.write(payload)
        with sftp.open(temporary, "rb") as f:
            if f.read() != payload:
                raise RuntimeError("Upload readback mismatch")
        sftp.rename(temporary, target)
        print("OK: Preview published at /nachrichten/vorschau/index.html")
finally:
    t.close()
