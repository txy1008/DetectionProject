import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Detection from '../views/Detection.vue'
import Analysis from '../views/Analysis.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'

const routes = [
  { path: '/login', name: 'Login', component: Login, meta: { public: true } },
  { path: '/register', name: 'Register', component: Register, meta: { public: true } },
  { path: '/', name: 'Home', component: Home },
  { path: '/detection', name: 'Detection', component: Detection },
  { path: '/analysis', name: 'Analysis', component: Analysis }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('vision_token')
  
  if (to.matched.some(record => !record.meta.public)) {
    // Protected route
    if (!token) {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
    } else {
      next()
    }
  } else {
    // Public route
    if (token && (to.path === '/login' || to.path === '/register')) {
      next('/')
    } else {
      next()
    }
  }
})

export default router
