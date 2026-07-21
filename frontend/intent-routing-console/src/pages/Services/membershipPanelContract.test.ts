import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const readSource = (relativePath: string) =>
  readFileSync(resolve(process.cwd(), 'src/pages/Services', relativePath), 'utf8');

const servicesIndexSource = () =>
  readFileSync(resolve(process.cwd(), 'src/pages/Services/index.tsx'), 'utf8');

describe('Services membership panel contract', () => {
  it('replaces the C-2 future notice with the real selected-Service panel', () => {
    const source = readSource('index.tsx');
    const selectedServiceIndex = source.indexOf('<Card title="선택한 Service">');
    const membershipPanelIndex = source.indexOf('<ServiceMembershipPanel');

    expect(source).toContain("import { ServiceMembershipPanel } from './ServiceMembershipPanel'");
    expect(source).toContain('canManageServiceMembers(session)');
    expect(source).toContain('onMembershipChanged={restoreSession}');
    expect(source).not.toContain('FutureFeatureNotice');
    expect(selectedServiceIndex).toBeGreaterThan(-1);
    expect(membershipPanelIndex).toBeGreaterThan(selectedServiceIndex);
  });

  it('loads and clears membership state when the selected Service changes', () => {
    const source = readSource('ServiceMembershipPanel.tsx');
    const effectIndex = source.indexOf('useEffect(() => {');
    const clearIndex = source.indexOf('clearMembershipState();', effectIndex);
    const loadIndex = source.indexOf('loadMembers(selectedServiceId);', effectIndex);

    expect(source).toContain('shouldClearMembershipState(previousServiceId, selectedServiceId)');
    expect(source).toContain('serviceIdRef.current = selectedServiceId');
    expect(source).toContain(
      '}, [clearMembershipState, loadMembers, selectedServiceId]);',
    );
    expect(clearIndex).toBeGreaterThan(effectIndex);
    expect(loadIndex).toBeGreaterThan(clearIndex);
  });

  it('reloads members and refreshes session scope after grant and revoke', () => {
    const source = readSource('ServiceMembershipPanel.tsx');
    const grantIndex = source.indexOf('await grantServiceRole(');
    const grantCurrentCheckIndex = source.indexOf('if (!isCurrentRequest()) return;', grantIndex);
    const grantSuccessIndex = source.indexOf(
      "message.success('Service 역할을 부여했습니다.');",
      grantCurrentCheckIndex,
    );
    const grantClearIndex = source.indexOf('setSelectedUserId(undefined);', grantSuccessIndex);
    const grantReloadIndex = source.indexOf('await loadMembers(expectedServiceId);', grantIndex);
    const grantRefreshIndex = source.indexOf('await onMembershipChanged();', grantReloadIndex);
    const revokeIndex = source.indexOf('await revokeServiceRole(');
    const revokeReloadIndex = source.indexOf('await loadMembers(expectedServiceId);', revokeIndex);
    const revokeRefreshIndex = source.indexOf('await onMembershipChanged();', revokeReloadIndex);

    expect(source).toContain('searchServiceUsers(expectedServiceId, { query, limit: 25 })');
    expect(source).not.toContain('searchAdminUsers');
    expect(source).toContain('listServiceMembers(expectedServiceId)');
    expect(grantSuccessIndex).toBeGreaterThan(grantCurrentCheckIndex);
    expect(grantClearIndex).toBeGreaterThan(grantSuccessIndex);
    expect(grantReloadIndex).toBeGreaterThan(grantSuccessIndex);
    expect(grantReloadIndex).toBeGreaterThan(grantIndex);
    expect(grantRefreshIndex).toBeGreaterThan(grantReloadIndex);
    expect(revokeReloadIndex).toBeGreaterThan(revokeIndex);
    expect(revokeRefreshIndex).toBeGreaterThan(revokeReloadIndex);
  });

  it('requires confirmation before granting a selected-Service role', () => {
    const source = readSource('ServiceMembershipPanel.tsx');
    const grantArea = source.match(/<Space wrap align="end"[\s\S]*?<\/Space>/)?.[0];

    expect(grantArea).toContain('<ConfirmActionButton');
    expect(grantArea).toContain('title="Service 역할을 부여할까요?"');
    expect(grantArea).toContain('onConfirm={handleGrant}');
    expect(grantArea).not.toContain('onClick={handleGrant}');
  });

  it('bounds membership table overflow without fake pagination', () => {
    const source = readSource('ServiceMembershipPanel.tsx');

    expect(source).toContain('scroll={{');
    expect(source).toContain('tableLayout="fixed"');
    expect(source).toContain('pagination={false}');
  });

  it('bounds the accessible services table without server pagination', () => {
    const source = servicesIndexSource();

    expect(source).toContain('scroll={{');
    expect(source).toContain('pagination={false}');
    expect(source).toContain('tableLayout="fixed"');
  });

  it('localizes the selected-Service membership controls', () => {
    const source = readSource('ServiceMembershipPanel.tsx');

    expect(source).toContain('<Card title="Service 멤버십">');
    expect(source).toContain('<Typography.Text>사용자</Typography.Text>');
    expect(source).toContain('<Typography.Text>역할</Typography.Text>');
    expect(source).toContain('placeholder="관리자 계정 검색"');
    expect(source).toContain('멤버가 없습니다.');
  });

  it('does not reserve a fixed vertical viewport for an empty member list', () => {
    const source = readSource('ServiceMembershipPanel.tsx');

    expect(source).toContain('scroll={{ x: 760 }}');
    expect(source).not.toContain('scroll={{ x: 760, y: 320 }}');
  });
});
