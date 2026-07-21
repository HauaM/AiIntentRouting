import { useEffect, useRef, useState } from 'react';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Form,
  Input,
  Space,
  Steps,
  Tabs,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { StatusTag } from '@/components/StatusTag';
import { WorkflowNextActionBar } from '@/components/WorkflowNextActionBar';
import { canEditCatalog, isAdminSessionReady } from '@/models/adminSession';
import {
  createTestRun,
  fetchTestRun,
  fetchTestRunDiagnostics,
  fetchTestRunResults,
} from '@/services/adminServices';
import { CatalogVersionStep } from './CatalogVersionStep';
import { CsvCasesGrid } from './CsvCasesGrid';
import { CsvImportModal } from './CsvImportModal';
import { TestRunCatalogStatusPanel } from './TestRunCatalogStatusPanel';
import { TestRunDiagnosticsPanel } from './TestRunDiagnosticsPanel';
import { TestRunHistorySelect } from './TestRunHistorySelect';
import { TestPolicyPanel } from './TestPolicyPanel';
import {
  buildCsvText,
  downloadCsvFile,
  type CsvCaseDraft,
} from './csvCaseBuilder';

const formatRate = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'none';
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
};

const resultLabel: Record<string, string> = {
  pass: '통과',
  fail: '실패',
  review: '검토',
};

const csvTemplate = [
  'case_id,query,expected_intent,case_type,memo',
  'tc-001,password reset help,it_password_reset,positive,known happy path',
  'tc-002,maybe login maybe password,,clarify,should request clarification',
].join('\n');

const testRunModeTabs = [
  { key: 'new', label: '새 테스트 실행' },
  { key: 'history', label: '기존 결과 불러오기' },
];

