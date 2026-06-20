<script setup>
import axios from 'axios';
import { computed, onMounted, ref } from 'vue';

const stats = ref(null);
const loading = ref(true);
const error = ref('');

const formatDuration = (milliseconds) => {
  if (!milliseconds) return '0 ms';
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
};

const lastRunLabel = computed(() => {
  if (!stats.value?.last_run) return 'No runs yet';
  const createdAt = new Date(stats.value.last_run.created_at).toLocaleString();
  return `#${stats.value.last_run.id} · ${stats.value.last_run.status} · ${createdAt}`;
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

    <div v-if="loading" class="card muted">Loading dashboard metrics…</div>
    <div v-else-if="error" class="card error">{{ error }}</div>
    <div v-else class="cards metric-grid">
      <article class="card metric-card">
        <span>Total Tests</span>
        <strong>{{ stats.total_tests }}</strong>
      </article>
      <article class="card metric-card">
        <span>Suites</span>
        <strong>{{ stats.total_suites }}</strong>
      </article>
      <article class="card metric-card">
        <span>Pass Rate</span>
        <strong>{{ stats.pass_rate }}%</strong>
      </article>
      <article class="card metric-card">
        <span>Avg Duration</span>
        <strong>{{ formatDuration(stats.avg_duration_ms) }}</strong>
      </article>
      <article class="card metric-card wide">
        <span>Last Run</span>
        <strong>{{ lastRunLabel }}</strong>
      </article>
      <article class="card metric-card">
        <span>Total Runs</span>
        <strong>{{ stats.total_runs }}</strong>
      </article>
    </div>
  </section>
</template>
