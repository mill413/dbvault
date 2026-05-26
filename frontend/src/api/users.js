import api from './request'

export function getUsers(params) {
  return api.get('/users', { params })
}

export function getUser(id) {
  return api.get(`/users/${id}`)
}

export function createUser(data) {
  return api.post('/users', data)
}

export function updateUser(id, data) {
  return api.put(`/users/${id}`, data)
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`)
}

export function resetPassword(id, data) {
  return api.post(`/users/${id}/reset-password`, data)
}
