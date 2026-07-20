import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MoreOutlined } from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import type { TableProps } from 'antd';
import {
  Alert,
  Button,
  Descriptions,
  Dropdown,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
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
  createCatalogVersion,
  createExample,
  createIntent,
  deactivateCatalogVersion,
  deleteExample,
  deleteIntent,
  fetchCatalogVersionDiff,
  listCatalogVersions,
  listExamples,
  loadCatalogVersionToDraft,
  patchExample,
  patchIntent,
} from '@/services/adminServices';
import { CatalogVersionCreateModal } from './CatalogVersionCreateModal';
import {
  CatalogVersionDiffDrawer,
  selectCatalogVersionDiffBaseline,
} from './CatalogVersionDiffDrawer';
import { CatalogVersionHistoryModal } from './CatalogVersionHistoryModal';
import { CatalogVersionPanel } from './CatalogVersionPanel';
import type { CatalogPageState } from './catalogVersionTypes';

type IntentFormMode = 'create' | 'edit';
type ExampleFormMode = 'create' | 'edit';

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
  example_type?: 'positive' | 'negative';
  text_raw?: string;
  positive_text_raw?: string;
  negative_text_raw?: string;
  source: string;
};

const statusOptions = [
  { label: 'Draft', value: 'draft' },
  { label: 'Active', value: 'active' },
  { label: 'Deprecated', value: 'deprecated' },
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
  positiveExamples: '이 Intent에 해당하는 문장을 한 줄에 하나씩 입력합니다.',
  negativeExamples: '이 Intent로 분류되면 안 되는 헷갈리는 문장을 한 줄에 하나씩 입력합니다.',
  source: '이 예시가 어디서 왔는지 남기는 값입니다. 예: admin_ui, ticket_sample, qa_seed',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

const normalizeTags = (values?: string[]) =>
  Array.from(new Set((values ?? []).map((value) => value.trim()).filter(Boolean)));

const splitExampleLines = (value?: string) =>
  (value ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

const getOperationErrorMessage = (error: unknown) =>
  error instanceof Error ? error.message : '요청 처리 중 오류가 발생했습니다.';

const buildExampleCreateRequests = (values: ExampleFormValues): API.ExampleCreateRequest[] => {
  const source = values.source.trim();
  const toRequest = (
    example_type: API.ExampleCreateRequest['example_type'],
    text_raw: string,
  ): API.ExampleCreateRequest => ({
    example_type,
    text_raw,
    source,
  });

  return [
    ...splitExampleLines(values.positive_text_raw).map((text) =>
      toRequest('positive', text),
    ),
    ...splitExampleLines(values.negative_text_raw).map((text) =>
      toRequest('negative', text),
    ),
  ];
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
  const [exampleFormMode, setExampleFormMode] = useState<ExampleFormMode>('create');
  const [editingExample, setEditingExample] = useState<API.Example>();
  const [exampleSaving, setExampleSaving] = useState(false);
  const [catalogHistoryExists, setCatalogHistoryExists] = useState(false);
  const [catalogPageState, setCatalogPageState] = useState<CatalogPageState>();
  const [catalogVersionLoadOpen, setCatalogVersionLoadOpen] = useState(false);
  const [catalogVersionRows, setCatalogVersionRows] = useState<API.CatalogVersionListItem[]>([]);
  const [catalogVersionLoading, setCatalogVersionLoading] = useState(false);
  const [catalogVersionSelection, setCatalogVersionSelection] =
    useState<API.CatalogVersionListItem>();
  const [catalogVersionLoadingToDraft, setCatalogVersionLoadingToDraft] = useState(false);
  const [catalogVersionCreateOpen, setCatalogVersionCreateOpen] = useState(false);
  const [catalogVersionCreating, setCatalogVersionCreating] = useState(false);
  const [catalogVersionDiffOpen, setCatalogVersionDiffOpen] = useState(false);
  const [catalogVersionDiffLoading, setCatalogVersionDiffLoading] = useState(false);
  const [catalogVersionDiffTarget, setCatalogVersionDiffTarget] =
    useState<API.CatalogVersionListItem>();
  const [catalogVersionDiffBaseline, setCatalogVersionDiffBaseline] =
    useState<API.CatalogVersionListItem>();
  const [catalogVersionDiff, setCatalogVersionDiff] = useState<API.CatalogVersionDiff>();
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
    setEditingExample(undefined);
    setExampleFormMode('create');
    setCatalogHistoryExists(false);
    setCatalogPageState(undefined);
    setCatalogVersionLoadOpen(false);
    setCatalogVersionRows([]);
    setCatalogVersionSelection(undefined);
    setCatalogVersionCreateOpen(false);
    setCatalogVersionDiffOpen(false);
    setCatalogVersionDiffTarget(undefined);
    setCatalogVersionDiffBaseline(undefined);
    setCatalogVersionDiff(undefined);
    intentForm.resetFields();
    exampleForm.resetFields();
  }, [exampleForm, intentForm, session.serviceId]);

  const loadLatestCatalogVersionState = useCallback(async () => {
    if (!ready) {
      setCatalogHistoryExists(false);
      setCatalogPageState(undefined);
      return;
    }
    const serviceId = session.serviceId;
    const latestVersions = await listCatalogVersions(session.serviceId, { limit: 1 });
    const latestVersion = latestVersions[0];
    if (serviceIdRef.current !== serviceId) return;
    setCatalogHistoryExists(Boolean(latestVersion));
    setCatalogPageState(
      latestVersion ? { mode: 'version', version: latestVersion } : undefined,
    );
  }, [ready, session.serviceId]);

  useEffect(() => {
    void loadLatestCatalogVersionState();
  }, [loadLatestCatalogVersionState]);

  const markCatalogPageDraft = useCallback(() => {
    setCatalogPageState((current) => {
      if (!catalogHistoryExists) return current;
      if (current?.mode === 'draft') return current;
      return { mode: 'draft', sourceVersion: current?.version };
    });
  }, [catalogHistoryExists]);

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

  const reloadCatalogVersionRows = useCallback(async () => {
    if (!ready) return [];
    const serviceId = session.serviceId;
    setCatalogVersionLoading(true);
    try {
      const rows = await listCatalogVersions(serviceId, { limit: 100 });
      if (serviceIdRef.current !== serviceId) return [];
      setCatalogVersionRows(rows);
      return rows;
    } finally {
      if (serviceIdRef.current === serviceId) setCatalogVersionLoading(false);
    }
  }, [ready, session.serviceId]);

  const openCatalogVersionLoadModal = async () => {
    setCatalogVersionLoadOpen(true);
    setCatalogVersionSelection(undefined);
    await reloadCatalogVersionRows();
  };

  const handleCreateCatalogVersion = async (description: string) => {
    const serviceId = session.serviceId;
    setCatalogVersionCreating(true);
    try {
      const created = await createCatalogVersion(session.serviceId, { description });
      if (serviceIdRef.current !== serviceId) return;
      setCatalogHistoryExists(true);
      setCatalogPageState({ mode: 'version', version: created });
      message.success('Catalog 버전이 등록되었습니다.');
      setCatalogVersionCreateOpen(false);
      refreshCatalog();
      if (selected?.intent_id) await loadSelectedExamples(selected.intent_id);
      if (catalogVersionLoadOpen) await reloadCatalogVersionRows();
    } catch (error) {
      message.error(getOperationErrorMessage(error));
      throw error;
    } finally {
      if (serviceIdRef.current === serviceId) setCatalogVersionCreating(false);
    }
  };

  const openCatalogVersionDiff = async (row: API.CatalogVersionListItem) => {
    const serviceId = session.serviceId;
    const rows = catalogVersionRows.length
      ? catalogVersionRows
      : await reloadCatalogVersionRows();
    const baseline = selectCatalogVersionDiffBaseline(rows, row);
    setCatalogVersionDiffTarget(row);
    setCatalogVersionDiffBaseline(baseline);
    setCatalogVersionDiff(undefined);
    setCatalogVersionDiffOpen(true);
    setCatalogVersionDiffLoading(true);
    try {
      const result = await fetchCatalogVersionDiff(
        serviceId,
        row.intent_catalog_version,
        { compare_to: baseline?.intent_catalog_version },
      );
      if (serviceIdRef.current !== serviceId) return;
      setCatalogVersionDiff(result);
    } catch (error) {
      message.error(getOperationErrorMessage(error));
    } finally {
      if (serviceIdRef.current === serviceId) setCatalogVersionDiffLoading(false);
    }
  };

  const confirmLoadCatalogVersionToDraft = (version = catalogVersionSelection) => {
    if (!version) return;
    const target = version;
    Modal.confirm({
      title: `${target.display_version}을 초안으로 불러올까요?`,
      content: '현재 Intent Catalog 초안이 선택한 catalog version snapshot으로 갱신됩니다.',
      okText: '불러오기',
      cancelText: '취소',
      onOk: async () => {
        setCatalogVersionLoadingToDraft(true);
        try {
          const loaded = await loadCatalogVersionToDraft(
            session.serviceId,
            target.intent_catalog_version,
          );
          if (serviceIdRef.current !== session.serviceId) return;
          setCatalogHistoryExists(true);
          setCatalogPageState({ mode: 'draft', sourceVersion: loaded });
          setSelected(undefined);
          setExamples([]);
          setCatalogVersionLoadOpen(false);
          setCatalogVersionSelection(undefined);
          refreshCatalog();
          message.success('Catalog version을 초안으로 불러왔습니다.');
        } finally {
          setCatalogVersionLoadingToDraft(false);
        }
      },
    });
  };

  const confirmDeactivateCatalogVersion = (version: API.CatalogVersionListItem) => {
    const serviceId = session.serviceId;
    Modal.confirm({
      title: `${version.display_version}을 비활성화할까요?`,
      content: '비활성화하면 해당 버전의 embedding이 해제되어 테스트/런타임 후보로 사용할 수 없습니다.',
      okText: '비활성화',
      cancelText: '취소',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deactivateCatalogVersion(serviceId, version.intent_catalog_version);
          if (serviceIdRef.current !== serviceId) return;
          message.success('Catalog 버전이 비활성화되었습니다.');
          await loadLatestCatalogVersionState();
          if (catalogVersionLoadOpen) await reloadCatalogVersionRows();
        } catch (error) {
          message.error(getOperationErrorMessage(error));
          throw error;
        }
      },
    });
  };

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
        markCatalogPageDraft();
        setSelected(created);
        message.success('Intent가 추가되었습니다.');
      } else if (editingIntent) {
        const updated = await patchIntent(serviceId, editingIntent.intent_id, {
          ...payloadBase,
          status: values.status,
        });
        if (serviceIdRef.current !== serviceId) return;
        markCatalogPageDraft();
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

  const handleDeleteIntent = async (intent: API.Intent) => {
    const serviceId = session.serviceId;
    await deleteIntent(serviceId, intent.intent_id);
    if (serviceIdRef.current !== serviceId) return;
    setSelected((current) =>
      current?.intent_id === intent.intent_id ? undefined : current,
    );
    setExamples((current) =>
      selected?.intent_id === intent.intent_id ? [] : current,
    );
    markCatalogPageDraft();
    refreshCatalog();
  };

  const openExampleDrawer = () => {
    setEditingExample(undefined);
    setExampleFormMode('create');
    exampleForm.resetFields();
    exampleForm.setFieldsValue({
      positive_text_raw: '',
      negative_text_raw: '',
      source: 'admin_ui',
    });
    setExampleDrawerOpen(true);
  };

  const openEditExample = useCallback((example: API.Example) => {
    setEditingExample(example);
    setExampleFormMode('edit');
    exampleForm.resetFields();
    exampleForm.setFieldsValue({
      example_type: example.example_type as ExampleFormValues['example_type'],
      text_raw: '',
      source: example.source,
    });
    setExampleDrawerOpen(true);
  }, [exampleForm]);

  const closeExampleDrawer = () => {
    setExampleDrawerOpen(false);
    setEditingExample(undefined);
    setExampleFormMode('create');
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
    if (exampleFormMode === 'edit' && editingExample) {
      const payload: API.ExamplePatchRequest = {
        example_type: values.example_type,
        source: values.source.trim(),
      };
      const textRaw = values.text_raw?.trim();
      if (textRaw) {
        payload.text_raw = textRaw;
      }
      setExampleSaving(true);
      try {
        await patchExample(serviceId, editingExample.example_id, payload);
        if (serviceIdRef.current !== serviceId) return;
        markCatalogPageDraft();
        message.success('Example이 저장되었습니다.');
        closeExampleDrawer();
        await loadSelectedExamples(intentId);
      } finally {
        setExampleSaving(false);
      }
      return;
    }

    const requests = buildExampleCreateRequests(values);
    if (!requests.length) {
      message.warning('Positive 또는 Negative example을 한 줄 이상 입력하세요.');
      return;
    }

    const positiveCount = requests.filter(
      (request) => request.example_type === 'positive',
    ).length;
    const negativeCount = requests.length - positiveCount;
    setExampleSaving(true);
    try {
      await Promise.all(
        requests.map((request) => createExample(serviceId, intentId, request)),
      );
      if (serviceIdRef.current !== serviceId) return;
      markCatalogPageDraft();
      message.success(
        `Example ${requests.length}건이 추가되었습니다. Positive ${positiveCount}건, Negative ${negativeCount}건`,
      );
      closeExampleDrawer();
      await loadSelectedExamples(intentId);
    } finally {
      setExampleSaving(false);
    }
  };

  const confirmApproveExample = useCallback(
    (example: API.Example) => {
      Modal.confirm({
        title: 'Example 승인',
        content: `${example.example_id} example을 승인합니다.`,
        okText: '승인',
        cancelText: '취소',
        async onOk() {
          await approveExample(example.service_id, example.example_id);
          markCatalogPageDraft();
          message.success('처리되었습니다.');
          await loadSelectedExamples(example.intent_id);
        },
      });
    },
    [loadSelectedExamples, markCatalogPageDraft],
  );

  const confirmDeleteExample = useCallback(
    (example: API.Example) => {
      Modal.confirm({
        title: 'Example 삭제',
        content: `${example.example_id} example과 embedding을 삭제합니다.`,
        okText: '삭제',
        cancelText: '취소',
        okButtonProps: { danger: true },
        async onOk() {
          await deleteExample(example.service_id, example.example_id);
          markCatalogPageDraft();
          message.success('처리되었습니다.');
          await loadSelectedExamples(example.intent_id);
        },
      });
    },
    [loadSelectedExamples, markCatalogPageDraft],
  );

  const catalogStateVersion =
    catalogPageState?.mode === 'draft'
      ? catalogPageState.sourceVersion
      : catalogPageState?.version;

  const exampleColumns = useMemo<TableProps<API.Example>['columns']>(() => {
    const columns: TableProps<API.Example>['columns'] = [
      {
        title: 'Type',
        dataIndex: 'example_type',
        width: 80,
        render: (value: string) => (
          <Tag color={value === 'positive' ? 'green' : 'default'}>{value}</Tag>
        ),
      },
      {
        title: 'Text',
        dataIndex: 'text_masked',
        width: 220,
        render: (value: string) => (
          <Typography.Text className="intent-example-text">{value}</Typography.Text>
        ),
      },
      {
        title: 'Source',
        dataIndex: 'source',
        width: 88,
      },
      {
        title: 'Status',
        dataIndex: 'approved',
        width: 72,
        render: (approved: boolean) =>
          approved ? <Tag color="green">승인됨</Tag> : <Tag color="orange">대기</Tag>,
      },
    ];

    if (catalogEditable) {
      columns.push({
        title: '',
        width: 52,
        align: 'right',
        render: (_, row) => (
          <Dropdown
            menu={{
              items: [
                row.approved
                  ? null
                  : {
                      key: 'approve',
                      label: '승인',
                    },
                {
                  key: 'edit',
                  label: '편집',
                },
                {
                  key: 'delete',
                  label: '삭제',
                  danger: true,
                },
              ].filter(Boolean),
              onClick: ({ key }) => {
                if (key === 'approve') {
                  confirmApproveExample(row);
                  return;
                }
                if (key === 'edit') {
                  openEditExample(row);
                  return;
                }
                if (key === 'delete') {
                  confirmDeleteExample(row);
                }
              },
            }}
            trigger={['click']}
          >
            <Button
              aria-label="Example actions"
              icon={<MoreOutlined />}
              size="small"
              type="text"
            />
          </Dropdown>
        ),
      });
    }

    return columns;
  }, [catalogEditable, confirmApproveExample, confirmDeleteExample, openEditExample]);

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
          {!catalogHistoryExists && catalogEditable ? (
            <Space wrap>
              <Button type="primary" onClick={() => setCatalogVersionCreateOpen(true)}>
                Catalog 버전 등록
              </Button>
              <Button onClick={openCatalogVersionLoadModal}>
                Catalog version 불러오기
              </Button>
            </Space>
          ) : null}
          <CatalogVersionPanel
            state={catalogPageState}
            historyExists={catalogHistoryExists}
            canManage={catalogEditable}
            onCreate={() => setCatalogVersionCreateOpen(true)}
            onOpenHistory={openCatalogVersionLoadModal}
            onCompareCurrent={() => {
              if (catalogStateVersion) void openCatalogVersionDiff(catalogStateVersion);
            }}
            onDeactivateCurrent={() => {
              if (catalogStateVersion) confirmDeactivateCatalogVersion(catalogStateVersion);
            }}
          />
          <IntentCatalogTable
            key={`${session.serviceId}:${catalogReloadKey}`}
            serviceId={session.serviceId}
            canEditCatalog={catalogEditable}
            onSelectIntent={setSelected}
            onCreateIntent={openCreateIntent}
            onEditIntent={openEditIntent}
            onDeleteIntent={handleDeleteIntent}
          />
        </Space>
      ) : (
        <AdminSessionRequired />
      )}
      <CatalogVersionCreateModal
        open={catalogVersionCreateOpen}
        loading={catalogVersionCreating}
        onCancel={() => setCatalogVersionCreateOpen(false)}
        onCreate={handleCreateCatalogVersion}
      />
      <CatalogVersionHistoryModal
        open={catalogVersionLoadOpen}
        rows={catalogVersionRows}
        loading={catalogVersionLoading}
        loadingToDraft={catalogVersionLoadingToDraft}
        selectedVersion={catalogVersionSelection}
        canManage={catalogEditable}
        onCancel={() => setCatalogVersionLoadOpen(false)}
        onSelect={setCatalogVersionSelection}
        onLoadSelected={() => confirmLoadCatalogVersionToDraft()}
        onCompare={openCatalogVersionDiff}
        onLoadToDraft={confirmLoadCatalogVersionToDraft}
        onDeactivate={confirmDeactivateCatalogVersion}
      />
      <CatalogVersionDiffDrawer
        open={catalogVersionDiffOpen}
        loading={catalogVersionDiffLoading}
        target={catalogVersionDiffTarget}
        baseline={catalogVersionDiffBaseline}
        diff={catalogVersionDiff}
        onClose={() => setCatalogVersionDiffOpen(false)}
      />
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
            <Space className="intent-detail-actions">
              <Button onClick={() => openEditIntent(selected)}>편집</Button>
              <ConfirmActionButton
                danger
                title="Intent 삭제"
                content={`${selected.intent_id} Intent와 연결된 Example/embedding을 삭제합니다.`}
                okText="삭제"
                onConfirm={() => handleDeleteIntent(selected)}
                onSuccess={closeDetailDrawer}
              >
                삭제
              </ConfirmActionButton>
            </Space>
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
                description="수정/삭제 시 승인된 Example의 embedding도 함께 갱신 또는 제거됩니다."
              />
              <div className="intent-examples-table">
                <Table<API.Example>
                  rowKey="example_id"
                  size="small"
                  loading={examplesLoading}
                  dataSource={examples}
                  columns={exampleColumns}
                  pagination={false}
                  scroll={{ x: 512 }}
                  tableLayout="fixed"
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              </div>
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
        title={
          exampleFormMode === 'edit'
            ? 'Example 편집'
            : selected
              ? `${selected.intent_id} Example 추가`
              : 'Example 추가'
        }
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
          {exampleFormMode === 'create' ? (
            <>
              <Form.Item
                label={helpLabel('Positive examples', intentHelp.positiveExamples)}
                name="positive_text_raw"
              >
                <Input.TextArea
                  rows={6}
                  placeholder={'비밀번호를 재설정하고 싶어요\n로그인이 안 돼서 비밀번호 초기화가 필요합니다'}
                />
              </Form.Item>
              <Form.Item
                label={helpLabel('Negative examples', intentHelp.negativeExamples)}
                name="negative_text_raw"
              >
                <Input.TextArea
                  rows={6}
                  placeholder={'비밀번호 정책을 바꾸고 싶어요\n계정 잠금 해제 절차를 알려주세요'}
                />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item
                label="Type"
                name="example_type"
                rules={[{ required: true, message: 'Type을 선택하세요.' }]}
              >
                <Select
                  options={[
                    { label: 'Positive', value: 'positive' },
                    { label: 'Negative', value: 'negative' },
                  ]}
                />
              </Form.Item>
              <Form.Item
                label="Text raw"
                name="text_raw"
                extra="문장을 변경할 때만 새 raw text를 입력하세요. 승인된 Example은 저장 시 embedding이 다시 생성됩니다."
              >
                <Input.TextArea
                  rows={4}
                  placeholder={editingExample?.text_masked ?? '새 example 문장을 입력하세요.'}
                />
              </Form.Item>
            </>
          )}
          <Form.Item
            label={helpLabel('Source', intentHelp.source)}
            name="source"
            rules={[{ required: true, whitespace: true, message: 'Source를 입력하세요.' }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Drawer>
    </AdminShell>
  );
}
