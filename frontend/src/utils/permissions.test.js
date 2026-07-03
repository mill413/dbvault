import { describe, expect, it } from 'vitest'

import { canViewRoute, hasPermission } from './permissions'

describe('permissions', () => {
  it('grants admin-only permissions to admins', () => {
    expect(hasPermission('Admin', 'user:read')).toBe(true)
    expect(canViewRoute('Admin', 'Users')).toBe(true)
    expect(canViewRoute('Admin', 'Audit')).toBe(true)
  })

  it('keeps normal users out of admin routes', () => {
    expect(hasPermission('User', 'user:read')).toBe(false)
    expect(canViewRoute('User', 'Users')).toBe(false)
    expect(canViewRoute('User', 'Audit')).toBe(false)
  })

  it('allows known operational routes for normal users', () => {
    expect(canViewRoute('User', 'Databases')).toBe(true)
    expect(canViewRoute('User', 'Backups')).toBe(true)
    expect(canViewRoute('User', 'Restores')).toBe(true)
  })
})
