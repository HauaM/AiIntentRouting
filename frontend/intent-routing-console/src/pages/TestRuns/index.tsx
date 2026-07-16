import { useEffect, useRef, useState } from 'react';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { AdminTableActions } from '@/components/AdminTableActions';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';
import { WorkflowNextActionBar } from '@/components/WorkflowNextActionBar';
import { canEditCatalog, isAdminSessionReady } from '@/models/adminSession';
import {
  createTestRun,
  fetchTestRun,
  fetchTestRunResults,
} from '@/services/adminServices';
import {
  ValidationBundlePanel,
  type ValidationBundle,
} from './ValidationBundlePanel';

const formatRate = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'none';
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
};

const resultColor: Record<string, string> = {
  pass: 'green',
  fail: 'red',
  review: 'orange',
};

const csvTemplate = [
  'case_id,query,expected_intent,case_type,memo',
  'tc-001,password reset help,it_password_reset,positive,known happy path',
].join('\n');

const testRunHelp = {
  sourceFilename: '업로드 파일명처럼 기록되는 이름입니다. 실제 파일 업로드가 아니라 CSV text 내용과 함께 저장됩니다.',
  csvText: '헤더는 반드시 case_id,query,expected_intent,case_type,memo 입니다. case_type은 positive, confusing, risk, off_topic, fallback 중 하나입니다. positive/confusing은 expected_intent가 필요하고, 나머지는 비워야 합니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

export default function TestRunsPage() {
  const { session } = useModel('adminSession');
  const [createForm] = Form.useForm<API.TestRunCreateRequest>();
  const [lookupForm] = Form.useForm<{ test_run_id: string }>();
  const [summary, setSummary] = useState<API.TestRunSummary>();
  const [results, setResults] = useState<API.TestRunResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [bundle, setBundle] = useState<ValidationBundle>({
    threshold_preset: 'balanced',
  });
  const serviceIdRef = useRef(session.serviceId);
  const ready = isAdminSessionReady(session);
  const canRun = canEditCatalog(session);

  useEffect(() => {
    serviceIdRef.current = session.serviceId;
    setSummary(undefined);
    setResults([]);
    lookupForm.resetFields();
    createForm.resetFields();
    setBundle({ threshold_preset: 'balanced' });
    createForm.setFieldsValue({ threshold_preset: 'balanced' });
  }, [createForm, lookupForm, session.serviceId]);

  const handleBundleChange = (nextBundle: ValidationBundle) => {
    setBundle(nextBundle);
    createForm.setFieldsValue({
      policy_version: nextBundle.policy_version,
      intent_catalog_version: nextBundle.intent_catalog_version,
      threshold_preset: nextBundle.threshold_preset,
    });
  };

  const loadRun = async (testRunId: string, serviceId = session.serviceId) => {
    const nextSummary = await fetchTestRun(serviceId, testRunId);
    const nextResults = await fetchTestRunResults(serviceId, testRunId);
    if (serviceIdRef.current !== serviceId) return false;
    setSummary(nextSummary);
    setResults(nextResults);
    lookupForm.setFieldsValue({ test_run_id: testRunId });
    return true;
  };

  const handleCreate = async (values: API.TestRunCreateRequest) => {
    const serviceId = session.serviceId;
    if (!bundle.policy_version || !bundle.intent_catalog_version) {
      message.error('Validation bundle을 먼저 불러오거나 생성하세요.');
      return;
    }
    setLoading(true);
    try {
      const created = await createTestRun(serviceId, {
        policy_version: values.policy_version.trim(),
        intent_catalog_version: values.intent_catalog_version.trim(),
        threshold_preset: values.threshold_preset,
        source_filename: values.source_filename.trim(),
        csv_text: values.csv_text.trim(),
      });
      if (serviceIdRef.current !== serviceId) return;
      setSummary(created);
      lookupForm.setFieldsValue({ test_run_id: created.test_run_id });
      const nextResults = await fetchTestRunResults(serviceId, created.test_run_id);
      if (serviceIdRef.current !== serviceId) return;
      setResults(nextResults);
      message.success('Test run created.');
    } finally {
      setLoading(false);
    }
  };

  const handleLookup = async (values: { test_run_id: string }) => {
    setLoading(true);
    try {
      const loaded = await loadRun(values.test_run_id.trim(), session.serviceId);
      if (loaded) message.success('Test run loaded.');
    } finally {
      setLoading(false);
    }
  };

  const columns: ProColumns<API.TestRunResult>[] = [
    {
      title: 'Case',
      dataIndex: 'case_id',
      copyable: true,
      width: 140,
      render: (_, row) => <Typography.Text code>{row.case_id}</Typography.Text>,
    },
    {
      title: 'Masked query',
      dataIndex: 'query_masked',
      search: false,
      render: (text) => <span className="masked-query">{text}</span>,
    },
    {
      title: 'Expected',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span>{row.expected_decision}</span>
          <span className="muted-small">{row.expected_intent ?? 'no intent'}</span>
        </Space>
      ),
    },
    {
      title: 'Actual',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span>{row.actual_decision}</span>
          <span className="muted-small">{row.actual_intent ?? row.actual_route_key ?? 'none'}</span>
        </Space>
      ),
    },
    {
      title: 'Confidence',
      dataIndex: 'confidence',
      search: false,
      width: 112,
      renderText: (value) => (value === null || value === undefined ? 'none' : Number(value).toFixed(3)),
    },
    {
      title: 'Result',
      dataIndex: 'result',
      valueType: 'select',
      valueEnum: {
        pass: { text: 'pass' },
        fail: { text: 'fail' },
        review: { text: 'review' },
      },
      width: 104,
      render: (_, row) => <Tag color={resultColor[row.result] ?? 'default'}>{row.result}</Tag>,
    },
    {
      title: 'Reason',
      dataIndex: 'reason',
      search: false,
      ellipsis: true,
    },
  ];

  return (
    <AdminShell title="Test Runs">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <FutureFeatureNotice
          compact
          title="CSV export"
          backendRequirement="Phase 2 backend export contracts are required before this console can generate downloadable result files."
        />
        {ready ? (
          <>
            {canRun ? (
              <Card title="Create test run">
                <Form
                  form={createForm}
                  layout="vertical"
                  onFinish={handleCreate}
                  initialValues={{ threshold_preset: 'balanced', source_filename: 'test-cases.csv' }}
                >
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="Test run은 릴리즈 전에 실행하는 검증입니다."
                    description="Validation bundle을 불러오거나 생성한 뒤 CSV 테스트를 실행하세요. 통과한 test run은 Release 화면에서 후보로 선택할 수 있습니다."
                  />
                  <Form.Item name="policy_version" hidden>
                    <Input />
                  </Form.Item>
                  <Form.Item name="intent_catalog_version" hidden>
                    <Input />
                  </Form.Item>
                  <Form.Item name="threshold_preset" hidden>
                    <Input />
                  </Form.Item>
                  <ValidationBundlePanel
                    serviceId={session.serviceId}
                    value={bundle}
                    onChange={handleBundleChange}
                  />
                  <Space wrap align="start" size={12} style={{ marginTop: 16 }}>
                    <Form.Item
                      name="source_filename"
                      label={helpLabel('CSV filename', testRunHelp.sourceFilename)}
                      rules={[{ required: true, whitespace: true, message: 'Filename is required.' }]}
                    >
                      <Input placeholder="test-cases.csv" style={{ width: 220 }} />
                    </Form.Item>
                    <Form.Item label="CSV example">
                      <Button
                        onClick={() => createForm.setFieldsValue({ csv_text: csvTemplate })}
                      >
                        CSV 예시 채우기
                      </Button>
                    </Form.Item>
                  </Space>
                  <Form.Item
                    name="csv_text"
                    label={helpLabel('CSV text', testRunHelp.csvText)}
                    rules={[{ required: true, whitespace: true, message: 'CSV text is required.' }]}
                  >
                    <Input.TextArea rows={8} placeholder={csvTemplate} />
                  </Form.Item>
                  <Space wrap>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={loading}
                      disabled={!bundle.policy_version || !bundle.intent_catalog_version}
                    >
                      Test run 생성
                    </Button>
                    {!bundle.policy_version || !bundle.intent_catalog_version ? (
                      <Typography.Text type="secondary">
                        Validation bundle이 필요합니다.
                      </Typography.Text>
                    ) : null}
                  </Space>
                </Form>
              </Card>
            ) : (
              <Alert
                type="info"
                showIcon
                message="Test run actions require catalog access"
                description="Create and fetch actions are available to system_admin, service_owner, and service_developer roles for the selected service."
              />
            )}
            <Card title="Fetch test run">
              <Form form={lookupForm} layout="inline" onFinish={handleLookup}>
                <Form.Item
                  name="test_run_id"
                  rules={[{ required: true, whitespace: true, message: 'Test run id is required.' }]}
                >
                  <Input placeholder="tr_..." style={{ width: 260 }} disabled={!canRun} />
                </Form.Item>
                <Button htmlType="submit" loading={loading} disabled={!canRun}>
                  결과 조회
                </Button>
              </Form>
            </Card>
            {summary ? (
              <Card title="Summary">
                <Alert
                  type={summary.gate_passed ? 'success' : 'warning'}
                  showIcon
                  style={{ marginBottom: 12 }}
                  message={
                    summary.gate_passed
                      ? 'Release 생성에 사용할 test_run_id가 준비되었습니다.'
                      : 'Release 생성 전에 blocked 사유를 해결해야 합니다.'
                  }
                  description="Release에는 이 test_run_id와 테스트에 사용한 version 값을 그대로 입력합니다."
                />
                <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
                  <Descriptions.Item label="Test run">
                    <Typography.Text code>{summary.test_run_id}</Typography.Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Dataset">
                    {summary.test_dataset_version}
                  </Descriptions.Item>
                  <Descriptions.Item label="Threshold">
                    {summary.threshold_preset} / {summary.threshold_value}
                  </Descriptions.Item>
                  <Descriptions.Item label="Pass rate">
                    {formatRate(summary.pass_rate)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Review rate">
                    {formatRate(summary.review_rate)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Risk pass">
                    {formatRate(summary.risk_pass_rate)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Gate">
                    <Tag color={summary.gate_passed ? 'green' : 'red'}>
                      {summary.gate_passed ? 'passed' : 'blocked'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Block reasons">
                    {summary.block_reasons.length ? summary.block_reasons.join(', ') : 'none'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Recommendations">
                    {summary.recommendations.length ? summary.recommendations.join(', ') : 'none'}
                  </Descriptions.Item>
                </Descriptions>
                {summary.gate_passed && summary.risk_pass_rate === 1 ? (
                  <WorkflowNextActionBar
                    title="Release candidate ready"
                    description="이 test run으로 Release 화면에서 후보를 선택할 수 있습니다."
                    primaryLabel="Release 화면으로 이동"
                    onPrimary={() => history.push('/releases')}
                  />
                ) : null}
              </Card>
            ) : null}
            <ProTable<API.TestRunResult>
              rowKey="case_id"
              columns={columns}
              dataSource={results}
              search={false}
              pagination={false}
              options={false}
              toolBarRender={() =>
                summary
                  ? [
                      <AdminTableActions
                        key="table-actions"
                        onReload={() => loadRun(summary.test_run_id, session.serviceId)}
                        reloadDisabled={loading}
                      />,
                    ]
                  : []
              }
              locale={{
                emptyText: (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No test run results loaded" />
                ),
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
