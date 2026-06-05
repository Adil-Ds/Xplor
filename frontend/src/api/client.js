import axios from 'axios'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore'
import { useAIStore } from '../store/aiStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
})

// AI endpoints that accept a `provider` (ollama | groq | auto)
const AI_ENDPOINTS = ['/chat/', '/narrative', '/suggest']

// Attach JWT token + AI provider preference on every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`

  // Inject the chosen AI provider into AI-related requests
  const url = config.url || ''
  if (AI_ENDPOINTS.some(e => url.includes(e))) {
    const provider = useAIStore.getState().provider
    if (config.method === 'get') {
      config.params = { ...(config.params || {}), provider }
    } else {
      // POST/PUT — merge into the JSON body
      if (config.data && typeof config.data === 'object' && !(config.data instanceof FormData)) {
        config.data = { ...config.data, provider }
      } else if (!config.data) {
        config.data = { provider }
      }
    }
  }

  return config
})

// Handle 401 → notify + redirect (but never when already on the login page)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      useAuthStore.getState().logout()
      toast.error('Session expired — please log in again', { id: 'session-expired', duration: 3000 })
      setTimeout(() => { window.location.href = '/login' }, 1200)
    }
    return Promise.reject(err)
  }
)

export default api
