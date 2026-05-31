import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const method = (error.config?.method || 'get').toLowerCase()
    const silent = error.config?.silent === true || method === 'get'
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        router.push('/login')
        ElMessage.warning('Session expired. Please sign in again.')
      } else if (status === 403) {
        ElMessage.error('Access Denied: Insufficient permissions.')
      } else {
        if (!silent) ElMessage.error(data?.error?.message || data?.detail || 'Operation failed. Please try again.')
      }
    } else {
      if (!silent) ElMessage.error('Network Error: Unable to connect to the server.')
    }
    return Promise.reject(error)
  }
)

export default api
