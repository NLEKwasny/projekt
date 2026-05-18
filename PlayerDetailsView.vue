<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const player = ref(null)

onMounted(async () => {
  const token = localStorage.getItem('token')
  const res = await axios.get(`http://localhost/football-app/backend/get_player.php?id=${route.params.id}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  player.value = res.data
})
</script>

<template>
  <div class="page-container">
    <div v-if="player" class="details-card">
      <div class="profile-header">
        <div class="big-avatar">⚽</div>
        <h1>{{ player.firstname }} {{ player.lastname }}</h1>
        <span class="badge">{{ player.position }}</span>
      </div>
      
      <div class="info-grid">
        <div class="info-item"><strong>Klub:</strong> {{ player.club }}</div>
        <div class="info-item"><strong>Status:</strong> Aktywny</div>
        <div class="info-item"><strong>ID Systemowe:</strong> #{{ player.id }}</div>
      </div>

      <div class="footer-btns">
        <router-link to="/players" class="btn-back">← Wróć do listy</router-link>
        <router-link :to="'/edit-player/'+player.id" class="btn-edit">Edytuj dane</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container { display: flex; justify-content: center; padding: 40px 0; }
.details-card { background: white; width: 100%; max-width: 500px; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center; }
.big-avatar { font-size: 4rem; margin-bottom: 20px; }
.profile-header h1 { margin: 10px 0; color: #1a252f; }
.badge { background: #42b983; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 0.9rem; }

.info-grid { margin: 30px 0; display: grid; gap: 15px; text-align: left; background: #f9f9f9; padding: 20px; border-radius: 12px; }
.info-item { border-bottom: 1px solid #eee; padding-bottom: 10px; }
.info-item:last-child { border: none; }

.footer-btns { display: flex; justify-content: space-between; align-items: center; margin-top: 30px; }
.btn-back { text-decoration: none; color: #7f8c8d; font-weight: 500; }
.btn-edit { background: #2c3e50; color: white; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; }
</style>