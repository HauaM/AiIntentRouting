import { useRef } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { Button, Space, Tag } from 'antd';
import { listIntents } from '@/services/adminServices';

const statusColor: Record<string, string> = {
  active: 'green',
  draft: 'orange',
  deprecated: 'default',
};

type IntentCatalogTableProps = {
  serviceId: string;
  onSelectIntent: (intent: API.Intent) => void;
};

export function IntentCatalogTable({ serviceId, onSelectIntent }: IntentCatalogTableProps) {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<API.Intent>[] = [
    {
      title: 'Intent',
      dataIndex: 'intent_id',
      copyable: true,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span className="text-mono">{row.intent_id}</span>
          <span className="muted-small">{row.display_name}</span>
        </Space>
      ),
    },
    {
      title: 'Route',
      dataIndex: 'route_key',
      render: (_, row) => <Tag>{row.route_key}</Tag>,
    },
    {
      title: 'Keywords',
      search: false,
      width: 110,
      render: (_, row) => `${row.include_keywords?.length ?? 0}/${row.exclude_keywords?.length ?? 0}`,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      valueType: 'select',
      valueEnum: {
        active: { text: 'Active' },
        draft: { text: 'Draft' },
        deprecated: { text: 'Deprecated' },
      },
      render: (_, row) => <Tag color={statusColor[row.status] ?? 'default'}>{row.status}</Tag>,
    },
    {
      title: '',
      valueType: 'option',
      width: 88,
      render: (_, row) => [
        <Button key="detail" type="link" size="small" onClick={() => onSelectIntent(row)}>
          상세
        </Button>,
      ],
    },
  ];

  return (
    <ProTable<API.Intent>
      rowKey="intent_id"
      actionRef={actionRef}
      columns={columns}
      request={(params) => listIntents(serviceId, params)}
      pagination={false}
      search={{ labelWidth: 96 }}
      options={{ density: true, fullScreen: false, reload: true, setting: true }}
      toolBarRender={() => []}
    />
  );
}
