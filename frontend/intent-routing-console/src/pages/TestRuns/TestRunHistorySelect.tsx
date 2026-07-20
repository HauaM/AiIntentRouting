import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Empty, Select, Space, Spin, Tag, Typography } from 'antd';
import { listTestRuns } from '@/services/adminServices';

type TestRunHistorySelectProps = {
  serviceId: string;
  value?: string;
  disabled?: boolean;
  loading?: boolean;
  onSelect: (testRunId: string) => void;
};

const TEST_RUN_HISTORY_LIMIT = 50;

const formatRate = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'none';
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
};

const formatCreatedAt = (value: string) =>
  new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));

const testRunSearchLabel = (run: API.TestRunListItem) =>
  [
    run.test_run_id,
    run.source_filename,
    run.policy_version,
    run.intent_catalog_version,
    run.test_dataset_version,
    run.gate_passed ? 'gate passed' : 'gate blocked',
    run.created_at,
  ]
    .filter(Boolean)
    .join(' ');

const testRunOptionLabel = (run: API.TestRunListItem) =>
  `${run.source_filename || run.test_dataset_version} / ${formatCreatedAt(run.created_at)}`;

export function TestRunHistorySelect({
  serviceId,
  value,
  disabled,
  loading,
  onSelect,
}: TestRunHistorySelectProps) {
  const [runs, setRuns] = useState<API.TestRunListItem[]>([]);
  const [fetching, setFetching] = useState(false);
  const [loadError, setLoadError] = useState<string>();
  const requestRef = useRef(0);

  const selectedRun = useMemo(
    () => runs.find((run) => run.test_run_id === value),
    [runs, value],
  );

  const loadRuns = useCallback(async () => {
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setRuns([]);
    setLoadError(undefined);
    setFetching(true);
    try {
      const nextRuns = await listTestRuns(serviceId, {
        limit: TEST_RUN_HISTORY_LIMIT,
      });
      if (requestRef.current !== requestId) return;
      setRuns(nextRuns);
    } catch {
      if (requestRef.current !== requestId) return;
      setRuns([]);
      setLoadError('기존 테스트 실행 목록을 불러오지 못했습니다.');
    } finally {
      if (requestRef.current === requestId) setFetching(false);
    }
  }, [serviceId]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    return () => {
      requestRef.current += 1;
    };
  }, []);

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space direction="vertical" size={4}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          기존 테스트 실행 결과 조회
        </Typography.Title>
        <Typography.Text type="secondary">
          이전 실행을 선택하면 테스트 결과 확인 단계로 이동합니다.
        </Typography.Text>
      </Space>
      <div className="test-run-step-field">
        <label className="test-run-step-field-label" htmlFor="test-run-history-select">
          기존 테스트 실행 결과
        </label>
        <Select
          id="test-run-history-select"
          showSearch
          value={value}
          loading={fetching || loading}
          disabled={disabled}
          placeholder="이전 테스트 실행을 선택하세요"
          optionFilterProp="searchLabel"
          className="test-run-step-select"
          notFoundContent={
            fetching ? (
              <Spin size="small" />
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  loadError ?? '현재 서비스의 이전 테스트 실행이 없습니다.'
                }
              />
            )
          }
          options={runs.map((run) => ({
            value: run.test_run_id,
            label: testRunOptionLabel(run),
            searchLabel: testRunSearchLabel(run),
            testRun: run,
          }))}
          onChange={(nextTestRunId) => {
            if (nextTestRunId) onSelect(nextTestRunId);
          }}
          optionRender={({ data }) => {
            const run = data.testRun as API.TestRunListItem;
            return (
              <Space direction="vertical" size={2}>
                <Space wrap size={6}>
                  <Typography.Text strong>
                    {run.source_filename || run.test_dataset_version}
                  </Typography.Text>
                  <Tag color={run.gate_passed ? 'green' : 'red'}>
                    {run.gate_passed ? 'gate 통과' : 'gate 차단'}
                  </Tag>
                  <Tag>pass {formatRate(run.pass_rate)}</Tag>
                  <Tag>risk {formatRate(run.risk_pass_rate)}</Tag>
                </Space>
                <Typography.Text type="secondary">
                  {formatCreatedAt(run.created_at)} / policy {run.policy_version}
                </Typography.Text>
                <Typography.Text type="secondary" ellipsis>
                  catalog {run.intent_catalog_version} / run {run.test_run_id}
                </Typography.Text>
              </Space>
            );
          }}
        />
        {selectedRun ? (
          <Typography.Text type="secondary" className="test-run-step-field-help">
            선택됨: {selectedRun.test_run_id}
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary" className="test-run-step-field-help">
            실행 ID를 직접 입력하지 않고 DB에 저장된 실행 목록에서 선택합니다.
          </Typography.Text>
        )}
      </div>
    </Space>
  );
}
