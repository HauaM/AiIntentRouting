import { useModel } from '@umijs/max';
import { Space } from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';
import { RuntimeLogsTable } from '@/components/RuntimeLogsTable';
import { isAdminSessionReady } from '@/models/adminSession';

export default function RuntimeLogsPage() {
  const { session } = useModel('adminSession');
  const ready = isAdminSessionReady(session);

  return (
    <AdminShell title="Runtime Logs">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <FutureFeatureNotice
          compact
          title="Original text approval"
          backendRequirement="Phase 2 backend approval and audit contracts are required before this console can expose original request text."
        />
        {ready ? <RuntimeLogsTable serviceId={session.serviceId} /> : <AdminSessionRequired />}
      </Space>
    </AdminShell>
  );
}
