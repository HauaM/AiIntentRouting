import { useMemo, useState } from 'react';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Empty, List, Modal, Spin, Space, Typography } from 'antd';
import { StatusTag } from '@/components/StatusTag';
import {
  formatDecisionLabel,
  formatIntentLabel,
  formatIssueTitle,
  formatRouterDecisionLabel,
} from './testRunResultCopy';
import {
  buildReleaseReadiness,
  buildActualDecisionCounts,
  buildTestRunInsights,
  type TestRunNextAction,
  type TestRunPatternValueType,
  type TestRunResultsLoadState,
} from './testRunResultInsights';

const patternStatus = {
  intent_mismatch: 'warning',
  route_key_mismatch: 'warning',
  decision_mismatch: 'fail',
  fallback: 'fallback',
} as const;

type TestRunDiagnosticsPanelProps = {
  testRunId?: string;
  summary?: API.TestRunSummary;
  diagnostics?: API.TestRunDiagnostics | null;
  diagnosticsLoading?: boolean;
  diagnosticsError?: string | null;
  results?: API.TestRunResult[];
  resultsLoadState?: TestRunResultsLoadState;
};

const formatPatternValue = (valueType: TestRunPatternValueType, value: string) =>
  valueType === 'decision' ? formatDecisionLabel(value) : formatIntentLabel(value);

const formatPatternTooltip = (valueType: TestRunPatternValueType, value: string) =>
  valueType === 'decision' ? formatDecisionLabel(value) : undefined;

const resultLoadStateCopy = {
  not_loaded: {
    patternDescription: '상세 결과를 아직 불러오지 않아 실패 패턴을 집계할 수 없습니다.',
    nextActionDescription: '상세 결과를 불러온 뒤 추가 권장 조치를 확인할 수 있습니다.',
  },
  loading: {
    patternDescription: '상세 결과를 불러오는 중이라 실패 패턴을 집계할 수 없습니다.',
    nextActionDescription: '상세 결과를 불러오는 중이라 추가 권장 조치를 계산하고 있습니다.',
  },
  error: {
    patternDescription: '상세 결과를 불러오지 못해 실패 패턴을 집계할 수 없습니다.',
    nextActionDescription: '상세 결과를 불러오지 못해 추가 권장 조치를 제시할 수 없습니다.',
  },
} as const;

