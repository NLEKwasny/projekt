import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import PlayersView from '../views/PlayersView.vue'
import AddPlayerView from '../views/AddPlayerView.vue'
import EditPlayerView from '../views/EditPlayerView.vue'
import PlayerDetailsView from '../views/PlayerDetailsView.vue'

const routes = [
  { path: '/', component: HomeView },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  // Dodajemy meta: { requiresAuth: true } do wszystkich chronionych stron
  { path: '/players', component: PlayersView, meta: { requiresAuth: true } },
  { path: '/add-player', component: AddPlayerView, meta: { requiresAuth: true } },
  { path: '/edit-player/:id', component: EditPlayerView, meta: { requiresAuth: true } },
  { path: '/player/:id', component: PlayerDetailsView, meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// GLOBALNY STRAŻNIK (Navigation Guard)
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token');
  
  // Jeśli strona wymaga logowania, a tokena brak -> wyrzuć do logowania
  if (to.meta.requiresAuth && !token) {
    next('/login');
  } else {
    next(); // W przeciwnym razie wpuść
  }
});

export default router