import { Button, Empty, Space, Table, Tag, Tooltip, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { CsvCaseDraft } from './csvCaseBuilder';

type CsvCasesGridProps = {
  cases: CsvCaseDraft[];
  sourceFilename: string;
  onImport: () => void;
  onExport: () => void;
};

const expectedIntentRequired = new Set(['positive', 'confusing']);

const columns: ColumnsType<CsvCaseDraft> = [
  {
    title: 'Case',
    dataIndex: 'case_id',
    width: 140,
    ellipsis: true,
    render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
  },
  {
    title: 'Query',
    dataIndex: 'query',
    ellipsis: true,
    render: (value: string) => (
      <Tooltip title={value}>
        <Typography.Text ellipsis>{value}</Typography.Text>
      </Tooltip>
    ),
  },
  {
    title: 'Expected intent',
    dataIndex: 'expected_intent',
    width: 180,
    ellipsis: true,
    render: (value: string, row) =>
      expectedIntentRequired.has(row.case_type) ? (
        <Typography.Text>{value}</Typography.Text>
      ) : (
        <Typography.Text type="secondary">없음</Typography.Text>
      ),
  },
  {
    title: 'Case type',
    dataIndex: 'case_type',
    width: 132,
    render: (value: string) => <Tag>{value}</Tag>,
  },
  {
    title: 'Memo',
    dataIndex: 'memo',
    width: 220,
    ellipsis: true,
  },
];

export function CsvCasesGrid({
  cases,
  sourceFilename,
  onImport,
  onExport,
}: CsvCasesGridProps) {
  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space direction="vertical" size={2}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            테스트 CSV 데이터
          </Typography.Title>
          <Typography.Text type="secondary">
            {cases.length ? `${sourceFilename} · ${cases.length}건` : '적용된 CSV 데이터가 없습니다.'}
          </Typography.Text>
        </Space>
        <Space wrap>
          <Button onClick={onImport}>CSV 가져오기</Button>
          <Button onClick={onExport} disabled={!cases.length}>
            CSV 내보내기
          </Button>
        </Space>
      </Space>
      <Table<CsvCaseDraft>
        rowKey="case_id"
        size="small"
        columns={columns}
        dataSource={cases}
        pagination={false}
        scroll={{ x: 920 }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="CSV 가져오기로 테스트 데이터를 등록하세요."
            />
          ),
        }}
      />
    </Space>
  );
}
