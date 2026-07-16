import { describe, expect, it } from 'vitest';
import {
  formatReleaseRate,
  canRollbackRelease,
  getActivationConfirmation,
  getActiveRelease,
  getRollbackConfirmation,
  getSelectedReleaseCandidate,
} from './releasePresentation';

describe('release presentation', () => {
  it('allows rollback only from the active release with a configured target', () => {
    expect(canRollbackRelease({ active: true, rollback_target: 'rel-1' } as API.Release)).toBe(true);
    expect(canRollbackRelease({ active: false, rollback_target: 'rel-1' } as API.Release)).toBe(false);
    expect(canRollbackRelease({ active: true, rollback_target: null } as API.Release)).toBe(false);
  });

  it('formats fractions and percentages while preserving missing values', () => {
    expect(formatReleaseRate(null)).toBe('없음');
    expect(formatReleaseRate(undefined)).toBe('없음');
    expect(formatReleaseRate(Number.NaN)).toBe('없음');
    expect(formatReleaseRate(0.75)).toBe('75.0%');
    expect(formatReleaseRate(75)).toBe('75.0%');
  });

  it('finds the selected candidate', () => {
    const candidate = { test_run_id: 'tr-1' } as API.ReleaseCandidate;

    expect(getSelectedReleaseCandidate([candidate], 'tr-1')).toBe(candidate);
    expect(getSelectedReleaseCandidate([candidate], undefined)).toBeUndefined();
  });

  it('finds the current active release', () => {
    const activeRelease = {
      release_version: 'rel-1',
      active: true,
    } as API.Release;

    expect(
      getActiveRelease([
        { release_version: 'rel-0', active: false } as API.Release,
        activeRelease,
      ]),
    ).toBe(activeRelease);
  });

  it('describes activation from the current release to the selected release', () => {
    const copy = getActivationConfirmation(
      {
        service_id: 'svc-a',
        environment: 'prod',
        release_version: 'rel-2',
      } as API.Release,
      { release_version: 'rel-1' } as API.Release,
    );

    expect(copy).toEqual({
      title: 'rel-2을 활성화할까요?',
      serviceId: 'svc-a',
      environment: 'prod',
      currentRelease: 'rel-1',
      resultRelease: 'rel-2',
      impact: '완료 후 prod 런타임 요청은 rel-2 Release를 사용합니다.',
    });
  });

  it('describes rollback to the configured rollback target', () => {
    const copy = getRollbackConfirmation(
      {
        service_id: 'svc-a',
        environment: 'prod',
        release_version: 'rel-2',
        rollback_target: 'rel-1',
      } as API.Release,
      { release_version: 'rel-2' } as API.Release,
    );

    expect(copy).toEqual({
      title: 'rel-1으로 롤백할까요?',
      serviceId: 'svc-a',
      environment: 'prod',
      currentRelease: 'rel-2',
      resultRelease: 'rel-1',
      impact: '장애 대응을 위해 prod 런타임의 active Release를 rel-1으로 변경합니다.',
    });
  });
});
