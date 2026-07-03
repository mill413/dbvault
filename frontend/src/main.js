import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './assets/style.css'
import {
  ArrowDown,
  Clock,
  Coin,
  Document,
  Download,
  Files,
  InfoFilled,
  Lock,
  Message,
  Odometer,
  Plus,
  Refresh,
  Upload,
  User,
  UserFilled,
  Warning,
} from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import i18n from './locales'

const icons = {
  ArrowDown,
  Clock,
  Coin,
  Document,
  Download,
  Files,
  InfoFilled,
  Lock,
  Message,
  Odometer,
  Plus,
  Refresh,
  Upload,
  User,
  UserFilled,
  Warning,
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(ElementPlus)

for (const [key, component] of Object.entries(icons)) {
  app.component(key, component)
}

app.mount('#app')
