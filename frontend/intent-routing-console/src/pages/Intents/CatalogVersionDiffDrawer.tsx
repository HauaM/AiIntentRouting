import { ArrowRightOutlined } from '@ant-design/icons';
import { Drawer, Empty, Skeleton, Space, Tag, Typography } from 'antd';
import { StatusTag } from '../../components/StatusTag';
import { VersionChip } from '../../components/VersionChip';
import type {
  CatalogVersionDiffSection,
  CatalogVersionDiffSectionKey,
} from './catalogVersionTypes';

const intentDiffSections: CatalogVersionDiffSection[] = [
  { key: 'added_intents', title: '추가된 Intent' },
  { key: 'removed_intents', title: '삭제된 Intent' },
  { key: 'changed_intents', title: '변경된 Intent' },
];

const exampleDiffSections: CatalogVersionDiffSection[] = [
  { key: 'added_examples', title: '추가된 Example' },
  { key: 'removed_examples', title: '삭제된 Example' },
  { key: 'changed_examples', title: '변경된 Example' },
];

const summaryItems: { key: CatalogVersionDiffSectionKey; label: string }[] = [
  { key: 'added_intents', label: '+ Intent' },
  { key: 'removed_intents', label: '- Intent' },
  { key: 'changed_intents', label: '~ Intent' },
  { key: 'added_examples', label: '+ Example' },
  { key: 'removed_examples', label: '- Example' },
  { key: 'changed_examples', label: '~ Example' },
];

type CatalogVersionDiffDrawerProps = {
  open: boolean;
  loading?: boolean;
  target?: API.CatalogVersionListItem;
  baseline?: API.CatalogVersionListItem;
  diff?: API.CatalogVersionDiff;
  onClose: () => void;
};

type CatalogVersionExampleDiffGroup = {
  intent_id: string;
  intent_display_name: string;
  route_key: string;
  positive: string[];
  negative: string[];
};

const describeIntentDiffItem = (item: unknown) => {
  if (!item || typeof item !== 'object') return String(item ?? '-');
  const record = item as Record<string, unknown>;
  const after = record.after as Record<string, unknown> | undefined;
  const before = record.before as Record<string, unknown> | undefined;
  const target = after ?? before ?? record;
  return String(target.intent_id ?? target.display_name ?? JSON.stringify(target));
};

export const groupCatalogVersionExampleDiffItems = (
  items: API.CatalogVersionDiffExample[],
): CatalogVersionExampleDiffGroup[] => {
  const groups = new Map<string, CatalogVersionExampleDiffGroup>();

  items.forEach((item) => {
    const key = item.intent_id;
    const group =
      groups.get(key) ??
      {
        intent_id: item.intent_id,
        intent_display_name: item.intent_display_name,
        route_key: item.route_key,
        positive: [],
        negative: [],
      };

    if (item.example_type === 'positive') {
      group.positive.push(item.text_masked);
    } else {
      group.negative.push(item.text_masked);
    }
    groups.set(key, group);
  });

  return [...groups.values()];
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

const diffCount = (diff: API.CatalogVersionDiff | undefined, key: CatalogVersionDiffSectionKey) =>
  (diff?.[key] ?? []).length;

function VersionSummary({
  label,
  version,
  fallbackVersion,
}: {
  label: string;
  version?: API.CatalogVersionListItem;
  fallbackVersion?: string | null;
}) {
  return (
    <div className="catalog-diff-version-panel">
      <Typography.Text type="secondary">{label}</Typography.Text>
      <Space size={8} wrap>
        <Typography.Text strong>{version?.display_version ?? '-'}</Typography.Text>
        <VersionChip value={version?.intent_catalog_version ?? fallbackVersion} maxDisplayLength={28} />
      </Space>
      <Typography.Paragraph className="catalog-diff-version-description" ellipsis={{ rows: 2 }}>
        {version?.description ?? '-'}
      </Typography.Paragraph>
    </div>
  );
}

function EmptyChange() {
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description="변경 없음"
      className="catalog-diff-empty"
    />
  );
}

