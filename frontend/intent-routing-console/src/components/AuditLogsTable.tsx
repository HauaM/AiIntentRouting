import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { Alert, Empty, Tag, Typography } from 'antd';
import { listAuditLogs } from '@/services/adminServices';

type AuditLogsTableProps = {
  serviceId: string;
};

export function AuditLogsTable({ serviceId }: AuditLogsTableProps) {
  const columns: ProColumns<API.AuditLog>[] = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      search: false,
      width: 168,
    },
    {
      title: 'Actor',
      dataIndex: 'actor_id',
      search: false,
      render: (_, row) => <Typography.Text code>{row.actor_id}</Typography.Text>,
    },
    {
      title: 'Action',
      dataIndex: 'event_type',
      render: (_, row) => <Typography.Text code>{row.event_type}</Typography.Text>,
    },
    {
      title: 'Target',
      dataIndex: 'target_id',
      search: false,
      ellipsis: true,
      render: (_, row) => (
        <Typography.Text ellipsis={{ tooltip: row.target_id }}>{row.target_id}</Typography.Text>
      ),
    },
    { title: 'Trace', dataIndex: 'trace_id', ellipsis: true },
    {
      title: 'Result',
      search: false,
      width: 92,
      render: () => <Tag className="audit-result-recorded">recorded</Tag>,
    },
  ];

  return (
    <>
      <Alert
        type="info"
        showIcon
        message="Audit logs are append-only"
        description="Phase 0 does not expose edit, delete, export, approve, or reject controls."
        style={{ marginBottom: 12 }}
      />
      <ProTable<API.AuditLog>
        rowKey="audit_id"
        columns={columns}
        request={(params) => listAuditLogs(serviceId, params)}
        toolBarRender={() => []}
        pagination={false}
        locale={{
          emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No audit logs" />,
        }}
        search={{ labelWidth: 96 }}
        options={{ density: true, fullScreen: false, reload: true, setting: true }}
      />
    </>
  );
}
