import { useMemo, useState } from 'react';
import { history, useModel } from '@umijs/max';
import type { TableProps } from 'antd';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import {
  canCreateServices,
  canManageServiceMembers,
  canSelectServiceFromScope,
  canUseServicesPage,
} from '@/models/adminSession';
import { createService } from '@/services/adminServices';
import {
  serviceFormInitialValues,
  toServiceCreateRequest,
  type ServiceFormValues,
} from './serviceForm';
import { ServiceMembershipPanel } from './ServiceMembershipPanel';

const serviceIdPattern = /^[a-z][a-z0-9_-]{1,62}$/;

const serviceHelp = {
  serviceId:
    '고정 Service ID입니다. 소문자, 숫자, 하이픈, 언더스코어만 사용합니다. 예: it-helpdesk',
  displayName: '운영자가 화면에서 알아보기 쉬운 서비스 이름입니다.',
  environment: '이 Service가 사용할 환경입니다. Release와 API key environment 기준이 됩니다.',
  preset:
    '개발자가 숫자 threshold를 직접 다루지 않도록 제공하는 기본 분류 기준입니다.',
  maxInputTokens: 'runtime API가 받을 사용자 질의의 최대 token 수입니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

const environmentOptions = [
  { label: 'dev', value: 'dev' },
  { label: 'test', value: 'test' },
  { label: 'stage', value: 'stage' },
  { label: 'staging', value: 'staging' },
  { label: 'prod', value: 'prod' },
];

const presetOptions = [
  { label: 'strict', value: 'strict' },
  { label: 'balanced', value: 'balanced' },
  { label: 'exploratory', value: 'exploratory' },
];

export default function ServicesPage() {
  const { session, restoreSession, setServiceId } = useModel('adminSession');
  const [form] = Form.useForm<ServiceFormValues>();
  const [creating, setCreating] = useState(false);
  const [createdService, setCreatedService] = useState<API.Service>();
  const ready = canUseServicesPage(session);
  const canCreate = canCreateServices(session);
  const canManageMembers = canManageServiceMembers(session);

  const selectedService = session.services.find(
    (service) => service.service_id === session.serviceId,
  );

  const columns = useMemo<TableProps<API.AccessibleService>['columns']>(
    () => [
      {
        title: 'Service',
        dataIndex: 'service_id',
        render: (_, row) => (
          <Space direction="vertical" size={0}>
            <Typography.Text code>{row.service_id}</Typography.Text>
            <Typography.Text type="secondary">{row.display_name}</Typography.Text>
          </Space>
        ),
      },
      {
        title: 'Environment',
        dataIndex: 'environment',
        width: 128,
        render: (_, row) => <Tag color="blue">{row.environment}</Tag>,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        width: 112,
        render: (_, row) => (
          <Tag color={row.status === 'active' ? 'green' : 'default'}>{row.status}</Tag>
        ),
      },
      {
        title: 'Roles',
        dataIndex: 'roles',
        render: (_, row) => (
          <Space wrap size={4}>
            {row.roles.map((role) => (
              <Tag key={`${row.service_id}:${role}`}>{role}</Tag>
            ))}
          </Space>
        ),
      },
      {
        title: '',
        width: 112,
        render: (_, row) => (
          <Button
            type="link"
            size="small"
            onClick={() => {
              setServiceId(row.service_id);
            }}
          >
            선택
          </Button>
        ),
      },
    ],
    [setServiceId],
  );

  const handleCreate = async (values: ServiceFormValues) => {
    setCreating(true);
    try {
      const created = await createService(toServiceCreateRequest(values));
      const restoredSession = await restoreSession();
      if (!canSelectServiceFromScope(restoredSession, created.service_id)) {
        setCreatedService(undefined);
        message.warning(
          'Service는 등록되었지만 아직 접근 가능한 Service scope에 포함되지 않았습니다.',
        );
        return;
      }
      setServiceId(created.service_id);
      setCreatedService(created);
      message.success('Service가 등록되었습니다.');
      form.resetFields();
      form.setFieldsValue(serviceFormInitialValues);
    } finally {
      setCreating(false);
    }
  };

  return (
    <AdminShell title="Services">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {ready ? (
          <>
            <Alert
              type="info"
              showIcon
              message="C-1 Service onboarding"
              description="Service 등록은 권한 우선 온보딩의 첫 단계입니다. 이후 C-2에서 서비스별 사용자 권한 부여 흐름이 연결됩니다."
            />
            {selectedService ? (
              <>
                <Card title="Selected Service">
                  <Descriptions bordered size="small" column={{ xs: 1, md: 3 }}>
                    <Descriptions.Item label="Service ID">
                      <Typography.Text code>{selectedService.service_id}</Typography.Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="Display name">
                      {selectedService.display_name}
                    </Descriptions.Item>
                    <Descriptions.Item label="Environment">
                      <Tag color="blue">{selectedService.environment}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Status">
                      <Tag color={selectedService.status === 'active' ? 'green' : 'default'}>
                        {selectedService.status}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Roles">
                      <Space wrap size={4}>
                        {selectedService.roles.map((role) => (
                          <Tag key={`${selectedService.service_id}:${role}`}>{role}</Tag>
                        ))}
                      </Space>
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
                <ServiceMembershipPanel
                  selectedService={selectedService}
                  canManage={canManageMembers}
                  onMembershipChanged={restoreSession}
                />
              </>
            ) : null}
            {canCreate ? (
              <Card title="Create Service">
                <Form<ServiceFormValues>
                  form={form}
                  layout="vertical"
                  requiredMark={false}
                  initialValues={serviceFormInitialValues}
                  onFinish={handleCreate}
                >
                  <Space wrap align="start" size={12}>
                    <Form.Item
                      name="service_id"
                      label={helpLabel('Service ID', serviceHelp.serviceId)}
                      rules={[
                        { required: true, whitespace: true, message: 'Service ID를 입력하세요.' },
                        {
                          pattern: serviceIdPattern,
                          message:
                            'Service ID는 소문자로 시작하고 소문자, 숫자, 하이픈, 언더스코어만 사용할 수 있습니다.',
                        },
                      ]}
                    >
                      <Input placeholder="it-helpdesk" style={{ width: 240 }} />
                    </Form.Item>
                    <Form.Item
                      name="display_name"
                      label={helpLabel('Display name', serviceHelp.displayName)}
                      rules={[
                        { required: true, whitespace: true, message: 'Display name을 입력하세요.' },
                      ]}
                    >
                      <Input placeholder="IT Helpdesk" style={{ width: 260 }} />
                    </Form.Item>
                    <Form.Item
                      name="environment"
                      label={helpLabel('Environment', serviceHelp.environment)}
                      rules={[
                        { required: true, whitespace: true, message: 'Environment를 선택하세요.' },
                      ]}
                    >
                      <Select
                        showSearch
                        options={environmentOptions}
                        style={{ width: 160 }}
                      />
                    </Form.Item>
                    <Form.Item
                      name="default_threshold_preset"
                      label={helpLabel('Default preset', serviceHelp.preset)}
                      rules={[{ required: true, message: 'Preset을 선택하세요.' }]}
                    >
                      <Select options={presetOptions} style={{ width: 180 }} />
                    </Form.Item>
                    <Form.Item
                      name="max_input_tokens"
                      label={helpLabel('Max input tokens', serviceHelp.maxInputTokens)}
                      rules={[{ required: true, message: 'Token limit을 입력하세요.' }]}
                    >
                      <InputNumber min={1} max={8192} style={{ width: 180 }} />
                    </Form.Item>
                  </Space>
                  <Button type="primary" htmlType="submit" loading={creating}>
                    Service 등록
                  </Button>
                </Form>
              </Card>
            ) : (
              <Alert
                type="info"
                showIcon
                message="Service creation requires system_admin"
                description="현재 계정은 접근 가능한 Service를 볼 수 있지만 신규 Service를 등록할 수 없습니다."
              />
            )}
            {createdService ? (
              <Alert
                type="success"
                showIcon
                message="Service onboarding started"
                description={
                  <Space direction="vertical" size={8}>
                    <Typography.Text>
                      {createdService.display_name} Service가 등록되었고 현재 Service scope로 선택되었습니다.
                    </Typography.Text>
                    <Button type="primary" onClick={() => history.push('/intents')}>
                      Intent Catalog로 이동
                    </Button>
                  </Space>
                }
              />
            ) : null}
            <Card title="Accessible Services">
              <Table<API.AccessibleService>
                rowKey="service_id"
                size="small"
                pagination={false}
                dataSource={session.services}
                columns={columns}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="No accessible services"
                    />
                  ),
                }}
              />
            </Card>
          </>
        ) : (
          <AdminSessionRequired />
        )}
      </Space>
    </AdminShell>
  );
}
