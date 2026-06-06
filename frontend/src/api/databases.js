import api from './request'

export function getDatabases(params) {
  return api.get('/databases', { params })
}

export function getDatabase(id) {
  return api.get(`/databases/${id}`)
}

export function createDatabase(data) {
  return api.post('/databases', data)
}

export function updateDatabase(id, data) {
  return api.put(`/databases/${id}`, data)
}

export function deleteDatabase(id) {
  return api.delete(`/databases/${id}`)
}

export function testDatabaseConnection(data) {
  return api.post('/databases/test', data)
}

export function testSavedDatabase(id) {
  return api.post(`/databases/${id}/test`)
}

export function getK8sNamespaces(params) {
  return api.get('/databases/k8s/namespaces', { params })
}

export function getK8sPods(params) {
  return api.get('/databases/k8s/pods', { params })
}
