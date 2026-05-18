<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const message = ref('') // TO TEGO BRAKOWAŁO!

const handleLogin = async () => {
  console.log("Próba logowania..."); 
  error.value = ""
  message.value = ""

  try {
    const response = await axios.post('http://localhost/football-app/backend/login.php', {
      email: email.value,
      password: password.value
    })
    
    console.log("Odpowiedź serwera:", response.data)

    if (response.data.token) {
      localStorage.setItem('token', response.data.token)
      message.value = "Zalogowano pomyślnie! Przekierowuję..."
      
      // Przekierowanie na stronę główną po krótkiej chwili
      setTimeout(() => {
        router.push('/')
        // Odświeżamy, żeby pasek nawigacji w App.vue "zauważył" nowy token
        setTimeout(() => window.location.reload(), 100)
      }, 1000)
    }
  } catch (err) {
    console.error("Błąd logowania:", err)
    error.value = err.response?.data?.error || "Nieprawidłowe dane logowania"
  }
}
</script>

<template>
  <div style="max-width: 400px; margin: 50px auto; padding: 30px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h2 style="text-align: center; color: #2c3e50;">Logowanie</h2>
    
    <form @submit.prevent="handleLogin">
      <div style="margin-bottom: 15px;">
        <label>Email:</label>
        <input v-model="email" type="email" required style="width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px;">
      </div>
      
      <div style="margin-bottom: 20px;">
        <label>Hasło:</label>
        <input v-model="password" type="password" required style="width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px;">
      </div>
      
      <button type="submit" style="width: 100%; padding: 12px; background: #42b983; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">
        Zaloguj się
      </button>
    </form>
    
    <p v-if="error" style="color: #e74c3c; text-align: center; margin-top: 15px;">{{ error }}</p>
    <p v-if="message" style="color: #27ae60; text-align: center; margin-top: 15px;">{{ message }}</p>
    
    <p style="text-align: center; margin-top: 20px;">
      Nie masz konta? <router-link to="/register">Zarejestruj się</router-link>
    </p>
  </div>
</template>