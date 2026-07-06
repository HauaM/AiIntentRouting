import { Button, Space, Typography } from 'antd';
import type { ReactNode } from 'react';

type WorkflowNextActionBarProps = {
  title: string;
  description?: ReactNode;
  primaryLabel: string;
  onPrimary: () => void;
  disabled?: boolean;
};

export function WorkflowNextActionBar({
  title,
  description,
  primaryLabel,
  onPrimary,
  disabled,
}: WorkflowNextActionBarProps) {
  return (
    <Space
      className="workflow-next-action-bar"
      align="center"
      style={{ justifyContent: 'space-between', width: '100%' }}
    >
      <Space direction="vertical" size={0}>
        <Typography.Text strong>{title}</Typography.Text>
        {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
      </Space>
      <Button type="primary" onClick={onPrimary} disabled={disabled}>
        {primaryLabel}
      </Button>
    </Space>
  );
}
