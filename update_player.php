<?php
// backend/update_player.php
require_once __DIR__ . '/config.php';
global $conn, $secret_key;

// 1. Obsługa CORS i JWT (pobieranie tokenu)
$headers = getallheaders();
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $headers['Authorization'] ?? '';
$token = str_replace('Bearer ', '', $auth_header);

// 2. Weryfikacja JWT (podpis musi się zgadzać!)
$token_parts = explode('.', $token);
if (count($token_parts) != 3) {
    http_response_code(401);
    die(json_encode(["error" => "Brak autoryzacji do edycji."]));
}

$signature = hash_hmac('sha256', $token_parts[0] . "." . $token_parts[1], $secret_key, true);
$base64UrlSignature = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($signature));

if ($base64UrlSignature !== $token_parts[2]) {
    http_response_code(401);
    die(json_encode(["error" => "Sesja wygasła. Zaloguj się ponownie."]));
}

// 3. Odbiór danych z Vue
$data = json_decode(file_get_contents("php://input"));

if (empty($data->id)) {
    http_response_code(400);
    die(json_encode(["error" => "Brak ID piłkarza do aktualizacji."]));
}

$id = (int)$data->id;
$fn = $conn->real_escape_string($data->firstname);
$ln = $conn->real_escape_string($data->lastname);
$cl = $conn->real_escape_string($data->club);
$ps = $conn->real_escape_string($data->position);

// 4. Zapytanie SQL
$sql = "UPDATE players SET firstname='$fn', lastname='$ln', club='$cl', position='$ps' WHERE id=$id";

if ($conn->query($sql)) {
    echo json_encode(["message" => "Zaktualizowano pomyślnie!"]);
} else {
    http_response_code(500);
    echo json_encode(["error" => "Błąd bazy: " . $conn->error]);
}

$conn->close();