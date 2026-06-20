import { createRouter, createWebHistory } from 'vue-router';

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue') },
  { path: '/', component: () => import('../views/DashboardView.vue') },
  { path: '/tests', component: () => import('../views/TestCasesView.vue') },
  { path: '/suites', component: () => import('../views/SuitesView.vue') },
  { path: '/suites/builder', component: () => import('../views/SuiteBuilderView.vue') },
  { path: '/environments', component: () => import('../views/EnvironmentsView.vue') },
  { path: '/reports', component: () => import('../views/ReportView.vue') },
  { path: '/seeds', component: () => import('../views/SeedsView.vue') },
  { path: '/users', component: () => import('../views/UsersView.vue') },
  { path: '/runs/:id', component: () => import('../views/RunDetailView.vue') },
  { path: '/:pathMatch(.*)*', component: () => import('../views/NotFoundView.vue') },
];

export default createRouter({ history: createWebHistory(), routes });
