#!/usr/bin/env python3
"""Publish editorial text as supplemental JSON and append safe rendering to current site JS."""
import base64, hashlib, json, os, paramiko
from pathlib import Path

date = "2026-10-16"
data = Path("berichte/redaktionell-2026-10-16.json").read_bytes()
report = json.loads(data)
if report.get("date") != date or len(report.get("sections", [])) != 7 or not report.get("original_markdown"):
    raise RuntimeError("Redaktioneller Originalbericht unvollstaendig")
addition = Path("scripts/editorial_append.js").read_bytes()
if not addition.startswith(b"'use strict';") or b"renderEditorial" not in addition:
    raise RuntimeError("Renderer fehlt")
t = paramiko.Transport((os.environ["IONOS_SFTP_HOST"], 22))
try:
    t.get_security_options().key_types = ("ssh-ed25519",)
    t.start_client(timeout=20)
    key = t.get_remote_server_key()
    fp = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
    if fp != os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:
        raise RuntimeError("Host-Key Fingerprint nicht vertraut")
    t.auth_password(os.environ["IONOS_SFTP_USER"], os.environ["IONOS_SFTP_PASSWORD"])
    if not t.is_authenticated():
        raise RuntimeError("SFTP Anmeldung fehlgeschlagen")
    with paramiko.SFTPClient.from_transport(t) as sftp:
        base = "/nachrichten/"
        with sftp.open(base + "app.js", "rb") as f:
            existing = f.read()
        required = [b"function renderStories()", b"async function loadIssue(date)", b"const categories=", b"const KEY="]
        if not all(marker in existing for marker in required):
            raise RuntimeError("Live app.js stimmt nicht mit bekanntem Aufbau ueberein: keine Aenderung")
        if b"Editorial text renderer: appended" in existing:
            if addition not in existing:
                raise RuntimeError("Anderer redaktioneller Renderer ist bereits installiert")
            updated = existing
        else:
            updated = existing + b"\n\n" + addition

        # Validate index without touching other reports.
        with sftp.open(base + "berichte/index.json", "rb") as f:
            index = json.loads(f.read())
        if not isinstance(index, dict) or not isinstance(index.get("dates"), list):
            raise RuntimeError("Unbekanntes Archiv-Indexformat")

        # Upload only separate editorial source, never replace the existing dated report.
        remote_data = base + "berichte/redaktionell-2026-10-16.json"
        temp_data = base + "berichte/.redaktionell-2026-10-16.tmp"
        with sftp.open(temp_data, "wb") as f:
            f.write(data)
        with sftp.open(temp_data, "rb") as f:
            if f.read() != data:
                raise RuntimeError("Redaktioneller Upload nicht verifiziert")
        try:
            sftp.stat(remote_data)
        except FileNotFoundError:
            sftp.rename(temp_data, remote_data)
        else:
            sftp.posix_rename(temp_data, remote_data)
        print("Redaktioneller Originalbericht veroeffentlicht:", date)

        if updated != existing:
            temp_app = base + ".app-editorial-update.tmp"
            with sftp.open(temp_app, "wb") as f:
                f.write(updated)
            with sftp.open(temp_app, "rb") as f:
                if f.read() != updated:
                    raise RuntimeError("JS Upload nicht verifiziert")
            sftp.posix_rename(temp_app, base + "app.js")
            print("Website-Renderer erweitert; CSS und HTML unveraendert")
        else:
            print("Renderer bereits installiert")

        if date not in index["dates"]:
            index["dates"] = sorted(set(index["dates"] + [date]), reverse=True)
            updated_index = (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode()
            temp_index = base + "berichte/.index-editorial.tmp"
            with sftp.open(temp_index, "wb") as f:
                f.write(updated_index)
            with sftp.open(temp_index, "rb") as f:
                if f.read() != updated_index:
                    raise RuntimeError("Archiv-Index Upload nicht verifiziert")
            sftp.posix_rename(temp_index, base + "berichte/index.json")
            print("16. Oktober im Archiv ergaenzt")
        print("OK: Seite zeigt fuer 16. Oktober den redaktionellen Originaltext")
finally:
    t.close()
