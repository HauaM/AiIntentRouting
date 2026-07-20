export type TestPolicyPreset = API.ThresholdPreset | 'custom';

export type TestPolicyDraft = {
  threshold_preset: TestPolicyPreset;
  threshold_value?: number;
  clarify_margin: number;
  min_candidate_score: number;
  fallback_score: number;
  risk_policy: API.PolicyToggle;
  off_topic_policy: API.OffTopicPolicySettings;
};

export const policyPresetOptions: Array<{ label: string; value: TestPolicyPreset }> = [
  { label: '엄격 기준', value: 'strict' },
  { label: '기본 기준', value: 'balanced' },
  { label: '탐색 기준', value: 'exploratory' },
  { label: '직접 설정', value: 'custom' },
];

const defaultPolicyValues = {
  clarify_margin: 0.08,
  min_candidate_score: 0.55,
  fallback_score: 0.45,
  risk_policy: { enabled: true },
  off_topic_policy: { enabled: true, keywords: [], message: '' },
};

export function createPolicyDraft(
  preset: TestPolicyPreset,
  source?: API.PolicyVersion,
): TestPolicyDraft {
  const values = source
    ? {
        clarify_margin: source.clarify_margin,
        min_candidate_score: source.min_candidate_score,
        fallback_score: source.fallback_score,
        risk_policy: source.risk_policy,
        off_topic_policy: source.off_topic_policy,
      }
    : defaultPolicyValues;

  return {
    threshold_preset: preset,
    threshold_value: preset === 'custom' ? source?.threshold_value ?? 0.8 : undefined,
    ...values,
  };
}

export function validatePolicyDraft(draft: TestPolicyDraft): string[] {
  const errors: string[] = [];
  const numericValues: Array<[string, number]> = [
    ['명확화 여유 점수', draft.clarify_margin],
    ['최소 후보 점수', draft.min_candidate_score],
    ['Fallback 점수', draft.fallback_score],
  ];

  if (draft.threshold_preset === 'custom') {
    if (draft.threshold_value === undefined || Number.isNaN(draft.threshold_value)) {
      errors.push('직접 설정에서는 일치 기준 점수를 입력해야 합니다.');
    } else {
      numericValues.push(['일치 기준 점수', draft.threshold_value]);
    }
  }

  numericValues.forEach(([label, value]) => {
    if (value < 0 || value > 1) errors.push(`${label}는 0에서 1 사이여야 합니다.`);
  });

  const threshold = draft.threshold_value;
  if (
    draft.threshold_preset === 'custom' &&
    threshold !== undefined &&
    draft.min_candidate_score > threshold
  ) {
    errors.push('최소 후보 점수는 일치 기준 점수보다 클 수 없습니다.');
  }
  if (draft.fallback_score > draft.min_candidate_score) {
    errors.push('Fallback 점수는 최소 후보 점수보다 클 수 없습니다.');
  }

  return errors;
}

export function toPolicyVersionPayload(
  draft: TestPolicyDraft,
): API.PolicyVersionCreateRequest {
  return {
    threshold_preset: draft.threshold_preset,
    ...(draft.threshold_preset === 'custom'
      ? { threshold_value: draft.threshold_value }
      : {}),
    clarify_margin: draft.clarify_margin,
    min_candidate_score: draft.min_candidate_score,
    fallback_score: draft.fallback_score,
    risk_policy: draft.risk_policy,
    off_topic_policy: draft.off_topic_policy,
  };
}
