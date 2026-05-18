<?php
// backend/delete_player.php
require_once __DIR__ . '/config.php';
global $conn, $secret_key;

// 1. Weryfikacja tokenu JWT
$headers = getallheaders();
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $headers['Authorization'] ?? '';
$token = str_replace('Bearer ', '', $auth_header);

$token_parts = explode('.', $token);
if (count($token_parts) != 3) {
    http_response_code(401);
    die(json_encode(["error" => "Brak autoryzacji."]));
}

$signature = hash_hmac('sha256', $token_parts[0] . "." . $token_parts[1], $secret_key, true);
$base64UrlSignature = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($signature));

if ($base64UrlSignature !== $token_parts[2]) {
    http_response_code(401);
    die(json_encode(["error" => "Sesja wygasła."]));
}

// 2. Pobieramy ID zawodnika do usunięcia
$data = json_decode(file_get_contents("php://input"));

if (!empty($data->id)) {
    $id = (int)$data->id;
    $sql = "DELETE FROM players WHERE id = $id";

    if ($conn->query($sql)) {
        echo json_encode(["message" => "Zawodnik został usunięty."]);
    } else {
        http_response_code(500);
        echo json_encode(["error" => "Błąd bazy danych."]);
    }
} else {
    http_response_code(400);
    echo json_encode(["error" => "Brak ID zawodnika."]);
}

$conn->close();