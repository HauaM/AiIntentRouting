import { useMemo, useState } from 'react';
import { Alert, Button, Space, Typography, message } from 'antd';
import { VersionChip } from '@/components/VersionChip';
import { createPolicyVersion } from '@/services/adminServices';
import { CustomTestPolicyModal } from './CustomTestPolicyModal';
import {
  createPolicyDraft,
  policyPresetOptions,
  toPolicyVersionPayload,
  type TestPolicyDraft,
  type TestPolicyPreset,
  validatePolicyDraft,
} from './testPolicy';

type TestPolicyPanelProps = {
  serviceId: string;
  policy?: API.PolicyVersion;
  onPolicyCreated: (policy: API.PolicyVersion) => void;
};

export function TestPolicyPanel({ serviceId, policy, onPolicyCreated }: TestPolicyPanelProps) {
  const [preset, setPreset] = useState<TestPolicyPreset>('balanced');
  const [customDraft, setCustomDraft] = useState<TestPolicyDraft>();
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const draft = useMemo(
    () => customDraft ?? createPolicyDraft(preset, policy),
    [customDraft, policy, preset],
  );

  const selectPreset = (next: TestPolicyPreset) => {
    if (next === 'custom') {
      setModalOpen(true);
      return;
    }
    setPreset(next);
    setCustomDraft(undefined);
  };

  const saveCustomDraft = (next: TestPolicyDraft) => {
    setPreset('custom');
    setCustomDraft(next);
    setModalOpen(false);
  };

  const createPolicy = async () => {
    const errors = validatePolicyDraft(draft);
    if (errors.length) {
      message.error(errors[0]);
      return;
    }
    setCreating(true);
    try {
      const created = await createPolicyVersion(serviceId, toPolicyVersionPayload(draft));
      onPolicyCreated(created);
      message.success('새 정책 버전을 현재 테스트에 적용했습니다.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Typography.Title level={5} style={{ margin: 0 }}>테스트 정책 설정</Typography.Title>
      <Typography.Text type="secondary">
        테스트에 사용할 기준을 선택한 뒤 새 정책 버전으로 만드세요. 기존 정책 버전은 변경되지 않습니다.
      </Typography.Text>
      <Space.Compact>
        {policyPresetOptions.map((option) => (
          <Button
            key={option.value}
            type={preset === option.value ? 'primary' : 'default'}
            onClick={() => selectPreset(option.value)}
          >
            {option.label}
          </Button>
        ))}
      </Space.Compact>
      <Space wrap>
        <Button type="primary" loading={creating} onClick={createPolicy}>
          새 정책 버전 만들기
        </Button>
        <VersionChip label="현재 테스트 정책" value={policy?.policy_version} />
      </Space>
      {preset === 'custom' ? (
        <Alert
          type="info"
          showIcon
          message="직접 설정이 선택되었습니다."
          description="설정값 확인 및 수정은 ‘직접 설정’을 다시 눌러 진행할 수 있습니다."
        />
      ) : null}
      <CustomTestPolicyModal
        open={modalOpen}
        initialValue={customDraft ?? createPolicyDraft('custom', policy)}
        onCancel={() => setModalOpen(false)}
        onConfirm={saveCustomDraft}
      />
    </Space>
  );
}
