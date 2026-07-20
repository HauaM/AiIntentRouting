import {
  createPolicyDraft,
  policyPresetOptions,
  toPolicyVersionPayload,
  validatePolicyDraft,
} from './testPolicy';

it('uses the agreed Korean labels for the four test policy choices', () => {
  expect(policyPresetOptions).toEqual([
    { label: '엄격 기준', value: 'strict' },
    { label: '기본 기준', value: 'balanced' },
    { label: '탐색 기준', value: 'exploratory' },
    { label: '직접 설정', value: 'custom' },
  ]);
});

it('creates a preset policy payload without a user supplied threshold', () => {
  const payload = toPolicyVersionPayload(createPolicyDraft('strict'));

  expect(payload).toMatchObject({
    threshold_preset: 'strict',
    clarify_margin: 0.08,
    min_candidate_score: 0.55,
    fallback_score: 0.45,
  });
  expect(payload.threshold_value).toBeUndefined();
});

it('creates a custom payload with the configured threshold', () => {
  const draft = createPolicyDraft('custom');
  draft.threshold_value = 0.72;

  expect(validatePolicyDraft(draft)).toEqual([]);
  expect(toPolicyVersionPayload(draft).threshold_value).toBe(0.72);
});

it('rejects a custom threshold below the minimum candidate score', () => {
  const draft = createPolicyDraft('custom');
  draft.threshold_value = 0.5;

  expect(validatePolicyDraft(draft)).toContain(
    '최소 후보 점수는 일치 기준 점수보다 클 수 없습니다.',
  );
});
