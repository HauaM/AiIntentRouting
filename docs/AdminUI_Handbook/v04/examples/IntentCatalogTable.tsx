import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { Button, Space, Tag } from 'antd';
import { useRef } from 'react';
import { ConfirmActionButton } from './ConfirmActionButton';
import { listIntents } from './adminServices';

const statusColor: Record<string, string> = {
  active: 'green',
  draft: 'orange',
  deprecated: 'default',
};

type IntentCatalogTableProps = {
  serviceId: string;
  canEditCatalog: boolean;
  onSelectIntent: (intent: API.Intent) => void;
  onCreateIntent?: () => void;
  onEditIntent?: (intent: API.Intent) => void;
  onDeleteIntent?: (intent: API.Intent) => Promise<void>;
};

export function IntentCatalogTable({
  serviceId,
  canEditCatalog,
  onSelectIntent,
  onCreateIntent,
  onEditIntent,
  onDeleteIntent,
}: IntentCatalogTableProps) {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns<API.Intent>[] = [
    {
      title: 'Intent',
      dataIndex: 'intent_id',
      copyable: true,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span className="text-mono">{row.intent_id}</span>
          <span style={{ color: '#64748B', fontSize: 12 }}>{row.display_name}</span>
        </Space>
      ),
    },
    { title: 'Route', dataIndex: 'route_key', render: (_, row) => <Tag>{row.route_key}</Tag> },
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
      width: 176,
      render: (_, row) => [
        <Button key="detail" type="link" size="small" onClick={() => onSelectIntent(row)}>
          상세
        </Button>,
        canEditCatalog ? (
          <Button key="edit" type="link" size="small" onClick={() => onEditIntent?.(row)}>
            편집
          </Button>
        ) : null,
        canEditCatalog ? (
          <ConfirmActionButton
            key="delete"
            danger
            type="link"
            size="small"
            title="Intent 삭제"
            content={`${row.intent_id} Intent와 연결된 Example/embedding을 삭제합니다.`}
            okText="삭제"
            onConfirm={() => onDeleteIntent?.(row) ?? Promise.resolve()}
          >
            삭제
          </ConfirmActionButton>
        ) : null,
      ],
    },
  ];

  return (
    <ProTable<API.Intent>
      rowKey="intent_id"
      actionRef={actionRef}
      columns={columns}
      request={(params) => listIntents(serviceId, params)}
      pagination={{ pageSize: 20 }}
      search={{ labelWidth: 96 }}
      options={{ density: true, fullScreen: false, reload: true, setting: true }}
      toolBarRender={() =>
        canEditCatalog
          ? [
              <Button key="create" type="primary" onClick={onCreateIntent}>
                Intent 추가
              </Button>,
            ]
          : []
      }
    />
  );
}
