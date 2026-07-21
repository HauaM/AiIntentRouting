import { useMemo } from 'react';
import { Alert, Card, Empty, List, Spin, Space, Typography } from 'antd';
import { StatusTag } from '@/components/StatusTag';
import { formatDecisionLabel, formatIntentLabel, formatIssueTitle } from './testRunResultCopy';
import {
  buildTestRunInsights,
  type TestRunPatternKind,
  type TestRunResultsLoadState,
} from './testRunResultInsights';

const patternStatus = {
  intent_mismatch: 'warning',
  decision_mismatch: 'fail',
  fallback: 'fallback',
} as const;

type TestRunDiagnosticsPanelProps = {
  testRunId?: string;
  diagnostics?: API.TestRunDiagnostics | null;
  diagnosticsLoading?: boolean;
  diagnosticsError?: string | null;
  results?: API.TestRunResult[];
  resultsLoadState?: TestRunResultsLoadState;
};

const formatPatternValue = (kind: TestRunPatternKind, value: string) =>
  kind === 'decision_mismatch' || (kind === 'fallback' && value === 'fallback')
    ? formatDecisionLabel(value)
    : formatIntentLabel(value);

export function TestRunDiagnosticsPanel({
  testRunId,
  diagnostics,
  diagnosticsLoading = false,
  diagnosticsError,
  results,
  resultsLoadState = 'not_loaded',
}: TestRunDiagnosticsPanelProps) {
  const insights = useMemo(
    () => buildTestRunInsights(results ?? [], diagnostics ?? undefined, resultsLoadState),
    [diagnostics, results, resultsLoadState],
  );
  const primaryIssue = diagnostics?.primary_issue;

  if (!testRunId) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Test Run이 없습니다." />;
  }

  if (diagnosticsLoading) {
    return (
      <Spin spinning>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="진단 결과를 불러오는 중입니다." />
      </Spin>
    );
  }

  if (diagnosticsError) {
    return (
      <Alert
        type="error"
        showIcon
        message="진단 결과를 불러오지 못했습니다."
        description={diagnosticsError}
      />
    );
  }

  if (!diagnostics) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 진단 결과가 없습니다." />;
  }

  return (
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
                      <Typography.Text title={pattern.expected}>
                        {formatPatternValue(pattern.kind, pattern.expected)}
                      </Typography.Text>
                      <Typography.Text>→</Typography.Text>
                      <Typography.Text title={pattern.actual}>
                        {formatPatternValue(pattern.kind, pattern.actual)}
                      </Typography.Text>
                      <StatusTag status={patternStatus[pattern.kind]} label={`${pattern.count}건`} />
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="집계된 실패 패턴이 없습니다." />
            )}
            <Typography.Text strong>실제 결정 분포</Typography.Text>
            {Object.entries(diagnostics.actual_decision_counts).length ? (
              <List
                size="small"
                dataSource={Object.entries(diagnostics.actual_decision_counts)}
                renderItem={([decision, count]) => (
                  <List.Item>
                    <Space>
                      <StatusTag status={decision} label={formatDecisionLabel(decision)} />
                      <Typography.Text>{count}건</Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="집계된 실제 결정이 없습니다." />
            )}
            <Space wrap>
              {diagnostics.issues.map((issue) => (
                <StatusTag
                  key={issue.code}
                  status={issue.severity}
                  label={formatIssueTitle(issue.code)}
                />
              ))}
            </Space>
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
        </Space>
  );
}
