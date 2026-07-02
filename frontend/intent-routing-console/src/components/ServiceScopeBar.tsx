import { useEffect, useState } from 'react';
import { Button, Drawer, Form, Input, Select, Space, Tag, Tooltip, Typography } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import {
  type AdminSession,
  type ServiceOption,
  normalizeEnvironment,
  normalizeRoles,
} from '@/models/adminSession';

type ServiceScopeBarProps = {
  session: AdminSession;
  serviceOptions: ServiceOption[];
  onServiceChange: (serviceId: string) => void;
  onSessionSave: (session: AdminSession) => void;
};

type SessionFormValues = {
  serviceId: string;
  environment: string;
  adminToken: string;
  actorId: string;
  actorRoles: string;
};

export function ServiceScopeBar({
  session,
  serviceOptions,
  onServiceChange,
  onSessionSave,
}: ServiceScopeBarProps) {
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<SessionFormValues>();

  useEffect(() => {
    if (!open) return;
    form.setFieldsValue({
      serviceId: session.serviceId,
      environment: session.environment,
      adminToken: session.adminToken,
      actorId: session.actorId,
      actorRoles: session.actorRoles.join(','),
    });
  }, [form, open, session]);

  const saveSession = (values: SessionFormValues) => {
    const serviceId = values.serviceId.trim();
    const roles = normalizeRoles(values.actorRoles);
    onSessionSave({
      adminToken: values.adminToken.trim(),
      actorId: values.actorId.trim(),
      actorRoles: roles,
      serviceId,
      serviceScope: serviceId,
      environment: normalizeEnvironment(values.environment),
    });
    setOpen(false);
  };

  return (
    <>
      <div className="service-scope-bar">
        <Space size={8} wrap>
          <Typography.Text type="secondary">Service</Typography.Text>
          <Select
            size="small"
            showSearch
            value={session.serviceId}
            options={serviceOptions}
            onChange={onServiceChange}
            style={{ minWidth: 240 }}
          />
          <Tag color="blue">{session.environment}</Tag>
        </Space>
        <Space size={6} wrap>
          <Typography.Text code>{session.actorId}</Typography.Text>
          {session.actorRoles.map((role) => (
            <Tag key={role}>{role}</Tag>
          ))}
          <Tooltip title="Admin API session headers">
            <Button
              aria-label="Admin API session headers"
              icon={<SettingOutlined />}
              size="small"
              onClick={() => setOpen(true)}
            />
          </Tooltip>
        </Space>
      </div>
      <Drawer
        title="Admin API session"
        open={open}
        width={420}
        onClose={() => setOpen(false)}
        destroyOnClose
      >
        <Form<SessionFormValues>
          form={form}
          layout="vertical"
          onFinish={saveSession}
          requiredMark={false}
        >
          <Form.Item
            label="Service ID"
            name="serviceId"
            rules={[{ required: true, message: 'Service ID is required.' }]}
          >
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item label="Environment" name="environment">
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item label="Admin token" name="adminToken">
            <Input.Password autoComplete="off" />
          </Form.Item>
          <Form.Item
            label="Actor ID"
            name="actorId"
            rules={[{ required: true, message: 'Actor ID is required.' }]}
          >
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item
            label="Actor roles"
            name="actorRoles"
            rules={[{ required: true, message: 'Actor roles are required.' }]}
          >
            <Input autoComplete="off" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              저장
            </Button>
            <Button onClick={() => setOpen(false)}>취소</Button>
          </Space>
        </Form>
      </Drawer>
    </>
  );
}
