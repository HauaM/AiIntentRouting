import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Select, Space, Tag, Typography } from 'antd';
import { VersionChip } from '@/components/VersionChip';
import { listCatalogVersions } from '@/services/adminServices';

type CatalogVersionStepProps = {
  serviceId: string;
  value?: API.CatalogVersionListItem;
  onChange: (value?: API.CatalogVersionListItem) => void;
};

const CATALOG_VERSION_LIMIT = 100;

const catalogVersionStatusColor: Record<API.CatalogVersionStatus, string> = {
  active: 'green',
  inactive: 'default',
};

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

export function CatalogVersionStep({
  serviceId,
  value,
  onChange,
}: CatalogVersionStepProps) {
  const [loading, setLoading] = useState(false);
  const [versionMode, setVersionMode] = useState<'active' | 'all'>('active');
  const [versions, setVersions] = useState<API.CatalogVersionListItem[]>([]);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const versionRequestRef = useRef(0);
  const latestSelectionRequestedRef = useRef(false);

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

  const loadVersions = useCallback(
    async (nextVersionMode: 'active' | 'all', selectLatest = false) => {
      const requestId = versionRequestRef.current + 1;
      versionRequestRef.current = requestId;
      setLoading(true);
      try {
        const nextVersions = await listCatalogVersions(serviceId, {
          limit: CATALOG_VERSION_LIMIT,
          status: nextVersionMode === 'active' ? 'active' : undefined,
        });
        if (versionRequestRef.current !== requestId) return;
        setVersions(nextVersions);
        if (selectLatest || (!valueRef.current && nextVersionMode === 'active')) {
          onChangeRef.current(nextVersions[0]);
        }
      } finally {
        if (versionRequestRef.current === requestId) setLoading(false);
      }
    },
    [serviceId],
  );

  useEffect(() => {
    const selectLatest = latestSelectionRequestedRef.current;
    latestSelectionRequestedRef.current = false;
    void loadVersions(versionMode, selectLatest);
  }, [loadVersions, versionMode]);

  const handleLoadLatest = () => {
    if (versionMode === 'active') {
      void loadVersions('active', true);
      return;
    }
    latestSelectionRequestedRef.current = true;
    setVersionMode('active');
  };

  useEffect(() => {
    return () => {
      versionRequestRef.current += 1;
    };
  }, []);

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space direction="vertical" size={4}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          Intent Catalog 선택
        </Typography.Title>
        <Typography.Text type="secondary">
          기본값은 최신 Catalog 버전입니다. 과거 검증이 필요하면 전체 버전을 불러와 선택하세요.
        </Typography.Text>
      </Space>
      <Alert
        type="info"
        showIcon
        message="테스트는 선택한 Catalog 버전 스냅샷 기준으로 실행됩니다."
        description="테스트 결과와 Release 후보는 이 단계에서 선택한 intent_catalog_version을 계속 참조합니다."
      />
      {selectedCatalogVersionWarning && selectedVersion ? (
        <Alert
          type="warning"
          showIcon
          message="선택한 Catalog 버전 상태를 확인하세요"
          description={`status=${selectedVersion.status}, reproducibility=${selectedVersion.reproducibility_status}`}
        />
      ) : null}
      <Space wrap>
        <Button
          loading={loading && versionMode === 'active'}
          onClick={handleLoadLatest}
        >
          최신 Catalog 버전
        </Button>
        <Button
          loading={loading && versionMode === 'all'}
          onClick={() => setVersionMode('all')}
        >
          전체 버전 불러오기
        </Button>
      </Space>
      <Select
        showSearch
        allowClear
        value={selectedValue}
        loading={loading}
        placeholder="Catalog 버전을 선택하세요"
        optionFilterProp="label"
        style={{ width: '100%', maxWidth: 560 }}
        options={versions.map((version) => ({
          value: version.intent_catalog_version,
          label: catalogVersionSearchLabel(version),
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
                <Typography.Text strong>{version.display_version}</Typography.Text>
                <Tag color={catalogVersionStatusColor[version.status]}>
                  {version.status}
                </Tag>
                <Tag>{version.released ? `released ${version.release_count}` : 'unreleased'}</Tag>
                <Tag>{version.embedding_count} embeddings</Tag>
              </Space>
              <Typography.Text type="secondary" ellipsis>
                {version.description || version.intent_catalog_version}
              </Typography.Text>
              <Typography.Text type="secondary">
                model {version.model_version || 'none'} / vector {version.vector_index_version || 'none'}
              </Typography.Text>
            </Space>
          );
        }}
      />
      <Space wrap>
        <VersionChip label="Catalog" value={selectedVersion?.intent_catalog_version} />
        {selectedVersion ? (
          <>
            <Tag color={catalogVersionStatusColor[selectedVersion.status]}>
              {selectedVersion.status}
            </Tag>
            <Tag>{selectedVersion.display_version}</Tag>
          </>
        ) : null}
      </Space>
    </Space>
  );
}
