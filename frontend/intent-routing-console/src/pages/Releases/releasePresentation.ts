export type ReleaseConfirmationPresentation = {
  title: string;
  serviceId: string;
  environment: string;
  currentRelease: string;
  resultRelease: string;
  impact: string;
};

export const formatReleaseRate = (value: number | null | undefined) => {
  if (value === null || value === undefined || !Number.isFinite(value)) return '없음';
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(1)}%`;
};

export const getSelectedReleaseCandidate = (
  candidates: API.ReleaseCandidate[],
  testRunId?: string,
) => candidates.find((candidate) => candidate.test_run_id === testRunId);

export const getActiveRelease = (releases: API.Release[]) =>
  releases.find((release) => release.active);

export const canRollbackRelease = (release: API.Release) =>
  release.active && Boolean(release.rollback_target);

export const getActivationConfirmation = (
  release: API.Release,
  currentActive?: API.Release,
): ReleaseConfirmationPresentation => ({
  title: `${release.release_version}을 활성화할까요?`,
  serviceId: release.service_id,
  environment: release.environment,
  currentRelease: currentActive?.release_version ?? '없음',
  resultRelease: release.release_version,
  impact: `완료 후 ${release.environment} 런타임 요청은 ${release.release_version} Release를 사용합니다.`,
});

export const getRollbackConfirmation = (
  release: API.Release,
  currentActive?: API.Release,
): ReleaseConfirmationPresentation => {
  const rollbackTarget = release.rollback_target ?? '없음';
  return {
    title: `${rollbackTarget}으로 롤백할까요?`,
    serviceId: release.service_id,
    environment: release.environment,
    currentRelease: currentActive?.release_version ?? '없음',
    resultRelease: rollbackTarget,
    impact: `장애 대응을 위해 ${release.environment} 런타임의 active Release를 ${rollbackTarget}으로 변경합니다.`,
  };
};
