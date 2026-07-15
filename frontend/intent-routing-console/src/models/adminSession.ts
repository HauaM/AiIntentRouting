import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchCurrentAdminUser,
  listAccessibleServices,
  loginAdmin,
  logoutAdmin,
} from '../services/authServices';

const STORAGE_KEYS = {
  serviceId: 'admin_selected_service_id',
};

export type AdminSession = {
  authenticated: boolean;
  user?: API.AdminUser;
  globalRoles: string[];
  serviceRoles: API.AdminServiceRole[];
  services: API.AccessibleService[];
  serviceId: string;
};

export type ServiceOption = {
  label: string;
  value: string;
};

export const EMPTY_ADMIN_SESSION: AdminSession = {
  authenticated: false,
  user: undefined,
  globalRoles: [],
  serviceRoles: [],
  services: [],
  serviceId: '',
};

const storage = () => {
  if (typeof localStorage === 'undefined') return undefined;
  return localStorage;
};

const readSelectedServiceId = () => storage()?.getItem(STORAGE_KEYS.serviceId)?.trim() ?? '';

const writeSelectedServiceId = (serviceId: string) => {
  const target = storage();
  if (!target) return;
  if (serviceId) target.setItem(STORAGE_KEYS.serviceId, serviceId);
  else target.removeItem(STORAGE_KEYS.serviceId);
};

const clearSelectedServiceId = () => storage()?.removeItem(STORAGE_KEYS.serviceId);

export const isAdminSessionReady = (session: AdminSession) =>
  Boolean(session.authenticated && session.user && session.serviceId.trim());

export const selectInitialServiceId = (
  services: API.AccessibleService[],
  preferredServiceId: string,
) => {
  const preferred = preferredServiceId.trim();
  if (preferred && services.some((service) => service.service_id === preferred)) {
    return preferred;
  }
  return services[0]?.service_id ?? '';
};

export const normalizeAuthSession = (
  currentUser: API.AdminCurrentUserResponse,
  services: API.AccessibleService[],
  preferredServiceId = readSelectedServiceId(),
): AdminSession => ({
  authenticated: true,
  user: currentUser.user,
  globalRoles: currentUser.global_roles,
  serviceRoles: currentUser.service_roles,
  services,
  serviceId: selectInitialServiceId(services, preferredServiceId),
});

export const toServiceOptions = (services: API.AccessibleService[]): ServiceOption[] =>
  services.map((service) => ({
    label: service.display_name || service.service_id,
    value: service.service_id,
  }));

export const getDisplayRoles = (session: AdminSession) => {
  const serviceRoles =
    session.services.find((service) => service.service_id === session.serviceId)?.roles ??
    session.serviceRoles
      .filter((role) => role.service_id === session.serviceId)
      .map((role) => role.role);
  return Array.from(new Set([...session.globalRoles, ...serviceRoles]));
};

export const hasAnyDisplayRole = (session: AdminSession, roles: string[]) => {
  const roleSet = new Set(getDisplayRoles(session));
  return roles.some((role) => roleSet.has(role));
};

export const canEditCatalog = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner', 'service_developer']);

export const canManageReleases = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner', 'service_developer']);

export const canManageApiKeys = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner', 'service_developer']);

export const canManageRuntimeSetup = (session: AdminSession) =>
  canManageApiKeys(session);

export const canCreateServices = (session: AdminSession) =>
  session.globalRoles.includes('system_admin');

export const canManageServiceMembers = (session: AdminSession) =>
  session.globalRoles.includes('system_admin');

export const canUseServicesPage = (session: AdminSession) =>
  Boolean(
    session.authenticated &&
      session.user &&
      (session.serviceId.trim() || canCreateServices(session)),
  );

export const canSelectServiceFromScope = (session: AdminSession, serviceId: string) => {
  const targetServiceId = serviceId.trim();
  return Boolean(
    targetServiceId &&
      session.services.some((service) => service.service_id === targetServiceId),
  );
};

export default function useAdminSessionModel() {
  const [session, setSession] = useState<AdminSession>(EMPTY_ADMIN_SESSION);
  const [restoring, setRestoring] = useState(true);
  const [error, setError] = useState<string>();

  const restoreSession = useCallback(async () => {
    setRestoring(true);
    setError(undefined);
    try {
      const currentUser = await fetchCurrentAdminUser();
      const services = await listAccessibleServices();
      const next = normalizeAuthSession(currentUser, services);
      setSession(next);
      writeSelectedServiceId(next.serviceId);
      return next;
    } catch (err: any) {
      setSession(EMPTY_ADMIN_SESSION);
      if (err?.response?.status && err.response.status !== 401) {
        setError(err?.message ?? 'Failed to restore admin session.');
      }
      return EMPTY_ADMIN_SESSION;
    } finally {
      setRestoring(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (email: string, password: string) => {
    setError(undefined);
    const currentUser = await loginAdmin({ email, password });
    const services = await listAccessibleServices();
    const next = normalizeAuthSession(currentUser, services);
    setSession(next);
    writeSelectedServiceId(next.serviceId);
    return next;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutAdmin();
    } finally {
      clearSelectedServiceId();
      setSession(EMPTY_ADMIN_SESSION);
    }
  }, []);

  const setServiceId = useCallback((serviceId: string) => {
    const nextServiceId = serviceId.trim();
    if (!nextServiceId) return;
    writeSelectedServiceId(nextServiceId);
    setSession((current) => ({ ...current, serviceId: nextServiceId }));
  }, []);

  const serviceOptions = useMemo(() => toServiceOptions(session.services), [session.services]);

  return {
    session,
    serviceOptions,
    restoring,
    error,
    displayRoles: getDisplayRoles(session),
    restoreSession,
    login,
    logout,
    setServiceId,
  };
}
