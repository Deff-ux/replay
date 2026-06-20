<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';
const reports = ref([]); const loading = ref(true); const error = ref('');
onMounted(async()=>{try{const {data}=await axios.get('/api/v1/reports'); reports.value=data}catch(err){error.value=err.response?.data?.detail||'Unable to load reports.'}finally{loading.value=false}});
</script>
<template><section><div class="page-heading"><p class="eyebrow">Evidence</p><h1>Reports</h1><p>Generated run summaries and downloadable artifacts.</p></div><div v-if="loading" class="card muted">Loading reports…</div><div v-else-if="error" class="card error">{{ error }}</div><table v-else class="data-table"><thead><tr><th>Run</th><th>Created</th><th>Summary</th><th>Artifacts</th></tr></thead><tbody><tr v-for="report in reports" :key="report.id"><td>#{{ report.run_id }}</td><td>{{ new Date(report.created_at).toLocaleString() }}</td><td>{{ JSON.stringify(report.summary) }}</td><td>{{ report.html_path || report.pdf_path || '—' }}</td></tr><tr v-if="!reports.length"><td colspan="4">No reports yet.</td></tr></tbody></table></section></template>
