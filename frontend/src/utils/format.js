const UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

export function formatBytes(bytes, decimals = 2) {
  if (bytes == null || bytes === 0) return '0 B'
  const k = 1024
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k))
  const value = bytes / Math.pow(k, i)
  return `${parseFloat(value.toFixed(decimals))} ${UNITS[i] || UNITS[UNITS.length - 1]}`
}
