import { useMemo } from 'react';
import { Alert, Card, Empty, List, Spin, Space, Typography } from 'antd';
import { StatusTag } from '@/components/StatusTag';
import { formatIssueTitle } from './testRunResultCopy';
import { buildTestRunInsights } from './testRunResultInsights';

type TestRunDiagnosticsPanelProps = {
  testRunId?: string;
  diagnostics?: API.TestRunDiagnostics | null;
  diagnosticsLoading?: boolean;
  diagnosticsError?: string | null;
  results?: API.TestRunResult[];
};

export function TestRunDiagnosticsPanel({
  testRunId,
  diagnostics,
  diagnosticsLoading = false,
  diagnosticsError,
  results,
}: TestRunDiagnosticsPanelProps) {
  const insights = useMemo(
    () => buildTestRunInsights(results ?? [], diagnostics ?? undefined),
    [diagnostics, results],
  );
  const primaryIssue = diagnostics?.primary_issue;

  if (!testRunId) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Test Run이 없습니다." />;
  }

  return (
    <Spin spinning={diagnosticsLoading}>
      {diagnostics ? (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Alert
            type={primaryIssue?.severity === 'blocker' ? 'error' : 'info'}
            showIcon
            message="가장 먼저 확인할 문제"
            description={
              <Space direction="vertical" size={6}>
                <Typography.Text strong>
                  {primaryIssue ? formatIssueTitle(primaryIssue.code) : insights.primaryProblem}
                </Typography.Text>
                {insights.impactBullets.map((item) => (
                  <Typography.Text key={item}>{item}</Typography.Text>
                ))}
              </Space>
            }
          />

          <Card size="small" title="실패 패턴 요약">
            {insights.patterns.length ? (
              <List
                size="small"
                dataSource={insights.patterns}
                renderItem={(pattern) => (
                  <List.Item>
                    <Space>
                      <Typography.Text code>{pattern.expected}</Typography.Text>
                      <Typography.Text>→</Typography.Text>
                      <Typography.Text code>{pattern.actual}</Typography.Text>
                      <StatusTag status={pattern.kind} label={`${pattern.count}건`} />
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="집계된 실패 패턴이 없습니다." />
            )}
          </Card>

          <Card size="small" title="다음 조치">
            {insights.nextActions.length ? (
              <List
                size="small"
                dataSource={insights.nextActions}
                renderItem={(action, index) => (
                  <List.Item>
                    <Typography.Text>{index + 1}. {action}</Typography.Text>
                  </List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="추가 권장 조치가 없습니다." />
            )}
          </Card>

          {/* Includes program_supported_question이 구체 Intent를 과도하게 흡수하는지 점검하는 action. */}
          <Space wrap>
            {diagnostics.issues.map((issue) => (
              <StatusTag
                key={issue.code}
                status={issue.severity}
                label={formatIssueTitle(issue.code)}
              />
            ))}
          </Space>
        </Space>
      ) : diagnosticsError ? (
        <Alert
          type="error"
          showIcon
          message="진단 결과를 불러오지 못했습니다."
          description={diagnosticsError}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 진단 결과가 없습니다." />
      )}
    </Spin>
  );
}
