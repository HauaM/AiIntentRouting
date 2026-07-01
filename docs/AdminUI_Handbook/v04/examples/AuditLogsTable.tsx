import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { Alert, Tag, Typography } from 'antd';
import { listAuditLogs } from './adminServices';

type AuditLogsTableProps = {
  serviceId: string;
};

export function AuditLogsTable({ serviceId }: AuditLogsTableProps) {
  const columns: ProColumns<API.AuditLog>[] = [
    { title: 'Time', dataIndex: 'created_at', valueType: 'dateTime', search: false, width: 168 },
    { title: 'Actor', dataIndex: 'actor_id', search: false, render: (_, row) => <Typography.Text code>{row.actor_id}</Typography.Text> },
    { title: 'Action', dataIndex: 'event_type', render: (_, row) => <Typography.Text code>{row.event_type}</Typography.Text> },
    { title: 'Target', dataIndex: 'target_id', search: false, ellipsis: true },
    { title: 'Trace', dataIndex: 'trace_id', ellipsis: true },
    { title: 'Result', search: false, width: 92, render: () => <Tag color="green">recorded</Tag> },
  ];

  return (
    <>
      <Alert
        type="info"
        showIcon
        message="Audit logs are append-only"
        description="Do not add edit, delete, export, approve, or reject controls to this Phase 0 table."
        style={{ marginBottom: 12 }}
      />
      <ProTable<API.AuditLog>
        rowKey={(row) => `${row.event_type}:${row.created_at}:${row.target_id}`}
        columns={columns}
        request={(params) => listAuditLogs(serviceId, params)}
        toolBarRender={() => false}
        pagination={{ pageSize: 20 }}
        search={{ labelWidth: 96 }}
        options={{ density: true, fullScreen: false, reload: true, setting: true }}
      />
    </>
  );
}

