import { Card, Descriptions, Empty, Typography } from 'antd';

type TestRunCatalogStatusPanelProps = {
  diagnostics?: API.TestRunDiagnostics | null;
};

export function TestRunCatalogStatusPanel({ diagnostics }: TestRunCatalogStatusPanelProps) {
  const catalog = diagnostics?.catalog_version;

  return (
    <Card size="small" title="Catalog / Vector 상태">
      {catalog ? (
        <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
          <Descriptions.Item label="Catalog 버전">
            <Typography.Text code>{catalog.intent_catalog_version}</Typography.Text>
          </Descriptions.Item>
          <Descriptions.Item label="상태">{catalog.status}</Descriptions.Item>
          <Descriptions.Item label="재현성">{catalog.reproducibility_status}</Descriptions.Item>
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
