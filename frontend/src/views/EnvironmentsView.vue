<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';
const envs = ref([]); const loading = ref(true); const error = ref('');
onMounted(async()=>{try{const {data}=await axios.get('/api/v1/environments'); envs.value=data}catch(err){error.value=err.response?.data?.detail||'Unable to load environments.'}finally{loading.value=false}});
</script>
<template><section><div class="page-heading"><p class="eyebrow">Targets</p><h1>Environments</h1><p>Base URLs and variables used by test runs.</p></div><div v-if="loading" class="card muted">Loading environments…</div><div v-else-if="error" class="card error">{{ error }}</div><table v-else class="data-table"><thead><tr><th>Name</th><th>Base URL</th><th>Auth</th><th>Status</th></tr></thead><tbody><tr v-for="env in envs" :key="env.id"><td>{{ env.name }}</td><td>{{ env.base_url }}</td><td>{{ env.auth_type }}</td><td>{{ env.is_active ? 'Active' : 'Inactive' }}</td></tr><tr v-if="!envs.length"><td colspan="4">No environments yet.</td></tr></tbody></table></section></template>
