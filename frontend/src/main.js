import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import axios from 'axios'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'
import router from './router'

// Axios Request Interceptor: Automatically inject JWT Bearer Token
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('vision_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Axios Response Interceptor: Automatically handle 401 and redirect to Login
axios.interceptors.response.use(
  response => {
    return response
  },
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('vision_token')
      localStorage.removeItem('vision_username')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

createApp(App).use(router).use(ElementPlus).mount('#app')
