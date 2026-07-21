import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');

describe('Releases page UX contract', () => {
  it('shows operational evidence and uses the shared release status', () => {
    expect(source).toContain("import { StatusTag } from '@/components/StatusTag'");
    expect(source).toContain('release-candidate-evidence');
    expect(source).toContain('선택한 Release 근거');
    expect(source).toContain('현재 active Release');
    expect(source).toContain('변경 후 active Release');
  });

  it('uses scoped Korean list copy without a free-text environment filter', () => {
    expect(source).toContain('Release 목록');
    expect(source).toContain('등록된 Release가 없습니다.');
    expect(source).toContain('scroll={{ x: 1120 }}');
    expect(source).not.toContain('Filter environment');
    expect(source).not.toContain('No releases');
  });

  it('selects a release-owned dev, qa, or prod environment', () => {
    expect(source).toContain("value: 'dev'");
    expect(source).toContain("value: 'qa'");
    expect(source).toContain("value: 'prod'");
    expect(source).toContain('canManageReleases(session)');
    expect(source).not.toContain('selectedService?.environment');
    expect(source).not.toContain('Release environment는 서비스 environment와 반드시 같아야 합니다.');
  });

  it('ignores stale release-candidate responses for older service or environment requests', () => {
    expect(source).toContain('const candidateRequestIdRef = useRef(0);');
    expect(source).toContain('const latestCandidateServiceIdRef = useRef(session.serviceId);');
    expect(source).toContain("const latestCandidateEnvironmentRef = useRef<'dev' | 'qa' | 'prod'>('dev');");
    expect(source).toContain('const requestId = candidateRequestIdRef.current + 1;');
    expect(source).toContain('candidateRequestIdRef.current = requestId;');
    expect(source).toContain('const requestedServiceId = session.serviceId;');
    expect(source).toContain('const requestedEnvironment = selectedEnvironment;');
    expect(source).toContain('latestCandidateServiceIdRef.current = session.serviceId;');
    expect(source).toContain('latestCandidateEnvironmentRef.current = selectedEnvironment;');
    expect(source).toContain('candidateRequestIdRef.current !== requestId');
    expect(source).toContain('latestCandidateServiceIdRef.current !== requestedServiceId');
    expect(source).toContain('latestCandidateEnvironmentRef.current !== requestedEnvironment');
    expect(source).toContain('return;');
  });

  it('describes Phase 2 as frontend-not-wired', () => {
    expect(source).toContain('frontend route, role gate, and UX tests');
    expect(source).not.toContain('backend contracts are required');
  });
});
