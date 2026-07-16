import { useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { Drawer, Empty, Space, Tag, Typography } from 'antd';
import { AdminTableActions } from '@/components/AdminTableActions';
import { StatusTag } from '@/components/StatusTag';
import { fetchRuntimeLog, listRuntimeLogs } from '@/services/adminServices';

type RuntimeLogsTableProps = {
  serviceId: string;
};

const runtimeDecisionStatus = (decision?: string | null) =>
  decision === 'risk' ? 'risk' : decision ?? 'none';

export function RuntimeLogsTable({ serviceId }: RuntimeLogsTableProps) {
  const actionRef = useRef<ActionType>();
  const [selected, setSelected] = useState<API.RuntimeLog>();
  const [open, setOpen] = useState(false);

  const openTrace = async (traceId: string) => {
    const detail = await fetchRuntimeLog(serviceId, traceId);
    setSelected(detail);
    setOpen(true);
  };

  const columns: ProColumns<API.RuntimeLog>[] = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      search: false,
      width: 168,
    },
    {
      title: 'Trace',
      dataIndex: 'trace_id',
      copyable: true,
      ellipsis: true,
      render: (_, row) => <Typography.Text code>{row.trace_id}</Typography.Text>,
    },
    {
      title: 'Masked query',
      dataIndex: 'query_masked',
      search: false,
      render: (text) => <span className="masked-query">{text}</span>,
    },
    {
      title: 'Route',
      dataIndex: 'route_key',
      search: false,
      render: (_, row) => <Tag>{row.route_key ?? 'none'}</Tag>,
    },
    {
      title: 'Decision',
      dataIndex: 'decision',
      valueType: 'select',
      valueEnum: {
        confident: { text: 'confident' },
        clarify: { text: 'clarify' },
        fallback: { text: 'fallback' },
        off_topic: { text: 'off_topic' },
        risk: { text: 'risk' },
      },
      render: (_, row) => (
        <StatusTag status={runtimeDecisionStatus(row.decision)} />
      ),
    },
    {
      title: 'Latency',
      dataIndex: 'latency_ms',
      search: false,
      width: 96,
      renderText: (value) => `${value}ms`,
    },
  ];

  return (
    <>
      <ProTable<API.RuntimeLog>
        rowKey="trace_id"
        actionRef={actionRef}
        columns={columns}
        request={(params) => listRuntimeLogs(serviceId, params)}
        pagination={false}
        locale={{
          emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No recent runtime logs" />,
        }}
        search={{ labelWidth: 96 }}
        options={false}
        toolBarRender={() => [
          <AdminTableActions key="table-actions" onReload={() => actionRef.current?.reload()} />,
        ]}
        onRow={(row) => ({ onClick: () => openTrace(row.trace_id) })}
      />
      <Drawer title={selected?.trace_id} open={open} width={560} onClose={() => setOpen(false)}>
        {selected ? (
          <Space direction="vertical" size={10}>
            <Typography.Text>
              Decision{' '}
              <StatusTag status={runtimeDecisionStatus(selected.decision)} />
            </Typography.Text>
            <Typography.Text>Route {selected.route_key ?? 'none'}</Typography.Text>
            <Typography.Text>Masked query {selected.query_masked ?? 'none'}</Typography.Text>
          </Space>
        ) : null}
      </Drawer>
    </>
  );
}