export default function TestRunsPage() {
  const { session } = useModel('adminSession');
  const [createForm] = Form.useForm<API.TestRunCreateRequest>();
  const [summary, setSummary] = useState<API.TestRunSummary>();
  const [results, setResults] = useState<API.TestRunResult[]>([]);
  const [diagnostics, setDiagnostics] = useState<API.TestRunDiagnostics | null>(null);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [policy, setPolicy] = useState<API.PolicyVersion>();
  const [catalogVersion, setCatalogVersion] = useState<string>();
  const [currentStep, setCurrentStep] = useState(0);
  const [csvCases, setCsvCases] = useState<CsvCaseDraft[]>([]);
  const [csvText, setCsvText] = useState(csvTemplate);
  const [csvImportOpen, setCsvImportOpen] = useState(false);
  const [selectedCatalogVersion, setSelectedCatalogVersion] =
    useState<API.CatalogVersionListItem>();
  const [testRunMode, setTestRunMode] = useState<'new' | 'history'>('new');
  const [selectedHistoryRun, setSelectedHistoryRun] = useState<API.TestRunListItem>();
  const serviceIdRef = useRef(session.serviceId);
  const runRequestGenerationRef = useRef(0);
  const ready = isAdminSessionReady(session);
  const canRun = canEditCatalog(session);

  useEffect(() => {
    serviceIdRef.current = session.serviceId;
    runRequestGenerationRef.current += 1;
    setLoading(false);
    setSummary(undefined);
    setResults([]);
    setDiagnostics(null);
    setDiagnosticsLoading(false);
    setDiagnosticsError(null);
    setPolicy(undefined);
    setCatalogVersion(undefined);
    setSelectedCatalogVersion(undefined);
    setCsvCases([]);
    setCsvText(csvTemplate);
    setCsvImportOpen(false);
    setTestRunMode('new');
    setSelectedHistoryRun(undefined);
    setCurrentStep(0);
    createForm.resetFields();
  }, [createForm, session.serviceId]);

  useEffect(() => {
    const testRunId = summary?.test_run_id;
    if (currentStep !== 2 || !testRunId) {
      setDiagnostics(null);
      setDiagnosticsLoading(false);
      setDiagnosticsError(null);
      return;
    }

    let alive = true;
    setDiagnostics(null);
    setDiagnosticsError(null);
    setDiagnosticsLoading(true);
    fetchTestRunDiagnostics(session.serviceId, testRunId)
      .then((nextDiagnostics) => {
        if (alive) setDiagnostics(nextDiagnostics);
      })
      .catch(() => {
        if (alive) {
          setDiagnosticsError('진단 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
        }
      })
      .finally(() => {
        if (alive) setDiagnosticsLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [currentStep, session.serviceId, summary?.test_run_id]);

  const beginRunRequest = () => {
    runRequestGenerationRef.current += 1;
    setSummary(undefined);
    setResults([]);
    return runRequestGenerationRef.current;
  };

  const isCurrentRunRequest = (requestGeneration: number, serviceId: string) =>
    serviceIdRef.current === serviceId &&
    runRequestGenerationRef.current === requestGeneration;

  const loadRun = async (
    testRunId: string,
    serviceId: string,
    requestGeneration: number,
  ) => {
    const nextSummary = await fetchTestRun(serviceId, testRunId);
    const nextResults = await fetchTestRunResults(serviceId, testRunId);
    if (!isCurrentRunRequest(requestGeneration, serviceId)) return false;
    setSummary(nextSummary);
    setResults(nextResults);
    setCurrentStep(2);
    return true;
  };

  const handleCreate = async () => {
    const serviceId = session.serviceId;
    if (!policy?.policy_version || !catalogVersion) {
      message.error('테스트 정책과 Catalog 버전을 먼저 준비하세요.');
      return;
    }
    if (!csvCases.length) {
      message.error('테스트 CSV 데이터를 먼저 등록하세요.');
      return;
    }
    const sourceFilename =
      createForm.getFieldValue('source_filename')?.trim() || 'test-cases.csv';
    let testRunCreated = false;
    const requestGeneration = beginRunRequest();
    setLoading(true);
    try {
      const created = await createTestRun(serviceId, {
        policy_version: policy.policy_version,
        intent_catalog_version: catalogVersion,
        source_filename: sourceFilename,
        csv_text: buildCsvText(csvCases),
      });
      testRunCreated = true;
      if (!isCurrentRunRequest(requestGeneration, serviceId)) return;
      setSummary(created);
      setCurrentStep(2);
      const nextResults = await fetchTestRunResults(serviceId, created.test_run_id);
      if (!isCurrentRunRequest(requestGeneration, serviceId)) return;
      setResults(nextResults);
      message.success('테스트 실행을 생성했습니다.');
    } catch {
      if (!isCurrentRunRequest(requestGeneration, serviceId)) return;
      if (testRunCreated) {
        message.error('테스트 실행은 생성되었지만 결과를 불러오지 못했습니다.');
      } else {
        message.error('테스트 실행 생성에 실패했습니다.');
      }
    } finally {
      if (isCurrentRunRequest(requestGeneration, serviceId)) setLoading(false);
    }
  };

  const handleHistoryRunSelect = (testRun: API.TestRunListItem) => {
    setSelectedHistoryRun(testRun);
    setSummary(testRun);
    setResults([]);
  };

  const handleHistoryResultOpen = async () => {
    if (!selectedHistoryRun) return;
    const serviceId = session.serviceId;
    const requestGeneration = beginRunRequest();
    setLoading(true);
    try {
      const loaded = await loadRun(
        selectedHistoryRun.test_run_id,
        serviceId,
        requestGeneration,
      );
      if (loaded) message.success('테스트 실행 결과를 불러왔습니다.');
    } catch {
      if (isCurrentRunRequest(requestGeneration, serviceId)) {
        message.error('테스트 실행 결과를 불러오지 못했습니다.');
      }
    } finally {
      if (isCurrentRunRequest(requestGeneration, serviceId)) setLoading(false);
    }
  };

  const columns: ProColumns<API.TestRunResult>[] = [
    {
      title: '케이스',
      dataIndex: 'case_id',
      copyable: true,
      width: 140,
      render: (_, row) => <Typography.Text code>{row.case_id}</Typography.Text>,
    },
    {
      title: '마스킹된 질의',
      dataIndex: 'query_masked',
      search: false,
      render: (text) => <span className="masked-query">{text}</span>,
    },
    {
      title: '기대 결과',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span>{row.expected_decision}</span>
          <span className="muted-small">{row.expected_intent ?? '인텐트 없음'}</span>
        </Space>
      ),
    },
    {
      title: '실제 결과',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span>{row.actual_decision}</span>
          <span className="muted-small">
            {row.actual_intent ?? row.actual_route_key ?? '없음'}
          </span>
        </Space>
      ),
    },
    {
      title: '신뢰도',
      dataIndex: 'confidence',
      search: false,
      width: 112,
      renderText: (value) =>
        value === null || value === undefined ? '없음' : Number(value).toFixed(3),
    },
    {
      title: '결과',
      dataIndex: 'result',
      valueType: 'select',
      valueEnum: {
        pass: { text: '통과' },
        fail: { text: '실패' },
        review: { text: '검토' },
      },
      width: 104,
      render: (_, row) => {
        const normalizedResult = row.result.toLowerCase();
        return (
          <StatusTag
            status={normalizedResult}
            label={resultLabel[normalizedResult] ?? row.result}
          />
        );
      },
    },
    {
      title: '사유',
      dataIndex: 'reason',
      search: false,
      ellipsis: true,
    },
  ];

  return (
    <AdminShell title="Test Runs">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {ready ? (
          <>
            {canRun ? (
              <div className="ds-page-card steps-form-page-card">
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  <Steps
                    current={currentStep}
                    items={[
                      { title: 'Intent Catalog 선택' },
                      { title: '테스트 설정' },
                      { title: '테스트 결과 확인' },
                    ]}
                  />
                  {currentStep === 0 ? (
                    <Tabs
                      activeKey={testRunMode}
                      onChange={(key) => setTestRunMode(key as 'new' | 'history')}
                      items={testRunModeTabs}
                    />
                  ) : null}
                  {currentStep === 0 && testRunMode === 'new' ? (
                    <CatalogVersionStep
                      key={session.serviceId}
                      serviceId={session.serviceId}
                      value={selectedCatalogVersion}
                      onChange={(nextCatalogVersion) => {
                        setSelectedCatalogVersion(nextCatalogVersion);
                        setCatalogVersion(nextCatalogVersion?.intent_catalog_version);
                        createForm.setFieldsValue({
                          intent_catalog_version: nextCatalogVersion?.intent_catalog_version,
                        });
                      }}
                    />
                  ) : null}
                  {currentStep === 0 && testRunMode === 'history' ? (
                    <div aria-label="기존 테스트 실행 결과">
                        <TestRunHistorySelect
                          key={session.serviceId}
                          serviceId={session.serviceId}
                          value={selectedHistoryRun?.test_run_id}
                          disabled={!canRun}
                          loading={loading}
                          onSelect={handleHistoryRunSelect}
                        />
                    </div>
                  ) : null}
                  {currentStep === 1 ? (
                    <Form
                      form={createForm}
                      layout="vertical"
                      initialValues={{ source_filename: 'test-cases.csv' }}
                    >
                      <Form.Item name="policy_version" hidden>
                        <Input />
                      </Form.Item>
                      <Form.Item name="intent_catalog_version" hidden>
                        <Input />
                      </Form.Item>
                      <Form.Item
                        name="source_filename"
                        label="CSV 파일명"
                        rules={[
                          {
                            required: true,
                            whitespace: true,
                            message: 'CSV 파일명을 입력하세요.',
                          },
                        ]}
                      >
                        <Input placeholder="test-cases.csv" style={{ width: 220 }} />
                      </Form.Item>
                      <TestPolicyPanel
                        serviceId={session.serviceId}
                        policy={policy}
                        onPolicyCreated={(nextPolicy) => {
                          setPolicy(nextPolicy);
                          createForm.setFieldsValue({
                            policy_version: nextPolicy.policy_version,
                          });
                        }}
                      />
                      <div style={{ marginTop: 16 }}>
                        <CsvCasesGrid
                          cases={csvCases}
                          sourceFilename={
                            createForm.getFieldValue('source_filename') || 'test-cases.csv'
                          }
                          onImport={() => setCsvImportOpen(true)}
                          onExport={() =>
                            downloadCsvFile(
                              createForm.getFieldValue('source_filename') || 'test-cases.csv',
                              csvCases,
                            )
                          }
                        />
                      </div>
                    </Form>
                  ) : null}
                  {currentStep === 2 ? (
                    <Space direction="vertical" size={16} style={{ width: '100%' }}>
                      {summary ? (
                        <section>
                          <Typography.Title level={5} style={{ marginTop: 0 }}>
                            테스트 요약
                          </Typography.Title>
                          <Alert
                            type={summary.gate_passed ? 'success' : 'warning'}
                            showIcon
                            style={{ marginBottom: 12 }}
                            message={
                              summary.gate_passed
                                ? <>
                                    Release 생성에 사용할 <Typography.Text code>test_run_id</Typography.Text>가 준비되었습니다.
                                  </>
                                : 'Release 생성 전에 차단 사유를 해결해야 합니다.'
                            }
                            description={
                              <>
                                Release에는 <Typography.Text code>test_run_id</Typography.Text>와 테스트에 사용한
                                version 값을 그대로 입력합니다.
                              </>
                            }
                          />
                          <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
                            <Descriptions.Item label="테스트 실행 ID">
                              <Typography.Text code>{summary.test_run_id}</Typography.Text>
                            </Descriptions.Item>
                            <Descriptions.Item label="데이터셋">
                              {summary.test_dataset_version}
                            </Descriptions.Item>
                            <Descriptions.Item label="정책 기준">
                              {summary.threshold_preset} / {summary.threshold_value}
                            </Descriptions.Item>
                            <Descriptions.Item label="통과율">
                              {formatRate(summary.pass_rate)}
                            </Descriptions.Item>
                            <Descriptions.Item label="검토율">
                              {formatRate(summary.review_rate)}
                            </Descriptions.Item>
                            <Descriptions.Item label="위험 통과율">
                              {formatRate(summary.risk_pass_rate)}
                            </Descriptions.Item>
                            <Descriptions.Item label="검증 게이트">
                              <StatusTag
                                status={summary.gate_passed ? 'pass' : 'blocked'}
                                label={summary.gate_passed ? '통과' : '차단'}
                              />
                            </Descriptions.Item>
                            <Descriptions.Item label="차단 사유">
                              {summary.block_reasons.length
                                ? summary.block_reasons.join(', ')
                                : '없음'}
                            </Descriptions.Item>
                            <Descriptions.Item label="권장 조치">
                              {summary.recommendations.length
                                ? summary.recommendations.join(', ')
                                : '없음'}
                            </Descriptions.Item>
                          </Descriptions>
                          {summary.gate_passed && summary.risk_pass_rate === 1 ? (
                            <WorkflowNextActionBar
                              title="Release 후보 준비 완료"
                              description="이 test run으로 Release 화면에서 후보를 선택할 수 있습니다."
                              primaryLabel="Release 화면으로 이동"
                              onPrimary={() => history.push('/releases')}
                            />
                          ) : null}
                        </section>
                      ) : (
                          <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="조회된 테스트 실행이 없습니다."
                        />
                      )}
                      <TestRunDiagnosticsPanel
                        testRunId={summary?.test_run_id}
                        diagnostics={diagnostics}
                        diagnosticsLoading={diagnosticsLoading}
                        diagnosticsError={diagnosticsError}
                        results={results}
                      />
                      <ProTable<API.TestRunResult>
                        rowKey="case_id"
                        columns={columns}
                        dataSource={results}
                        search={false}
                        pagination={false}
                        options={{ density: true, fullScreen: false, reload: false, setting: true }}
                        locale={{
                          emptyText: (
                            <Empty
                              image={Empty.PRESENTED_IMAGE_SIMPLE}
                              description="조회된 테스트 실행 결과가 없습니다."
                            />
                          ),
                        }}
                      />
                      <TestRunCatalogStatusPanel diagnostics={diagnostics} />
                    </Space>
                  ) : null}
                  <Space wrap>
                    <Button
                      disabled={currentStep === 0}
                      onClick={() => setCurrentStep((step) => Math.max(step - 1, 0))}
                    >
                      이전
                    </Button>
                    {currentStep < 1 && testRunMode === 'new' ? (
                      <Button
                        type="primary"
                        disabled={!catalogVersion}
                        onClick={() => setCurrentStep(1)}
                      >
                        다음 → 테스트 설정
                      </Button>
                    ) : null}
                    {currentStep < 1 && testRunMode === 'history' ? (
                      <Button
                        type="primary"
                        loading={loading}
                        disabled={!selectedHistoryRun}
                        onClick={handleHistoryResultOpen}
                      >
                        결과 확인 → Step 3
                      </Button>
                    ) : null}
                    {currentStep === 1 ? (
                      <Button
                        type="primary"
                        loading={loading}
                        disabled={!policy?.policy_version || !catalogVersion || !csvCases.length}
                        onClick={handleCreate}
                      >
                        테스트 실행 생성
                      </Button>
                    ) : null}
                  </Space>
                </Space>
              </div>
            ) : (
              <Alert
                type="info"
                showIcon
                message="테스트 실행 작업 권한이 필요합니다."
                description="선택한 서비스의 system_admin, service_owner, service_developer 역할만 테스트 실행 생성과 조회를 사용할 수 있습니다."
              />
            )}
            <CsvImportModal
              open={csvImportOpen}
              initialCsvText={csvText}
              onCancel={() => setCsvImportOpen(false)}
              onSave={(nextCases, nextCsvText) => {
                setCsvCases(nextCases);
                setCsvText(nextCsvText);
                setCsvImportOpen(false);
                message.success('CSV 데이터를 적용했습니다.');
              }}
            />
          </>
        ) : (
          <AdminSessionRequired />
        )}
      </Space>
    </AdminShell>
  );
}
