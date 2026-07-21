export type AdminShellRouteIcon =
  | 'dashboard'
  | 'services'
  | 'organizationDirectory'
  | 'permissionManagement'
  | 'intentCatalog'
  | 'releases'
  | 'testRuns'
  | 'apiKeys'
  | 'runtimeLogs'
  | 'auditLogs';

export type AdminShellRouteSpec = {
  path: string;
  name: string;
  icon: AdminShellRouteIcon;
  allowedRoles?: string[];
};

export const ADMIN_SHELL_ROUTE_SPECS: AdminShellRouteSpec[] = [
  { path: '/dashboard', name: 'Dashboard', icon: 'dashboard' },
  { path: '/services', name: 'Services', icon: 'services' },
  {
    path: '/organization-directory',
    name: '조직 디렉터리',
    icon: 'organizationDirectory',
    allowedRoles: ['system_admin'],
  },
  {
    path: '/permission-management',
    name: '권한관리',
    icon: 'permissionManagement',
    allowedRoles: ['system_admin'],
  },
  { path: '/intents', name: 'Intent Catalog', icon: 'intentCatalog' },
  { path: '/releases', name: 'Releases', icon: 'releases' },
  { path: '/test-runs', name: 'Test Runs', icon: 'testRuns' },
  {
    path: '/api-keys',
    name: 'API Keys',
    icon: 'apiKeys',
    allowedRoles: ['system_admin', 'service_owner'],
  },
  { path: '/runtime-logs', name: 'Runtime Logs', icon: 'runtimeLogs' },
  {
    path: '/audit-logs',
    name: 'Audit Logs',
    icon: 'auditLogs',
    allowedRoles: ['system_admin', 'service_operator', 'auditor'],
  },
];

export function getAdminShellRouteSpecs(navigationRoles: readonly string[] = []) {
  const roleSet = new Set(navigationRoles);

  return ADMIN_SHELL_ROUTE_SPECS.filter(
    (route) => !route.allowedRoles || route.allowedRoles.some((role) => roleSet.has(role)),
  );
}
