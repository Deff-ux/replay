<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';
const users = ref([]); const loading = ref(true); const error = ref('');
onMounted(async()=>{try{const {data}=await axios.get('/api/v1/users'); users.value=data}catch(err){error.value=err.response?.data?.detail||'Unable to load users. Admin role required.'}finally{loading.value=false}});
</script>
<template><section><div class="page-heading"><p class="eyebrow">Access</p><h1>Users</h1><p>Team members and roles for Replay.</p></div><div v-if="loading" class="card muted">Loading users…</div><div v-else-if="error" class="card error">{{ error }}</div><table v-else class="data-table"><thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody><tr v-for="user in users" :key="user.id"><td>{{ user.username }}</td><td>{{ user.email }}</td><td>{{ user.role }}</td><td>{{ user.is_active ? 'Active' : 'Inactive' }}</td></tr><tr v-if="!users.length"><td colspan="4">No users yet.</td></tr></tbody></table></section></template>
