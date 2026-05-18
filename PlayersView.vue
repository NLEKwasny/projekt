<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const players = ref([])
const loading = ref(true)

const fetchPlayers = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('http://localhost/football-app/backend/get_players.php', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    players.value = response.data
  } catch (err) {
    console.error("Błąd pobierania listy")
  } finally {
    loading.value = false
  }
}

const deletePlayer = async (id) => {
  if (!confirm("Usunąć zawodnika?")) return
  try {
    const token = localStorage.getItem('token')
    await axios.post('http://localhost/football-app/backend/delete_player.php', { id }, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    players.value = players.value.filter(p => p.id !== id)
  } catch (err) { alert("Błąd usuwania") }
}

onMounted(fetchPlayers)
</script>

<template>
  <div class="page-container">
    <div class="header-actions">
      <h2>Skład Drużyny</h2>
      <router-link to="/add-player" class="btn-add">+ Nowy Zawodnik</router-link>
    </div>

    <div v-if="loading" class="loader">Ładowanie składu...</div>

    <div v-else class="players-grid">
      <div v-for="p in players" :key="p.id" class="player-card">
        <div class="player-info">
          <div class="player-icon">⚽</div>
          <div>
            <h3>{{ p.firstname }} {{ p.lastname }}</h3>
            <p>{{ p.club }} • <span>{{ p.position }}</span></p>
          </div>
        </div>
        <div class="card-actions">
          <router-link :to="'/player/'+p.id" class="btn-icon view" title="Szczegóły">👁</router-link>
          <router-link :to="'/edit-player/'+p.id" class="btn-icon edit" title="Edytuj">✏️</router-link>
          <button @click="deletePlayer(p.id)" class="btn-icon delete" title="Usuń">🗑</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { max-width: 900px; margin: 0 auto; }
.header-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.header-actions h2 { font-size: 2rem; color: #1a252f; margin: 0; }

.btn-add { background: #42b983; color: white; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; transition: 0.3s; }
.btn-add:hover { background: #3aa876; transform: translateY(-2px); }

.players-grid { display: grid; gap: 15px; }
.player-card { background: white; padding: 20px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: 0.3s; }
.player-card:hover { transform: scale(1.01); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }

.player-info { display: flex; align-items: center; gap: 20px; }
.player-icon { font-size: 2rem; background: #f4f7f6; padding: 10px; border-radius: 50%; }
.player-info h3 { margin: 0; font-size: 1.2rem; color: #2c3e50; }
.player-info p { margin: 5px 0 0; color: #7f8c8d; }
.player-info span { color: #42b983; font-weight: bold; }

.card-actions { display: flex; gap: 10px; }
.btn-icon { border: none; background: #f4f7f6; width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: pointer; text-decoration: none; transition: 0.2s; font-size: 1.1rem; }
.view:hover { background: #3498db; color: white; }
.edit:hover { background: #f39c12; color: white; }
.delete:hover { background: #e74c3c; color: white; }
</style>