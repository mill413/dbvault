import { createI18n } from 'vue-i18n'
import zh from './zh.js'
import en from './en.js'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('language') || 'zh', // default locale
  fallbackLocale: 'en',
  messages: {
    zh,
    en
  }
})

export default i18n
