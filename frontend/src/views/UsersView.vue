<script setup>
import axios from 'axios';
import { onMounted, ref } from 'vue';

const users = ref([]);
const loading = ref(true);
const error = ref('');

const showForm = ref(false);
const editingId = ref(null);
const form = ref({ username: '', email: '', password: '', role: 'qa', is_active: true });
const saving = ref(false);

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await axios.get('/api/v1/users');
    users.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Unable to load users. Admin role required.';
  } finally {
    loading.value = false;
  }
}

function openAdd() {
  editingId.value = null;
  form.value = { username: '', email: '', password: '', role: 'qa', is_active: true };
  showForm.value = true;
}

function openEdit(u) {
  editingId.value = u.id;
  form.value = {
    username: u.username,
    email: u.email,
    password: '',
    role: u.role,
    is_active: u.is_active,
  };
  showForm.value = true;
}

async function save() {
  saving.value = true;
  try {
    const payload = {
      username: form.value.username,
      email: form.value.email,
      role: form.value.role,
      is_active: form.value.is_active,
    };
    if (editingId.value) {
      if (form.value.password) payload.password = form.value.password;
      await axios.patch(`/api/v1/users/${editingId.value}`, payload);
    } else {
      payload.password = form.value.password;
      await axios.post('/api/v1/users', payload);
    }
    showForm.value = false;
    await load();
  } catch (err) {
    alert(err.response?.data?.detail || 'Failed to save user');
  } finally {
    saving.value = false;
  }
}

async function removeUser(u) {
  if (!confirm(`Delete user "${u.username}"?`)) return;
  try {
    await axios.delete(`/api/v1/users/${u.id}`);
    await load();
  } catch (err) {
    alert(err.response?.data?.detail || 'Failed to delete user');
  }
}

onMounted(load);
</script>

<template>
  <section>
    <div class="page-heading">
      <p class="eyebrow">Access</p>
      <h1>Users</h1>
      <p>Team members and roles for Replay.</p>
    </div>

    <div v-if="loading" class="card muted">Loading users…</div>
    <div v-else-if="error" class="card error">{{ error }}</div>

    <div v-else>
      <button class="btn btn-primary mb-2" @click="openAdd">+ Add User</button>

      <!-- Inline add/edit form -->
      <div v-if="showForm" class="card mb-2" style="border-left: 3px solid var(--accent);">
        <h3>{{ editingId ? 'Edit' : 'Add' }} User</h3>
        <div class="form-row">
          <label>Username</label>
          <input v-model="form.username" placeholder="qa-tester" class="input" />
        </div>
        <div class="form-row">
          <label>Email</label>
          <input v-model="form.email" type="email" placeholder="qa@example.com" class="input" />
        </div>
        <div class="form-row">
          <label>Password {{ editingId ? '(leave blank to keep current)' : '' }}</label>
          <input v-model="form.password" type="password" placeholder="password" class="input" />
        </div>
        <div class="form-row">
          <label>Role</label>
          <select v-model="form.role" class="input">
            <option value="qa">QA</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div class="form-row">
          <label>Active</label>
          <input type="checkbox" v-model="form.is_active" />
        </div>
        <div class="form-actions">
          <button class="btn" :disabled="saving" @click="showForm = false">Cancel</button>
          <button class="btn btn-primary" :disabled="saving || !form.username || !form.email || (!editingId && !form.password)" @click="save">
            {{ saving ? 'Saving…' : editingId ? 'Update' : 'Create' }}
          </button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.role }}</td>
            <td>{{ u.is_active ? 'Active' : 'Inactive' }}</td>
            <td>
              <button class="btn btn-sm" @click="openEdit(u)">Edit</button>
              <button class="btn btn-sm btn-danger" @click="removeUser(u)">Delete</button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="5">No users yet.</td>
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
.form-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.card { padding: 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; }
</style>