export function TestRunDiagnosticsPanel({
  testRunId,
  summary,
  diagnostics,
  diagnosticsLoading = false,
  diagnosticsError,
  results,
  resultsLoadState = 'not_loaded',
}: TestRunDiagnosticsPanelProps) {
  const [selectedActionHelp, setSelectedActionHelp] = useState<TestRunNextAction | null>(null);
  const insights = useMemo(
    () => buildTestRunInsights(results ?? [], diagnostics ?? undefined, resultsLoadState),
    [diagnostics, results, resultsLoadState],
  );
  const actualDecisionCounts = useMemo(() => {
    const diagnosticCounts = diagnostics?.actual_decision_counts ?? {};
    return Object.keys(diagnosticCounts).length
      ? diagnosticCounts
      : buildActualDecisionCounts(results ?? []);
  }, [diagnostics, results]);
  const resultSectionState = resultsLoadState === 'loaded'
    ? {
        isLoaded: true,
        patternDescription: '집계된 실패 패턴이 없습니다.',
        nextActionDescription: '추가 권장 조치가 없습니다.',
      }
    : {
        isLoaded: false,
        ...resultLoadStateCopy[resultsLoadState],
      };
  const primaryIssue = diagnostics?.primary_issue;
  const diagnosticsUnavailable = Boolean(diagnosticsError);
  const releaseReadiness = buildReleaseReadiness(summary, results);

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

  if (!diagnostics && !diagnosticsUnavailable && resultsLoadState !== 'loaded') {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 진단 결과가 없습니다." />;
  }

  return (
    <>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {diagnosticsUnavailable ? (
          <Alert
            type="warning"
            showIcon
            message="진단 결과를 불러오지 못했습니다."
            description={diagnosticsError}
          />
        ) : null}

        {summary ? (
          <Card size="small" title="Release 가능 여부">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <StatusTag status={releaseReadiness.status} label={releaseReadiness.gateLabel} />
              <div>
                <Typography.Text strong>Release 차단 사유</Typography.Text>
                <Typography.Paragraph style={{ marginBottom: 0 }}>
                  {releaseReadiness.blockerMessages.length
                    ? releaseReadiness.blockerMessages.join(' ')
                    : '없음'}
                </Typography.Paragraph>
              </div>
              {releaseReadiness.recommendationMessages.length ? (
                <div>
                  <Typography.Text strong>권장 조치</Typography.Text>
                  <Typography.Paragraph style={{ marginBottom: 0 }}>
                    {releaseReadiness.recommendationMessages.join(' ')}
                  </Typography.Paragraph>
                </div>
              ) : null}
            </Space>
          </Card>
        ) : null}

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
          {resultSectionState.isLoaded && insights.patterns.length ? (
            <List
              size="small"
              dataSource={insights.patterns}
              renderItem={(pattern) => (
                <List.Item>
                  <Space wrap>
                    <Space size={6}>
                      <Typography.Text title={formatPatternTooltip(pattern.expectedValueType, pattern.expected)}>
                        {formatPatternValue(pattern.expectedValueType, pattern.expected)}
                      </Typography.Text>
                      <Typography.Text>→</Typography.Text>
                      <Typography.Text title={formatPatternTooltip(pattern.actualValueType, pattern.actual)}>
                        {formatPatternValue(pattern.actualValueType, pattern.actual)}
                      </Typography.Text>
                      <StatusTag
                        status={patternStatus[pattern.kind]}
                        label={`${pattern.count}건`}
                      />
                    </Space>
                    {pattern.caseIds.length ? (
                      <Typography.Text type="secondary">
                        대상 케이스 {pattern.caseIds.join(', ')}
                      </Typography.Text>
                    ) : null}
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={resultSectionState.patternDescription}
            />
          )}
          <div
            className="test-run-decision-distribution"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              flexWrap: 'wrap',
              marginTop: 12,
            }}
          >
            <Typography.Text strong>라우터가 실제로 처리한 방식</Typography.Text>
            {Object.entries(actualDecisionCounts).length ? (
              <Space wrap size={[8, 8]}>
                {Object.entries(actualDecisionCounts).map(([decision, count]) => (
                  <Space key={decision} size={4}>
                    <StatusTag status={decision} label={formatRouterDecisionLabel(decision)} />
                    <Typography.Text>{count}건</Typography.Text>
                  </Space>
                ))}
              </Space>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="집계된 실제 결정이 없습니다." />
            )}
          </div>
        </Card>

        <Card size="small" title="다음 조치">
          {resultSectionState.isLoaded && insights.nextActions.length ? (
            <List
              size="small"
              dataSource={insights.nextActions}
              renderItem={(action) => (
                <List.Item>
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Space wrap align="center">
                      <StatusTag
                        status={action.status}
                        label={action.caseIds.length ? `${action.caseIds.length}건` : '전체'}
                      />
                      <Typography.Text strong>{action.title}</Typography.Text>
                      <Typography.Text type="secondary">{action.targetLabel}</Typography.Text>
                      <Button
                        size="small"
                        icon={<ExclamationCircleOutlined />}
                        onClick={() => setSelectedActionHelp(action)}
                        aria-label={`${action.title} 조치 방법 열기`}
                      >
                        ! 조치 방법
                      </Button>
                    </Space>
                    <Typography.Text type="secondary">{action.summary}</Typography.Text>
                    {action.caseIds.length ? (
                      <Space wrap size={[4, 4]}>
                        <Typography.Text type="secondary">대상 케이스</Typography.Text>
                        {action.caseIds.map((caseId) => (
                          <Typography.Text code key={caseId}>
                            {caseId}
                          </Typography.Text>
                        ))}
                      </Space>
                    ) : null}
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={resultSectionState.nextActionDescription}
            />
          )}
        </Card>
      </Space>
      <Modal
        title={selectedActionHelp?.title ?? '조치 방법'}
        open={Boolean(selectedActionHelp)}
        footer={null}
        onCancel={() => setSelectedActionHelp(null)}
        width={680}
      >
        {selectedActionHelp ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Space direction="vertical" size={4}>
              <Typography.Text strong>문제 패턴</Typography.Text>
              <Typography.Text>{selectedActionHelp.targetLabel}</Typography.Text>
            </Space>
            {selectedActionHelp.caseIds.length ? (
              <Space wrap size={[4, 4]}>
                <Typography.Text strong>대상 케이스</Typography.Text>
                {selectedActionHelp.caseIds.map((caseId) => (
                  <Typography.Text code key={caseId}>
                    {caseId}
                  </Typography.Text>
                ))}
              </Space>
            ) : null}
            <List
              size="small"
              dataSource={selectedActionHelp.helpSteps}
              renderItem={(step) => (
                <List.Item>
                  <Typography.Text>{step}</Typography.Text>
                </List.Item>
              )}
            />
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
