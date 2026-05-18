<?php
// login.php
require_once __DIR__ . '/config.php';
// Dodajemy $secret_key do global, żeby PHP wiedział, że ma go wziąć z config.php
global $conn, $secret_key;

$data = json_decode(file_get_contents("php://input"));

if (!empty($data->email) && !empty($data->password)) {
    $email = $conn->real_escape_string($data->email);
    $result = $conn->query("SELECT * FROM users WHERE email = '$email'");

    if ($result->num_rows > 0) {
        $user = $result->fetch_assoc();
        if (password_verify($data->password, $user['password'])) {
            
            // Generowanie JWT
            $header = json_encode(['typ' => 'JWT', 'alg' => 'HS256']);
            $base64UrlHeader = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($header));
            $payload = json_encode(['user_id' => $user['id'], 'exp' => time() + 3600]);
            $base64UrlPayload = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($payload));
            
            // TUTAJ UŻYWAMY $secret_key z pliku config.php
            $signature = hash_hmac('sha256', $base64UrlHeader . "." . $base64UrlPayload, $secret_key, true);
            $base64UrlSignature = str_replace(['+', '/', '='], ['-', '_', ''], base64_encode($signature));

            $jwt = $base64UrlHeader . "." . $base64UrlPayload . "." . $base64UrlSignature;

            echo json_encode(["message" => "Zalogowano!", "token" => $jwt]);
        } else {
            http_response_code(401);
            echo json_encode(["error" => "Błędne hasło!"]);
        }
    } else {
        http_response_code(404);
        echo json_encode(["error" => "Nie ma takiego użytkownika."]);
    }
}
$conn->close();