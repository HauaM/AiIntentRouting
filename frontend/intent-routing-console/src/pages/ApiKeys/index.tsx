import { useEffect, useRef, useState } from 'react';
import { CopyOutlined } from '@ant-design/icons';
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
  Radio,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
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
  revealServiceApiKey,
  revokeServiceApiKey,
} from '@/services/adminServices';
import {
  runRuntimeIntentRoute,
  type RuntimeIntentRouteLiveTestResult,
} from '@/services/runtimeServices';
import {
  runtimeSetupBodyTemplateText,
  runtimeSetupHeaderRows,
  runtimeSetupSelectedKeyLabel,
} from './runtimeSetup';
import {
  completeApiKeyCreation,
  type CreatedApiKey,
} from './apiKeyCreateFlow';

type ApiKeyFormValues = {
  app_id: string;
  allowed_intents?: string[];
  allowed_route_keys?: string[];
  expiry_mode: 'days' | 'none';
  expires_in_days?: number | null;
};

const apiKeyHelp = {
  environment: 'API key가 사용할 active Release 환경입니다.',
  appId: '이 key를 사용할 호출 앱/클라이언트 이름입니다. 예: checkout-web, helpdesk-bot',
  expiryMode: '기간 지정 또는 무기한을 선택합니다. 무기한 key는 직접 폐기하기 전까지 활성 상태로 남습니다.',
  expiresInDays: 'Key 만료까지의 일수입니다. 비워두면 무기한으로 설정되지 않고 검증 오류가 납니다.',
  allowedIntents:
    '선택 항목입니다. 특정 intent_id만 허용하려면 입력합니다. 비워두면 모든 intent 접근을 허용합니다.',
  allowedRouteKeys:
    '선택 항목입니다. 특정 route_key만 허용하려면 입력합니다. 비워두면 모든 route 접근을 허용합니다.',
};

const environmentOptions = [
  { label: 'dev', value: 'dev' },
  { label: 'qa', value: 'qa' },
  { label: 'prod', value: 'prod' },
];

const expiryModeOptions = [
  { label: '기간 지정', value: 'days' },
  { label: '무기한', value: 'none' },
];

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

const expiryLabel = (expiresAt: string | null) => {
  if (!expiresAt) return '무기한';
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(expiresAt));
};

const selectedKeyMatches = (row: API.ApiKey, selected?: Pick<API.ApiKey, 'key_id'>) =>
  Boolean(selected?.key_id && row.key_id === selected.key_id);

