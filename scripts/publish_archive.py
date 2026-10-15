#!/usr/bin/env python3
"""Publish one dated news JSON to IONOS, preserving all existing dated files."""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
import paramiko

path = Path(sys.argv[1])
date = "2026-10-14"
if path.name != date + ".json":
    raise ValueError("Nur die freigegebene Tagesdatei vom 14. Oktober erlaubt")
payload = path.read_bytes()
report = json.loads(payload)
if report.get("date") != date or not isinstance(report.get("stories"), list) or not report["stories"]:
    raise ValueError("Tagesbericht ist ungueltig")
remote_report = "/nachrichten/berichte/" + path.name
remote_index = "/nachrichten/berichte/index.json"

t = paramiko.Transport((os.environ["IONOS_SFTP_HOST"], 22))
try:
    t.get_security_options().key_types = ("ssh-ed25519",)
    t.start_client(timeout=20)
    key = t.get_remote_server_key()
    actual = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
    if actual != os.environ["IONOS_SFTP_HOSTKEY_SHA256"]:
        raise RuntimeError("SFTP-Host-Key nicht vertrauenswuerdig")
    t.auth_password(os.environ["IONOS_SFTP_USER"], os.environ["IONOS_SFTP_PASSWORD"])
    if not t.is_authenticated():
        raise RuntimeError("SFTP-Anmeldung fehlgeschlagen")

    with paramiko.SFTPClient.from_transport(t) as sftp:
        with sftp.open(remote_index, "rb") as file:
            index = json.loads(file.read())
        if not isinstance(index, dict) or not isinstance(index.get("dates"), list):
            raise ValueError("Archivindex hat unerwartete Struktur")
        if not all(isinstance(d, str) for d in index["dates"]):
            raise ValueError("Archivindex enthaelt ungueltige Datumswerte")

        try:
            with sftp.open(remote_report, "rb") as file:
                existing = file.read()
        except FileNotFoundError:
            existing = None
        if existing is not None and existing != payload:
            raise RuntimeError("Tagesbericht ist schon vorhanden und weicht ab; keine Aenderung")

        if existing is None:
            temporary_report = "/nachrichten/berichte/.upload-2026-10-14.tmp"
            with sftp.open(temporary_report, "wb") as file:
                file.write(payload)
            with sftp.open(temporary_report, "rb") as file:
                if file.read() != payload:
                    raise RuntimeError("Fehler bei der Upload-Kontrolle")
            sftp.rename(temporary_report, remote_report)
            print("Tagesbericht: hochgeladen und kontrolliert")
        else:
            print("Tagesbericht: identische Datei bereits vorhanden")

        if date not in index["dates"]:
            index["dates"] = sorted(set(index["dates"] + [date]), reverse=True)
            new_index = (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            temporary_index = "/nachrichten/berichte/.index-2026-10-14.tmp"
            with sftp.open(temporary_index, "wb") as file:
                file.write(new_index)
            with sftp.open(temporary_index, "rb") as file:
                if file.read() != new_index:
                    raise RuntimeError("Fehler bei Index-Kontrolle")
            sftp.posix_rename(temporary_index, remote_index)
            print("Archivindex: 14. Oktober ergaenzt")
        else:
            print("Archivindex: Datum bereits enthalten")

        with sftp.open(remote_index, "rb") as file:
            actual_index = json.loads(file.read())
        if date not in actual_index["dates"]:
            raise RuntimeError("14. Oktober ist nicht im Archivindex")
        with sftp.open(remote_report, "rb") as file:
            if file.read() != payload:
                raise RuntimeError("Abschliessende Berichtspruefung fehlgeschlagen")
        print("ERFOLG: 14. Oktober archiviert, andere Tagesberichte nicht veraendert")
finally:
    t.close()
