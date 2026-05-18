<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const player = ref({
  firstname: '',
  lastname: '',
  club: '',
  position: 'Napastnik' // Domyślna wartość
})

const loading = ref(false)
const error = ref('')

const handleAddPlayer = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const token = localStorage.getItem('token')
    
    // Wysyłamy dane do backendu z tokenem w nagłówku
    await axios.post('http://localhost/football-app/backend/add_player.php', player.value, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    // Po sukcesie wracamy do listy zawodników
    router.push('/players')
  } catch (err) {
    console.error("Błąd podczas dodawania:", err)
    error.value = err.response?.data?.error || "Nie udało się dodać zawodnika. Sprawdź połączenie."
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <div class="form-card">
      <div class="icon-circle">➕</div>
      <h2>Dodaj Zawodnika</h2>
      <p class="subtitle">Wprowadź dane nowego gracza do bazy danych</p>

      <form @submit.prevent="handleAddPlayer">
        <div class="input-group">
          <label>Imię</label>
          <input 
            v-model="player.firstname" 
            type="text" 
            placeholder="np. Robert" 
            required
          >
        </div>

        <div class="input-group">
          <label>Nazwisko</label>
          <input 
            v-model="player.lastname" 
            type="text" 
            placeholder="np. Lewandowski" 
            required
          >
        </div>

        <div class="input-group">
          <label>Klub</label>
          <input 
            v-model="player.club" 
            type="text" 
            placeholder="np. FC Barcelona" 
            required
          >
        </div>

        <div class="input-group">
          <label>Pozycja na boisku</label>
          <select v-model="player.position">
            <option>Bramkarz</option>
            <option>Obrońca</option>
            <option>Pomocnik</option>
            <option>Napastnik</option>
          </select>
        </div>

        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? 'Dodawanie...' : 'Zapisz zawodnika' }}
        </button>
        
        <router-link to="/players" class="btn-cancel">Wróć do listy</router-link>
      </form>

      <p v-if="error" class="error-msg">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 40px 20px;
}

.form-card {
  background: white;
  padding: 40px;
  border-radius: 20px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.05);
  width: 100%;
  max-width: 450px;
  text-align: center;
}

.icon-circle {
  font-size: 2.5rem;
  background: #f4f7f6;
  width: 80px;
  height: 80px;
  line-height: 80px;
  border-radius: 50%;
  margin: 0 auto 20px;
}

h2 {
  margin: 0;
  color: #1a252f;
  font-size: 1.8rem;
}

.subtitle {
  color: #7f8c8d;
  margin: 10px 0 30px;
  font-size: 0.9rem;
}

.input-group {
  margin-bottom: 20px;
  text-align: left;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #34495e;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.input-group input, 
.input-group select {
  width: 100%;
  padding: 12px 15px;
  border: 2px solid #edf2f7;
  border-radius: 10px;
  font-size: 1rem;
  transition: all 0.3s;
  box-sizing: border-box;
}

.input-group input:focus, 
.input-group select:focus {
  border-color: #42b983;
  outline: none;
  background-color: #fff;
  box-shadow: 0 0 0 4px rgba(66, 185, 131, 0.1);
}

.btn-submit {
  width: 100%;
  background: #42b983;
  color: white;
  border: none;
  padding: 15px;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 10px;
}

.btn-submit:hover {
  background: #3aa876;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(66, 185, 131, 0.3);
}

.btn-submit:disabled {
  background: #a8d5c2;
  cursor: not-allowed;
  transform: none;
}

.btn-cancel {
  display: block;
  margin-top: 20px;
  text-decoration: none;
  color: #95a5a6;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.3s;
}

.btn-cancel:hover {
  color: #34495e;
}

.error-msg {
  color: #e74c3c;
  background: #fdf2f2;
  padding: 10px;
  border-radius: 8px;
  margin-top: 20px;
  font-size: 0.9rem;
  font-weight: 500;
}
</style>