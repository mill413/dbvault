export function createPasswordValidator(t) {
  return (rule, value, callback) => {
    if (!value) {
      callback(new Error(t('user.passwordRequired')))
      return
    }
    if (value.length < 5) {
      callback(new Error(t('user.passwordLength')))
      return
    }
    if (!/[a-zA-Z]/.test(value)) {
      callback(new Error(t('user.passwordLetterRequired')))
      return
    }
    if (!/[0-9]/.test(value)) {
      callback(new Error(t('user.passwordDigitRequired')))
      return
    }
    callback()
  }
}
