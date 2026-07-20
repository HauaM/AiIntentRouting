import { useEffect, useMemo, useState } from 'react';
import { Button, Select, Space, Tag, Typography, message } from 'antd';
import { VersionChip } from '@/components/VersionChip';
import {
  listCatalogVersions,
  listPolicyVersions,
} from '@/services/adminServices';

type ValidationVersionsPanelProps = {
  serviceId: string;
  policy?: API.PolicyVersion;
  catalogVersion?: string;
  onChange: (value: { policy?: API.PolicyVersion; catalogVersion?: string }) => void;
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

export function ValidationVersionsPanel({
  serviceId,
  policy,
  catalogVersion,
  onChange,
}: ValidationVersionsPanelProps) {
  const [loadingLatest, setLoadingLatest] = useState(false);
  const [loadingCatalogVersions, setLoadingCatalogVersions] = useState(false);
  const [catalogVersions, setCatalogVersions] = useState<API.CatalogVersionListItem[]>([]);

  const selectedCatalogVersion = useMemo(
    () =>
      catalogVersions.find(
        (version) => version.intent_catalog_version === catalogVersion,
      ),
    [catalogVersion, catalogVersions],
  );

  useEffect(() => {
    let active = true;
    setLoadingCatalogVersions(true);
    listCatalogVersions(serviceId, {
      limit: CATALOG_VERSION_LIMIT,
      status: 'active',
    })
      .then((versions) => {
        if (active) setCatalogVersions(versions);
      })
      .finally(() => {
        if (active) setLoadingCatalogVersions(false);
      });
    return () => {
      active = false;
    };
  }, [serviceId]);

  const loadLatest = async () => {
    setLoadingLatest(true);
    try {
      const [policies, catalogs] = await Promise.all([
        listPolicyVersions(serviceId, 1),
        listCatalogVersions(serviceId, {
          limit: CATALOG_VERSION_LIMIT,
          status: 'active',
        }),
      ]);
      setCatalogVersions(catalogs);
      onChange({ policy: policies[0], catalogVersion: catalogs[0]?.intent_catalog_version });
      message.success('최신 검증 버전을 불러왔습니다.');
    } finally {
      setLoadingLatest(false);
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Typography.Title level={5} style={{ margin: 0 }}>검증 대상 버전</Typography.Title>
      <Typography.Text type="secondary">
        테스트 실행에는 정책 버전과 Catalog 버전이 모두 필요합니다.
      </Typography.Text>
      <Space wrap>
        <Button onClick={loadLatest} loading={loadingLatest}>최신 버전 불러오기</Button>
      </Space>
      <Select
        showSearch
        allowClear
        value={catalogVersion}
        loading={loadingCatalogVersions || loadingLatest}
        placeholder="활성 Catalog 버전 선택"
        optionFilterProp="label"
        style={{ width: '100%', maxWidth: 520 }}
        options={catalogVersions.map((version) => ({
          value: version.intent_catalog_version,
          label: catalogVersionSearchLabel(version),
          catalogVersion: version,
        }))}
        onChange={(selectedCatalogVersionValue) => {
          onChange({ policy, catalogVersion: selectedCatalogVersionValue });
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
        <VersionChip label="정책" value={policy?.policy_version} />
        <VersionChip label="Catalog" value={catalogVersion} />
        {selectedCatalogVersion ? (
          <>
            <Tag color={catalogVersionStatusColor[selectedCatalogVersion.status]}>
              {selectedCatalogVersion.status}
            </Tag>
            <Tag>{selectedCatalogVersion.display_version}</Tag>
          </>
        ) : null}
      </Space>
    </Space>
  );
}
