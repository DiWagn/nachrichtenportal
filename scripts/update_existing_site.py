#!/usr/bin/env python3
"""Inspect existing live website before changing it. No blind overwrites."""
import base64, hashlib, os
import paramiko
t=paramiko.Transport((os.environ["IONOS_SFTP_HOST"],22))
try:
 t.get_security_options().key_types=("ssh-ed25519",)
 t.start_client(timeout=20)
 actual="SHA256:"+base64.b64encode(hashlib.sha256(t.get_remote_server_key().asbytes()).digest()).decode().rstrip("=")
 if actual!=os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:raise RuntimeError("Host key mismatch")
 t.auth_password(os.environ["IONOS_SFTP_USER"],os.environ["IONOS_SFTP_PASSWORD"])
 with paramiko.SFTPClient.from_transport(t) as sftp:
  for name in sftp.listdir("/nachrichten"):
   if name.endswith((".html",".css",".js")):print("WEBSITE FILE",name)
  with sftp.open("/nachrichten/index.html","rb") as f: html=f.read()
  print("LIVE HTML",len(html),"bytes; sha256",hashlib.sha256(html).hexdigest())
  for marker in ("Meine Themen","Impressum","stories","original_markdown","Tagesüberblick"):
   print("MARKER",marker,marker.encode() in html)
  # No write until the existing page's code has been reviewed.
finally:
 t.close()
