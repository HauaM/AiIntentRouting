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
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { IntentRouteMultiSelect } from '@/components/IntentRouteMultiSelect';
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
      message.success('API key created. Copy the secret before leaving this page.');
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
      message.success('API key revoked.');
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

  const columns: ProColumns<API.ApiKey>[] = [
    {
      title: 'Key ID',
      dataIndex: 'key_id',
      copyable: true,
      render: (_, row) => <Typography.Text code>{row.key_id}</Typography.Text>,
    },
    {
      title: 'App',
      dataIndex: 'app_id',
    },
    {
      title: 'Fingerprint',
      dataIndex: 'key_fingerprint',
      copyable: true,
      ellipsis: true,
    },
    {
      title: 'Scopes',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span className="muted-small">intents {row.allowed_intents.length}</span>
          <span className="muted-small">routes {row.allowed_route_keys.length}</span>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (_, row) => (
        <Tag color={row.status === 'active' ? 'green' : 'default'}>{row.status}</Tag>
      ),
    },
    {
      title: 'Expires',
      dataIndex: 'expires_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '',
      valueType: 'option',
      render: (_, row) =>
        row.status === 'active'
          ? [
              <ConfirmActionButton
                key="revoke"
                danger
                type="link"
                size="small"
                title="Revoke API key?"
                okText="Revoke"
                content={`Revoke ${row.key_id}.`}
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
                    <Space wrap align="start" size={12}>
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
                    </Space>
                    <Button type="primary" htmlType="submit" loading={creating}>
                      API key 생성
                    </Button>
                  </Form>
                </Card>
                {createdKey ? (
                  <Alert
                    type="warning"
                    showIcon
                    message="New API key secret"
                    description={
                      <Space direction="vertical" size={8} style={{ width: '100%' }}>
                        <Typography.Text>
                          This secret is kept only in the current page state and will not be shown again
                          after refresh or navigation.
                        </Typography.Text>
                        <Typography.Text>
                          Revoke uses the key_id below, not the secret value.
                        </Typography.Text>
                        <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
                          {createdKey.api_key}
                        </Typography.Paragraph>
                        <Space wrap>
                          <Typography.Text copyable code>
                            key_id {createdKey.key_id}
                          </Typography.Text>
                          <Tag>fingerprint {createdKey.key_fingerprint}</Tag>
                          <Tag>{createdKey.status}</Tag>
                        </Space>
                      </Space>
                    }
                  />
                ) : null}
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
                      <Descriptions size="small" column={2}>
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
                      <Space wrap>
                        {runtimeSetup.checklist.map((item) => (
                          <Tag key={item}>{item}</Tag>
                        ))}
                      </Space>
                    </Space>
                  ) : (
                    <Alert
                      type="info"
                      showIcon
                      message="Runtime setup guidance loads after selecting a Service."
                    />
                  )}
                </Card>
                <ProTable<API.ApiKey>
                  rowKey="key_id"
                  loading={loadingKeys}
                  dataSource={keys}
                  search={false}
                  pagination={false}
                  columns={columns}
                  toolbar={{
                    title: 'API key inventory',
                    actions: [
                      <Button
                        key="reload"
                        onClick={() => loadApiKeyPageData()}
                        loading={loadingKeys}
                      >
                        새로고침
                      </Button>,
                    ],
                  }}
                  options={{ density: true, fullScreen: false, reload: false, setting: true }}
                />
                <Card title="Manual revoke">
                  <Form form={revokeForm} layout="inline">
                    <Form.Item
                      name="key_id"
                      label={helpLabel('Key ID', apiKeyHelp.revokeKeyId)}
                      rules={[{ required: true, whitespace: true, message: 'Key id is required.' }]}
                    >
                      <Input placeholder="key_id" style={{ width: 320 }} />
                    </Form.Item>
                    <ConfirmActionButton
                      danger
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
                message="API key actions require system_admin"
                description="Create and revoke controls are hidden unless the session has the system_admin role."
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
