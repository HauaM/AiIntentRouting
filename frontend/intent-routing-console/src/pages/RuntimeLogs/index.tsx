import { useState } from 'react';
import { useModel } from '@umijs/max';
import { Select, Space } from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';
import { RuntimeLogsTable } from '@/components/RuntimeLogsTable';
import { isAdminSessionReady } from '@/models/adminSession';

const environmentOptions = [
  { label: '전체', value: '' },
  { label: 'dev', value: 'dev' },
  { label: 'qa', value: 'qa' },
  { label: 'prod', value: 'prod' },
];

export default function RuntimeLogsPage() {
  const { session } = useModel('adminSession');
  const [selectedEnvironment, setSelectedEnvironment] =
    useState<'dev' | 'qa' | 'prod' | ''>('');
  const ready = isAdminSessionReady(session);

  return (
    <AdminShell title="Runtime Logs">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <FutureFeatureNotice
          compact
          title="Original text approval"
          backendRequirement="Phase 2 backend approval and audit contracts are required before this console can expose original request text."
        />
        {ready ? (
          <>
            <Select
              aria-label="Environment"
              value={selectedEnvironment}
              options={environmentOptions}
              onChange={setSelectedEnvironment}
              style={{ width: 180 }}
            />
            <RuntimeLogsTable
              serviceId={session.serviceId}
              environment={selectedEnvironment || undefined}
            />
          </>
        ) : <AdminSessionRequired />}
      </Space>
    </AdminShell>
  );
}
