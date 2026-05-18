<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const player = ref({ firstname: '', lastname: '', club: '', position: '' })

onMounted(async () => {
  const token = localStorage.getItem('token')
  const res = await axios.get(`http://localhost/football-app/backend/get_player.php?id=${route.params.id}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  player.value = res.data
})

const handleUpdate = async () => {
  try {
    const token = localStorage.getItem('token')
    await axios.post('http://localhost/football-app/backend/update_player.php', player.value, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    router.push('/players')
  } catch (err) { alert("Błąd zapisu") }
}
</script>

<template>
  <div class="page-container">
    <div class="form-card">
      <h2>Edytuj Zawodnika</h2>
      <form @submit.prevent="handleUpdate">
        <div class="input-group">
          <label>Imię</label>
          <input v-model="player.firstname" required>
        </div>
        <div class="input-group">
          <label>Nazwisko</label>
          <input v-model="player.lastname" required>
        </div>
        <div class="input-group">
          <label>Klub</label>
          <input v-model="player.club" required>
        </div>
        <div class="input-group">
          <label>Pozycja</label>
          <select v-model="player.position">
            <option>Bramkarz</option>
            <option>Obrońca</option>
            <option>Pomocnik</option>
            <option>Napastnik</option>
          </select>
        </div>
        <button type="submit" class="btn-submit">Zaktualizuj Dane</button>
        <router-link to="/players" class="btn-cancel">Anuluj</router-link>
      </form>
    </div>
  </div>
</template>

<style scoped>
.page-container { display: flex; justify-content: center; padding: 40px 0; }
.form-card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); width: 100%; max-width: 400px; }
h2 { text-align: center; color: #1a252f; margin-bottom: 30px; }

.input-group { margin-bottom: 20px; text-align: left; }
.input-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #7f8c8d; font-size: 0.9rem; }
.input-group input, .input-group select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
.input-group input:focus { border-color: #42b983; outline: none; }

.btn-submit { width: 100%; background: #42b983; color: white; border: none; padding: 14px; border-radius: 8px; font-size: 1rem; font-weight: bold; cursor: pointer; transition: 0.3s; margin-bottom: 15px; }
.btn-submit:hover { background: #3aa876; }
.btn-cancel { display: block; text-align: center; text-decoration: none; color: #7f8c8d; font-size: 0.9rem; }
</style>