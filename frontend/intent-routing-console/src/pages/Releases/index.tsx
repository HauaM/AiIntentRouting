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
import { StatusTag } from '@/components/StatusTag';
import {
  activateRelease,
  createRelease,
  listReleaseCandidates,
  listReleases,
  rollbackRelease,
} from '@/services/adminServices';
import { canManageReleases, isAdminSessionReady } from '@/models/adminSession';
import { ReleaseCandidateSelect } from './ReleaseCandidateSelect';
import {
  canRollbackRelease,
  formatReleaseRate,
  getActivationConfirmation,
  getActiveRelease,
  getRollbackConfirmation,
  getSelectedReleaseCandidate,
  type ReleaseConfirmationPresentation,
} from './releasePresentation';

const releaseHelp = {
  environment: '선택한 서비스의 environment를 자동 사용합니다. Release environment는 서비스 environment와 반드시 같아야 합니다.',
  testRun: 'Test Runs summary에 표시되는 tr-... 값입니다. Gate passed이고 risk pass가 100%여야 release가 생성됩니다.',
  rollbackTarget: '선택 항목입니다. 기존 release_version으로 되돌릴 수 있게 연결할 때만 입력합니다.',
};

const helpLabel = (label: string, help: string) => (
  <FieldHelpLabel label={label} help={help} />
);

const ReleaseConfirmationSummary = ({
  presentation,
}: {
  presentation: ReleaseConfirmationPresentation;
}) => (
  <Space direction="vertical" size={12} style={{ width: '100%' }}>
    <div className="release-confirmation-grid">
      <Typography.Text type="secondary">Service</Typography.Text>
      <Typography.Text code>{presentation.serviceId}</Typography.Text>
      <Typography.Text type="secondary">Environment</Typography.Text>
      <Typography.Text>{presentation.environment}</Typography.Text>
      <Typography.Text type="secondary">현재 active Release</Typography.Text>
      <Typography.Text code>{presentation.currentRelease}</Typography.Text>
      <Typography.Text type="secondary">변경 후 active Release</Typography.Text>
      <Typography.Text code>{presentation.resultRelease}</Typography.Text>
    </div>
    <Typography.Text>{presentation.impact}</Typography.Text>
  </Space>
);

