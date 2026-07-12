import api from './request'

export const getCatalogs = (databaseId) => api.get(`/databases/${databaseId}/browser/catalogs`)
export const getTables = (databaseId, catalog) => api.get(`/databases/${databaseId}/browser/tables`, { params: { catalog } })
export const getColumns = (databaseId, params) => api.get(`/databases/${databaseId}/browser/columns`, { params })
export const getRows = (databaseId, params) => api.get(`/databases/${databaseId}/browser/rows`, { params })
