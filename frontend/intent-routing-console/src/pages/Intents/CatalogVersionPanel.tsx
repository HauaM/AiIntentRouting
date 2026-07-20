import { MoreOutlined } from '@ant-design/icons';
import { Alert, Button, Descriptions, Dropdown, Space, Tag, Typography } from 'antd';
import type { CatalogPageState } from './catalogVersionTypes';

type CatalogVersionPanelProps = {
  state?: CatalogPageState;
  historyExists: boolean;
  canManage: boolean;
  onCreate: () => void;
  onOpenHistory: () => void;
  onCompareCurrent: () => void;
  onDeactivateCurrent: () => void;
};

const statusColor: Record<API.CatalogVersionStatus, string> = {
  active: 'success',
  inactive: 'default',
};

const formatCatalogDate = (value?: string | null) =>
  value ? new Date(value).toLocaleString('ko-KR') : '-';

export function CatalogVersionPanel({
  state,
  historyExists,
  canManage,
  onCreate,
  onOpenHistory,
  onCompareCurrent,
  onDeactivateCurrent,
}: CatalogVersionPanelProps) {
  if (!historyExists) return null;

  const version = state?.mode === 'draft' ? state.sourceVersion : state?.version;
  const isDraft = state?.mode === 'draft';
  const canDeactivate = Boolean(
    canManage && !isDraft && version && !version.released && version.release_count === 0,
  );

  return (
    <Alert
      type={isDraft ? 'warning' : 'info'}
      showIcon
      message={isDraft ? '버전 상태: 수정된 초안' : `버전 상태: ${version?.display_version ?? '확인 중'}`}
      description={
        <Descriptions size="small" column={4}>
          <Descriptions.Item label="Version">
            {version?.display_version ?? '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            {isDraft ? (
              <Tag color="warning">초안</Tag>
            ) : version ? (
              <Tag color={statusColor[version.status]}>{version.status}</Tag>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Release">
            {version ? (
              version.released || version.release_count > 0 ? (
                <Tag color="processing">released {version.release_count}</Tag>
              ) : (
                <Tag>unreleased</Tag>
              )
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Created">
            {formatCatalogDate(version?.created_at)}
          </Descriptions.Item>
          <Descriptions.Item label="Description" span={4}>
            <Typography.Text ellipsis>{version?.description ?? '-'}</Typography.Text>
          </Descriptions.Item>
        </Descriptions>
      }
      action={
        canManage ? (
          <Space size={4} wrap>
            <Button size="small" type="primary" onClick={onCreate}>
              Catalog 버전 등록
            </Button>
            <Button size="small" onClick={onOpenHistory}>
              Catalog version 불러오기
            </Button>
            <Button size="small" disabled={!version} onClick={onCompareCurrent}>
              비교
            </Button>
            {canDeactivate ? (
              <Dropdown
                menu={{
                  items: [{ key: 'deactivate', label: '비활성화', danger: true }],
                  onClick: ({ key }) => {
                    if (key === 'deactivate') onDeactivateCurrent();
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
        ) : undefined
      }
    />
  );
}
