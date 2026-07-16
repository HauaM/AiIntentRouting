import { ReloadOutlined } from '@ant-design/icons';
import { Button, Space } from 'antd';
import type { ReactNode } from 'react';

export function AdminTableActions({
  onReload,
  reloadDisabled,
  extra,
}: {
  onReload?: () => void;
  reloadDisabled?: boolean;
  extra?: ReactNode;
}) {
  return (
    <Space size={8} wrap>
      {onReload ? (
        <Button icon={<ReloadOutlined />} disabled={reloadDisabled} onClick={onReload}>
          새로고침
        </Button>
      ) : null}
      {extra}
    </Space>
  );
}
