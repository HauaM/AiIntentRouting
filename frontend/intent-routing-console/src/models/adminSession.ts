import { useCallback, useState } from 'react';

const STORAGE_KEYS = {
  adminToken: 'admin_token',
  actorId: 'actor_id',
  actorRoles: 'actor_roles',
  serviceId: 'service_id',
  serviceScope: 'service_scope',
  environment: 'admin_environment',
  serviceOptions: 'admin_service_options',
};

export type AdminSession = {
  adminToken: string;
  actorId: string;
  actorRoles: string[];
  serviceId: string;
  serviceScope: string;
  environment: string;
};

export const DEFAULT_ADMIN_SESSION: AdminSession = {
  adminToken: '',
  actorId: 'admin-user',
  actorRoles: ['system_admin'],
  serviceId: 'it-helpdesk-pilot-sprint10-operation-monitoring',
  serviceScope: 'it-helpdesk-pilot-sprint10-operation-monitoring',
  environment: 'local',
};

export type ServiceOption = {
  label: string;
  value: string;
};

const storage = () => {
  if (typeof localStorage === 'undefined') return undefined;
  return localStorage;
};

const readValue = (key: string, fallback: string) => {
  const value = storage()?.getItem(key)?.trim();
  return value || fallback;
};

export const normalizeRoles = (roles: string | string[]) => {
  const values = Array.isArray(roles) ? roles : roles.split(',');
  const normalized = values.map((role) => role.trim()).filter(Boolean);
  return normalized.length > 0 ? normalized : DEFAULT_ADMIN_SESSION.actorRoles;
};

export const normalizeEnvironment = (environment: string) =>
  environment.trim() || DEFAULT_ADMIN_SESSION.environment;

export const isAdminSessionReady = (session: AdminSession) =>
  Boolean(
    session.adminToken.trim() &&
      session.actorId.trim() &&
      session.actorRoles.length > 0 &&
      session.serviceId.trim() &&
      session.serviceScope.trim(),
  );

const uniqueServiceIds = (values: string[]) =>
  Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));

export function readAdminSession(): AdminSession {
  const serviceId = readValue(STORAGE_KEYS.serviceId, DEFAULT_ADMIN_SESSION.serviceId);
  return {
    adminToken: readValue(STORAGE_KEYS.adminToken, DEFAULT_ADMIN_SESSION.adminToken),
    actorId: readValue(STORAGE_KEYS.actorId, DEFAULT_ADMIN_SESSION.actorId),
    actorRoles: normalizeRoles(readValue(STORAGE_KEYS.actorRoles, DEFAULT_ADMIN_SESSION.actorRoles.join(','))),
    serviceId,
    serviceScope: readValue(STORAGE_KEYS.serviceScope, serviceId),
    environment: readValue(STORAGE_KEYS.environment, DEFAULT_ADMIN_SESSION.environment),
  };
}

export function writeAdminSession(session: AdminSession) {
  const next = {
    ...session,
    actorRoles: normalizeRoles(session.actorRoles),
    serviceScope: session.serviceScope || session.serviceId,
  };
  const target = storage();
  if (!target) return;
  target.setItem(STORAGE_KEYS.adminToken, next.adminToken);
  target.setItem(STORAGE_KEYS.actorId, next.actorId);
  target.setItem(STORAGE_KEYS.actorRoles, next.actorRoles.join(','));
  target.setItem(STORAGE_KEYS.serviceId, next.serviceId);
  target.setItem(STORAGE_KEYS.serviceScope, next.serviceScope);
  target.setItem(STORAGE_KEYS.environment, next.environment);
  writeServiceOptions(readServiceOptions(next.serviceId).map((option) => option.value));
}

export function readServiceOptions(currentServiceId = readAdminSession().serviceId): ServiceOption[] {
  const stored = storage()?.getItem(STORAGE_KEYS.serviceOptions);
  const ids = uniqueServiceIds([
    currentServiceId,
    ...(stored ? stored.split(',') : []),
  ]);
  return ids.map((serviceId) => ({ label: serviceId, value: serviceId }));
}

export function writeServiceOptions(serviceIds: string[]) {
  storage()?.setItem(STORAGE_KEYS.serviceOptions, uniqueServiceIds(serviceIds).join(','));
}

export default function useAdminSessionModel() {
  const [session, setSessionState] = useState<AdminSession>(() => readAdminSession());
  const [serviceOptions, setServiceOptions] = useState<ServiceOption[]>(() =>
    readServiceOptions(session.serviceId),
  );

  const commitSession = useCallback((next: AdminSession) => {
    writeAdminSession(next);
    setSessionState(next);
    setServiceOptions(readServiceOptions(next.serviceId));
  }, []);

  const setServiceId = useCallback(
    (serviceId: string) => {
      const nextServiceId = serviceId.trim();
      if (!nextServiceId) return;
      commitSession({
        ...readAdminSession(),
        serviceId: nextServiceId,
        serviceScope: nextServiceId,
      });
    },
    [commitSession],
  );

  return {
    session,
    serviceOptions,
    setServiceId,
    updateSession: commitSession,
  };
}
