<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';
const suites = ref([]); const loading = ref(true); const error = ref('');
onMounted(async()=>{try{const {data}=await axios.get('/api/v1/suites'); suites.value=data}catch(err){error.value=err.response?.data?.detail||'Unable to load suites.'}finally{loading.value=false}});
</script>
<template><section><div class="page-heading"><p class="eyebrow">Execution sets</p><h1>Suites</h1><p>Manage ordered groups of tests for scheduled or manual runs.</p></div><RouterLink class="button-link" to="/suites/builder">Create Suite</RouterLink><div v-if="loading" class="card muted">Loading suites…</div><div v-else-if="error" class="card error">{{ error }}</div><table v-else class="data-table"><thead><tr><th>Name</th><th>Product</th><th>Type</th><th>Tests</th><th>Schedule</th><th>Status</th></tr></thead><tbody><tr v-for="suite in suites" :key="suite.id"><td>{{ suite.name }}</td><td>{{ suite.product }}</td><td>{{ suite.suite_type }}</td><td>{{ suite.test_case_order.length }}</td><td>{{ suite.cron_schedule || 'Manual' }}</td><td>{{ suite.is_active ? 'Active' : 'Inactive' }}</td></tr><tr v-if="!suites.length"><td colspan="6">No suites yet.</td></tr></tbody></table></section></template>
