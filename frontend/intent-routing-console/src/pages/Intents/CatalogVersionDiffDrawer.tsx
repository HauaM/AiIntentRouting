import { Descriptions, Drawer, Space, Tag, Typography } from 'antd';
import type { CatalogVersionDiffSection } from './catalogVersionTypes';

const diffSections: CatalogVersionDiffSection[] = [
  { key: 'added_intents', title: '추가된 Intent' },
  { key: 'removed_intents', title: '삭제된 Intent' },
  { key: 'changed_intents', title: '변경된 Intent' },
  { key: 'added_examples', title: '추가된 Example' },
  { key: 'removed_examples', title: '삭제된 Example' },
  { key: 'changed_examples', title: '변경된 Example' },
];

type CatalogVersionDiffDrawerProps = {
  open: boolean;
  loading?: boolean;
  target?: API.CatalogVersionListItem;
  baseline?: API.CatalogVersionListItem;
  diff?: API.CatalogVersionDiff;
  onClose: () => void;
};

const describeDiffItem = (item: unknown) => {
  if (!item || typeof item !== 'object') return String(item ?? '-');
  const record = item as Record<string, unknown>;
  const after = record.after as Record<string, unknown> | undefined;
  const before = record.before as Record<string, unknown> | undefined;
  const target = after ?? before ?? record;
  return String(
    target.intent_id ??
      target.example_id ??
      target.display_name ??
      target.text_masked ??
      JSON.stringify(target),
  );
};

export const selectCatalogVersionDiffBaseline = (
  versions: API.CatalogVersionListItem[],
  target: API.CatalogVersionListItem,
) =>
  versions
    .filter(
      (version) =>
        version.intent_catalog_version !== target.intent_catalog_version &&
        new Date(version.created_at).getTime() < new Date(target.created_at).getTime(),
    )
    .sort(
      (left, right) =>
        new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
    )[0];

export function CatalogVersionDiffDrawer({
  open,
  loading = false,
  target,
  baseline,
  diff,
  onClose,
}: CatalogVersionDiffDrawerProps) {
  return (
    <Drawer
      title={target ? `${target.display_version} 비교` : 'Catalog 버전 비교'}
      open={open}
      width={720}
      onClose={onClose}
      styles={{ body: { overflowY: 'auto' } }}
    >
      {target ? (
        <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
          <Descriptions.Item label="대상 버전">
            <Space size={6} wrap>
              <Typography.Text strong>{target.display_version}</Typography.Text>
              <Typography.Text code>{target.intent_catalog_version}</Typography.Text>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="대상 설명">{target.description || '-'}</Descriptions.Item>
          <Descriptions.Item label="비교 기준">
            {baseline ? (
              <Space size={6} wrap>
                <Typography.Text strong>{baseline.display_version}</Typography.Text>
                <Typography.Text code>{baseline.intent_catalog_version}</Typography.Text>
              </Space>
            ) : diff?.from_version ? (
              <Typography.Text code>{diff.from_version}</Typography.Text>
            ) : (
              '이전 버전 없음'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="기준 설명">
            {baseline?.description ?? '-'}
          </Descriptions.Item>
        </Descriptions>
      ) : null}
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {diffSections.map((section) => {
          const values = (diff?.[section.key] ?? []) as unknown[];
          return (
            <div key={section.key}>
              <Space size={8} style={{ marginBottom: 4 }}>
                <Typography.Text strong>{section.title}</Typography.Text>
                <Tag>{values.length}</Tag>
              </Space>
              {loading ? (
                <Typography.Text type="secondary">불러오는 중...</Typography.Text>
              ) : values.length ? (
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  {values.slice(0, 20).map((item, index) => (
                    <Typography.Text key={`${section.key}-${index}`} code ellipsis>
                      {describeDiffItem(item)}
                    </Typography.Text>
                  ))}
                </Space>
              ) : (
                <Typography.Text type="secondary">변경 없음</Typography.Text>
              )}
            </div>
          );
        })}
      </Space>
    </Drawer>
  );
}
