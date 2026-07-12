const ROLE_PERMISSIONS = {
  Admin: new Set([
    'user:read', 'user:write',
    'database:read', 'database:write',
    'backup:read', 'backup:run', 'backup:delete',
    'restore:run',
    'job:read', 'job:write',
    'storage:read', 'storage:write',
    'audit:read',
  ]),
  Operator: new Set([
    'database:read', 'database:write',
    'backup:read', 'backup:run', 'backup:delete',
    'restore:run',
    'job:read', 'job:write',
    'storage:read',
  ]),
  Viewer: new Set([
    'database:read',
    'backup:read',
    'job:read',
    'storage:read',
  ]),
}

export function hasPermission(role, permission) {
  return ROLE_PERMISSIONS[role]?.has(permission) ?? false
}

export function canViewRoute(role, routeName) {
  const map = {
    Dashboard: 'backup:read',
    Databases: 'database:read',
    DatabaseBrowser: 'database:read',
    Storages: 'storage:read',
    Backups: 'backup:read',
    Jobs: 'job:read',
    Audit: 'audit:read',
    Restores: 'backup:read',
    Alerts: 'backup:read',
    Users: 'user:read',
  }
  const permission = map[routeName]
  if (!permission) return true
  return hasPermission(role, permission)
}
