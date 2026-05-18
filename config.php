<?php
// 1. NAGŁÓWKI CORS - Muszą być na samym początku!
// Pozwalamy na dostęp tylko z Twojego frontendu (Vite)
header("Access-Control-Allow-Origin: http://localhost:5173");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS, PUT, DELETE");
header("Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With");
header("Access-Control-Allow-Credentials: true");

// 2. OBSŁUGA ZAPYTANIA TESTOWEGO (OPTIONS)
// To najważniejszy fragment dla błędu "Preflight"
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit(); // Kończymy skrypt tutaj, nie łączymy się nawet z bazą dla testu
}

// 3. DANE DO BAZY
$db_host = "localhost";
$db_user = "root";
$db_pass = "";
$db_name = "football_app";

// 4. TAJNY KLUCZ DO JWT (Wspólny dla wszystkich plików)
$secret_key = "nasz_wspolny_tajny_klucz_123";

// 5. POŁĄCZENIE
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    header('Content-Type: application/json');
    die(json_encode(["error" => "Błąd połączenia: " . $conn->connect_error]));
}

$conn->set_charset("utf8mb4");