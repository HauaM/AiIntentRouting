import { Button, Select, Space, Tag, Tooltip, Typography } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { type AdminSession, type ServiceOption } from '@/models/adminSession';

type ServiceScopeBarProps = {
  session: AdminSession;
  roles: string[];
  serviceOptions: ServiceOption[];
  onServiceChange: (serviceId: string) => void;
  onLogout: () => Promise<void>;
};

export function ServiceScopeBar({
  session,
  roles,
  serviceOptions,
  onServiceChange,
  onLogout,
}: ServiceScopeBarProps) {
  const selectedService = session.services.find(
    (service) => service.service_id === session.serviceId,
  );

  return (
    <div className="service-scope-bar">
      <Space size={8} wrap>
        <Typography.Text type="secondary">Service</Typography.Text>
        <Select
          size="small"
          showSearch
          value={session.serviceId || undefined}
          options={serviceOptions}
          onChange={onServiceChange}
          placeholder="No accessible services"
          optionFilterProp="label"
          style={{ minWidth: 240 }}
        />
        {selectedService?.environment ? <Tag color="blue">{selectedService.environment}</Tag> : null}
        {selectedService?.status ? <Tag>{selectedService.status}</Tag> : null}
      </Space>
      <Space size={6} wrap>
        <Typography.Text code>{session.user?.email ?? session.user?.user_id}</Typography.Text>
        {roles.map((role) => (
          <Tag key={role}>{role}</Tag>
        ))}
        <Tooltip title="Log out">
          <Button
            aria-label="Log out"
            icon={<LogoutOutlined />}
            size="small"
            onClick={() => {
              void onLogout();
            }}
          />
        </Tooltip>
      </Space>
    </div>
  );
}
