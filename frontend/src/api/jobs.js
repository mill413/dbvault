import api from './request'

export function getJobs(params) {
  return api.get('/jobs', { params })
}

export function getJob(id) {
  return api.get(`/jobs/${id}`)
}

export function createJob(data) {
  return api.post('/jobs', data)
}

export function updateJob(id, data) {
  return api.put(`/jobs/${id}`, data)
}

export function deleteJob(id) {
  return api.delete(`/jobs/${id}`)
}

export function enableJob(id) {
  return api.post(`/jobs/${id}/enable`)
}

export function disableJob(id) {
  return api.post(`/jobs/${id}/disable`)
}

export function runJobNow(id) {
  return api.post(`/jobs/${id}/run-now`)
}
