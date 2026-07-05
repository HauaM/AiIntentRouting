import { useModel } from '@umijs/max';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { AuditLogsTable } from '@/components/AuditLogsTable';
import { isAdminSessionReady } from '@/models/adminSession';

export default function AuditLogsPage() {
  const { session } = useModel('adminSession');
  const ready = isAdminSessionReady(session);

  return (
    <AdminShell title="Audit Logs">
      {ready ? <AuditLogsTable serviceId={session.serviceId} /> : <AdminSessionRequired />}
    </AdminShell>
  );
}
