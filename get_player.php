<?php
// MUSI BYĆ NA SAMEJ GÓRZE, żeby załadować nagłówki CORS z configa
require_once __DIR__ . '/config.php'; 
global $conn;

// Sprawdzamy czy ID dotarło
$id = isset($_GET['id']) ? (int)$_GET['id'] : 0;

if ($id > 0) {
    $result = $conn->query("SELECT * FROM players WHERE id = $id");
    if ($result && $result->num_rows > 0) {
        echo json_encode($result->fetch_assoc());
    } else {
        http_response_code(404);
        echo json_encode(["error" => "Nie znaleziono zawodnika o tym ID."]);
    }
} else {
    http_response_code(400);
    echo json_encode(["error" => "Błędne lub brakujące ID."]);
}