import api from './request'

export function login(data) {
  return api.post('/auth/login', data)
}

export function register(data) {
  return api.post('/auth/register', data)
}

export function refreshToken(data) {
  return api.post('/auth/refresh', data)
}

export function logout() {
  return api.post('/auth/logout')
}

export function getCurrentUser() {
  return api.get('/auth/me')
}

export function changePassword(data) {
  return api.post('/auth/change-password', data)
}