export default function ReleasesPage() {
  const { session } = useModel('adminSession');
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm<API.ReleaseCreateRequest>();
  const [creating, setCreating] = useState(false);
  const [candidates, setCandidates] = useState<API.ReleaseCandidate[]>([]);
  const [releaseRows, setReleaseRows] = useState<API.Release[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const ready = isAdminSessionReady(session);
  const canManage = canManageReleases(session);
  const selectedService = session.services.find((service) => service.service_id === session.serviceId);
  const selectedEnvironment = selectedService?.environment || 'prod';
  const selectedTestRunId = Form.useWatch('test_run_id', form);
  const selectedRollbackTarget = Form.useWatch('rollback_target', form);
  const selectedCandidate = getSelectedReleaseCandidate(candidates, selectedTestRunId);
  const activeRelease = getActiveRelease(releaseRows);

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
      title: 'Version',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <span className="muted-small">policy {row.policy_version}</span>
          <span className="muted-small">catalog {row.intent_catalog_version}</span>
        </Space>
      ),
    },
    {
      title: '전체 통과율',
      dataIndex: 'pass_rate',
      search: false,
      width: 108,
      renderText: (value) => formatReleaseRate(value as number | null | undefined),
    },
    {
      title: 'Risk 통과율',
      dataIndex: 'risk_pass_rate',
      search: false,
      width: 108,
      renderText: (value) => formatReleaseRate(value as number | null | undefined),
    },
    {
      title: '상태',
      dataIndex: 'active',
      search: false,
      width: 96,
      render: (_, row) => <StatusTag status={row.active ? 'active' : 'inactive'} />,
    },
    {
      title: '생성 일시',
      dataIndex: 'released_at',
      valueType: 'dateTime',
      search: false,
      width: 168,
    },
    {
      title: '작업',
      valueType: 'option',
      width: 176,
      render: (_, row) =>
        canManage
          ? [
              <ConfirmActionButton
                key="activate"
                title={getActivationConfirmation(row, activeRelease).title}
                disabled={row.active}
                type="link"
                size="small"
                okText="활성화"
                content={
                  <ReleaseConfirmationSummary
                    presentation={getActivationConfirmation(row, activeRelease)}
                  />
                }
                onConfirm={() => handleActivate(row.service_id, row.release_version)}
              >
                활성화
              </ConfirmActionButton>,
              <ConfirmActionButton
                key="rollback"
                danger
                title={getRollbackConfirmation(row, activeRelease).title}
                disabled={!canRollbackRelease(row)}
                type="link"
                size="small"
                okText="롤백"
                content={
                  row.rollback_target
                    ? <ReleaseConfirmationSummary
                        presentation={getRollbackConfirmation(row, activeRelease)}
                      />
                    : '이 Release에는 rollback target이 없습니다.'
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
      <div className="releases-page-stack">
        <FutureFeatureNotice
          compact
          title="Release diff 승인"
          backendRequirement="Phase 2 backend is implemented, but the frontend route, role gate, and UX tests are not wired yet."
        />
        {ready ? (
          <>
            {canManage ? (
              <Card title="Release 생성" className="release-form-card ds-page-card">
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleCreate}
                  initialValues={{ environment: selectedEnvironment }}
                >
                  <Alert
                    type="info"
                    showIcon
                    className="release-form-guidance"
                    message="Release는 검증이 끝난 policy/catalog/test run 조합만 등록할 수 있습니다."
                    description="Test Runs에서 통과한 release candidate를 불러와 선택하세요. 선택하면 version 값이 자동으로 채워집니다."
                  />
                  <div className="release-form-content">
                    <div className="release-candidate-row">
                      <Form.Item
                        label={helpLabel('Release candidate', releaseHelp.testRun)}
                        className="release-candidate-field"
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
                      <Form.Item label=" " className="release-candidate-load-action">
                        <Button onClick={loadCandidates} loading={candidatesLoading}>
                          후보 불러오기
                        </Button>
                      </Form.Item>
                    </div>
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
                    {selectedCandidate ? (
                      <section className="release-candidate-evidence" aria-label="선택한 Release 근거">
                        <Typography.Text strong className="release-evidence-title">
                          선택한 Release 근거
                        </Typography.Text>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">Test run</Typography.Text>
                          <Typography.Text code copyable>{selectedCandidate.test_run_id}</Typography.Text>
                        </div>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">Policy version</Typography.Text>
                          <Typography.Text code copyable>{selectedCandidate.policy_version}</Typography.Text>
                        </div>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">Catalog version</Typography.Text>
                          <Typography.Text code copyable>{selectedCandidate.intent_catalog_version}</Typography.Text>
                        </div>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">전체 통과율</Typography.Text>
                          <Typography.Text>{formatReleaseRate(selectedCandidate.pass_rate)}</Typography.Text>
                        </div>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">Risk 통과율</Typography.Text>
                          <Typography.Text>{formatReleaseRate(selectedCandidate.risk_pass_rate)}</Typography.Text>
                        </div>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">Environment</Typography.Text>
                          <Typography.Text>{selectedCandidate.environment}</Typography.Text>
                        </div>
                        <div className="release-evidence-item">
                          <Typography.Text type="secondary">Rollback target</Typography.Text>
                          <Typography.Text code>{selectedRollbackTarget || '없음'}</Typography.Text>
                        </div>
                      </section>
                    ) : null}
                    <div className="release-form-grid">
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
                        <Input disabled />
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
                    </div>
                    <div className="release-form-actions">
                      <Button type="primary" htmlType="submit" loading={creating}>
                        Release 생성
                      </Button>
                    </div>
                  </div>
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
            <div className="ds-page-card ds-table-card-padded ds-pro-table-card">
              <ProTable<API.Release>
                key={session.serviceId}
                rowKey="release_version"
                actionRef={actionRef}
                columns={columns}
                headerTitle="Release 목록"
                request={async () => {
                  const rows = await listReleases(session.serviceId, selectedEnvironment);
                  setReleaseRows(rows);
                  return { data: rows, total: rows.length, success: true };
                }}
                params={{ environment: selectedEnvironment, serviceId: session.serviceId }}
                pagination={false}
                search={false}
                scroll={{ x: 1120 }}
                options={{ density: true, fullScreen: false, reload: true, setting: true }}
                locale={{
                  emptyText: (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="등록된 Release가 없습니다."
                    />
                  ),
                }}
              />
            </div>
          </>
        ) : (
          <AdminSessionRequired />
        )}
      </div>
    </AdminShell>
  );
}
