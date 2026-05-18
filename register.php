<?php
// register.php
require_once __DIR__ . '/config.php';
global $conn;

$data = json_decode(file_get_contents("php://input"));

if (!empty($data->email) && !empty($data->password)) {
    $email = $conn->real_escape_string($data->email);
    // Hashujemy hasło (bezpieczeństwo!)
    $password = password_hash($data->password, PASSWORD_BCRYPT);

    $sql = "INSERT INTO users (email, password) VALUES ('$email', '$password')";

    if ($conn->query($sql) === TRUE) {
        http_response_code(201);
        echo json_encode(["message" => "Użytkownik zarejestrowany!"]);
    } else {
        http_response_code(400);
        echo json_encode(["error" => "Email może już istnieć w bazie."]);
    }
}
$conn->close();