function IntentDiffSection({
  section,
  values,
  loading,
}: {
  section: CatalogVersionDiffSection;
  values: unknown[];
  loading: boolean;
}) {
  return (
    <div className="catalog-diff-section-block">
      <Space size={8} className="catalog-diff-section-title">
        <Typography.Text strong>{section.title}</Typography.Text>
        <Tag>{values.length}</Tag>
      </Space>
      {loading ? (
        <Skeleton active paragraph={{ rows: 2 }} title={false} />
      ) : values.length ? (
        <Space direction="vertical" size={6} className="catalog-diff-list">
          {values.slice(0, 20).map((item, index) => (
            <Typography.Text key={`${section.key}-${index}`} code ellipsis>
              {describeIntentDiffItem(item)}
            </Typography.Text>
          ))}
        </Space>
      ) : (
        <EmptyChange />
      )}
    </div>
  );
}

function ExampleBucket({
  status,
  label,
  values,
}: {
  status: 'positive' | 'negative';
  label: string;
  values: string[];
}) {
  if (!values.length) return null;

  return (
    <div className="catalog-diff-example-bucket">
      <Space size={8} className="catalog-diff-example-bucket-title">
        <StatusTag status={status} label={label} />
        <Tag>{values.length}</Tag>
      </Space>
      <ul className="catalog-diff-example-list">
        {values.map((value, index) => (
          <li key={`${status}-${index}`}>{value}</li>
        ))}
      </ul>
    </div>
  );
}

function ExampleDiffSection({
  section,
  values,
  loading,
}: {
  section: CatalogVersionDiffSection;
  values: API.CatalogVersionDiffExample[];
  loading: boolean;
}) {
  const groups = groupCatalogVersionExampleDiffItems(values);

  return (
    <div className="catalog-diff-section-block">
      <Space size={8} className="catalog-diff-section-title">
        <Typography.Text strong>{section.title}</Typography.Text>
        <Tag>{values.length}</Tag>
      </Space>
      {loading ? (
        <Skeleton active paragraph={{ rows: 4 }} title={false} />
      ) : groups.length ? (
        <Space direction="vertical" size={10} className="catalog-diff-list">
          {groups.slice(0, 20).map((group) => (
            <div key={group.intent_id} className="catalog-diff-example-group">
              <div className="catalog-diff-example-group-head">
                <Space size={8} wrap>
                  <Typography.Text strong>{group.intent_id}</Typography.Text>
                  <Typography.Text>{group.intent_display_name}</Typography.Text>
                </Space>
                <Typography.Text code>{group.route_key}</Typography.Text>
              </div>
              <ExampleBucket status="positive" label="Positive" values={group.positive} />
              <ExampleBucket status="negative" label="Negative" values={group.negative} />
            </div>
          ))}
        </Space>
      ) : (
        <EmptyChange />
      )}
    </div>
  );
}

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
      width={860}
      onClose={onClose}
      rootClassName="catalog-diff-drawer"
      styles={{ body: { overflowY: 'auto' } }}
    >
      <Space direction="vertical" size={16} className="catalog-diff-body">
        {target ? (
          <div className="catalog-diff-version-compare">
            <VersionSummary label="대상 버전" version={target} />
            <ArrowRightOutlined className="catalog-diff-version-arrow" />
            <VersionSummary
              label="비교 기준"
              version={baseline}
              fallbackVersion={diff?.from_version}
            />
          </div>
        ) : null}

        <div className="catalog-diff-summary-panel">
          <Typography.Text strong>변화 요약</Typography.Text>
          <div className="catalog-diff-summary-grid">
            {summaryItems.map((item) => (
              <div key={item.key} className="catalog-diff-summary-item">
                <Typography.Text type="secondary">{item.label}</Typography.Text>
                <Typography.Text strong>{diffCount(diff, item.key)}</Typography.Text>
              </div>
            ))}
          </div>
        </div>

        <div className="catalog-diff-group">
          <Typography.Title level={5}>Intent 변경</Typography.Title>
          {intentDiffSections.map((section) => (
            <IntentDiffSection
              key={section.key}
              section={section}
              values={(diff?.[section.key] ?? []) as unknown[]}
              loading={loading}
            />
          ))}
        </div>

        <div className="catalog-diff-group">
          <Typography.Title level={5}>Example 변경</Typography.Title>
          {exampleDiffSections.map((section) => (
            <ExampleDiffSection
              key={section.key}
              section={section}
              values={(diff?.[section.key] ?? []) as API.CatalogVersionDiffExample[]}
              loading={loading}
            />
          ))}
        </div>
      </Space>
    </Drawer>
  );
}
