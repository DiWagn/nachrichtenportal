<?php
session_start();
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');
if (isset($_POST['password']) && password_verify($_POST['password'], getenv('VOLT_HASH') ?: '')) {
    $_SESSION['allowed'] = true;
}
if (empty($_SESSION['allowed'])) {
    echo '<form method="post"><label>Passwort<input type="password" name="password"></label><button>Öffnen</button></form>';
    exit;
}
require __DIR__ . '/protected-content.php';
