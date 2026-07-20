import { useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { Button, Input, Select, Space, Typography } from 'antd';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import { StatusTag } from '@/components/StatusTag';
import { listIntents } from '@/services/adminServices';

type IntentCatalogTableProps = {
  serviceId: string;
  canEditCatalog: boolean;
  onSelectIntent: (intent: API.Intent) => void;
  onCreateIntent: () => void;
  onEditIntent: (intent: API.Intent) => void;
  onDeleteIntent: (intent: API.Intent) => Promise<void>;
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
  const [searchInput, setSearchInput] = useState('');
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState<string>();
  const [resultCount, setResultCount] = useState(0);

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
      title: 'Route key',
      dataIndex: 'route_key',
      copyable: true,
      ellipsis: true,
      render: (_, row) => (
        <span className="text-mono admin-ellipsis-cell" title={row.route_key}>
          {row.route_key}
        </span>
      ),
    },
    {
      title: 'Keywords',
      search: false,
      width: 160,
      render: (_, row) =>
        `포함 ${row.include_keywords?.length ?? 0} · 제외 ${row.exclude_keywords?.length ?? 0}`,
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
      render: (_, row) => <StatusTag status={row.status} />,
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
          <Button key="edit" type="link" size="small" onClick={() => onEditIntent(row)}>
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
            onConfirm={() => onDeleteIntent(row)}
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
      params={{ keyword, status }}
      request={async (params) => {
        const result = await listIntents(serviceId, params);
        setResultCount(result.total);
        return result;
      }}
      pagination={false}
      search={false}
      scroll={{ x: 860 }}
      options={{ density: true, fullScreen: false, reload: true, setting: true }}
      toolbar={{
        filter: (
          <div className="intent-catalog-toolbar">
            <Input.Search
              allowClear
              className="intent-catalog-search"
              placeholder="Intent ID 또는 이름 검색"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              onSearch={(value) => setKeyword(value.trim())}
            />
            <Select
              allowClear
              className="intent-catalog-status-filter"
              placeholder="전체 상태"
              value={status}
              options={[
                { label: 'Active', value: 'active' },
                { label: 'Draft', value: 'draft' },
                { label: 'Deprecated', value: 'deprecated' },
              ]}
              onChange={setStatus}
            />
            <Typography.Text type="secondary">{resultCount}개 Intent</Typography.Text>
          </div>
        ),
      }}
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
