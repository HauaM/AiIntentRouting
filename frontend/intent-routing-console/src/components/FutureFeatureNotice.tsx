import { Alert, Button, Space, Tag } from 'antd';

type FutureFeatureNoticeProps = {
  title: string;
  backendRequirement: string;
  phase?: 'Phase 2' | 'Future';
  compact?: boolean;
};

export function FutureFeatureNotice({
  title,
  backendRequirement,
  phase = 'Phase 2',
  compact = false,
}: FutureFeatureNoticeProps) {
  return (
    <Alert
      className={compact ? 'future-feature-notice-compact' : undefined}
      type="info"
      showIcon
      message={
        <Space size={8}>
          <span>{title}</span>
          <Tag>{phase}</Tag>
        </Space>
      }
      description={backendRequirement}
      action={<Button disabled size={compact ? 'small' : 'middle'}>사용 불가</Button>}
    />
  );
}
