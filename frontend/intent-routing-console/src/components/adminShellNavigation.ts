export type AdminShellRouteIcon =
  | 'dashboard'
  | 'services'
  | 'organizationDirectory'
  | 'permissionManagement'
  | 'intentCatalog'
  | 'catalogVersions'
  | 'releases'
  | 'testRuns'
  | 'apiKeys'
  | 'runtimeLogs'
  | 'auditLogs';

export type AdminShellRouteSpec = {
  path: string;
  name: string;
  icon: AdminShellRouteIcon;
  systemAdminOnly?: boolean;
};

export const ADMIN_SHELL_ROUTE_SPECS: AdminShellRouteSpec[] = [
  { path: '/dashboard', name: 'Dashboard', icon: 'dashboard' },
  { path: '/services', name: 'Services', icon: 'services' },
  {
    path: '/organization-directory',
    name: '조직 디렉터리',
    icon: 'organizationDirectory',
    systemAdminOnly: true,
  },
  {
    path: '/permission-management',
    name: '권한관리',
    icon: 'permissionManagement',
    systemAdminOnly: true,
  },
  { path: '/intents', name: 'Intent Catalog', icon: 'intentCatalog' },
  { path: '/catalog-versions', name: 'Catalog 버전관리', icon: 'catalogVersions' },
  { path: '/releases', name: 'Releases', icon: 'releases' },
  { path: '/test-runs', name: 'Test Runs', icon: 'testRuns' },
  { path: '/api-keys', name: 'API Keys', icon: 'apiKeys' },
  { path: '/runtime-logs', name: 'Runtime Logs', icon: 'runtimeLogs' },
  { path: '/audit-logs', name: 'Audit Logs', icon: 'auditLogs' },
];

export function getAdminShellRouteSpecs(globalRoles: readonly string[] = []) {
  const isSystemAdmin = globalRoles.includes('system_admin');

  return ADMIN_SHELL_ROUTE_SPECS.filter(
    (route) => !route.systemAdminOnly || isSystemAdmin,
  );
}
