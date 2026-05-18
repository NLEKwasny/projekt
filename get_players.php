<?php
require_once __DIR__ . '/config.php';
global $conn, $secret_key;

// 1. WERYFIKACJA TOKENU (Kopiuj ten fragment do każdego chronionego pliku PHP)
$headers = getallheaders();
$auth = $headers['Authorization'] ?? '';
$token = str_replace('Bearer ', '', $auth);
$parts = explode('.', $token);

if (count($parts) !== 3) {
    http_response_code(401);
    die(json_encode(["error" => "Musisz się zalogować, aby zobaczyć listę!"]));
}

$sig = hash_hmac('sha256', $parts[0] . "." . $parts[1], $secret_key, true);
$validSig = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($sig));

if ($validSig !== $parts[2]) {
    http_response_code(401);
    die(json_encode(["error" => "Nieprawidłowy token!"]));
}

// 2. JEŚLI TOKEN OK -> WYDAJ DANE
$result = $conn->query("SELECT * FROM players");
$players = [];
while($row = $result->fetch_assoc()) {
    $players[] = $row;
}
echo json_encode($players);