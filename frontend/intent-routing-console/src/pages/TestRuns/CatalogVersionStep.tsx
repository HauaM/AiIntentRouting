import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TableProps } from 'antd';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import { StatusTag } from '@/components/StatusTag';
import { VersionChip } from '@/components/VersionChip';
import { fetchCatalogVersion, listCatalogVersions } from '@/services/adminServices';
import {
  extractCatalogSnapshotIntents,
  type CatalogSnapshotExample,
  type CatalogSnapshotIntent,
} from './catalogSnapshot';

type CatalogVersionStepProps = {
  serviceId: string;
  value?: API.CatalogVersionListItem;
  onChange: (value?: API.CatalogVersionListItem) => void;
};

const CATALOG_VERSION_LIMIT = 100;

const catalogVersionSearchLabel = (version: API.CatalogVersionListItem) =>
  [
    version.display_version,
    version.description,
    version.intent_catalog_version,
    version.status,
    version.model_version,
    version.vector_index_version,
  ]
    .filter(Boolean)
    .join(' ');

const catalogVersionOptionLabel = (version: API.CatalogVersionListItem) =>
  version.display_version || version.intent_catalog_version;

type ExampleModalState = {
  intent: CatalogSnapshotIntent;
  type: 'positive' | 'negative';
};

export function CatalogVersionStep({
  serviceId,
  value,
  onChange,
}: CatalogVersionStepProps) {
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState<API.CatalogVersionListItem[]>([]);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotIntents, setSnapshotIntents] = useState<CatalogSnapshotIntent[]>([]);
  const [snapshotError, setSnapshotError] = useState<string>();
  const [intentKeyword, setIntentKeyword] = useState('');
  const [intentStatus, setIntentStatus] = useState<string>();
  const [exampleModal, setExampleModal] = useState<ExampleModalState>();
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const versionRequestRef = useRef(0);
  const snapshotRequestRef = useRef(0);

  valueRef.current = value;
  onChangeRef.current = onChange;

  const selectedValue = value?.intent_catalog_version;
  const selectedVersion = useMemo(
    () =>
      versions.find(
        (version) => version.intent_catalog_version === selectedValue,
      ) ?? value,
    [selectedValue, value, versions],
  );
  const selectedCatalogVersionWarning = selectedVersion
    ? selectedVersion.status !== 'active' ||
      selectedVersion.reproducibility_status !== 'complete'
    : false;
  const filteredSnapshotIntents = useMemo(() => {
    const keyword = intentKeyword.trim().toLowerCase();
    return snapshotIntents.filter((intent) => {
      const matchesStatus = !intentStatus || intent.status === intentStatus;
      const matchesKeyword =
        !keyword ||
        [
          intent.intent_id,
          intent.display_name,
          intent.description,
          intent.route_key,
          intent.status,
        ].some((value) => value.toLowerCase().includes(keyword));
      return matchesStatus && matchesKeyword;
    });
  }, [intentKeyword, intentStatus, snapshotIntents]);
  const intentStatusOptions = useMemo(
    () =>
      Array.from(new Set(snapshotIntents.map((intent) => intent.status).filter(Boolean))).map(
        (status) => ({ label: status, value: status }),
      ),
    [snapshotIntents],
  );
  const openExampleModal = useCallback(
    (intent: CatalogSnapshotIntent, type: ExampleModalState['type']) => {
      setExampleModal({ intent, type });
    },
    [],
  );
  const exampleModalExamples = useMemo<CatalogSnapshotExample[]>(() => {
    if (!exampleModal) return [];
    return exampleModal.type === 'positive'
      ? exampleModal.intent.positive_examples
      : exampleModal.intent.negative_examples;
  }, [exampleModal]);
  const exampleModalTitle = exampleModal
    ? `${exampleModal.intent.intent_id || exampleModal.intent.route_key} ${
        exampleModal.type === 'positive' ? 'Positive' : 'Negative'
      } examples`
    : 'Examples';
  const exampleModalColumns: TableProps<CatalogSnapshotExample>['columns'] = [
    {
      title: 'Example',
      dataIndex: 'text_masked',
      render: (value: string) => (
        <Typography.Text className="test-run-example-text">
          {value || '-'}
        </Typography.Text>
      ),
    },
    {
      title: 'Source',
      dataIndex: 'source',
      width: 120,
      render: (value: string) => value || '-',
    },
    {
      title: 'Status',
      dataIndex: 'approved',
      width: 112,
      render: (approved: boolean) =>
        approved ? (
          <StatusTag status="approved" label="승인됨" />
        ) : (
          <StatusTag status="pending" label="대기" />
        ),
    },
  ];
  const snapshotIntentColumns: TableProps<CatalogSnapshotIntent>['columns'] = [
    {
      title: 'Intent',
      dataIndex: 'intent_id',
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.intent_id}</Typography.Text>
          <Typography.Text type="secondary">{row.display_name || row.description || '-'}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Route key',
      dataIndex: 'route_key',
      render: (value: string) => (
        <Tooltip title={value}>
          <Typography.Text code ellipsis style={{ maxWidth: 320 }}>
            {value || '-'}
          </Typography.Text>
        </Tooltip>
      ),
    },
    {
      title: 'Example',
      width: 184,
      render: (_, row) => (
        <Space size={4} wrap>
          <Button
            type="link"
            size="small"
            className="test-run-example-count-button"
            onClick={() => openExampleModal(row, 'positive')}
          >
            Positive {row.positive_example_count}
          </Button>
          <Button
            type="link"
            size="small"
            className="test-run-example-count-button"
            onClick={() => openExampleModal(row, 'negative')}
          >
            Negative {row.negative_example_count}
          </Button>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 112,
      render: (value: string) => (
        <StatusTag status={value || 'none'} label={value || '-'} />
      ),
    },
  ];

  const loadVersions = useCallback(async () => {
    const requestId = versionRequestRef.current + 1;
    versionRequestRef.current = requestId;
    setLoading(true);
    try {
      const nextVersions = await listCatalogVersions(serviceId, {
        limit: CATALOG_VERSION_LIMIT,
        status: 'active',
      });
      if (versionRequestRef.current !== requestId) return;
      setVersions(nextVersions);
      if (!valueRef.current) {
        const defaultVersion = nextVersions[0];
        onChangeRef.current(defaultVersion);
      }
    } finally {
      if (versionRequestRef.current === requestId) setLoading(false);
    }
  }, [serviceId]);

  useEffect(() => {
    void loadVersions();
  }, [loadVersions]);

  useEffect(() => {
    return () => {
      versionRequestRef.current += 1;
      snapshotRequestRef.current += 1;
    };
  }, []);

  useEffect(() => {
    if (!selectedValue) {
      setSnapshotIntents([]);
      setSnapshotError(undefined);
      setSnapshotLoading(false);
      return;
    }

    const requestId = snapshotRequestRef.current + 1;
    snapshotRequestRef.current = requestId;
    setSnapshotLoading(true);
    setSnapshotError(undefined);
    void fetchCatalogVersion(serviceId, selectedValue)
      .then((catalog) => {
        if (snapshotRequestRef.current !== requestId) return;
        setSnapshotIntents(extractCatalogSnapshotIntents(catalog.snapshot));
      })
      .catch(() => {
        if (snapshotRequestRef.current !== requestId) return;
        setSnapshotIntents([]);
        setSnapshotError('선택한 Catalog의 Intent snapshot을 불러오지 못했습니다.');
      })
      .finally(() => {
        if (snapshotRequestRef.current === requestId) setSnapshotLoading(false);
      });
  }, [selectedValue, serviceId]);

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space direction="vertical" size={4}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          Intent Catalog 선택
        </Typography.Title>
        <Typography.Text type="secondary">
          테스트에 사용할 Catalog 스냅샷을 선택합니다. 기본값은 최신 active 버전입니다.
        </Typography.Text>
      </Space>
      <div className="test-run-step-field">
        <label
          className="test-run-step-field-label"
          htmlFor="test-run-catalog-version-select"
        >
          Catalog 버전
        </label>
        <Select
          id="test-run-catalog-version-select"
          showSearch
          allowClear
          value={selectedValue}
          loading={loading}
          placeholder="Catalog 버전을 선택하세요"
          optionFilterProp="searchLabel"
          className="test-run-step-select"
          options={versions.map((version) => ({
            value: version.intent_catalog_version,
            label: catalogVersionOptionLabel(version),
            searchLabel: catalogVersionSearchLabel(version),
            catalogVersion: version,
          }))}
          onChange={(nextVersionId) => {
            onChange(
              versions.find(
                (version) => version.intent_catalog_version === nextVersionId,
              ),
            );
          }}
          optionRender={({ data }) => {
            const version = data.catalogVersion as API.CatalogVersionListItem;
            return (
              <Space direction="vertical" size={2}>
                <Space wrap size={6}>
                  <Typography.Text strong>
                    {version.display_version}
                  </Typography.Text>
                  <StatusTag status={version.status} label={version.status} />
                  <Tag>
                    {version.released ? `released ${version.release_count}` : 'unreleased'}
                  </Tag>
                  <Tag>{version.embedding_count} embeddings</Tag>
                </Space>
                <Typography.Text type="secondary" ellipsis>
                  {version.description || version.intent_catalog_version}
                </Typography.Text>
                <Typography.Text type="secondary">
                  model {version.model_version || 'none'} / vector{' '}
                  {version.vector_index_version || 'none'}
                </Typography.Text>
              </Space>
            );
          }}
        />
        <Typography.Text type="secondary" className="test-run-step-field-help">
          선택한 Catalog 버전은 테스트 결과와 Release 후보에서 그대로 참조됩니다.
        </Typography.Text>
      </div>
      {selectedVersion ? (
        <Descriptions
          className="test-run-step-summary"
          size="small"
          column={{ xs: 1, md: 2, xl: 3 }}
          items={[
            {
              key: 'catalog',
              label: 'Catalog',
              children: (
                <VersionChip
                  value={selectedVersion.intent_catalog_version}
                  maxDisplayLength={8}
                />
              ),
            },
            {
              key: 'status',
              label: '상태',
              children: (
                <StatusTag
                  status={selectedVersion.status}
                  label={selectedVersion.status}
                />
              ),
            },
            {
              key: 'version',
              label: '버전',
              children: selectedVersion.display_version,
            },
            {
              key: 'reproducibility',
              label: '재현성',
              children: selectedVersion.reproducibility_status,
            },
            {
              key: 'model',
              label: '모델',
              children: selectedVersion.model_version || 'none',
            },
            {
              key: 'vector',
              label: 'Vector index',
              children: selectedVersion.vector_index_version || 'none',
            },
          ]}
        />
      ) : null}
      {selectedCatalogVersionWarning && selectedVersion ? (
        <Alert
          type="warning"
          showIcon
          message="선택한 Catalog 버전 상태를 확인하세요"
          description={`status=${selectedVersion.status}, reproducibility=${selectedVersion.reproducibility_status}`}
        />
      ) : null}
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <div className="test-run-catalog-intent-toolbar">
          <Space direction="vertical" size={2}>
            <Typography.Title level={5} style={{ margin: 0 }}>
              선택한 Catalog의 Intent 목록
            </Typography.Title>
            <Typography.Text type="secondary">
              테스트할 내용을 미리 확인하세요.
            </Typography.Text>
          </Space>
          <Space wrap>
            <Input
              allowClear
              placeholder="Intent 검색"
              value={intentKeyword}
              onChange={(event) => setIntentKeyword(event.target.value)}
              className="test-run-catalog-intent-search"
            />
            <Select
              allowClear
              placeholder="전체 상태"
              value={intentStatus}
              onChange={setIntentStatus}
              options={intentStatusOptions}
              className="test-run-catalog-intent-status"
            />
            <Typography.Text type="secondary">{filteredSnapshotIntents.length}개</Typography.Text>
          </Space>
        </div>
        {snapshotError ? (
          <Alert type="warning" showIcon message={snapshotError} />
        ) : (
          <Table<CatalogSnapshotIntent>
            rowKey={(row) => row.intent_id || row.route_key}
            size="small"
            loading={snapshotLoading}
            columns={snapshotIntentColumns}
            dataSource={filteredSnapshotIntents}
            pagination={false}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="선택한 Catalog에 표시할 Intent가 없습니다."
                />
              ),
            }}
          />
        )}
      </Space>
      <Modal
        title={exampleModalTitle}
        open={Boolean(exampleModal)}
        footer={null}
        width={760}
        destroyOnHidden
        onCancel={() => setExampleModal(undefined)}
      >
        <Table<CatalogSnapshotExample>
          rowKey={(row, index) => row.example_id || `${row.example_type}-${index}`}
          size="small"
          className="test-run-example-modal-table"
          columns={exampleModalColumns}
          dataSource={exampleModalExamples}
          pagination={false}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="표시할 Example이 없습니다."
              />
            ),
          }}
        />
      </Modal>
    </Space>
  );
}
