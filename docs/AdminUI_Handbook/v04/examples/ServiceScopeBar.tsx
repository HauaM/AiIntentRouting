import { Select, Space, Tag, Typography } from 'antd';

export type ServiceScopeBarProps = {
  serviceId: string;
  environment?: string;
  actorId: string;
  roles: string[];
  serviceOptions: { label: string; value: string }[];
  onServiceChange: (serviceId: string) => void;
};

export function ServiceScopeBar({
  serviceId,
  environment = 'prod',
  actorId,
  roles,
  serviceOptions,
  onServiceChange,
}: ServiceScopeBarProps) {
  return (
    <div
      style={{
        minHeight: 46,
        border: '1px solid #E6EAEF',
        borderRadius: 6,
        background: '#FFFFFF',
        padding: '8px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 12,
      }}
    >
      <Space size={8} wrap>
        <Typography.Text type="secondary">Service</Typography.Text>
        <Select
          size="small"
          value={serviceId}
          options={serviceOptions}
          onChange={onServiceChange}
          style={{ minWidth: 220 }}
        />
        <Tag color="blue">{environment}</Tag>
      </Space>
      <Space size={6} wrap>
        <Typography.Text code>{actorId}</Typography.Text>
        {roles.map((role) => (
          <Tag key={role}>{role}</Tag>
        ))}
      </Space>
    </div>
  );
}

