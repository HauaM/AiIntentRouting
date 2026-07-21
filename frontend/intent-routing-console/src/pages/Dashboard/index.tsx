import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Col,
  Row,
  Segmented,
  Select,
  Skeleton,
  Space,
  Statistic,
  Table,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { isAdminSessionReady } from '@/models/adminSession';
import { fetchRuntimeMetrics } from '@/services/adminServices';
import { getDashboardViewState, getScopedRuntimeMetrics } from './dashboardViewState';
import { formatLatencyMs } from './metricDisplay';

const windowOptions = [
  { label: '24h', value: 24 },
  { label: '7d', value: 168 },
  { label: '31d', value: 744 },
];

const environmentOptions = [
  { label: '전체 환경', value: '' },
  { label: 'dev', value: 'dev' },
  { label: 'qa', value: 'qa' },
  { label: 'prod', value: 'prod' },
];

export default function DashboardPage() {
  const { session } = useModel('adminSession');
  const [windowHours, setWindowHours] = useState<number>(24);
  const [selectedEnvironment, setSelectedEnvironment] =
    useState<'dev' | 'qa' | 'prod' | ''>('');
  const [metrics, setMetrics] = useState<API.RuntimeMetrics>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const metricRequestSeqRef = useRef(0);
  const ready = isAdminSessionReady(session);
  const scopedMetrics = getScopedRuntimeMetrics({
    metrics,
    serviceId: session.serviceId,
    windowHours,
  });
  const viewState = getDashboardViewState({
    hasMetrics: Boolean(scopedMetrics),
    loading,
    ready,
  });

  const loadMetrics = useCallback(async () => {
    if (!ready) return;
    const requestSeq = (metricRequestSeqRef.current += 1);
    setLoading(true);
    setError(undefined);
    setMetrics(undefined);
    try {
      const nextMetrics = await fetchRuntimeMetrics(
        session.serviceId,
        windowHours,
        selectedEnvironment || undefined,
      );
      if (requestSeq !== metricRequestSeqRef.current) return;
      setMetrics(nextMetrics);
    } catch (err: any) {
      if (requestSeq !== metricRequestSeqRef.current) return;
      setError(err?.message ?? 'Failed to load runtime metrics.');
    } finally {
      if (requestSeq === metricRequestSeqRef.current) setLoading(false);
    }
  }, [ready, selectedEnvironment, session.serviceId, windowHours]);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  const decisionRows = useMemo(
    () =>
      Object.entries(scopedMetrics?.decision_counts ?? {}).map(([decision, count]) => ({
        decision,
        count,
      })),
    [scopedMetrics],
  );

  const errorRows = useMemo(
    () =>
      Object.entries(scopedMetrics?.error_counts ?? {}).map(([errorCode, count]) => ({
        errorCode,
        count,
      })),
    [scopedMetrics],
  );

  return (
    <AdminShell title="Dashboard">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          className="admin-compact-page-notice"
          message="Admin UI Phase 1"
          description="현재 화면은 서비스 범위 운영, 런타임 증거, 감사 증거를 중심으로 합니다. 승인형 Phase 2 흐름은 연결된 화면에서 안내됩니다."
        />
        {viewState === 'session-required' ? <AdminSessionRequired /> : null}
        {viewState === 'session-required' ? null : (
          <div className="toolbar-line">
            <Select
              aria-label="Environment"
              value={selectedEnvironment}
              options={environmentOptions}
              onChange={setSelectedEnvironment}
              style={{ width: 180 }}
            />
            <Segmented
              options={windowOptions}
              value={windowHours}
              onChange={(value) => setWindowHours(Number(value))}
            />
            <Button icon={<ReloadOutlined />} loading={loading} onClick={loadMetrics}>
              새로고침
            </Button>
          </div>
        )}
        {viewState !== 'session-required' && error ? (
          <Alert type="error" showIcon message={error} />
        ) : null}
        {viewState === 'loading' ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : null}
        {viewState === 'empty' ? (
          <Alert
            type="warning"
            showIcon
            message="Runtime metrics are unavailable."
            description="Dashboard metric panels stay hidden until the Admin API returns a metrics payload."
          />
        ) : null}
        {viewState === 'data' ? (
          <>
            <Row gutter={[12, 12]}>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="Requests" value={scopedMetrics?.request_count ?? 0} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic
                    title="Latency p95"
                    value={formatLatencyMs(scopedMetrics?.latency_ms.p95)}
                  />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic
                    title="Encrypted text retained"
                    value={scopedMetrics?.raw_query_retention.encrypted_count ?? 0}
                  />
                </Card>
              </Col>
            </Row>
            <Row gutter={[12, 12]}>
              <Col xs={24} lg={12}>
                <Card title="Decision Counts">
                  <Table
                    rowKey="decision"
                    size="small"
                    pagination={false}
                    dataSource={decisionRows}
                    columns={[
                      { title: 'Decision', dataIndex: 'decision' },
                      { title: 'Count', dataIndex: 'count', align: 'right' },
                    ]}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="Top Route Keys">
                  <Table
                    rowKey="route_key"
                    size="small"
                    pagination={false}
                    dataSource={scopedMetrics?.top_route_keys ?? []}
                    columns={[
                      { title: 'Route', dataIndex: 'route_key', ellipsis: true },
                      { title: 'Count', dataIndex: 'count', align: 'right' },
                    ]}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="Errors">
                  <Table
                    rowKey="errorCode"
                    size="small"
                    pagination={false}
                    dataSource={errorRows}
                    columns={[
                      { title: 'Code', dataIndex: 'errorCode' },
                      { title: 'Count', dataIndex: 'count', align: 'right' },
                    ]}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="Retention">
                  <Table
                    rowKey="state"
                    size="small"
                    pagination={false}
                    dataSource={[
                      {
                        state: 'encrypted',
                        count: scopedMetrics?.raw_query_retention.encrypted_count ?? 0,
                      },
                      {
                        state: 'incomplete',
                        count: scopedMetrics?.raw_query_retention.incomplete_count ?? 0,
                      },
                      {
                        state: 'redacted',
                        count: scopedMetrics?.raw_query_retention.redacted_count ?? 0,
                      },
                    ]}
                    columns={[
                      { title: 'State', dataIndex: 'state' },
                      { title: 'Count', dataIndex: 'count', align: 'right' },
                    ]}
                  />
                </Card>
              </Col>
            </Row>
          </>
        ) : null}
      </Space>
    </AdminShell>
  );
}
