import api from './request'

export function dryRunRestore(data) {
  return api.post('/restore/dry-run', data)
}

export function runRestore(data) {
  return api.post('/restore/run', data)
}

export function getRestoreTasks(params) {
  return api.get('/restore-tasks', { params })
}

export function getRestoreTask(id) {
  return api.get(`/restore-tasks/${id}`)
}

export function getRestoreTaskEvents(id) {
  return api.get(`/restore-tasks/${id}/events`)
}
