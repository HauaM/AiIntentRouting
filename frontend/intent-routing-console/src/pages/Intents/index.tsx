import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { history, useModel } from '@umijs/max';
import type { TableProps } from 'antd';
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { IntentCatalogTable } from '@/components/IntentCatalogTable';
import { StatusTag } from '@/components/StatusTag';
import { WorkflowNextActionBar } from '@/components/WorkflowNextActionBar';
import { canEditCatalog, isAdminSessionReady } from '@/models/adminSession';
import {
  approveExample,
  createExample,
  createIntent,
  listExamples,
  patchIntent,
} from '@/services/adminServices';

type IntentFormMode = 'create' | 'edit';

type IntentFormValues = {
  intent_id: string;
  domain: string;
  display_name: string;
  description: string;
  route_key: string;
  status?: 'draft' | 'active' | 'deprecated';
  include_keywords?: string[];
  exclude_keywords?: string[];
};

type ExampleFormValues = {
  example_type: 'positive' | 'negative';
  text_raw: string;
  source: string;
  test_case_id?: string;
};

const statusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Active', value: 'active' },
  { label: 'Deprecated', value: 'deprecated' },
];

const exampleTypeOptions = [
  { label: 'Positive', value: 'positive' },
  { label: 'Negative', value: 'negative' },
];

const routeKeyPattern = /^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,3}$/;
const routeKeyEnvironmentSegments = new Set(['dev', 'staging', 'prod', 'production']);

