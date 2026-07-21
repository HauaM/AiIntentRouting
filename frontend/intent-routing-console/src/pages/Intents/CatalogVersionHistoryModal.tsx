import { MoreOutlined } from '@ant-design/icons';
import type { TableProps } from 'antd';
import { Button, Dropdown, Empty, Modal, Space, Table, Tag, Tooltip, Typography } from 'antd';
import { StatusTag } from '@/components/StatusTag';

type CatalogVersionHistoryModalProps = {
  open: boolean;
  rows: API.CatalogVersionListItem[];
  loading?: boolean;
  loadingToDraft?: boolean;
  selectedVersion?: API.CatalogVersionListItem;
  canManage: boolean;
  onCancel: () => void;
  onSelect: (version?: API.CatalogVersionListItem) => void;
  onLoadSelected: () => void;
  onCompare: (version: API.CatalogVersionListItem) => void;
  onLoadToDraft: (version: API.CatalogVersionListItem) => void;
  onDeactivate: (version: API.CatalogVersionListItem) => void;
};

const formatCatalogDate = (value?: string | null) =>
  value ? new Date(value).toLocaleString('ko-KR') : '-';

export function CatalogVersionHistoryModal({
  open,
  rows,
  loading = false,
  loadingToDraft = false,
  selectedVersion,
  canManage,
  onCancel,
  onSelect,
  onLoadSelected,
  onCompare,
  onLoadToDraft,
  onDeactivate,
}: CatalogVersionHistoryModalProps) {
  const columns: TableProps<API.CatalogVersionListItem>['columns'] = [
    {
      title: '버전',
      dataIndex: 'display_version',
      width: 104,
      render: (_, row) => (
        <Tooltip title={row.intent_catalog_version}>
          <Typography.Text strong>{row.display_version}</Typography.Text>
        </Tooltip>
      ),
    },
    {
      title: '설명',
      dataIndex: 'description',
      width: 260,
      render: (value: string) => (
        <Tooltip title={value}>
          <Typography.Text ellipsis style={{ display: 'block', whiteSpace: 'nowrap' }}>
            {value || '-'}
          </Typography.Text>
        </Tooltip>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status',
      width: 96,
      render: (value: API.CatalogVersionStatus) => (
        <StatusTag status={value} label={value} />
      ),
    },
    {
      title: 'Release',
      dataIndex: 'release_count',
      width: 120,
      render: (_, row) =>
        row.released || row.release_count > 0 ? (
          <StatusTag status="released" label={`released ${row.release_count}`} />
        ) : (
          <Tag>unreleased</Tag>
        ),
    },
    { title: 'Intent', dataIndex: 'intent_count', width: 96 },
    { title: 'Example', dataIndex: 'example_count', width: 104 },
    { title: 'Embedding', dataIndex: 'embedding_count', width: 112 },
    {
      title: '생성 일시',
      dataIndex: 'created_at',
      width: 168,
      render: (value: string) => formatCatalogDate(value),
    },
  ];

  columns.push({
    title: '작업',
    key: 'actions',
    width: 220,
    fixed: 'right',
    render: (_, row) => (
      <Space size={8} className="table-action-cell" style={{ whiteSpace: 'nowrap' }}>
        <Button type="link" size="small" onClick={() => onCompare(row)}>
          비교
        </Button>
        {canManage ? (
          <Button type="link" size="small" onClick={() => onLoadToDraft(row)}>
            draft로 불러오기
          </Button>
        ) : null}
        {canManage ? (
          <Dropdown
            menu={{
              items: [
                {
                  key: 'deactivate',
                  label: '비활성화',
                  danger: true,
                  disabled:
                    row.status !== 'active' || row.released || row.release_count > 0,
                },
              ],
              onClick: ({ key }) => {
                if (key === 'deactivate') onDeactivate(row);
              },
            }}
            trigger={['click']}
          >
            <Button
              aria-label="Catalog 버전 작업 더보기"
              icon={<MoreOutlined />}
              size="small"
              type="text"
            />
          </Dropdown>
        ) : null}
      </Space>
    ),
  });

  return (
    <Modal
      title="Catalog version 불러오기"
      open={open}
      width={1320}
      centered
      okText="선택한 버전 불러오기"
      cancelText="취소"
      okButtonProps={{ disabled: !selectedVersion || !canManage }}
      confirmLoading={loadingToDraft}
      onOk={onLoadSelected}
      onCancel={onCancel}
    >
      <Table<API.CatalogVersionListItem>
        rowKey="intent_catalog_version"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={rows}
        pagination={false}
        scroll={{ x: 1280, y: 360 }}
        rowSelection={
          canManage
            ? {
                type: 'radio',
                selectedRowKeys: selectedVersion
                  ? [selectedVersion.intent_catalog_version]
                  : [],
                onChange: (_, selectedRows) => onSelect(selectedRows[0]),
              }
            : undefined
        }
        onRow={(row) => ({ onClick: () => onSelect(row) })}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="불러올 Catalog version이 없습니다."
            />
          ),
        }}
      />
    </Modal>
  );
}
