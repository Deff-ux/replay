<template>
  <div class="login-wrapper">
    <form class="login-card" @submit.prevent="submit">
      <div class="login-header">
        <div class="login-logo">Replay</div>
        <p class="login-subtitle">Sign in to your account</p>
      </div>

      <div v-if="error" class="login-error">{{ error }}</div>

      <label class="field">
        <span class="field-label">Username</span>
        <input
          v-model="username"
          placeholder="Enter your username"
          :disabled="loading"
          autocomplete="username"
          autofocus
        />
      </label>

      <label class="field">
        <span class="field-label">Password</span>
        <input
          v-model="password"
          placeholder="Enter your password"
          type="password"
          :disabled="loading"
          autocomplete="current-password"
        />
      </label>

      <button type="submit" class="login-btn" :disabled="loading || !username || !password">
        <span v-if="loading" class="btn-loading">
          <span class="spinner"></span>
          Logging in…
        </span>
        <span v-else>Sign In</span>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const router = useRouter();
const auth = useAuthStore();

async function submit() {
  if (!username.value || !password.value) return;

  error.value = '';
  loading.value = true;

  try {
    await auth.login(username.value, password.value);
    router.push('/');
  } catch (err) {
    error.value = err.response?.data?.detail || 'Login failed. Please check your credentials.';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  padding: 1rem;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: #1e293b;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 16px;
  padding: 2rem 1.5rem 1.5rem;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.login-header {
  text-align: center;
}

.login-logo {
  font-size: 1.75rem;
  font-weight: 800;
  color: #38bdf8;
  letter-spacing: -0.03em;
}

.login-subtitle {
  margin: 0.25rem 0 0;
  color: #94a3b8;
  font-size: 0.875rem;
}

.login-error {
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: #fecaca;
  padding: 0.7rem 1rem;
  border-radius: 10px;
  font-size: 0.85rem;
  line-height: 1.4;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #cbd5e1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field input {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #0f172a;
  color: #e2e8f0;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.15s ease;
}

.field input:focus {
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
}

.field input:disabled {
  opacity: 0.6;
}

.login-btn {
  padding: 0.8rem;
  border-radius: 10px;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
  margin-top: 0.25rem;
}

.login-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.login-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
