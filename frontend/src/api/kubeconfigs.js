import api from './request'

export function getKubeconfigs() {
  return api.get('/kubeconfigs')
}

export function createKubeconfig(data) {
  return api.post('/kubeconfigs', data)
}

export function deleteKubeconfig(name) {
  return api.delete(`/kubeconfigs/${name}`)
}

export function testKubeconfig(name, context = null) {
  const params = {}
  if (context) {
    params.context = context
  }
  return api.post(`/kubeconfigs/${name}/test`, null, { params })
}
