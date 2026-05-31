import api from './request'

export function getStorages(params) {
  return api.get('/storages', { params })
}

export function getStorage(id) {
  return api.get(`/storages/${id}`)
}

export function createStorage(data) {
  return api.post('/storages', data)
}

export function updateStorage(id, data) {
  return api.put(`/storages/${id}`, data)
}

export function deleteStorage(id) {
  return api.delete(`/storages/${id}`)
}

export function testStorage(id) {
  return api.post(`/storages/${id}/test`)
}

export function getStorageCapacity(id) {
  return api.get(`/storages/${id}/capacity`)
}

export function getAllStorageCapacity() {
  return api.get('/storages/capacity/all')
}
