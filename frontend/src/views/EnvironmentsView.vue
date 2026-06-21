<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';

const envs = ref([]);
const loading = ref(true);
const error = ref('');

const showForm = ref(false);
const editingId = ref(null);
const form = ref({ name: '', base_url: '', auth_type: 'none', auth_config: { user: '', pass: '' }, variables: {}, is_active: true });
const saving = ref(false);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await axios.get('/api/v1/environments');
    envs.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to load environments.';
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  editingId.value = null;
  form.value = { name: '', base_url: '', auth_type: 'none', auth_config: { user: '', pass: '' }, variables: {}, is_active: true };
  showForm.value = true;
}

function openEdit(env) {
  editingId.value = env.id;
  form.value = {
    name: env.name,
    base_url: env.base_url,
    auth_type: env.auth_type,
    auth_config: { ...(env.auth_config || {}) },
    variables: { ...(env.variables || {}) },
    is_active: env.is_active,
  };
  showForm.value = true;
}

async function save() {
  saving.value = true;
  try {
    const payload = {
      name: form.value.name,
      base_url: form.value.base_url,
      auth_type: form.value.auth_type,
      auth_config: form.value.auth_type === 'basic' ? form.value.auth_config : {},
      variables: form.value.variables,
      is_active: form.value.is_active,
    };
    if (editingId.value) {
      await axios.put(`/api/v1/environments/${editingId.value}`, payload);
    } else {
      await axios.post('/api/v1/environments', payload);
    }
    showForm.value = false;
    await load();
  } catch (err) {
    alert(err.response?.data?.detail || 'Failed to save environment');
  } finally {
    saving.value = false;
  }
}

async function removeEnv(env) {
  if (!confirm(`Delete environment "${env.name}"?`)) return;
  try {
    await axios.delete(`/api/v1/environments/${env.id}`);
    await load();
  } catch (err) {
    alert(err.response?.data?.detail || 'Failed to delete environment');
  }
}

onMounted(load);
</script>

<template>
  <section>
    <div class="page-heading">
      <p class="eyebrow">Targets</p>
      <h1>Environments</h1>
      <p>Base URLs and variables used by test runs.</p>
    </div>

    <div v-if="loading" class="card muted">Loading environments…</div>
    <div v-else-if="error" class="card error">{{ error }}</div>

    <div v-else>
      <!-- Add button -->
      <button class="btn btn-primary mb-2" @click="openAdd">+ Add Environment</button>

      <!-- Inline add/edit form -->
      <div v-if="showForm" class="card mb-2" style="border-left: 3px solid var(--accent);">
        <h3>{{ editingId ? 'Edit' : 'Add' }} Environment</h3>
        <div class="form-row">
          <label>Name</label>
          <input v-model="form.name" placeholder="e.g. Phiro Neo Staging" class="input" />
        </div>
        <div class="form-row">
          <label>Base URL</label>
          <input v-model="form.base_url" placeholder="https://neo-staging.phirogo.com" class="input" />
        </div>
        <div class="form-row">
          <label>Auth Type</label>
          <select v-model="form.auth_type" class="input">
            <option value="none">None</option>
            <option value="basic">Basic Auth</option>
          </select>
        </div>
        <div v-if="form.auth_type === 'basic'" class="form-row-group">
          <div class="form-row">
            <label>Username</label>
            <input v-model="form.auth_config.user" placeholder="qa-tester" class="input" />
          </div>
          <div class="form-row">
            <label>Password</label>
            <input v-model="form.auth_config.pass" type="password" placeholder="password" class="input" />
          </div>
        </div>
        <div class="form-row">
          <label>Active</label>
          <input type="checkbox" v-model="form.is_active" />
        </div>
        <div class="form-actions">
          <button class="btn" :disabled="saving" @click="showForm = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !form.name || !form.base_url" @click="save">
            {{ saving ? 'Saving…' : editingId ? 'Update' : 'Create' }}
          </button>
        </div>
      </div>

      <!-- Table -->
      <table class="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Base URL</th>
            <th>Auth</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="env in envs" :key="env.id">
            <td>{{ env.name }}</td>
            <td><code>{{ env.base_url }}</code></td>
            <td>{{ env.auth_type }}</td>
            <td>{{ env.is_active ? 'Active' : 'Inactive' }}</td>
            <td>
              <button class="btn btn-sm" @click="openEdit(env)">Edit</button>
              <button class="btn btn-sm btn-danger" @click="removeEnv(env)">Delete</button>
            </td>
          </tr>
          <tr v-if="!envs.length">
            <td colspan="5">No environments yet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.mb-2 { margin-bottom: 1rem; }
.btn { padding: 0.5rem 1rem; border: 1px solid var(--border); background: var(--surface); border-radius: 6px; cursor: pointer; }
.btn-primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn-danger { background: #e74c3c; color: #fff; border-color: #e74c3c; }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.85em; margin-right: 0.25rem; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.form-row { margin-bottom: 0.75rem; }
.form-row label { display: block; font-size: 0.85em; font-weight: 600; margin-bottom: 0.25rem; color: var(--muted); }
.form-row .input { width: 100%; max-width: 480px; padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); }
.form-row select.input { max-width: 200px; }
.form-row input[type="checkbox"] { transform: scale(1.2); margin-top: 0.25rem; }
.form-row-group { padding-left: 1rem; border-left: 2px solid var(--border); margin-bottom: 0.75rem; }
.form-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.card { padding: 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; }
</style>
