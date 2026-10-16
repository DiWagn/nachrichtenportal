#!/usr/bin/env python3
"""Recover a missing news archive index from existing dated reports, without changing any report or UI."""
import base64
import hashlib
import json
import os
import re

import paramiko

t = paramiko.Transport((os.environ["IONOS_SFTP_HOST"], 22))
try:
    t.get_security_options().key_types = ("ssh-ed25519",)
    t.start_client(timeout=20)
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(t.get_remote_server_key().asbytes()).digest()).decode().rstrip("=")
    if fingerprint != os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:
        raise RuntimeError("IONOS Host-Key Fingerprint stimmt nicht")
    t.auth_password(os.environ["IONOS_SFTP_USER"], os.environ["IONOS_SFTP_PASSWORD"])
    with paramiko.SFTPClient.from_transport(t) as sftp:
        base = "/nachrichten/berichte/"
        names = sorted((n for n in sftp.listdir(base) if re.fullmatch(r"20\d\d-\d\d-\d\d\.json", n)), reverse=True)
        if not names:
            raise RuntimeError("Keine datierten Berichte auf dem Server gefunden")
        dates = []
        for name in names:
            with sftp.open(base + name, "rb") as f:
                report = json.loads(f.read())
            date = name[:-5]
            if report.get("date") != date or not isinstance(report.get("stories"), list):
                raise RuntimeError("Ungültige Tagesdatei: " + name)
            dates.append(date)
        path = base + "index.json"
        try:
            with sftp.open(path, "rb") as f:
                original = json.loads(f.read())
        except FileNotFoundError:
            original = None
        if original is not None:
            print("Archivindex bereits vorhanden; nichts überschrieben.", original)
        else:
            body = (json.dumps({"dates": dates}, ensure_ascii=False, indent=2) + "\n").encode()
            temp = base + ".index-recovery-tmp"
            with sftp.open(temp, "wb") as f:
                f.write(body)
            with sftp.open(temp, "rb") as f:
                if f.read() != body:
                    raise RuntimeError("Indexprüfung fehlgeschlagen")
            sftp.rename(temp, path)
            print("Archivindex aus vorhandenen, geprüften Tagesdateien erstellt:", dates)
        with sftp.open(path, "rb") as f:
            index = json.loads(f.read())
        if not isinstance(index, dict) or not isinstance(index.get("dates"), list):
            raise RuntimeError("Indexformat nicht erkannt")
        print("OK: Archivindex ist lesbar:", index["dates"])
finally:
    t.close()