const intentHelp = {
  intentId: '릴리즈와 테스트 CSV에서 참조하는 고정 기술 ID입니다. 생성 후에는 변경할 수 없습니다. 예: it_password_reset',
  domain: 'Intent를 묶는 업무 영역입니다. 검색/필터와 운영 분류에 사용됩니다. 예: it, billing, account',
  displayName: '운영자가 화면에서 알아보기 쉬운 표시 이름입니다. 라우팅 로직의 고정 키는 아닙니다.',
  description: '이 Intent가 어떤 사용자 요청을 담당하는지 짧게 설명합니다. 운영 검토와 테스트 작성에 사용됩니다.',
  routeKey: '다운스트림 시스템으로 넘길 라우팅 키입니다. 점(.)으로 구분된 3~4개 소문자 segment를 사용합니다. 예: it.password_reset.self_service',
  includeKeywords: '이 Intent 판단에 도움이 되는 단어를 입력합니다. 쉼표로 여러 개를 추가할 수 있습니다.',
  excludeKeywords: '이 Intent가 아니라고 판단할 때 도움이 되는 단어를 입력합니다.',
  exampleType: 'Positive는 해당 Intent에 맞는 문장, Negative는 해당 Intent로 분류되면 안 되는 문장입니다.',
  rawText: '사용자가 실제로 입력할 법한 문장을 넣습니다. 저장 후 화면에는 마스킹된 텍스트가 표시됩니다.',
  source: '이 예시가 어디서 왔는지 남기는 값입니다. 예: admin_ui, ticket_sample, qa_seed',
  testCaseId: '선택 항목입니다. 별도 테스트 케이스와 연결할 때만 입력합니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

const normalizeTags = (values?: string[]) =>
  Array.from(new Set((values ?? []).map((value) => value.trim()).filter(Boolean)));

const trimOptional = (value?: string) => {
  const trimmed = value?.trim();
  return trimmed || null;
};

const validateRouteKey = (_: unknown, value?: string) => {
  const routeKey = value?.trim() ?? '';
  if (!routeKey) return Promise.resolve();
  if (!routeKeyPattern.test(routeKey)) {
    return Promise.reject(
      new Error('Route key는 예: it.test.manual_lookup 처럼 점(.)으로 구분된 3~4개 소문자 segment여야 합니다.'),
    );
  }
  if (routeKey.split('.').some((segment) => routeKeyEnvironmentSegments.has(segment))) {
    return Promise.reject(
      new Error('Route key segment에는 dev, staging, prod, production을 사용할 수 없습니다.'),
    );
  }
  return Promise.resolve();
};

export default function IntentsPage() {
  const { session } = useModel('adminSession');
  const [selected, setSelected] = useState<API.Intent>();
  const [examples, setExamples] = useState<API.Example[]>([]);
  const [examplesLoading, setExamplesLoading] = useState(false);
  const [catalogReloadKey, setCatalogReloadKey] = useState(0);
  const [intentDrawerOpen, setIntentDrawerOpen] = useState(false);
  const [intentFormMode, setIntentFormMode] = useState<IntentFormMode>('create');
  const [editingIntent, setEditingIntent] = useState<API.Intent>();
  const [intentSaving, setIntentSaving] = useState(false);
  const [exampleDrawerOpen, setExampleDrawerOpen] = useState(false);
  const [exampleSaving, setExampleSaving] = useState(false);
  const [intentForm] = Form.useForm<IntentFormValues>();
  const [exampleForm] = Form.useForm<ExampleFormValues>();
  const serviceIdRef = useRef(session.serviceId);
  const ready = isAdminSessionReady(session);
  const catalogEditable = ready && canEditCatalog(session);

  useEffect(() => {
    serviceIdRef.current = session.serviceId;
    setSelected(undefined);
    setExamples([]);
    setIntentDrawerOpen(false);
    setEditingIntent(undefined);
    setExampleDrawerOpen(false);
    intentForm.resetFields();
    exampleForm.resetFields();
  }, [exampleForm, intentForm, session.serviceId]);

  const loadSelectedExamples = useCallback(
    async (intentId = selected?.intent_id) => {
      if (!ready || !intentId) {
        setExamples([]);
        return;
      }
      const serviceId = session.serviceId;
      setExamplesLoading(true);
      try {
        const rows = await listExamples(serviceId, intentId);
        if (serviceIdRef.current !== serviceId) return;
        setExamples(rows);
      } finally {
        setExamplesLoading(false);
      }
    },
    [ready, selected?.intent_id, session.serviceId],
  );

  useEffect(() => {
    loadSelectedExamples();
  }, [loadSelectedExamples]);

  const refreshCatalog = () => setCatalogReloadKey((current) => current + 1);

  const openCreateIntent = () => {
    setEditingIntent(undefined);
    setIntentFormMode('create');
    intentForm.resetFields();
    intentForm.setFieldsValue({
      include_keywords: [],
      exclude_keywords: [],
    });
    setIntentDrawerOpen(true);
  };

  const openEditIntent = (intent: API.Intent) => {
    setEditingIntent(intent);
    setIntentFormMode('edit');
    intentForm.resetFields();
    intentForm.setFieldsValue({
      intent_id: intent.intent_id,
      domain: intent.domain,
      display_name: intent.display_name,
      description: intent.description,
      route_key: intent.route_key,
      status: intent.status as IntentFormValues['status'],
      include_keywords: intent.include_keywords,
      exclude_keywords: intent.exclude_keywords,
    });
    setIntentDrawerOpen(true);
  };

  const closeIntentDrawer = () => {
    setIntentDrawerOpen(false);
    setEditingIntent(undefined);
    intentForm.resetFields();
  };

  const handleIntentSubmit = async (values: IntentFormValues) => {
    const serviceId = session.serviceId;
    setIntentSaving(true);
    try {
      const payloadBase = {
        domain: values.domain.trim(),
        display_name: values.display_name.trim(),
        description: values.description.trim(),
        route_key: values.route_key.trim(),
        include_keywords: normalizeTags(values.include_keywords),
        exclude_keywords: normalizeTags(values.exclude_keywords),
      };

      if (intentFormMode === 'create') {
        const created = await createIntent(serviceId, {
          intent_id: values.intent_id.trim(),
          ...payloadBase,
        });
        if (serviceIdRef.current !== serviceId) return;
        setSelected(created);
        message.success('Intent가 추가되었습니다.');
      } else if (editingIntent) {
        const updated = await patchIntent(serviceId, editingIntent.intent_id, {
          ...payloadBase,
          status: values.status,
        });
        if (serviceIdRef.current !== serviceId) return;
        setSelected((current) =>
          current?.intent_id === editingIntent.intent_id ? updated : current,
        );
        message.success('Intent가 저장되었습니다.');
      }

      refreshCatalog();
      closeIntentDrawer();
    } finally {
      setIntentSaving(false);
    }
  };

  const openExampleDrawer = () => {
    exampleForm.resetFields();
    exampleForm.setFieldsValue({ example_type: 'positive', source: 'admin_ui' });
    setExampleDrawerOpen(true);
  };

  const closeExampleDrawer = () => {
    setExampleDrawerOpen(false);
    exampleForm.resetFields();
  };

  const closeDetailDrawer = () => {
    setSelected(undefined);
    closeExampleDrawer();
  };

  const handleExampleSubmit = async (values: ExampleFormValues) => {
    if (!selected) return;
    const serviceId = session.serviceId;
    const intentId = selected.intent_id;
    setExampleSaving(true);
    try {
      await createExample(serviceId, intentId, {
        example_type: values.example_type,
        text_raw: values.text_raw.trim(),
        source: values.source.trim(),
        test_case_id: trimOptional(values.test_case_id),
      });
      if (serviceIdRef.current !== serviceId) return;
      message.success('Example이 추가되었습니다.');
      closeExampleDrawer();
      await loadSelectedExamples(intentId);
    } finally {
      setExampleSaving(false);
    }
  };

  const exampleColumns = useMemo<TableProps<API.Example>['columns']>(() => {
    const columns: TableProps<API.Example>['columns'] = [
      {
        title: 'Type',
        dataIndex: 'example_type',
        width: 96,
        render: (value: string) => (
          <Tag color={value === 'positive' ? 'green' : 'default'}>{value}</Tag>
        ),
      },
      {
        title: 'Text',
        dataIndex: 'text_masked',
        render: (value: string) => <Typography.Text>{value}</Typography.Text>,
      },
      {
        title: 'Source',
        dataIndex: 'source',
        width: 120,
      },
      {
        title: 'Status',
        dataIndex: 'approved',
        width: 96,
        render: (approved: boolean) =>
          approved ? <Tag color="green">승인됨</Tag> : <Tag color="orange">대기</Tag>,
      },
    ];

    if (catalogEditable) {
      columns.push({
        title: '',
        width: 96,
        render: (_, row) =>
          row.approved ? null : (
            <ConfirmActionButton
              type="link"
              size="small"
              title="Example 승인"
              content={`${row.example_id} example을 승인합니다.`}
              okText="승인"
              onConfirm={async () => {
                await approveExample(row.service_id, row.example_id);
              }}
              onSuccess={() => loadSelectedExamples(row.intent_id)}
            >
              승인
            </ConfirmActionButton>
          ),
      });
    }

    return columns;
  }, [catalogEditable, loadSelectedExamples, session.serviceId]);

  return (
    <AdminShell title="Intent Catalog">
      {ready ? (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <WorkflowNextActionBar
            title="다음 단계: Test Runs에서 검증"
            description="Intent와 Example을 정리한 뒤 Test Runs에서 검증 bundle을 만드세요."
            primaryLabel="Test Runs로 이동"
            onPrimary={() => history.push('/test-runs')}
            disabled={!catalogEditable}
          />
          <IntentCatalogTable
            key={`${session.serviceId}:${catalogReloadKey}`}
            serviceId={session.serviceId}
            canEditCatalog={catalogEditable}
            onSelectIntent={setSelected}
            onCreateIntent={openCreateIntent}
            onEditIntent={openEditIntent}
          />
        </Space>
      ) : (
        <AdminSessionRequired />
      )}
      <Drawer
        title={
          selected ? (
            <Space size={8}>
              <span className="text-mono">{selected.intent_id}</span>
              <StatusTag status={selected.status} />
            </Space>
          ) : undefined
        }
        width={560}
        open={Boolean(selected)}
        onClose={closeDetailDrawer}
        extra={
          catalogEditable && selected ? (
            <Button onClick={() => openEditIntent(selected)}>편집</Button>
          ) : null
        }
      >
        {selected ? (
          <Space direction="vertical" size={20} style={{ width: '100%' }}>
            <section className="intent-detail-section">
              <Typography.Title level={5} style={{ margin: 0 }}>
                기본 정보
              </Typography.Title>
              <Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="Display name">{selected.display_name}</Descriptions.Item>
                <Descriptions.Item label="Domain">{selected.domain}</Descriptions.Item>
                <Descriptions.Item label="Description">{selected.description}</Descriptions.Item>
                <Descriptions.Item label="Route key">
                  <Typography.Text copyable className="text-mono">
                    {selected.route_key}
                  </Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="Status">
                  <StatusTag status={selected.status} />
                </Descriptions.Item>
                <Descriptions.Item label="Created">{selected.created_at ?? '없음'}</Descriptions.Item>
                <Descriptions.Item label="Updated">{selected.updated_at ?? '없음'}</Descriptions.Item>
              </Descriptions>
            </section>

            <section className="intent-detail-section">
              <Typography.Title level={5} style={{ margin: 0 }}>
                키워드
              </Typography.Title>
              <div className="intent-keyword-groups">
                <div className="intent-keyword-group">
                  <Typography.Text strong>포함 키워드</Typography.Text>
                  {selected.include_keywords.length ? (
                    <Space wrap>
                      {selected.include_keywords.map((keyword) => (
                        <Tag color="green" key={`include:${keyword}`}>
                          + {keyword}
                        </Tag>
                      ))}
                    </Space>
                  ) : (
                    <Typography.Text type="secondary">없음</Typography.Text>
                  )}
                </div>
                <div className="intent-keyword-group">
                  <Typography.Text strong>제외 키워드</Typography.Text>
                  {selected.exclude_keywords.length ? (
                    <Space wrap>
                      {selected.exclude_keywords.map((keyword) => (
                        <Tag key={`exclude:${keyword}`}>- {keyword}</Tag>
                      ))}
                    </Space>
                  ) : (
                    <Typography.Text type="secondary">없음</Typography.Text>
                  )}
                </div>
              </div>
            </section>

            <section className="intent-detail-section">
              <div className="intent-detail-examples-header">
                <Typography.Title level={5} style={{ margin: 0 }}>
                  Examples
                </Typography.Title>
                {catalogEditable ? (
                  <Button type="primary" onClick={openExampleDrawer}>
                    Example 추가
                  </Button>
                ) : null}
              </div>
              <Alert
                type="info"
                showIcon
                message="Example은 사용자가 실제로 입력할 법한 예시 문장입니다."
                description="현재 백엔드는 Example 추가와 승인만 제공합니다. 편집/삭제/반려는 Phase 2 항목입니다."
              />
              <Table<API.Example>
                rowKey="example_id"
                size="small"
                loading={examplesLoading}
                dataSource={examples}
                columns={exampleColumns}
                pagination={false}
                scroll={{ x: true }}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              />
            </section>
          </Space>
        ) : null}
      </Drawer>
      <Drawer
        title={intentFormMode === 'create' ? 'Intent 추가' : 'Intent 편집'}
        width={560}
        open={intentDrawerOpen}
        onClose={closeIntentDrawer}
        destroyOnClose
        footer={
          <Space style={{ justifyContent: 'flex-end', width: '100%' }}>
            <Button onClick={closeIntentDrawer}>취소</Button>
            <Button type="primary" htmlType="submit" form="intent-form" loading={intentSaving}>
              저장
            </Button>
          </Space>
        }
      >
        <Form<IntentFormValues>
          id="intent-form"
          form={intentForm}
          layout="vertical"
          requiredMark={false}
          onFinish={handleIntentSubmit}
        >
          <Form.Item
            label={helpLabel('Intent ID', intentHelp.intentId)}
            name="intent_id"
            rules={[{ required: true, whitespace: true, message: 'Intent ID를 입력하세요.' }]}
          >
            <Input disabled={intentFormMode === 'edit'} />
          </Form.Item>
          <Form.Item
            label={helpLabel('Domain', intentHelp.domain)}
            name="domain"
            rules={[{ required: true, whitespace: true, message: 'Domain을 입력하세요.' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label={helpLabel('Display name', intentHelp.displayName)}
            name="display_name"
            rules={[{ required: true, whitespace: true, message: 'Display name을 입력하세요.' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label={helpLabel('Description', intentHelp.description)}
            name="description"
            rules={[{ required: true, whitespace: true, message: 'Description을 입력하세요.' }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label={helpLabel('Route key', intentHelp.routeKey)}
            name="route_key"
            rules={[
              { required: true, whitespace: true, message: 'Route key를 입력하세요.' },
              { validator: validateRouteKey },
            ]}
          >
            <Input />
          </Form.Item>
          {intentFormMode === 'edit' ? (
            <Form.Item
              label="Status"
              name="status"
              rules={[{ required: true, message: 'Status를 선택하세요.' }]}
            >
              <Select options={statusOptions} />
            </Form.Item>
          ) : null}
          <Form.Item
            label={helpLabel('Include keywords', intentHelp.includeKeywords)}
            name="include_keywords"
          >
            <Select
              mode="tags"
              tokenSeparators={[',']}
              open={false}
              placeholder="이 Intent 판단에 도움이 되는 단어를 입력합니다."
            />
          </Form.Item>
          <Form.Item
            label={helpLabel('Exclude keywords', intentHelp.excludeKeywords)}
            name="exclude_keywords"
          >
            <Select
              mode="tags"
              tokenSeparators={[',']}
              open={false}
              placeholder="이 Intent가 아니라고 판단할 때 도움이 되는 단어를 입력합니다."
            />
          </Form.Item>
        </Form>
      </Drawer>
      <Drawer
        title={selected ? `${selected.intent_id} Example 추가` : 'Example 추가'}
        width={560}
        open={exampleDrawerOpen}
        onClose={closeExampleDrawer}
        destroyOnClose
        footer={
          <Space style={{ justifyContent: 'flex-end', width: '100%' }}>
            <Button onClick={closeExampleDrawer}>취소</Button>
            <Button type="primary" htmlType="submit" form="example-form" loading={exampleSaving}>
              저장
            </Button>
          </Space>
        }
      >
        <Form<ExampleFormValues>
          id="example-form"
          form={exampleForm}
          layout="vertical"
          requiredMark={false}
          onFinish={handleExampleSubmit}
        >
          <Form.Item
            label={helpLabel('Type', intentHelp.exampleType)}
            name="example_type"
            rules={[{ required: true, message: 'Type을 선택하세요.' }]}
          >
            <Select options={exampleTypeOptions} />
          </Form.Item>
          <Form.Item
            label={helpLabel('Raw text', intentHelp.rawText)}
            name="text_raw"
            rules={[{ required: true, whitespace: true, message: 'Example 문장을 입력하세요.' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item
            label={helpLabel('Source', intentHelp.source)}
            name="source"
            rules={[{ required: true, whitespace: true, message: 'Source를 입력하세요.' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label={helpLabel('Test case ID', intentHelp.testCaseId)}
            name="test_case_id"
          >
            <Input />
          </Form.Item>
        </Form>
      </Drawer>
    </AdminShell>
  );
}
