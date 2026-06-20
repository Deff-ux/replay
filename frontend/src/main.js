import { createApp } from 'vue'; import { createPinia } from 'pinia'; import PrimeVue from 'primevue/config'; import App from './App.vue'; import router from './router'; import './assets/styles/global.css';
createApp(App).use(createPinia()).use(router).use(PrimeVue).mount('#app')
