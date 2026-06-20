import axios from 'axios';
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import PrimeVue from 'primevue/config';
import App from './App.vue';
import router from './router';
import './assets/styles/global.css';

const token = localStorage.getItem('token');
if (token) {
  axios.defaults.headers.common.Authorization = `Bearer ${token}`;
}

createApp(App).use(createPinia()).use(router).use(PrimeVue).mount('#app');
