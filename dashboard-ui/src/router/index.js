import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '@/layouts/BasicLayout.vue'

const routes = [
  {
    path: '/',
    component: BasicLayout,
    redirect: '/crawler',
    children: [
      {
        path: '/crawler',
        name: 'Crawler',
        component: () => import('@/views/crawler/List.vue'),
        meta: { title: 'Crawler Management' }
      },
      {
        path: '/session',
        name: 'Session',
        component: () => import('@/views/session/List.vue'),
        meta: { title: 'Session Management' }
      },
      {
        path: '/log',
        name: 'Log',
        component: () => import('@/views/log/List.vue'),
        meta: { title: 'Log Management' }
      }
    ]
  },
  {
    path: '/index',
    redirect: '/crawler'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router