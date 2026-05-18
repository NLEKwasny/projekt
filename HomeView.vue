<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const stats = ref({ playersCount: 0 })
const isLogged = ref(!!localStorage.getItem('token'))
const loading = ref(true)

onMounted(async () => {
  if (!isLogged.value) {
    loading.value = false
    return
  }

  try {
    const token = localStorage.getItem('token')
    // Musimy wysłać nagłówek Authorization, tak jak w PlayersView
    const res = await axios.get('http://localhost/football-app/backend/get_players.php', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    // Sprawdzamy czy res.data jest tablicą
    if (Array.isArray(res.data)) {
      stats.value.playersCount = res.data.length
    }
  } catch (e) {
    console.error("Błąd pobierania statystyk - prawdopodobnie brak autoryzacji")
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="home-container">
    <div class="hero-section">
      <h1>Witaj na naszej stronie</h1>
      <p>Twoje centrum dowodzenia składem drużyny.</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <h3>Liczba zawodników</h3>
        <div v-if="loading" class="stat-value">...</div>
        <div v-else-if="!isLogged" class="stat-value-small">Zaloguj się, aby zobaczyć</div>
        <div v-else class="stat-value">{{ stats.playersCount }}</div>
      </div>

      
    </div>

    <div class="action-buttons">
      <router-link v-if="!isLogged" to="/login" class="btn btn-primary">Zaloguj się</router-link>
      <router-link v-else to="/players" class="btn btn-primary">Przejdź do składu</router-link>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  text-align: center;
  padding: 40px 20px;
}

.hero-section h1 {
  font-size: 3rem;
  margin-bottom: 10px;
}

.hero-section span {
  color: #42b983;
}

.stats-grid {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin: 50px 0;
}

.stat-card {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 20px rgba(0,0,0,0.05);
  min-width: 250px;
}

.stat-value {
  font-size: 3.5rem;
  font-weight: 800;
  color: #2c3e50;
}

.stat-value-small {
  font-size: 1rem;
  color: #7f8c8d;
  margin-top: 20px;
}

.stat-status {
  font-size: 1.5rem;
  color: #42b983;
  font-weight: bold;
  margin-top: 20px;
}

.btn {
  padding: 15px 40px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: bold;
  transition: transform 0.2s;
  display: inline-block;
}

.btn-primary {
  background: #2c3e50;
  color: white;
}

.btn:hover {
  transform: translateY(-3px);
}
</style>