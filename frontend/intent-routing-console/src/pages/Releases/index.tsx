import { useEffect, useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';
import {
  activateRelease,
  createRelease,
  listReleaseCandidates,
  listReleases,
  rollbackRelease,
} from '@/services/adminServices';
import { canManageReleases, isAdminSessionReady } from '@/models/adminSession';
import { ReleaseCandidateSelect } from './ReleaseCandidateSelect';

const formatRate = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'none';
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
};

const releaseHelp = {
  environment: '선택한 서비스의 environment를 자동 사용합니다. Release environment는 서비스 environment와 반드시 같아야 합니다.',
  testRun: 'Test Runs summary에 표시되는 tr-... 값입니다. Gate passed이고 risk pass가 100%여야 release가 생성됩니다.',
  rollbackTarget: '선택 항목입니다. 기존 release_version으로 되돌릴 수 있게 연결할 때만 입력합니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

export default function ReleasesPage() {
  const { session } = useModel('adminSession');
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm<API.ReleaseCreateRequest>();
  const [environment, setEnvironment] = useState<string>();
  const [creating, setCreating] = useState(false);
  const [candidates, setCandidates] = useState<API.ReleaseCandidate[]>([]);
  const [releaseRows, setReleaseRows] = useState<API.Release[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const ready = isAdminSessionReady(session);
  const canManage = canManageReleases(session);
  const selectedService = session.services.find((service) => service.service_id === session.serviceId);
  const selectedEnvironment = selectedService?.environment || 'prod';
  const selectedTestRunId = Form.useWatch('test_run_id', form);

  const reload = () => actionRef.current?.reload();

  useEffect(() => {
    form.resetFields();
    form.setFieldsValue({ environment: selectedEnvironment });
    setCandidates([]);
    setReleaseRows([]);
    actionRef.current?.reloadAndRest?.();
  }, [form, selectedEnvironment, session.serviceId]);

  const loadCandidates = async () => {
    setCandidatesLoading(true);
    try {
      const rows = await listReleaseCandidates(session.serviceId, {
        environment: selectedEnvironment,
      });
      setCandidates(rows);
    } finally {
      setCandidatesLoading(false);
    }
  };

  const handleSelectCandidate = (candidate: API.ReleaseCandidate) => {
    form.setFieldsValue({
      environment: candidate.environment,
      policy_version: candidate.policy_version,
      intent_catalog_version: candidate.intent_catalog_version,
      test_run_id: candidate.test_run_id,
    });
  };

  const handleCreate = async (values: API.ReleaseCreateRequest) => {
    if (!ready) return;
    setCreating(true);
    try {
      await createRelease(session.serviceId, {
        environment: selectedEnvironment,
        policy_version: values.policy_version.trim(),
        intent_catalog_version: values.intent_catalog_version.trim(),
        test_run_id: values.test_run_id.trim(),
        rollback_target: values.rollback_target?.trim() || null,
      });
      message.success('Release가 생성되었습니다.');
      form.resetFields();
      form.setFieldsValue({ environment: selectedEnvironment });
      setCandidates((current) =>
        current.map((candidate) =>
          candidate.test_run_id === values.test_run_id
            ? {
                ...candidate,
                eligible: false,
                already_released: true,
                block_reasons: [
                  ...candidate.block_reasons,
                  'test run already has a release',
                ],
              }
            : candidate,
        ),
      );
      reload();
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (serviceId: string, releaseVersion: string) => {
    await activateRelease(serviceId, releaseVersion);
    message.success('Release가 활성화되었습니다.');
    reload();
  };

  const handleRollback = async (serviceId: string, releaseVersion: string) => {
    await rollbackRelease(serviceId, releaseVersion);
    message.success('Rollback이 실행되었습니다.');
    reload();
  };

  const columns: ProColumns<API.Release>[] = [
    {
      title: 'Release',
      dataIndex: 'release_version',
      copyable: true,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text code>{row.release_version}</Typography.Text>
          <span className="muted-small">test run {row.test_run_id}</span>
        </Space>
      ),
    },
    {
      title: 'Environment',
      dataIndex: 'environment',
      render: (_, row) => <Tag>{row.environment}</Tag>,
    },
    {
      title: 'Versions',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span className="muted-small">policy {row.policy_version}</span>
          <span className="muted-small">catalog {row.intent_catalog_version}</span>
        </Space>
      ),
    },
    {
      title: 'Pass rate',
      dataIndex: 'pass_rate',
      search: false,
      width: 108,
      renderText: (value) => formatRate(Number(value)),
    },
    {
      title: 'Risk pass',
      dataIndex: 'risk_pass_rate',
      search: false,
      width: 108,
      renderText: (value) => formatRate(Number(value)),
    },
    {
      title: 'Status',
      dataIndex: 'active',
      search: false,
      width: 96,
      render: (_, row) => (
        <Tag color={row.active ? 'green' : 'default'}>{row.active ? 'active' : 'inactive'}</Tag>
      ),
    },
    {
      title: 'Released',
      dataIndex: 'released_at',
      valueType: 'dateTime',
      search: false,
      width: 168,
    },
    {
      title: '',
      valueType: 'option',
      width: 176,
      render: (_, row) =>
        canManage
          ? [
              <ConfirmActionButton
                key="activate"
                title="Activate release?"
                disabled={row.active}
                type="link"
                size="small"
                okText="Activate"
                content={`Activate ${row.release_version} for ${row.environment}.`}
                onConfirm={() => handleActivate(row.service_id, row.release_version)}
              >
                활성화
              </ConfirmActionButton>,
              <ConfirmActionButton
                key="rollback"
                danger
                title="Rollback release?"
                disabled={!row.rollback_target}
                type="link"
                size="small"
                okText="Rollback"
                content={
                  row.rollback_target
                    ? `Rollback ${row.release_version} to ${row.rollback_target}.`
                    : 'This release has no rollback target.'
                }
                onConfirm={() => handleRollback(row.service_id, row.release_version)}
              >
                롤백
              </ConfirmActionButton>,
            ]
          : [],
    },
  ];

  return (
    <AdminShell title="Releases">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <FutureFeatureNotice
          compact
          title="Release diff approval"
          backendRequirement="Phase 2 backend contracts are required before this console can request, approve, or reject release diffs."
        />
        {ready ? (
          <>
            {canManage ? (
              <Card title="Create release">
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleCreate}
                  initialValues={{ environment: selectedEnvironment }}
                >
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="Release는 검증이 끝난 policy/catalog/test run 조합만 등록할 수 있습니다."
                    description="Test Runs에서 통과한 release candidate를 불러와 선택하세요. 선택하면 version 값이 자동으로 채워집니다."
                  />
                  <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    <Space wrap align="center">
                      <Form.Item
                        label={helpLabel('Release candidate', releaseHelp.testRun)}
                        style={{ minWidth: 420, marginBottom: 0 }}
                      >
                        <ReleaseCandidateSelect
                          value={selectedTestRunId}
                          candidates={candidates}
                          onChange={(testRunId) =>
                            form.setFieldsValue({ test_run_id: testRunId })
                          }
                          onSelectCandidate={handleSelectCandidate}
                        />
                      </Form.Item>
                      <Form.Item label=" " style={{ marginBottom: 0 }}>
                        <Button onClick={loadCandidates} loading={candidatesLoading}>
                          후보 불러오기
                        </Button>
                      </Form.Item>
                    </Space>
                    <Form.Item name="policy_version" hidden>
                      <Input />
                    </Form.Item>
                    <Form.Item name="intent_catalog_version" hidden>
                      <Input />
                    </Form.Item>
                    <Form.Item
                      name="test_run_id"
                      hidden
                      rules={[
                        {
                          required: true,
                          whitespace: true,
                          message: 'Release candidate is required.',
                        },
                      ]}
                    >
                      <Input />
                    </Form.Item>
                    <Space wrap align="start" size={12}>
                      <Form.Item
                        name="environment"
                        label={helpLabel('Environment', releaseHelp.environment)}
                        rules={[
                          {
                            required: true,
                            whitespace: true,
                            message: 'Environment is required.',
                          },
                        ]}
                      >
                        <Input disabled style={{ width: 160 }} />
                      </Form.Item>
                      <Form.Item
                        name="rollback_target"
                        label={helpLabel('Rollback target', releaseHelp.rollbackTarget)}
                      >
                        <Select
                          allowClear
                          showSearch
                          placeholder="Rollback target 선택"
                          optionFilterProp="label"
                          style={{ width: 260 }}
                          options={releaseRows.map((release) => ({
                            value: release.release_version,
                            label: release.release_version,
                            release,
                          }))}
                          optionRender={({ data }) => {
                            const release = data.release as API.Release;
                            return (
                              <Space direction="vertical" size={0}>
                                <Typography.Text code>{release.release_version}</Typography.Text>
                                <Typography.Text type="secondary">
                                  {release.active ? 'active' : 'inactive'} / {release.test_run_id}
                                </Typography.Text>
                              </Space>
                            );
                          }}
                        />
                      </Form.Item>
                      <Form.Item label=" ">
                        <Button type="primary" htmlType="submit" loading={creating}>
                          Release 생성
                        </Button>
                      </Form.Item>
                    </Space>
                  </Space>
                </Form>
              </Card>
            ) : (
              <Alert
                type="info"
                showIcon
                message="선택한 Service에 대한 Release 관리 권한이 없습니다."
                description="system_admin 또는 선택한 Service의 service_owner/service_developer만 생성, 활성화, 롤백할 수 있습니다."
              />
            )}
            <ProTable<API.Release>
              key={session.serviceId}
              rowKey="release_version"
              actionRef={actionRef}
              columns={columns}
              request={async () => {
                const rows = await listReleases(session.serviceId, environment);
                setReleaseRows(rows);
                return { data: rows, total: rows.length, success: true };
              }}
              params={{ environment, serviceId: session.serviceId }}
              pagination={false}
              search={false}
              toolbar={{
                filter: (
                  <Input
                    allowClear
                    placeholder="Filter environment"
                    value={environment}
                    onChange={(event) => setEnvironment(event.target.value || undefined)}
                    style={{ width: 220 }}
                  />
                ),
              }}
              options={{ density: true, fullScreen: false, reload: true, setting: true }}
              locale={{
                emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No releases" />,
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
