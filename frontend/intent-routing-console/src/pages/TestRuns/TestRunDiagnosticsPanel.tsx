import { useEffect, useMemo, useState } from 'react';
import { Alert, Descriptions, Empty, Spin, Space, Tag, Typography } from 'antd';
import { fetchTestRunDiagnostics } from '@/services/adminServices';

type TestRunDiagnosticsPanelProps = {
  serviceId: string;
  testRunId?: string;
};

const severityColor: Record<string, string> = {
  blocker: 'error',
  warning: 'warning',
  recommendation: 'processing',
};

const issueCopy: Record<string, string> = {
  catalog_version_not_active: '선택한 Catalog 버전이 활성 상태가 아닙니다.',
  catalog_version_not_reproducible: '선택한 Catalog 버전의 재현성 상태가 완전하지 않습니다.',
  catalog_version_has_no_intents: '선택한 Catalog 버전에 Intent가 없습니다.',
  catalog_version_has_no_examples: '선택한 Catalog 버전에 예시 데이터가 없습니다.',
  catalog_version_has_no_ready_vector_index: '선택한 Catalog 버전에 준비된 vector index가 없습니다.',
  catalog_version_has_no_embeddings: '선택한 Catalog 버전에 활성 embedding이 없습니다.',
  test_run_vector_index_not_ready: 'Test Run이 사용한 vector index가 현재 준비 상태와 일치하지 않습니다.',
  risk_case_failed: 'Risk 테스트 케이스가 실패했습니다.',
  fallback_failures_dominant: '실패한 케이스 중 fallback 결과가 많습니다.',
  intent_mismatch_exists: 'Decision은 맞았지만 Intent가 다른 실패가 있습니다.',
  pass_rate_below_gate: 'Pass rate가 release gate 기준보다 낮습니다.',
  review_rate_above_guidance: 'Review 비율이 권장 기준보다 높습니다.',
};

export function TestRunDiagnosticsPanel({
  serviceId,
  testRunId,
}: TestRunDiagnosticsPanelProps) {
  const [loading, setLoading] = useState(false);
  const [diagnostics, setDiagnostics] = useState<API.TestRunDiagnostics>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (!testRunId) {
      setDiagnostics(undefined);
      setError(undefined);
      setLoading(false);
      return;
    }
    let alive = true;
    setDiagnostics(undefined);
    setError(undefined);
    setLoading(true);
    fetchTestRunDiagnostics(serviceId, testRunId)
      .then((nextDiagnostics) => {
        if (alive) setDiagnostics(nextDiagnostics);
      })
      .catch(() => {
        if (alive) {
          setError('진단 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [serviceId, testRunId]);

  const primaryIssue = diagnostics?.primary_issue;
  const catalog = diagnostics?.catalog_version;
  const primaryCopy = useMemo(
    () =>
      primaryIssue
        ? issueCopy[primaryIssue.code] ?? primaryIssue.code
        : '진단 가능한 주요 이슈가 없습니다.',
    [primaryIssue],
  );

  if (!testRunId) {
    return (
      <section>
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          진단
        </Typography.Title>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Test Run이 없습니다." />
      </section>
    );
  }

  return (
    <section>
      <Typography.Title level={5} style={{ marginTop: 0 }}>
        진단
      </Typography.Title>
      <Spin spinning={loading}>
        {diagnostics ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Alert
              type={primaryIssue?.severity === 'blocker' ? 'error' : 'info'}
              showIcon
              message={primaryCopy}
              description={
                primaryIssue
                  ? (
                    <>
                      이슈 코드: <Typography.Text code>{primaryIssue.code}</Typography.Text>
                    </>
                  )
                  : '백엔드 진단에서 주요 이슈를 찾지 못했습니다.'
              }
            />
            {catalog ? (
              <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
                <Descriptions.Item label="Catalog 버전">
                  <Typography.Text code>{catalog.intent_catalog_version}</Typography.Text>
                </Descriptions.Item>
                <Descriptions.Item label="상태">{catalog.status}</Descriptions.Item>
                <Descriptions.Item label="재현성">
                  {catalog.reproducibility_status}
                </Descriptions.Item>
                <Descriptions.Item label="Intent 수">{catalog.intent_count}</Descriptions.Item>
                <Descriptions.Item label="예시 수">{catalog.example_count}</Descriptions.Item>
                <Descriptions.Item label="Embedding 수">{catalog.embedding_count}</Descriptions.Item>
                <Descriptions.Item label="준비된 vector index">
                  {catalog.ready_vector_index_version ?? '없음'}
                </Descriptions.Item>
                <Descriptions.Item label="Test Run vector index">
                  {catalog.test_run_vector_index_version ?? '없음'}
                </Descriptions.Item>
              </Descriptions>
            ) : null}
            <Space wrap>
              {diagnostics.issues.map((issue) => (
                <Tag key={issue.code} color={severityColor[issue.severity] ?? 'default'}>
                  {issue.severity}: <Typography.Text code>{issue.code}</Typography.Text>
                </Tag>
              ))}
            </Space>
            <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
              <Descriptions.Item label="결과 집계">
                <Typography.Text code>{JSON.stringify(diagnostics.result_counts)}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="실제 결정 집계">
                <Typography.Text code>
                  {JSON.stringify(diagnostics.actual_decision_counts)}
                </Typography.Text>
              </Descriptions.Item>
            </Descriptions>
          </Space>
        ) : error ? (
          <Alert type="error" showIcon message="진단 결과를 불러오지 못했습니다." description={error} />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 진단 결과가 없습니다." />
        )}
      </Spin>
    </section>
  );
}
