<?php
require_once __DIR__ . '/config.php';
global $conn, $secret_key;

// 1. Pobieramy nagłówki na kilka sposobów (dla pewności w XAMPP)
$headers = getallheaders();
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? $headers['Authorization'] ?? $headers['authorization'] ?? '';

if (empty($auth_header)) {
    http_response_code(401);
    die(json_encode(["error" => "PHP nie widzi nagłówka Authorization. Sprawdź .htaccess!"]));
}

$token = str_replace('Bearer ', '', $auth_header);
$token_parts = explode('.', $token);

if (count($token_parts) != 3) {
    http_response_code(401);
    die(json_encode(["error" => "Token ma zły format."]));
}

// 2. Weryfikacja podpisu
$signature = hash_hmac('sha256', $token_parts[0] . "." . $token_parts[1], $secret_key, true);
$base64UrlSignature = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($signature));

if ($base64UrlSignature !== $token_parts[2]) {
    http_response_code(401);
    die(json_encode([
        "error" => "Błąd podpisu JWT! Klucz w login.php i add_player.php musi być identyczny.",
        "debug_expected" => $base64UrlSignature,
        "debug_received" => $token_parts[2]
    ]));
}

// 3. Jeśli podpis OK -> Dodajemy piłkarza
$data = json_decode(file_get_contents("php://input"));

if (!empty($data->firstname) && !empty($data->lastname)) {
    $fn = $conn->real_escape_string($data->firstname);
    $ln = $conn->real_escape_string($data->lastname);
    $cl = $conn->real_escape_string($data->club);
    $ps = $conn->real_escape_string($data->position);

    $sql = "INSERT INTO players (firstname, lastname, club, position) VALUES ('$fn', '$ln', '$cl', '$ps')";
    
    if ($conn->query($sql)) {
        echo json_encode(["message" => "Sukces! Piłkarz dodany."]);
    } else {
        http_response_code(500);
        echo json_encode(["error" => "Błąd bazy: " . $conn->error]);
    }
} else {
    http_response_code(400);
    echo json_encode(["error" => "Wypełnij wszystkie pola."]);
}