import { defineConfig } from '@umijs/max';

const adminApiProxy = process.env.ADMIN_API_PROXY || 'http://127.0.0.1:30141';

export default defineConfig({
  title: 'Intent Routing Admin',
  npmClient: 'pnpm',
  antd: {},
  model: {},
  initialState: {},
  request: {},
  fastRefresh: true,
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: './Login' },
    { path: '/dashboard', component: './Dashboard' },
    { path: '/intents', component: './Intents' },
    { path: '/runtime-logs', component: './RuntimeLogs' },
    { path: '/audit-logs', component: './AuditLogs' },
  ],
  proxy: {
    '/admin/v1': {
      target: adminApiProxy,
      changeOrigin: true,
    },
  },
});
