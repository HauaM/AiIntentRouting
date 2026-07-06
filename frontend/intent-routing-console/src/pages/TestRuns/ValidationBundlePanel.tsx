import { Button, Segmented, Space, Typography, message } from 'antd';
import { useState } from 'react';
import { VersionChip } from '@/components/VersionChip';
import {
  createCatalogVersion,
  createPolicyVersion,
  listCatalogVersions,
  listPolicyVersions,
} from '@/services/adminServices';

export type ValidationBundle = {
  policy_version?: string;
  intent_catalog_version?: string;
  threshold_preset: API.ThresholdPreset;
};

type ValidationBundlePanelProps = {
  serviceId: string;
  value: ValidationBundle;
  onChange: (value: ValidationBundle) => void;
};

const defaultPolicyPayload = (
  preset: API.ThresholdPreset,
): API.PolicyVersionCreateRequest => ({
  threshold_preset: preset,
  clarify_margin: 0.08,
  min_candidate_score: 0.55,
  fallback_score: 0.45,
  risk_policy: { enabled: true },
  off_topic_policy: { enabled: true, keywords: [], message: '' },
});

export function ValidationBundlePanel({
  serviceId,
  value,
  onChange,
}: ValidationBundlePanelProps) {
  const [loadingPolicy, setLoadingPolicy] = useState(false);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [loadingLatest, setLoadingLatest] = useState(false);

  const loadLatest = async () => {
    setLoadingLatest(true);
    try {
      const [policies, catalogs] = await Promise.all([
        listPolicyVersions(serviceId, 1),
        listCatalogVersions(serviceId, 1),
      ]);
      onChange({
        threshold_preset:
          (policies[0]?.threshold_preset as API.ThresholdPreset | undefined) ||
          value.threshold_preset,
        policy_version: policies[0]?.policy_version,
        intent_catalog_version: catalogs[0]?.intent_catalog_version,
      });
      message.success('Latest validation bundle loaded.');
    } finally {
      setLoadingLatest(false);
    }
  };

  const createPolicy = async () => {
    setLoadingPolicy(true);
    try {
      const policy = await createPolicyVersion(
        serviceId,
        defaultPolicyPayload(value.threshold_preset),
      );
      onChange({
        ...value,
        policy_version: policy.policy_version,
        threshold_preset: policy.threshold_preset as API.ThresholdPreset,
      });
      message.success('Policy version created.');
    } finally {
      setLoadingPolicy(false);
    }
  };

  const createCatalog = async () => {
    setLoadingCatalog(true);
    try {
      const catalog = await createCatalogVersion(serviceId);
      onChange({ ...value, intent_catalog_version: catalog.intent_catalog_version });
      message.success('Catalog version created.');
    } finally {
      setLoadingCatalog(false);
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Typography.Text strong>Validation bundle</Typography.Text>
      <Segmented
        value={value.threshold_preset}
        onChange={(next) =>
          onChange({ ...value, threshold_preset: next as API.ThresholdPreset })
        }
        options={[
          { label: 'strict', value: 'strict' },
          { label: 'balanced', value: 'balanced' },
          { label: 'exploratory', value: 'exploratory' },
        ]}
      />
      <Space wrap>
        <Button onClick={loadLatest} loading={loadingLatest}>
          최신 bundle 불러오기
        </Button>
        <Button onClick={createPolicy} loading={loadingPolicy}>
          Policy 생성
        </Button>
        <Button onClick={createCatalog} loading={loadingCatalog}>
          Catalog 생성
        </Button>
      </Space>
      <Space wrap>
        <VersionChip label="policy" value={value.policy_version} />
        <VersionChip label="catalog" value={value.intent_catalog_version} />
      </Space>
    </Space>
  );
}
