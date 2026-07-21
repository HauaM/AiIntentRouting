import { useEffect, useMemo, useState } from 'react';
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
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
  notification,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { StatusTag } from '@/components/StatusTag';
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
  maxInputTokens: 'runtime API가 받을 사용자 질의의 최대 token 수입니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

export default function ServicesPage() {
  const { session, restoreSession, setServiceId } = useModel('adminSession');
  const [form] = Form.useForm<ServiceFormValues>();
  const [notificationApi, notificationContextHolder] = notification.useNotification();
  const [creating, setCreating] = useState(false);
  const [createdServiceNotification, setCreatedServiceNotification] =
    useState<API.Service>();
  const ready = canUseServicesPage(session);
  const canCreate = canCreateServices(session);
  const canManageMembers = canManageServiceMembers(session);

  const selectedService = session.services.find(
    (service) => service.service_id === session.serviceId,
  );

  useEffect(() => {
    if (!createdServiceNotification) return;

    notificationApi.success({
      message: 'Service 등록 완료',
      description: `${createdServiceNotification.display_name} Service가 등록되고 현재 Service scope로 선택되었습니다.`,
      duration: 6,
      actions: (
        <Button type="primary" size="small" onClick={() => history.push('/intents')}>
          Intent Catalog로 이동
        </Button>
      ),
    });
    setCreatedServiceNotification(undefined);
  }, [createdServiceNotification, notificationApi]);

  const columns = useMemo<TableProps<API.AccessibleService>['columns']>(
    () => [
      {
        title: 'Service',
        dataIndex: 'service_id',
        width: 260,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Tooltip title={row.display_name || row.service_id}>
            <Typography.Text code copyable ellipsis style={{ maxWidth: 220 }}>
              {row.service_id}
            </Typography.Text>
          </Tooltip>
        ),
      },
      {
        title: '상태',
        dataIndex: 'status',
        width: 112,
        className: 'admin-nowrap-cell',
        render: (_, row) => <StatusTag status={row.status} />,
      },
      {
        title: '역할',
        dataIndex: 'roles',
        width: 240,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Space size={4} className="admin-nowrap-cell">
            {row.roles.map((role) => (
              <Tag key={`${row.service_id}:${role}`}>{role}</Tag>
            ))}
          </Space>
        ),
      },
      {
        title: '',
        width: 96,
        className: 'admin-nowrap-cell',
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
        message.warning(
          'Service는 등록되었지만 아직 접근 가능한 Service scope에 포함되지 않았습니다.',
        );
        return;
      }
      setServiceId(created.service_id);
      setCreatedServiceNotification(created);
      form.resetFields();
      form.setFieldsValue(serviceFormInitialValues);
    } finally {
      setCreating(false);
    }
  };

  return (
    <AdminShell title="Services" notificationHolder={notificationContextHolder}>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {ready ? (
          <>
            <Alert
              type="info"
              showIcon
              message="Service 온보딩"
              description="C-1 Service 등록 후 C-2 권한 구성과 C-3 runtime 연동 준비를 순서대로 진행합니다."
            />
            {selectedService ? (
              <>
                <Card title="선택한 Service">
                  <Descriptions bordered size="small" column={{ xs: 1, lg: 2 }}>
                    <Descriptions.Item label="Service ID">
                      <Tooltip title={selectedService.service_id}>
                        <Typography.Text
                          code
                          copyable
                          ellipsis
                          className="services-selected-id"
                        >
                          {selectedService.service_id}
                        </Typography.Text>
                      </Tooltip>
                    </Descriptions.Item>
                    <Descriptions.Item label="표시 이름">
                      {selectedService.display_name}
                    </Descriptions.Item>
                    <Descriptions.Item label="상태">
                      <StatusTag status={selectedService.status} />
                    </Descriptions.Item>
                    <Descriptions.Item label="내 역할" span={2}>
                      <Space wrap size={4}>
                        {selectedService.roles.map((role) => (
                          <Tag key={`${selectedService.service_id}:${role}`}>{role}</Tag>
                        ))}
                      </Space>
                    </Descriptions.Item>
                  </Descriptions>
                  <div
                    className="services-onboarding-progress"
                    aria-label="Service 온보딩 진행 상태"
                  >
                    <div className="services-onboarding-step services-onboarding-step-complete">
                      <Typography.Text strong>C-1 · 등록 완료</Typography.Text>
                      <Typography.Text type="secondary">
                        Service가 현재 scope에 포함되었습니다.
                      </Typography.Text>
                    </div>
                    <div className="services-onboarding-step services-onboarding-step-current">
                      <Typography.Text strong>C-2 · 권한 구성</Typography.Text>
                      <Typography.Text type="secondary">
                        멤버와 Service 역할을 확인합니다.
                      </Typography.Text>
                    </div>
                    <div className="services-onboarding-step">
                      <Typography.Text strong>C-3 · 연동 준비</Typography.Text>
                      <Typography.Text type="secondary">
                        API Key와 runtime 상태는 해당 화면에서 확인합니다.
                      </Typography.Text>
                    </div>
                  </div>
                </Card>
                <ServiceMembershipPanel
                  selectedService={selectedService}
                  canManage={canManageMembers}
                  onMembershipChanged={restoreSession}
                />
              </>
            ) : null}
            {canCreate ? (
              <Card title="Service 등록">
                <Form<ServiceFormValues>
                  form={form}
                  layout="vertical"
                  requiredMark={false}
                  initialValues={serviceFormInitialValues}
                  onFinish={handleCreate}
                >
                  <div className="services-create-grid">
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
                      <Input placeholder="it-helpdesk" style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item
                      name="display_name"
                      label={helpLabel('표시 이름', serviceHelp.displayName)}
                      rules={[
                        { required: true, whitespace: true, message: 'Display name을 입력하세요.' },
                      ]}
                    >
                      <Input placeholder="IT Helpdesk" style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item
                      name="max_input_tokens"
                      label={helpLabel('최대 입력 token', serviceHelp.maxInputTokens)}
                      rules={[{ required: true, message: 'Token limit을 입력하세요.' }]}
                    >
                      <InputNumber min={1} max={8192} style={{ width: '100%' }} />
                    </Form.Item>
                  </div>
                  <Button type="primary" htmlType="submit" loading={creating}>
                    Service 등록
                  </Button>
                </Form>
              </Card>
            ) : (
              <Alert
                type="info"
                showIcon
                message="Service 등록에는 system_admin 권한이 필요합니다"
                description="현재 계정은 접근 가능한 Service를 볼 수 있지만 신규 Service를 등록할 수 없습니다."
              />
            )}
            <Card title="접근 가능한 Services">
              <Table<API.AccessibleService>
                className="admin-scroll-table"
                rowKey="service_id"
                size="small"
                pagination={false}
                dataSource={session.services}
                columns={columns}
                scroll={{ x: 760 }}
                tableLayout="fixed"
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="접근 가능한 Service가 없습니다."
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
