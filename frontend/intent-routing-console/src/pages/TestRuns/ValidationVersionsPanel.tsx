import { useState } from 'react';
import { Button, Space, Typography, message } from 'antd';
import { VersionChip } from '@/components/VersionChip';
import {
  createCatalogVersion,
  listCatalogVersions,
  listPolicyVersions,
} from '@/services/adminServices';

type ValidationVersionsPanelProps = {
  serviceId: string;
  policy?: API.PolicyVersion;
  catalogVersion?: string;
  onChange: (value: { policy?: API.PolicyVersion; catalogVersion?: string }) => void;
};

export function ValidationVersionsPanel({
  serviceId,
  policy,
  catalogVersion,
  onChange,
}: ValidationVersionsPanelProps) {
  const [loadingLatest, setLoadingLatest] = useState(false);
  const [creatingCatalog, setCreatingCatalog] = useState(false);

  const loadLatest = async () => {
    setLoadingLatest(true);
    try {
      const [policies, catalogs] = await Promise.all([
        listPolicyVersions(serviceId, 1),
        listCatalogVersions(serviceId, 1),
      ]);
      onChange({ policy: policies[0], catalogVersion: catalogs[0]?.intent_catalog_version });
      message.success('최신 검증 버전을 불러왔습니다.');
    } finally {
      setLoadingLatest(false);
    }
  };

  const createCatalog = async () => {
    setCreatingCatalog(true);
    try {
      const catalog = await createCatalogVersion(serviceId);
      onChange({ policy, catalogVersion: catalog.intent_catalog_version });
      message.success('새 Catalog 버전을 현재 테스트에 적용했습니다.');
    } finally {
      setCreatingCatalog(false);
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
        <Button onClick={createCatalog} loading={creatingCatalog}>새 Catalog 버전 만들기</Button>
      </Space>
      <Space wrap>
        <VersionChip label="정책" value={policy?.policy_version} />
        <VersionChip label="Catalog" value={catalogVersion} />
      </Space>
    </Space>
  );
}
