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
    { path: '/admin-access-request', component: './AdminAccessRequest' },
    { path: '/dashboard', component: './Dashboard' },
    { path: '/services', component: './Services' },
    { path: '/organization-directory', component: './OrganizationDirectory' },
    { path: '/permission-management', component: './PermissionManagement' },
    { path: '/intents', component: './Intents' },
    { path: '/catalog-versions', redirect: '/intents' },
    { path: '/releases', component: './Releases' },
    { path: '/test-runs', component: './TestRuns' },
    { path: '/api-keys', component: './ApiKeys' },
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