export default function ApiKeysPage() {
  const { session } = useModel('adminSession');
  const [createForm] = Form.useForm<ApiKeyFormValues>();
  const [activeTabKey, setActiveTabKey] = useState('new');
  const [createdKey, setCreatedKey] = useState<CreatedApiKey<API.ApiKeyCreateResponse>>();
  const [createdKeyModalOpen, setCreatedKeyModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [keys, setKeys] = useState<API.ApiKey[]>([]);
  const [selectedApiKey, setSelectedApiKey] = useState<API.ApiKey>();
  const [scopeCandidates, setScopeCandidates] = useState<API.IntentRouteCandidate[]>([]);
  const [runtimeSetup, setRuntimeSetup] = useState<API.RuntimeSetupGuidance>();
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [selectedEnvironment, setSelectedEnvironment] =
    useState<'dev' | 'qa' | 'prod'>('dev');
  const [liveTestSecret, setLiveTestSecret] = useState('');
  const [liveTestQuery, setLiveTestQuery] = useState('');
  const [liveTestRequestId, setLiveTestRequestId] = useState('');
  const [liveTestRunning, setLiveTestRunning] = useState(false);
  const [liveTestResult, setLiveTestResult] =
    useState<RuntimeIntentRouteLiveTestResult>();
  const [revealingKeyId, setRevealingKeyId] = useState<string>();
  const serviceIdRef = useRef(session.serviceId);
  const selectedEnvironmentRef = useRef(selectedEnvironment);
  const apiKeyPageRequestIdRef = useRef(0);
  const liveTestScopeTokenRef = useRef(0);
  const selectedApiKeyIdRef = useRef<string>();
  serviceIdRef.current = session.serviceId;
  selectedEnvironmentRef.current = selectedEnvironment;
  selectedApiKeyIdRef.current = selectedApiKey?.key_id;
  const ready = isAdminSessionReady(session);
  const canManage = canManageRuntimeSetup(session);
  const expiryMode = Form.useWatch('expiry_mode', createForm) ?? 'days';
  const hasActiveRelease = Boolean(runtimeSetup?.active_release);
  const showMissingActiveRelease =
    Boolean(runtimeSetup) && !hasActiveRelease && !loadingKeys;
  const showEmptyScopeCandidates =
    Boolean(runtimeSetup) &&
    hasActiveRelease &&
    scopeCandidates.length === 0 &&
    !loadingKeys;
  const selectedRuntimeKey = runtimeSetup?.selected_key;
  const canRunLiveTest = Boolean(
    runtimeSetup?.runtime_endpoint &&
      hasActiveRelease &&
      !loadingKeys &&
      selectedRuntimeKey?.status === 'active' &&
      liveTestSecret.trim() &&
      liveTestQuery.trim(),
  );

  const resetLiveTestInputs = () => {
    setLiveTestSecret('');
    setLiveTestQuery('');
    setLiveTestRequestId('');
    setLiveTestResult(undefined);
  };

  const invalidateLiveTestScope = () => {
    liveTestScopeTokenRef.current += 1;
    resetLiveTestInputs();
    setLiveTestRunning(false);
  };

  const loadApiKeyPageData = async (
    selectedKey?: Pick<API.ApiKey, 'app_id' | 'key_id'>,
  ) => {
    if (!ready || !canManage) return;
    const serviceId = session.serviceId;
    const environment = selectedEnvironment;
    const requestId = ++apiKeyPageRequestIdRef.current;
    const isCurrentRequest = () =>
      serviceIdRef.current === serviceId &&
      selectedEnvironmentRef.current === environment &&
      apiKeyPageRequestIdRef.current === requestId;
    setLoadingKeys(true);
    try {
      const [nextKeys, nextScopeCandidates] = await Promise.all([
        listServiceApiKeys(serviceId, { environment }),
        listIntentRouteCandidates(serviceId, {
          source: 'active_release',
          environment,
        }),
      ]);
      if (!isCurrentRequest()) return;

      const nextSelectedKey =
        nextKeys.find((row) => selectedKeyMatches(row, selectedKey)) ??
        nextKeys.find((row) => selectedKeyMatches(row, selectedApiKey)) ??
        nextKeys.find((row) => row.status === 'active') ??
        undefined;

      const nextRuntimeSetup = await fetchRuntimeSetupGuidance(serviceId, {
        environment,
        app_id: nextSelectedKey?.app_id,
        key_id: nextSelectedKey?.key_id,
      });
      if (!isCurrentRequest()) return;

      if (selectedApiKey?.key_id !== nextSelectedKey?.key_id) {
        invalidateLiveTestScope();
      }
      setKeys(nextKeys);
      setSelectedApiKey(nextSelectedKey);
      setScopeCandidates(nextScopeCandidates);
      setRuntimeSetup(nextRuntimeSetup);
    } finally {
      if (isCurrentRequest()) setLoadingKeys(false);
    }
  };

  useEffect(() => {
    serviceIdRef.current = session.serviceId;
    selectedEnvironmentRef.current = selectedEnvironment;
    setCreatedKey(undefined);
    setCreatedKeyModalOpen(false);
    setKeys([]);
    setSelectedApiKey(undefined);
    setScopeCandidates([]);
    setRuntimeSetup(undefined);
    invalidateLiveTestScope();
    createForm.resetFields(['app_id', 'allowed_intents', 'allowed_route_keys']);
    createForm.setFieldsValue({
      expiry_mode: 'days',
      expires_in_days: 90,
    });
  }, [createForm, selectedEnvironment, session.serviceId]);

  useEffect(() => {
    loadApiKeyPageData();
  }, [ready, canManage, selectedEnvironment, session.serviceId]);

  const handleCreate = async (values: ApiKeyFormValues) => {
    const serviceId = session.serviceId;
    const environment = selectedEnvironment;
    setCreating(true);
    try {
      await completeApiKeyCreation({
        create: () =>
          createServiceApiKey(serviceId, {
            environment,
            app_id: values.app_id.trim(),
            allowed_intents: values.allowed_intents ?? [],
            allowed_route_keys: values.allowed_route_keys ?? [],
            ...(values.expiry_mode === 'none'
              ? { expires_in_days: null }
              : { expires_in_days: values.expires_in_days ?? null }),
          }),
        scope: { serviceId, environment },
        isScopeCurrent: () =>
          serviceIdRef.current === serviceId && selectedEnvironmentRef.current === environment,
        onCreated: (created) => {
          setCreatedKey(created);
          setCreatedKeyModalOpen(true);
          setActiveTabKey('existing');
          message.success('API key가 생성되었습니다. 페이지를 떠나기 전에 secret을 복사해 주세요.');
        },
        reloadCurrentScope: async (response) => {
          createForm.resetFields(['app_id', 'allowed_intents', 'allowed_route_keys']);
          createForm.setFieldsValue({ expiry_mode: 'days', expires_in_days: 90 });
          await loadApiKeyPageData({ key_id: response.key_id, app_id: response.app_id });
        },
      });
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
      if (createdKey?.response.key_id === keyId) {
        setCreatedKey(undefined);
        setCreatedKeyModalOpen(false);
      }
      await loadApiKeyPageData();
    } finally {
      setRevoking(false);
    }
  };

  const selectApiKey = (row: API.ApiKey) => {
    if (row.key_id !== selectedApiKey?.key_id) {
      invalidateLiveTestScope();
    }
    setSelectedApiKey(row);
    loadApiKeyPageData({ key_id: row.key_id, app_id: row.app_id });
  };

  const clearCreatedKey = () => {
    setCreatedKey(undefined);
    setCreatedKeyModalOpen(false);
  };

  const copyText = async (text: string) => {
    await navigator.clipboard.writeText(text);
  };

  const handleCopyHeader = async (row: { name: string; value: string }) => {
    if (row.name.toLowerCase() !== 'authorization') {
      await copyText(row.value);
      message.success(`${row.name} 값이 복사되었습니다.`);
      return;
    }
    const keyId = runtimeSetup?.selected_key?.key_id;
    if (!runtimeSetup || !keyId) {
      await copyText(row.value);
      message.info('선택된 key가 없어 템플릿 값을 복사했습니다.');
      return;
    }
    const serviceId = runtimeSetup.service_id;
    const environment = runtimeSetup.environment;
    setRevealingKeyId(keyId);
    try {
      const response = await revealServiceApiKey(serviceId, keyId);
      if (
        serviceIdRef.current !== serviceId ||
        selectedEnvironmentRef.current !== environment ||
        selectedApiKeyIdRef.current !== keyId
      ) {
        return;
      }
      await copyText(response.authorization_header);
      message.success('Authorization header가 복사되었습니다.');
    } finally {
      setRevealingKeyId(undefined);
    }
  };

  const handleRunLiveTest = async () => {
    if (!runtimeSetup || !selectedRuntimeKey) {
      message.warning('테스트할 API key를 인벤토리에서 선택하세요.');
      return;
    }
    const query = liveTestQuery.trim();
    const apiSecret = liveTestSecret.trim();
    if (!apiSecret || !query) {
      message.warning('API Secret과 테스트 쿼리를 입력하세요.');
      return;
    }
    const requestId = liveTestRequestId.trim() || `admin-live-${Date.now()}`;
    const serviceId = runtimeSetup.service_id;
    const environment = runtimeSetup.environment;
    const liveTestScopeToken = liveTestScopeTokenRef.current;
    const isLiveTestScopeCurrent = () =>
      liveTestScopeTokenRef.current === liveTestScopeToken &&
      serviceIdRef.current === serviceId &&
      selectedEnvironmentRef.current === environment;
    setLiveTestRequestId(requestId);
    setLiveTestRunning(true);
    setLiveTestResult(undefined);
    try {
      const result = await runRuntimeIntentRoute({
        runtimeEndpoint: runtimeSetup.runtime_endpoint,
        apiSecret,
        keyId: selectedRuntimeKey.key_id,
        appId: selectedRuntimeKey.app_id,
        serviceId,
        requestId,
        query,
      });
      if (!isLiveTestScopeCurrent()) return;
      setLiveTestResult(result);
      if (result.ok) {
        message.success('라이브 테스트 호출이 완료되었습니다.');
      } else {
        message.error('라이브 테스트 호출이 실패했습니다.');
      }
    } finally {
      if (isLiveTestScopeCurrent()) setLiveTestRunning(false);
    }
  };

  const columns: ProColumns<API.ApiKey>[] = [
    {
      title: 'Routing Key ID',
      dataIndex: 'key_id',
      width: 240,
      copyable: true,
      ellipsis: true,
      render: (_, row) => <Typography.Text code>{row.key_id}</Typography.Text>,
    },
    {
      title: 'App',
      dataIndex: 'app_id',
      width: 180,
      ellipsis: true,
    },
    {
      title: 'Scopes',
      width: 160,
      search: false,
      render: (_, row) => (
        <Typography.Text className="admin-nowrap-cell">
          intent {row.allowed_intents.length} · route {row.allowed_route_keys.length}
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
      search: false,
      width: 140,
      render: (_, row) =>
        row.expires_at ? (
          <Typography.Text>{expiryLabel(row.expires_at)}</Typography.Text>
        ) : (
          <StatusTag status="none" label="무기한" />
        ),
    },
    {
      title: 'Fingerprint',
      dataIndex: 'key_fingerprint',
      width: 220,
      copyable: true,
      ellipsis: true,
    },
    {
      title: 'Copy',
      width: 180,
      search: false,
      render: (_, row) => (
        <Space size={8} className="admin-nowrap-cell">
          <Typography.Text copyable={{ text: row.key_id }}>X-Key-Id</Typography.Text>
          <Typography.Text copyable={{ text: '{{intent_routing_api_key}}' }}>
            API Secret 변수
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: '',
      valueType: 'option',
      width: 160,
      render: (_, row) => (
        <Space size={8} className="admin-nowrap-cell">
          <Button type="link" size="small" onClick={() => selectApiKey(row)}>
            가이드 적용
          </Button>
          {row.status === 'active' ? (
            <ConfirmActionButton
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
            </ConfirmActionButton>
          ) : null}
        </Space>
      ),
    },
  ];

  const createKeyPanel = (
    <Card title="Create API key">
      <Form form={createForm} layout="vertical" onFinish={handleCreate}>
        <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Selected service">
            <Space size={8} wrap>
              <Typography.Text code>{session.serviceId}</Typography.Text>
              <StatusTag status={selectedEnvironment} label={selectedEnvironment} />
            </Space>
          </Descriptions.Item>
          {runtimeSetup ? (
            <Descriptions.Item label="Active release">
              {runtimeSetup.active_release ? (
                <Typography.Text copyable code>
                  {runtimeSetup.active_release.release_version}
                </Typography.Text>
              ) : (
                <StatusTag status="none" label="none" />
              )}
            </Descriptions.Item>
          ) : null}
        </Descriptions>
        <Space wrap align="start" size={12}>
          <Form.Item label={helpLabel('Released environment', apiKeyHelp.environment)}>
            <Select
              value={selectedEnvironment}
              options={environmentOptions}
              onChange={(value: 'dev' | 'qa' | 'prod') => {
                selectedEnvironmentRef.current = value;
                invalidateLiveTestScope();
                setSelectedEnvironment(value);
                setCreatedKey(undefined);
                setCreatedKeyModalOpen(false);
                setKeys([]);
                setScopeCandidates([]);
                setRuntimeSetup(undefined);
              }}
              style={{ width: 180 }}
            />
          </Form.Item>
          <Form.Item
            name="app_id"
            label={helpLabel('App ID', apiKeyHelp.appId)}
            rules={[{ required: true, whitespace: true, message: 'App ID is required.' }]}
          >
            <Input placeholder="checkout-web" style={{ width: 220 }} />
          </Form.Item>
          <Form.Item
            name="expiry_mode"
            label={helpLabel('만료 기간', apiKeyHelp.expiryMode)}
            rules={[{ required: true, message: 'Expiry mode is required.' }]}
          >
            <Radio.Group optionType="button" buttonStyle="solid" options={expiryModeOptions} />
          </Form.Item>
          {expiryMode === 'days' ? (
            <Form.Item
              name="expires_in_days"
              label={helpLabel('Expires in days', apiKeyHelp.expiresInDays)}
              rules={[{ required: true, message: 'Expiry is required.' }]}
            >
              <InputNumber min={1} max={3650} style={{ width: 160 }} />
            </Form.Item>
          ) : null}
        </Space>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="선택하지 않으면 Service 내 모든 intent/route에 접근 가능합니다. 특정 범위만 허용하려면 아래에서 선택하세요."
        />
        {showMissingActiveRelease ? (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message="선택한 환경에 active Release가 없습니다."
            description={
              'Releases 화면에서 해당 환경의 Release를 활성화한 뒤 API key를 발급하세요. ' +
              '생성만 완료된 inactive Release는 런타임 후보로 사용되지 않습니다.'
            }
          />
        ) : null}
        {showEmptyScopeCandidates ? (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message="Active Release에 허용할 intent/route 후보가 없습니다."
            description="선택한 active Release의 catalog snapshot에 active intent가 있는지 확인하세요."
          />
        ) : null}
        <div className="api-key-scope-fields">
          <Form.Item
            name="allowed_intents"
            label={helpLabel('Allowed intents', apiKeyHelp.allowedIntents)}
          >
            <IntentRouteMultiSelect
              mode="intent"
              candidates={scopeCandidates}
              placeholder="허용할 intent 선택"
              disabled={!hasActiveRelease || loadingKeys}
              loading={loadingKeys}
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
              disabled={!hasActiveRelease || loadingKeys}
              loading={loadingKeys}
            />
          </Form.Item>
        </div>
        <Button
          type="primary"
          htmlType="submit"
          loading={creating}
          disabled={!hasActiveRelease || loadingKeys}
        >
          API key 생성
        </Button>
      </Form>
    </Card>
  );

  const runtimeChecklist =
    runtimeSetup?.checklist.filter((item) => !item.toLowerCase().includes('dify')) ?? [];

  const liveTestResultPanel = liveTestResult ? (
    liveTestResult.ok ? (
      <Alert
        type="success"
        showIcon
        message="Runtime call completed"
        description={
          <Descriptions size="small" column={{ xs: 1, md: 2 }}>
            <Descriptions.Item label="Decision">
              <StatusTag
                status={liveTestResult.body.decision}
                label={liveTestResult.body.decision}
              />
            </Descriptions.Item>
            <Descriptions.Item label="HTTP status">
              {liveTestResult.status}
            </Descriptions.Item>
            <Descriptions.Item label="Trace ID">
              <Typography.Text copyable code>
                {liveTestResult.body.trace_id}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Request ID">
              <Typography.Text copyable code>
                {liveTestResult.body.request_id ?? liveTestRequestId}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Intent">
              {liveTestResult.body.intent_id ? (
                <Typography.Text code>{liveTestResult.body.intent_id}</Typography.Text>
              ) : (
                <StatusTag status="none" label="none" />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Route key">
              {liveTestResult.body.route_key ? (
                <Typography.Text code>{liveTestResult.body.route_key}</Typography.Text>
              ) : (
                <StatusTag status="none" label="none" />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Confidence">
              {liveTestResult.body.confidence ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Release">
              {liveTestResult.body.release_version ? (
                <Typography.Text copyable code>
                  {liveTestResult.body.release_version}
                </Typography.Text>
              ) : (
                <StatusTag status="none" label="none" />
              )}
            </Descriptions.Item>
          </Descriptions>
        }
      />
    ) : (
      <Alert
        type="error"
        showIcon
        message={`${liveTestResult.error.code}: ${liveTestResult.error.message}`}
        description={
          <Descriptions size="small" column={{ xs: 1, md: 2 }}>
            <Descriptions.Item label="HTTP status">
              {liveTestResult.status || 'network'}
            </Descriptions.Item>
            <Descriptions.Item label="Retryable">
              {String(Boolean(liveTestResult.error.retryable))}
            </Descriptions.Item>
            <Descriptions.Item label="Trace ID">
              {liveTestResult.trace_id ? (
                <Typography.Text copyable code>
                  {liveTestResult.trace_id}
                </Typography.Text>
              ) : (
                <StatusTag status="none" label="none" />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Request ID">
              <Typography.Text copyable code>
                {liveTestResult.request_id ?? liveTestRequestId}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Category">
              {liveTestResult.error.category ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Layer">
              {liveTestResult.error.layer ?? '-'}
            </Descriptions.Item>
          </Descriptions>
        }
      />
    )
  ) : null;

  const existingKeyPanel = (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <ProTable<API.ApiKey>
        className="admin-scroll-table"
        rowKey="key_id"
        loading={loadingKeys}
        dataSource={keys}
        search={false}
        pagination={false}
        scroll={{ x: 1280 }}
        columns={columns}
        rowClassName={(row) =>
          selectedApiKey?.key_id === row.key_id ? 'api-key-selected-row' : ''
        }
        onRow={(row) => ({
          onClick: () => selectApiKey(row),
        })}
        toolbar={{
          title: 'API key inventory',
          actions: [
            <Button
              key="reload"
              onClick={() => loadApiKeyPageData(selectedApiKey)}
              loading={loadingKeys}
            >
              새로고침
            </Button>,
          ],
        }}
        options={{ density: true, fullScreen: false, reload: false, setting: true }}
      />
      <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
        행을 클릭하면 아래 Runtime setup guidance에 자동 반영됩니다. raw API Secret은
        생성 완료 모달과 Authorization의 Secret 보기/복사 작업에서만 표시되며 감사
        로그가 남습니다.
      </Typography.Paragraph>
      <Card title="Runtime setup guidance">
        {runtimeSetup ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {runtimeSetup.warnings.length ? (
              <Alert type="warning" showIcon message={runtimeSetup.warnings.join(' ')} />
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
                <StatusTag status={runtimeSetup.environment} label={runtimeSetup.environment} />
              </Descriptions.Item>
              <Descriptions.Item label="Active release">
                {runtimeSetup.active_release ? (
                  <Typography.Text copyable code>
                    {runtimeSetup.active_release.release_version}
                  </Typography.Text>
                ) : (
                  <StatusTag status="none" label="none" />
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Selected key">
                <Typography.Text copyable code>
                  {runtimeSetupSelectedKeyLabel(runtimeSetup)}
                </Typography.Text>
              </Descriptions.Item>
            </Descriptions>
            <Descriptions size="small" column={1} title="Headers template">
              {runtimeSetupHeaderRows(runtimeSetup).map((row) => {
                const isAuthorization = row.name.toLowerCase() === 'authorization';
                return (
                  <Descriptions.Item key={row.name} label={row.name}>
                    <Space size={8} wrap>
                      <Typography.Text code>{row.value}</Typography.Text>
                      <Button
                        size="small"
                        icon={<CopyOutlined />}
                        loading={
                          isAuthorization &&
                          revealingKeyId === runtimeSetup.selected_key?.key_id
                        }
                        onClick={() => handleCopyHeader(row)}
                      >
                        {isAuthorization ? 'Secret 보기/복사' : '복사'}
                      </Button>
                    </Space>
                  </Descriptions.Item>
                );
              })}
            </Descriptions>
            <Descriptions size="small" column={1} title="Body template">
              <Descriptions.Item label="JSON">
                <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
                  {runtimeSetupBodyTemplateText(runtimeSetup)}
                </Typography.Paragraph>
              </Descriptions.Item>
            </Descriptions>
            {runtimeChecklist.length ? (
              <div className="api-key-checklist">
                {runtimeChecklist.map((item) => (
                  <Tag key={item} className="api-key-checklist-item">
                    {item}
                  </Tag>
                ))}
              </div>
            ) : null}
          </Space>
        ) : (
          <Alert
            type="info"
            showIcon
            message="Service와 key를 선택하면 Runtime setup 안내가 표시됩니다."
          />
        )}
      </Card>
      <Card
        title="라이브 테스트"
        extra={
          selectedRuntimeKey ? (
            <Typography.Text copyable code>
              {selectedRuntimeKey.key_id}
            </Typography.Text>
          ) : (
            <StatusTag status="none" label="키 미선택" />
          )
        }
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message="선택한 key의 API Secret을 직접 입력하면 runtime API를 한 번 호출합니다. Secret은 저장하지 않습니다."
          />
          {!selectedRuntimeKey ? (
            <Alert
              type="warning"
              showIcon
              message="테스트할 active API key를 인벤토리에서 선택하세요."
            />
          ) : null}
          <Form layout="vertical" className="api-key-live-test-form">
            <div className="api-key-live-test-controls">
              <Form.Item label="API Secret">
                <Input.Password
                  value={liveTestSecret}
                  onChange={(event) => setLiveTestSecret(event.target.value)}
                  placeholder="irt_..."
                  autoComplete="off"
                  disabled={!selectedRuntimeKey || loadingKeys || liveTestRunning}
                />
              </Form.Item>
              <Form.Item label="테스트 쿼리">
                <Input
                  value={liveTestQuery}
                  onChange={(event) => setLiveTestQuery(event.target.value)}
                  placeholder="예: 비밀번호를 재설정하고 싶어요"
                  disabled={!selectedRuntimeKey || loadingKeys || liveTestRunning}
                />
              </Form.Item>
              <Form.Item label="Request ID">
                <Input
                  value={liveTestRequestId}
                  onChange={(event) => setLiveTestRequestId(event.target.value)}
                  placeholder="비우면 자동 생성"
                  disabled={!selectedRuntimeKey || loadingKeys || liveTestRunning}
                />
              </Form.Item>
              <Button
                type="primary"
                onClick={handleRunLiveTest}
                loading={liveTestRunning}
                disabled={!canRunLiveTest || liveTestRunning}
              >
                테스트 실행
              </Button>
            </div>
          </Form>
          {liveTestResultPanel}
        </Space>
      </Card>
    </Space>
  );

  const apiKeyTabs = [
    { key: 'new', label: '신규 발급', children: createKeyPanel },
    { key: 'existing', label: '기존 키 관리', children: existingKeyPanel },
  ];

  return (
    <AdminShell title="API Keys">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {ready ? (
          canManage ? (
            <>
              <Tabs
                activeKey={activeTabKey}
                onChange={setActiveTabKey}
                items={apiKeyTabs}
              />
              <Modal
                open={createdKeyModalOpen}
                title="새 API Key 발급 완료"
                onCancel={clearCreatedKey}
                footer={[
                  <Button key="clear" onClick={clearCreatedKey}>
                    Secret 지우기
                  </Button>,
                  <Button key="close" type="primary" onClick={clearCreatedKey}>
                    닫기
                  </Button>,
                ]}
                destroyOnHidden
                centered
                width={680}
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
                      message="이 모달을 닫으면 화면에 남은 secret은 지워집니다."
                      description="이후에는 기존 키 관리의 Authorization 행에서 Secret 보기/복사를 눌러 감사 로그를 남긴 뒤 다시 복사할 수 있습니다. API Secret은 안전한 보관소에 저장하세요."
                    />
                    <div className="api-key-secret-block">
                      <Typography.Text strong>API Secret Key</Typography.Text>
                      <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
                        {createdKey.response.api_key}
                      </Typography.Paragraph>
                    </div>
                    <div className="api-key-secret-block">
                      <Typography.Text strong>Routing Key ID</Typography.Text>
                      <Typography.Paragraph copyable code style={{ marginBottom: 0 }}>
                        {createdKey.response.key_id}
                      </Typography.Paragraph>
                    </div>
                    <Space wrap>
                      <Tag>Service: {createdKey.scope.serviceId}</Tag>
                      <StatusTag
                        status={createdKey.scope.environment}
                        label={createdKey.scope.environment}
                      />
                      <Tag>App: {createdKey.response.app_id}</Tag>
                      <Tag>만료: {expiryLabel(createdKey.response.expires_at)}</Tag>
                      <Tag>Fingerprint: {createdKey.response.key_fingerprint}</Tag>
                      <StatusTag status={createdKey.response.status} />
                    </Space>
                  </Space>
                ) : null}
              </Modal>
            </>
          ) : (
            <Alert
              type="info"
              showIcon
              message="선택한 Service에 대한 API key 관리 권한이 없습니다."
              description="system_admin 또는 선택한 Service의 service_owner만 생성, 조회, 폐기할 수 있습니다."
            />
          )
        ) : (
          <AdminSessionRequired />
        )}
      </Space>
    </AdminShell>
  );
}
