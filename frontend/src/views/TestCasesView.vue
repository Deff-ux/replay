<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';
import StatusBadge from '../components/common/StatusBadge.vue';

const tests = ref([]);
const loading = ref(true);
const error = ref('');

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/v1/test-cases');
    tests.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to load test cases.';
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section>
    <div class="page-heading"><p class="eyebrow">Coverage</p><h1>Test Cases</h1><p>Filter by product, module, tags, status, and last result.</p></div>
    <button>Record New Test</button>
    <div v-if="loading" class="card muted">Loading test cases…</div>
    <div v-else-if="error" class="card error">{{ error }}</div>
    <table v-else class="data-table"><thead><tr><th>Name</th><th>Product</th><th>Module</th><th>Status</th><th>Tags</th></tr></thead><tbody><tr v-for="test in tests" :key="test.id"><td>{{ test.name }}</td><td>{{ test.product }}</td><td>{{ test.module || '—' }}</td><td><StatusBadge :status="test.status" /></td><td>{{ test.tags.join(', ') || '—' }}</td></tr><tr v-if="!tests.length"><td colspan="5">No test cases yet.</td></tr></tbody></table>
  </section>
</template>
