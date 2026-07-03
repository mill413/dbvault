import { describe, expect, it } from 'vitest'

import { createPasswordValidator } from './validation'

const messages = {
  'user.passwordRequired': 'Password is required',
  'user.passwordLength': 'Password is too short',
  'user.passwordLetterRequired': 'Password needs a letter',
  'user.passwordDigitRequired': 'Password needs a digit',
}

const t = (key) => messages[key] || key

function validatePassword(value) {
  return new Promise((resolve) => {
    createPasswordValidator(t)({}, value, (error) => {
      resolve(error?.message || null)
    })
  })
}

describe('createPasswordValidator', () => {
  it('requires a value', async () => {
    await expect(validatePassword('')).resolves.toBe('Password is required')
  })

  it('requires length, letters, and digits', async () => {
    await expect(validatePassword('a1')).resolves.toBe('Password is too short')
    await expect(validatePassword('12345')).resolves.toBe('Password needs a letter')
    await expect(validatePassword('abcde')).resolves.toBe('Password needs a digit')
  })

  it('accepts valid passwords', async () => {
    await expect(validatePassword('abcde1')).resolves.toBeNull()
  })
})
