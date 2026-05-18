<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

// DEFINIUJEMY WSZYSTKIE ZMIENNE (to ich brak sypał błędami)
const email = ref('')
const password = ref('')
const message = ref('')
const error = ref('')

const handleRegister = async () => {
  console.log("Próba rejestracji..."); // Log w konsoli, żebyś wiedział że ruszyło
  message.value = ""
  error.value = ""

  try {
    const response = await axios.post('http://localhost/football-app/backend/register.php', {
      email: email.value,
      password: password.value
    })

    console.log("Serwer odpowiedział:", response.data)

    // Jeśli rejestracja się udała
    message.value = "Konto założone pomyślnie! Za chwilę będziesz mógł się zalogować."
    
    // Czyścimy pola formularza
    email.value = ""
    password.value = ""

    // Przekierowanie do logowania po 2 sekundach
    setTimeout(() => {
      router.push('/login')
    }, 2000)

  } catch (err) {
    console.error("Błąd podczas rejestracji:", err)
    error.value = err.response?.data?.error || "Wystąpił błąd podczas rejestracji. Może ten email jest już zajęty?"
  }
}
</script>

<template>
  <div style="max-width: 400px; margin: 50px auto; padding: 30px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h2 style="text-align: center; color: #2c3e50;">Rejestracja</h2>
    
    <form @submit.prevent="handleRegister">
      <div style="margin-bottom: 15px;">
        <label>Email:</label>
        <input v-model="email" type="email" required placeholder="twoj@email.com" 
               style="width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px;">
      </div>
      
      <div style="margin-bottom: 20px;">
        <label>Hasło (min. 6 znaków):</label>
        <input v-model="password" type="password" required minlength="6" placeholder="******" 
               style="width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px;">
      </div>
      
      <button type="submit" style="width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">
        Zarejestruj się
      </button>
    </form>
    
    <p v-if="error" style="color: #e74c3c; text-align: center; margin-top: 15px; font-weight: bold;">{{ error }}</p>
    <p v-if="message" style="color: #27ae60; text-align: center; margin-top: 15px; font-weight: bold;">{{ message }}</p>
    
    <p style="text-align: center; margin-top: 20px;">
      Masz już konto? <router-link to="/login">Zaloguj się</router-link>
    </p>
  </div>
</template>