import { Alert, Card, Descriptions, Empty, Spin, Typography } from 'antd';
import { StatusTag } from '@/components/StatusTag';

const catalogStatusTone = (status: string) => {
  if (status === 'active') return 'active';
  if (status === 'inactive') return 'inactive';
  return 'warning';
};

const catalogStatusLabel = (status: string) => {
  if (status === 'active') return '활성';
  if (status === 'inactive') return '비활성';
  return '상태 확인 필요';
};

const reproducibilityTone = (status: string) => (status === 'complete' ? 'pass' : 'warning');

const reproducibilityLabel = (status: string) =>
  status === 'complete' ? '완전' : '확인 필요';

type TestRunCatalogStatusPanelProps = {
  diagnostics?: API.TestRunDiagnostics | null;
  diagnosticsLoading?: boolean;
  diagnosticsError?: string | null;
};

export function TestRunCatalogStatusPanel({
  diagnostics,
  diagnosticsLoading = false,
  diagnosticsError,
}: TestRunCatalogStatusPanelProps) {
  const catalog = diagnostics?.catalog_version;

  return (
    <Card size="small" title="Catalog / Vector 상태">
      {diagnosticsLoading ? (
        <Spin spinning>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Catalog 상태를 불러오는 중입니다." />
        </Spin>
      ) : diagnosticsError ? (
        <Alert
          type="error"
          showIcon
          message="Catalog 상태를 불러오지 못했습니다."
          description={diagnosticsError}
        />
      ) : catalog ? (
        <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
          <Descriptions.Item label="Catalog 버전">
            <Typography.Text code>{catalog.intent_catalog_version}</Typography.Text>
          </Descriptions.Item>
          <Descriptions.Item label="상태">
            <StatusTag
              status={catalogStatusTone(catalog.status)}
              label={catalogStatusLabel(catalog.status)}
            />
          </Descriptions.Item>
          <Descriptions.Item label="재현성">
            <StatusTag
              status={reproducibilityTone(catalog.reproducibility_status)}
              label={reproducibilityLabel(catalog.reproducibility_status)}
            />
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
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Catalog 상태가 없습니다." />
      )}
    </Card>
  );
}
