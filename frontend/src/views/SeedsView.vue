<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';
const seeds = ref([]); const loading = ref(true); const error = ref('');
onMounted(async()=>{try{const {data}=await axios.get('/api/v1/seeds'); seeds.value=data}catch(err){error.value=err.response?.data?.detail||'Unable to load seed templates.'}finally{loading.value=false}});
</script>
<template><section><div class="page-heading"><p class="eyebrow">Data setup</p><h1>Seeds</h1><p>Reusable JSON templates for preparing test data.</p></div><div v-if="loading" class="card muted">Loading seed templates…</div><div v-else-if="error" class="card error">{{ error }}</div><div v-else class="cards"><article v-for="seed in seeds" :key="seed.name" class="card"><h2>{{ seed.name }}</h2><p>{{ seed.description || 'No description provided.' }}</p><code>{{ JSON.stringify(seed.parameters) }}</code></article><div v-if="!seeds.length" class="card muted">No seed templates found.</div></div></section></template>
