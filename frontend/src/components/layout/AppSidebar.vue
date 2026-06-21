<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <h2>Replay</h2>
      <span class="sidebar-sub">Regression Dashboard</span>
    </div>

    <nav class="sidebar-nav">
      <RouterLink to="/" class="nav-link">📊 Dashboard</RouterLink>
      <RouterLink to="/tests" class="nav-link">🧪 Tests</RouterLink>
      <RouterLink to="/suites" class="nav-link">📦 Suites</RouterLink>
      <RouterLink to="/suites/builder" class="nav-link">🔧 Suite Builder</RouterLink>
      <RouterLink to="/environments" class="nav-link">🌐 Environments</RouterLink>
      <RouterLink to="/reports" class="nav-link">📋 Reports</RouterLink>
      <RouterLink to="/seeds" class="nav-link">🌱 Seeds</RouterLink>
      <RouterLink to="/users" class="nav-link">👥 Users</RouterLink>
    </nav>

    <div class="sidebar-footer">
      <button class="logout-btn" @click="handleLogout">
        ← Logout
      </button>
    </div>
  </aside>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';

const router = useRouter();
const auth = useAuthStore();

function handleLogout() {
  auth.logout();
  router.push('/login');
}
</script>

<style scoped>
.sidebar-brand {
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  margin-bottom: 0.5rem;
}

.sidebar-brand h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #f8fafc;
}

.sidebar-sub {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.nav-link {
  color: #94a3b8 !important;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.9rem;
  transition: all 0.15s ease;
}

.nav-link:hover {
  background: rgba(56, 189, 248, 0.08);
  color: #e2e8f0 !important;
}

.nav-link.router-link-active,
.nav-link.router-link-exact-active {
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8 !important;
  font-weight: 600;
}

.sidebar-footer {
  border-top: 1px solid rgba(148, 163, 184, 0.15);
  padding-top: 0.75rem;
}

.logout-btn {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  border: 1px solid rgba(248, 113, 113, 0.2);
  background: transparent;
  color: #fca5a5;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.logout-btn:hover {
  background: rgba(248, 113, 113, 0.1);
  border-color: #fca5a5;
  color: #fecaca;
}
</style>
