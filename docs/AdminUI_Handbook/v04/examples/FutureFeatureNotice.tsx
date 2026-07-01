import { Alert, Button, Space, Tag } from 'antd';

type FutureFeatureNoticeProps = {
  title: string;
  backendRequirement: string;
  phase?: 'Phase 2' | 'Future';
};

export function FutureFeatureNotice({
  title,
  backendRequirement,
  phase = 'Phase 2',
}: FutureFeatureNoticeProps) {
  return (
    <Alert
      type="info"
      showIcon
      message={
        <Space size={8}>
          <span>{title}</span>
          <Tag>{phase}</Tag>
        </Space>
      }
      description={backendRequirement}
      action={<Button disabled>사용 불가</Button>}
    />
  );
}
