import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'game',
      component: () => import('./pages/GamePage.vue'),
    },
    {
      path: '/observe',
      name: 'observe',
      component: () => import('./pages/ObservePage.vue'),
    },
  ],
})

export default router
