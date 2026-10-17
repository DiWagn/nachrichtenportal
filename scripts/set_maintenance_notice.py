#!/usr/bin/env python3
"""Add a reversible maintenance notice to the existing live news page."""
import base64, hashlib, os, re, time
import paramiko

remote = "/nachrichten/index.html"
marker = 'id="redaktion-in-bearbeitung-20261017"'
notice = ('<div id="redaktion-in-bearbeitung-20261017" role="status" '
          'style="position:relative;z-index:2147483647;background:#fff3cd;'
          'color:#3d3100;border:2px solid #bd8c00;padding:16px 22px;'
          'font:600 18px/1.5 system-ui,-apple-system,sans-serif;'
          'text-align:center;">'
          'IN BEARBEITUNG – Diese Nachrichtenwebsite wird derzeit überarbeitet. '
          'Die angezeigten Inhalte entsprechen noch nicht der aktuellen redaktionellen Fassung.'
          '</div>\n')
t = paramiko.Transport((os.environ["IONOS_SFTP_HOST"], 22))
try:
    t.get_security_options().key_types = ("ssh-ed25519",)
    t.start_client(timeout=20)
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(t.get_remote_server_key().asbytes()).digest()).decode().rstrip("=")
    if fingerprint != os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:
        raise RuntimeError("Host-Key-Pruefung fehlgeschlagen")
    t.auth_password(os.environ["IONOS_SFTP_USER"], os.environ["IONOS_SFTP_PASSWORD"])
    with paramiko.SFTPClient.from_transport(t) as sftp:
        with sftp.open(remote, "rb") as f:
            original = f.read()
        html = original.decode("utf-8")
        if marker in html:
            print("Hinweis ist bereits vorhanden; keine Aenderung.")
        else:
            if len(original) < 200 or not re.search(r"<body\b[^>]*>", html, flags=re.I):
                raise RuntimeError("Unerwartete HTML-Struktur; keine Aenderung")
            changed, count = re.subn(r"(<body\b[^>]*>)", lambda m: m.group(1) + "\n" + notice, html, count=1, flags=re.I)
            if count != 1:
                raise RuntimeError("Body nicht eindeutig gefunden")
            backup = remote + ".backup-vor-hinweis-20261017-" + str(int(time.time()))
            with sftp.open(backup, "xb") as f:
                f.write(original)
            with sftp.open(backup, "rb") as f:
                if f.read() != original:
                    raise RuntimeError("Backup-Pruefung fehlgeschlagen")
            tmp = remote + ".hinweis-upload.tmp"
            with sftp.open(tmp, "wb") as f:
                f.write(changed.encode("utf-8"))
            with sftp.open(tmp, "rb") as f:
                if f.read() != changed.encode("utf-8"):
                    raise RuntimeError("Upload-Pruefung fehlgeschlagen")
            sftp.posix_rename(tmp, remote)
            with sftp.open(remote, "rb") as f:
                if f.read() != changed.encode("utf-8"):
                    raise RuntimeError("Live-Ruecklesepruefung fehlgeschlagen")
            print("Hinweis gesetzt und rueckgelesen. Backup:", backup)
finally:
    t.close()
