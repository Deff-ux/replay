import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { guest: true } },
  { path: '/', component: () => import('../views/DashboardView.vue') },
  { path: '/tests', component: () => import('../views/TestCasesView.vue') },
  { path: '/tests/:id', component: () => import('../views/TestCaseDetailView.vue') },
  { path: '/suites', component: () => import('../views/SuitesView.vue') },
  { path: '/suites/builder', component: () => import('../views/SuiteBuilderView.vue') },
  { path: '/suites/:id', component: () => import('../views/SuiteDetailView.vue') },
  { path: '/environments', component: () => import('../views/EnvironmentsView.vue') },
  { path: '/reports', component: () => import('../views/ReportView.vue') },
  { path: '/seeds', component: () => import('../views/SeedsView.vue') },
  { path: '/users', component: () => import('../views/UsersView.vue') },
  { path: '/runs/:id', component: () => import('../views/RunDetailView.vue') },
  { path: '/settings', component: () => import('../views/SettingsView.vue') },
  { path: '/:pathMatch(.*)*', component: () => import('../views/NotFoundView.vue') },
];

const router = createRouter({ history: createWebHistory(), routes });

// Auth guard — lazy import avoids circular dep at module level
router.beforeEach(async (to) => {
  const { useAuthStore } = await import('../stores/auth');
  const auth = useAuthStore();

  if (!auth.isAuthenticated && !to.meta?.guest) {
    return '/login';
  }

  if (auth.isAuthenticated && to.path === '/login') {
    return '/';
  }
});

export default router;
