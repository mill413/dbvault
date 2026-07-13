import api from './request'

export function getBackups(params) {
  return api.get('/backups', { params })
}

export function getBackup(id) {
  return api.get(`/backups/${id}`)
}

export function runBackup(data) {
  return api.post('/backups/run', data)
}

export function uploadBackup(data) {
  return api.post('/backups/upload', data)
}

export function runLifecycle() {
  return api.post('/backups/lifecycle/run')
}

export function deleteBackup(id) {
  return api.delete(`/backups/${id}`)
}

export function downloadBackup(id) {
  return api.get(`/backups/${id}/download`, { responseType: 'blob' })
}

export function verifyBackup(id) {
  return api.post(`/backups/${id}/verify`)
}

export function getBackupTasks(params) {
  return api.get('/backup-tasks', { params })
}

export function getBackupTask(id) {
  return api.get(`/backup-tasks/${id}`)
}

export function getBackupTaskEvents(id) {
  return api.get(`/backup-tasks/${id}/events`)
}

export function cancelBackupTask(id) {
  return api.post(`/backup-tasks/${id}/cancel`)
}
