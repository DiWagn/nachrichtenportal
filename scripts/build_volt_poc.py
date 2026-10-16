from pathlib import Path
import hashlib, os, secrets

secret = os.environ["VOLT_POC_PASSWORD"]
salt = secrets.token_hex(16)
hash_value = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), 150000).hex()
template = Path("VoltPOC/login-template.php").read_text(encoding="utf-8")
template = template.replace("password_verify($_POST['password'], getenv('VOLT_HASH') ?: '')", "hash_equals('" + hash_value + "', hash_pbkdf2('sha256', $_POST['password'], '" + salt + "', 150000))")
template = template.replace("require __DIR__ . '/protected-content.php';", "?>\n" + Path("VoltPOC/volt-radar-source.html").read_text(encoding="utf-8"))
out = Path("generated")
out.mkdir(exist_ok=True)
(out / "index.php").write_text(template, encoding="utf-8")
print("Passwortgeschuetzte PHP-Datei erzeugt.")
