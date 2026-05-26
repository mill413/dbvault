import api from './request'

export function getAuditLogs(params) {
  return api.get('/audit-logs', { params })
}

export function getAlerts(params) {
  return api.get('/alerts', { params })
}

export function resolveAlert(id) {
  return api.post(`/alerts/${id}/resolve`)
}

export function getDashboardSummary() {
  return api.get('/dashboard/summary')
}

export function getBackupTrends(days = 7) {
  return api.get('/dashboard/backup-trends', { params: { days } })
}

export function getStorageUsage() {
  return api.get('/dashboard/storage-usage')
}

export function getRestoreTasks(params) {
  return api.get('/restore-tasks', { params })
}

export function runRestore(data) {
  return api.post('/restore/run', data)
}
