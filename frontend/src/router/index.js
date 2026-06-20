import { createRouter, createWebHistory } from 'vue-router';
const routes=[{path:'/login',component:()=>import('../views/LoginView.vue')},{path:'/',component:()=>import('../views/DashboardView.vue')},{path:'/tests',component:()=>import('../views/TestCasesView.vue')},{path:'/suites/builder',component:()=>import('../views/SuiteBuilderView.vue')},{path:'/runs/:id',component:()=>import('../views/RunDetailView.vue')},{path:'/:pathMatch(.*)*',component:()=>import('../views/NotFoundView.vue')}];
export default createRouter({history:createWebHistory(),routes})
