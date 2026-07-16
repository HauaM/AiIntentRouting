import { useEffect, useRef, useState } from 'react';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { AdminTableActions } from '@/components/AdminTableActions';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { IntentRouteMultiSelect } from '@/components/IntentRouteMultiSelect';
import { StatusTag } from '@/components/StatusTag';
import { canManageRuntimeSetup, isAdminSessionReady } from '@/models/adminSession';
import {
  createServiceApiKey,
  fetchRuntimeSetupGuidance,
  listIntentRouteCandidates,
  listServiceApiKeys,
  revokeServiceApiKey,
} from '@/services/adminServices';
import {
  runtimeSetupBodyTemplateText,
  runtimeSetupHeaderRows,
  runtimeSetupSelectedKeyLabel,
} from './runtimeSetup';

type ApiKeyFormValues = {
  environment: string;
  app_id: string;
  allowed_intents?: string[];
  allowed_route_keys?: string[];
  expires_in_days: number;
};

const apiKeyHelp = {
  environment: '선택한 서비스의 environment를 자동 사용합니다.',
  appId: '이 key를 사용할 호출 앱/클라이언트 이름입니다. 예: checkout-web, helpdesk-bot',
  expiresInDays: 'Key 만료까지의 일수입니다.',
  allowedIntents:
    '선택 항목입니다. 특정 intent_id만 허용하려면 입력합니다. 비워두면 intent_id 제한 목록을 만들지 않습니다.',
  allowedRouteKeys:
    '선택 항목입니다. 특정 route_key만 허용하려면 입력합니다. 비워두면 route_key 제한 목록을 만들지 않습니다.',
  revokeKeyId: '생성 결과에 표시된 key_id를 입력합니다. irt_... secret 값으로는 폐기할 수 없습니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

export default function ApiKeysPage() {
  const { session } = useModel('adminSession');
  const [createForm] = Form.useForm<ApiKeyFormValues>();
  const [revokeForm] = Form.useForm<{ key_id: string }>();
  const [createdKey, setCreatedKey] = useState<API.ApiKeyCreateResponse>();
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [keys, setKeys] = useState<API.ApiKey[]>([]);
  const [scopeCandidates, setScopeCandidates] = useState<API.IntentRouteCandidate[]>([]);
  const [runtimeSetup, setRuntimeSetup] = useState<API.RuntimeSetupGuidance>();
  const [loadingKeys, setLoadingKeys] = useState(false);
  const serviceIdRef = useRef(session.serviceId);
  const ready = isAdminSessionReady(session);
  const canManage = canManageRuntimeSetup(session);
  const manualRevokeKeyId = Form.useWatch('key_id', revokeForm)?.trim();
  const selectedService = session.services.find(
    (service) => service.service_id === session.serviceId,
  );
  const selectedEnvironment = selectedService?.environment || 'prod';

  const loadApiKeyPageData = async (
    selectedKey?: Pick<API.ApiKey, 'app_id' | 'key_id'>,
  ) => {
    if (!ready || !canManage) return;
    const serviceId = session.serviceId;
    setLoadingKeys(true);
    try {
      const [nextKeys, nextScopeCandidates, nextRuntimeSetup] = await Promise.all([
        listServiceApiKeys(serviceId, { environment: selectedEnvironment }),
        listIntentRouteCandidates(serviceId, {
          source: 'active_release',
          environment: selectedEnvironment,
        }),
        fetchRuntimeSetupGuidance(serviceId, {
          environment: selectedEnvironment,
          app_id: selectedKey?.app_id,
          key_id: selectedKey?.key_id,
        }),
      ]);
      if (serviceIdRef.current !== serviceId) return;
      setKeys(nextKeys);
      setScopeCandidates(nextScopeCandidates);
      setRuntimeSetup(nextRuntimeSetup);
    } finally {
      setLoadingKeys(false);
    }
  };

  useEffect(() => {
    serviceIdRef.current = session.serviceId;
    setCreatedKey(undefined);
    setKeys([]);
    setScopeCandidates([]);
    setRuntimeSetup(undefined);
    createForm.resetFields(['app_id', 'allowed_intents', 'allowed_route_keys']);
    revokeForm.resetFields();
    createForm.setFieldsValue({
      environment: selectedEnvironment,
      expires_in_days: 90,
    });
  }, [createForm, revokeForm, selectedEnvironment, session.serviceId]);

  useEffect(() => {
    loadApiKeyPageData();
  }, [ready, canManage, selectedEnvironment, session.serviceId]);

  const handleCreate = async (values: ApiKeyFormValues) => {
    const serviceId = session.serviceId;
    setCreating(true);
    try {
      const response = await createServiceApiKey(serviceId, {
        environment: selectedEnvironment,
        app_id: values.app_id.trim(),
        allowed_intents: values.allowed_intents ?? [],
        allowed_route_keys: values.allowed_route_keys ?? [],
        expires_in_days: values.expires_in_days,
      });
      if (serviceIdRef.current !== serviceId) return;
      setCreatedKey(response);
      message.success('API key가 생성되었습니다. 페이지를 떠나기 전에 secret을 복사해 주세요.');
      createForm.resetFields(['app_id', 'allowed_intents', 'allowed_route_keys']);
      await loadApiKeyPageData({ key_id: response.key_id, app_id: response.app_id });
    } finally {
      setCreating(false);
    }
  };

  const handleRevokeById = async (keyId: string) => {
    const serviceId = session.serviceId;
    setRevoking(true);
    try {
      await revokeServiceApiKey(serviceId, keyId);
      message.success('API key가 폐기되었습니다.');
      if (createdKey?.key_id === keyId) setCreatedKey(undefined);
      revokeForm.resetFields();
      await loadApiKeyPageData();
    } finally {
      setRevoking(false);
    }
  };

  const handleManualRevoke = async () => {
    const values = await revokeForm.validateFields();
    await handleRevokeById(values.key_id.trim());
  };

  const clearCreatedKey = () => {
    setCreatedKey(undefined);
  };

  const columns: ProColumns<API.ApiKey>[] = [
    {
      title: 'Key ID',
      dataIndex: 'key_id',
      width: 220,
      copyable: true,
      render: (_, row) => <Typography.Text code>{row.key_id}</Typography.Text>,
    },
    {
      title: 'App',
      dataIndex: 'app_id',
      width: 180,
      ellipsis: true,
    },
    {
      title: 'Fingerprint',
      dataIndex: 'key_fingerprint',
      width: 220,
      copyable: true,
      ellipsis: true,
    },
    {
      title: 'Scopes',
      width: 160,
      search: false,
      render: (_, row) => (
        <Typography.Text className="admin-nowrap-cell">
          intents {row.allowed_intents.length} · routes {row.allowed_route_keys.length}
        </Typography.Text>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 112,
      render: (_, row) => <StatusTag status={row.status} />,
    },
    {
      title: 'Expires',
      dataIndex: 'expires_at',
      valueType: 'dateTime',
      search: false,
      width: 180,
    },
    {
      title: '',
      valueType: 'option',
      width: 120,
      render: (_, row) =>
        row.status === 'active'
          ? [
              <ConfirmActionButton
                key="revoke"
                danger
                riskLevel="high"
                requireTypedConfirmation
                confirmText={row.key_id}
                type="link"
                size="small"
                title="Revoke API key?"
                okText="Revoke"
                content={`Revoke ${row.key_id}. Requests using this key will be rejected immediately after revoke.`}
                onConfirm={() => handleRevokeById(row.key_id)}
                disabled={revoking}
              >
                폐기
              </ConfirmActionButton>,
            ]
          : [],
    },
  ];

  return (
    <AdminShell title="API Keys">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {ready ? (
          <>
            {canManage ? (
              <>
                <Card title="Create API key">
                  <Form form={createForm} layout="vertical" onFinish={handleCreate}>
                    <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
                      <Descriptions.Item label="Selected service">
                        <Typography.Text code>{session.serviceId}</Typography.Text>
                      </Descriptions.Item>
                    </Descriptions>
                    <Space wrap align="start" size={12}>
                      <Form.Item
                        name="environment"
                        label={helpLabel('Environment', apiKeyHelp.environment)}
                        rules={[
                          { required: true, whitespace: true, message: 'Environment is required.' },
                        ]}
                      >
                        <Input disabled style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item
                        name="app_id"
                        label={helpLabel('App ID', apiKeyHelp.appId)}
                        rules={[{ required: true, whitespace: true, message: 'App ID is required.' }]}
                      >
                        <Input placeholder="checkout-web" style={{ width: 220 }} />
                      </Form.Item>
                      <Form.Item
                        name="expires_in_days"
                        label={helpLabel('Expires in days', apiKeyHelp.expiresInDays)}
                        rules={[{ required: true, message: 'Expiry is required.' }]}
                      >
                        <InputNumber min={1} max={3650} style={{ width: 160 }} />
                      </Form.Item>
                    </Space>
                    <Alert
                      type="info"
                      showIcon
                      style={{ marginBottom: 12 }}
                      message="선택하지 않으면 selected Service 안에서 intent/route 제한 목록을 만들지 않습니다."
                    />
                    <div className="api-key-scope-fields">
                      <Form.Item
                        name="allowed_intents"
                        label={helpLabel('Allowed intents', apiKeyHelp.allowedIntents)}
                      >
                        <IntentRouteMultiSelect
                          mode="intent"
                          candidates={scopeCandidates}
                          placeholder="허용할 intent 선택"
                        />
                      </Form.Item>
                      <Form.Item
                        name="allowed_route_keys"
                        label={helpLabel('Allowed route keys', apiKeyHelp.allowedRouteKeys)}
                      >
                        <IntentRouteMultiSelect
                          mode="route"
                          candidates={scopeCandidates}
                          placeholder="허용할 route key 선택"
                        />
                      </Form.Item>
                    </div>
                    <Button type="primary" htmlType="submit" loading={creating}>
                      API key 생성
                    </Button>
                  </Form>
                </Card>
                <Modal
                  open={Boolean(createdKey)}
                  title="새 API key secret"
                  onCancel={clearCreatedKey}
                  footer={[
                    <Button key="close" type="primary" onClick={clearCreatedKey}>
                      복사 완료
                    </Button>,
                  ]}
                  destroyOnHidden
                  centered
                  width={640}
                  style={{ maxWidth: 'calc(100vw - 32px)' }}
                  styles={{
                    body: { maxHeight: 'calc(100vh - 220px)', overflow: 'auto' },
                  }}
                >
                  {createdKey ? (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      <Alert
                        type="warning"
                        showIcon
                        message="이 secret은 이 모달을 닫으면 다시 볼 수 없습니다."
                        description="폐기는 secret 값이 아니라 key_id로 수행합니다. 페이지 이동, 새로고침, 모달 닫기 후에는 raw secret을 다시 표시하지 않습니다."
                      />
                      <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
                        {createdKey.api_key}
                      </Typography.Paragraph>
                      <Space wrap>
                        <Typography.Text copyable code>
                          key_id {createdKey.key_id}
                        </Typography.Text>
                        <Tag>fingerprint {createdKey.key_fingerprint}</Tag>
                        <StatusTag status={createdKey.status} />
                      </Space>
                    </Space>
                  ) : null}
                </Modal>
                <Card title="Runtime setup guidance">
                  {runtimeSetup ? (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      {runtimeSetup.warnings.length ? (
                        <Alert
                          type="warning"
                          showIcon
                          message={runtimeSetup.warnings.join(' ')}
                        />
                      ) : null}
                      <Descriptions size="small" column={{ xs: 1, md: 2 }}>
                        <Descriptions.Item label="Runtime endpoint">
                          <Typography.Text copyable code>
                            {runtimeSetup.runtime_endpoint}
                          </Typography.Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="Timeout">
                          {runtimeSetup.recommended_timeout_seconds}s
                        </Descriptions.Item>
                        <Descriptions.Item label="Service">
                          <Typography.Text code>{runtimeSetup.service_id}</Typography.Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="Environment">
                          <Tag>{runtimeSetup.environment}</Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="Active release">
                          {runtimeSetup.active_release ? (
                            <Typography.Text copyable code>
                              {runtimeSetup.active_release.release_version}
                            </Typography.Text>
                          ) : (
                            <Tag color="default">none</Tag>
                          )}
                        </Descriptions.Item>
                        <Descriptions.Item label="Selected key">
                          <Typography.Text copyable code>
                            {runtimeSetupSelectedKeyLabel(runtimeSetup)}
                          </Typography.Text>
                        </Descriptions.Item>
                      </Descriptions>
                      <Descriptions
                        size="small"
                        column={1}
                        title="Headers template"
                      >
                        {runtimeSetupHeaderRows(runtimeSetup).map((row) => (
                          <Descriptions.Item key={row.name} label={row.name}>
                            <Typography.Text copyable code>
                              {row.value}
                            </Typography.Text>
                          </Descriptions.Item>
                        ))}
                      </Descriptions>
                      <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
                        {runtimeSetupBodyTemplateText(runtimeSetup)}
                      </Typography.Paragraph>
                      <Descriptions
                        size="small"
                        column={1}
                        title="Dify variable mapping"
                      >
                        {runtimeSetup.dify_variable_mapping.map((row) => (
                          <Descriptions.Item key={row.field} label={row.field}>
                            {row.source}
                          </Descriptions.Item>
                        ))}
                      </Descriptions>
                      <div className="api-key-checklist">
                        {runtimeSetup.checklist.map((item) => (
                          <Tag key={item} className="api-key-checklist-item">
                            {item}
                          </Tag>
                        ))}
                      </div>
                    </Space>
                  ) : (
                    <Alert
                      type="info"
                      showIcon
                      message="Service를 선택하면 Runtime setup 안내가 표시됩니다."
                    />
                  )}
                </Card>
                <ProTable<API.ApiKey>
                  className="admin-scroll-table"
                  rowKey="key_id"
                  loading={loadingKeys}
                  dataSource={keys}
                  search={false}
                  pagination={false}
                  scroll={{ x: 960 }}
                  columns={columns}
                  toolbar={{
                    title: 'API key inventory',
                    actions: [
                      <AdminTableActions
                        key="table-actions"
                        onReload={() => loadApiKeyPageData()}
                        reloadDisabled={loadingKeys}
                      />,
                    ],
                  }}
                  options={false}
                />
                <Card title="Manual revoke">
                  <Form form={revokeForm} layout="vertical">
                    <Form.Item
                      name="key_id"
                      label={helpLabel('Key ID', apiKeyHelp.revokeKeyId)}
                      rules={[{ required: true, whitespace: true, message: 'Key id is required.' }]}
                    >
                      <Input placeholder="key_id" style={{ width: '100%', maxWidth: 320 }} />
                    </Form.Item>
                    <ConfirmActionButton
                      danger
                      riskLevel="high"
                      requireTypedConfirmation={Boolean(manualRevokeKeyId)}
                      confirmText={manualRevokeKeyId}
                      title="Revoke API key?"
                      okText="Revoke"
                      content="This immediately revokes the key id you entered."
                      onConfirm={handleManualRevoke}
                      disabled={revoking}
                    >
                      폐기
                    </ConfirmActionButton>
                  </Form>
                </Card>
              </>
            ) : (
              <Alert
                type="info"
                showIcon
                message="선택한 Service에 대한 API key 관리 권한이 없습니다."
                description="system_admin 또는 선택한 Service의 service_owner/service_developer만 생성, 조회, 폐기할 수 있습니다."
              />
            )}
          </>
        ) : (
          <AdminSessionRequired />
        )}
      </Space>
    </AdminShell>
  );
}
