<script setup>
import axios from 'axios';
import { computed, onMounted, ref } from 'vue';

const stats = ref(null);
const loading = ref(true);
const error = ref('');

const formatDuration = (ms) => {
  if (!ms && ms !== 0) return '—';
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  const mins = Math.floor(ms / 60000);
  const secs = Math.round((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
};

const passRateColor = computed(() => {
  if (!stats.value) return '#94a3b8';
  const rate = stats.value.pass_rate;
  if (rate >= 80) return '#22c55e';
  if (rate >= 50) return '#eab308';
  return '#ef4444';
});

const passRateIcon = computed(() => {
  if (!stats.value) return '📊';
  const rate = stats.value.pass_rate;
  if (rate >= 80) return '✅';
  if (rate >= 50) return '⚠️';
  return '❌';
});

const timeAgo = (dateStr) => {
  if (!dateStr) return '';
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

const isEmpty = computed(() => {
  if (!stats.value) return false;
  return stats.value.total_tests === 0 && stats.value.total_suites === 0 && stats.value.total_runs === 0;
});

const metrics = computed(() => {
  if (!stats.value) return [];
  return [
    { icon: '🧪', label: 'Total Tests', value: stats.value.total_tests, accent: '#3b82f6' },
    { icon: '📦', label: 'Total Suites', value: stats.value.total_suites, accent: '#8b5cf6' },
    { icon: '🚀', label: 'Total Runs', value: stats.value.total_runs, accent: '#06b6d4' },
    { icon: passRateIcon.value, label: 'Pass Rate', value: `${stats.value.pass_rate}%`, accent: passRateColor.value, progress: stats.value.pass_rate },
    { icon: '⏱️', label: 'Avg Duration', value: formatDuration(stats.value.avg_duration_ms), accent: '#f59e0b' },
  ];
});

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/dashboard/stats');
    stats.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to load dashboard metrics.';
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="dashboard">
    <div class="page-heading">
      <p class="eyebrow">Replay overview</p>
      <h1>Dashboard</h1>
      <p>Track regression coverage, execution volume, and the latest run health.</p>
    </div>

    <!-- Skeleton Loading -->
    <div v-if="loading" class="cards metric-grid">
      <article v-for="i in 5" :key="i" class="card metric-card skeleton-card">
        <div class="skeleton-line skeleton-short"></div>
        <div class="skeleton-line skeleton-long"></div>
      </article>
      <article class="card metric-card wide skeleton-card">
        <div class="skeleton-line skeleton-short"></div>
        <div class="skeleton-line skeleton-long"></div>
      </article>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card error">{{ error }}</div>

    <!-- Dashboard Content -->
    <template v-else>
      <!-- Empty State -->
      <div v-if="isEmpty" class="empty-state card">
        <div class="empty-icon">📭</div>
        <h3>No test data yet</h3>
        <p>Create your first test case to get started. Head over to the Tests section to begin building your regression suite.</p>
        <RouterLink to="/tests" class="empty-cta">Go to Tests →</RouterLink>
      </div>

      <!-- Metric Cards -->
      <div v-else class="cards metric-grid">
        <article
          v-for="m in metrics"
          :key="m.label"
          class="card metric-card"
          :style="{ borderLeftColor: m.accent }"
        >
          <span class="metric-icon">{{ m.icon }}</span>
          <span class="metric-label">{{ m.label }}</span>
          <strong class="metric-value" :style="{ color: m.accent }">{{ m.value }}</strong>
          <div v-if="m.progress !== undefined" class="progress-track">
            <div
              class="progress-fill"
              :style="{ width: m.progress + '%', background: m.accent }"
            ></div>
          </div>
        </article>

        <!-- Last Run Card -->
        <article class="card metric-card wide last-run-card">
          <span class="metric-icon">🎯</span>
          <span class="metric-label">Last Run</span>
          <template v-if="stats.last_run">
            <div class="last-run-info">
              <RouterLink :to="`/runs/${stats.last_run.id}`" class="last-run-id">
                #{{ stats.last_run.id }}
              </RouterLink>
              <span class="badge" :class="stats.last_run.status">
                {{ stats.last_run.status }}
              </span>
              <span class="last-run-time">{{ timeAgo(stats.last_run.created_at) }}</span>
            </div>
            <div class="last-run-meta">
              {{ new Date(stats.last_run.created_at).toLocaleString() }}
            </div>
          </template>
          <span v-else class="muted">No runs yet</span>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
/* Skeleton */
.skeleton-card {
  gap: 0.75rem;
  border-left: 3px solid rgba(148, 163, 184, 0.15) !important;
}

.skeleton-line {
  height: 14px;
  border-radius: 8px;
  background: linear-gradient(90deg, rgba(148,163,184,0.08) 25%, rgba(148,163,184,0.18) 50%, rgba(148,163,184,0.08) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-short { width: 40%; }
.skeleton-long { width: 70%; height: 28px; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Metric Cards */
.metric-card {
  position: relative;
  border-left: 3px solid rgba(148, 163, 184, 0.2);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.3);
}

.metric-icon {
  font-size: 1.5rem;
  line-height: 1;
}

.metric-label {
  color: #94a3b8;
  font-size: 0.85rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.1;
}

/* Progress Bar */
.progress-track {
  height: 6px;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.25rem;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.8s ease;
}

/* Last Run */
.last-run-card {
  gap: 0.5rem;
}

.last-run-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.last-run-id {
  font-size: 1.2rem;
  font-weight: 700;
  color: #38bdf8;
  text-decoration: none;
}

.last-run-id:hover {
  text-decoration: underline;
}

.last-run-time {
  color: #64748b;
  font-size: 0.85rem;
}

.last-run-meta {
  color: #64748b;
  font-size: 0.8rem;
}

.badge {
  border-radius: 999px;
  padding: 0.2rem 0.7rem;
  font-size: 0.8rem;
  font-weight: 600;
  background: #475569;
  color: #e2e8f0;
  text-transform: capitalize;
}

.badge.passed { background: #16a34a; color: #fff; }
.badge.failed { background: #dc2626; color: #fff; }
.badge.running { background: #2563eb; color: #fff; }
.badge.pending { background: #d97706; color: #fff; }

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.empty-icon {
  font-size: 3rem;
}

.empty-state h3 {
  margin: 0;
  font-size: 1.5rem;
  color: #f8fafc;
}

.empty-state p {
  color: #94a3b8;
  max-width: 400px;
  margin: 0;
}

.empty-cta {
  display: inline-block;
  margin-top: 0.5rem;
  padding: 0.6rem 1.5rem;
  background: #2563eb;
  color: #fff;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
  transition: background 0.15s ease;
}

.empty-cta:hover {
  background: #1d4ed8;
}

/* Muted */
.muted { color: #64748b; }
</style>
