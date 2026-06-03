import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@vueuse/head'
import * as Sentry from '@sentry/vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { usePreferencesStore } from './store/preferences'
import './assets/css/main.css'
import '@vuepic/vue-datepicker/dist/main.css'

const app = createApp(App)
const pinia = createPinia()
const head = createHead()

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    app,
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production',
    release: import.meta.env.VITE_SENTRY_RELEASE || undefined,
    integrations: [Sentry.browserTracingIntegration({ router })],
    tracesSampleRate: parseFloat(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || '0.1'),
    sendDefaultPii: import.meta.env.VITE_SENTRY_SEND_PII === 'true',
  })
}

app.use(pinia)
app.use(router)
app.use(head)
app.use(i18n)

const preferencesStore = usePreferencesStore()
preferencesStore.loadFromLocalStorage()

app.mount('#app')
