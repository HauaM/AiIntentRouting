import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const pageSource = () =>
  readFileSync(resolve(process.cwd(), 'src/pages/Services/index.tsx'), 'utf8');

describe('Services page presentation contract', () => {
  it('orders selected Service workflow before creation and accessible Services', () => {
    const source = pageSource();
    const selected = source.indexOf('<Card title="선택한 Service"');
    const membership = source.indexOf('<ServiceMembershipPanel');
    const creation = source.indexOf('<Card title="Service 등록"');
    const accessible = source.indexOf('<Card title="접근 가능한 Services"');

    expect(selected).toBeGreaterThan(-1);
    expect(membership).toBeGreaterThan(selected);
    expect(creation).toBeGreaterThan(membership);
    expect(accessible).toBeGreaterThan(creation);
  });

  it('shows an honest C-1 C-2 C-3 onboarding summary', () => {
    const source = pageSource();

    expect(source).toContain('services-onboarding-progress');
    expect(source).toContain('C-1 · 등록 완료');
    expect(source).toContain('C-2 · 권한 구성');
    expect(source).toContain('C-3 · 연동 준비');
    expect(source).not.toContain('C-2 · 완료');
    expect(source).not.toContain('C-3 · 완료');
  });

  it('keeps the selected Service ID copyable, bounded, and discoverable', () => {
    const source = pageSource();

    expect(source).toContain('title={selectedService.service_id}');
    expect(source).toContain('className="services-selected-id"');
    expect(source).toContain('copyable');
    expect(source).toContain('ellipsis');
    expect(source).toContain('column={{ xs: 1, lg: 2 }}');
  });

  it('uses a responsive form grid and localized table copy', () => {
    const source = pageSource();

    expect(source).toContain('className="services-create-grid"');
    expect(source).not.toContain("title: '환경'");
    expect(source).not.toContain('default_threshold_preset');
    expect(source).toContain("title: '상태'");
    expect(source).toContain("title: '역할'");
    expect(source).toContain('description="접근 가능한 Service가 없습니다."');
  });

  it('does not reserve a fixed vertical viewport for a short accessible list', () => {
    const source = pageSource();

    expect(source).toContain('scroll={{ x: 760 }}');
    expect(source).not.toContain('scroll={{ x: 760, y: 420 }}');
  });

  it('uses a non-blocking success notification with an Intent Catalog action', () => {
    const source = pageSource();

    expect(source).toContain('notification.useNotification()');
    expect(source).toContain('notificationApi.success({');
    expect(source).toContain("message: 'Service 등록 완료'");
    expect(source).toContain('duration: 6');
    expect(source).toContain("history.push('/intents')");
    expect(source).toContain('Intent Catalog로 이동');
    expect(source).not.toContain('type="success"');
    expect(source).not.toContain('message="Service 온보딩을 시작했습니다"');
    expect(source).not.toContain("message.success('Service가 등록되었습니다.')");
  });

  it('opens the success notification from an effect after the holder remounts', () => {
    const source = pageSource();
    const notificationEffect = source.indexOf('notificationApi.success({');
    const createHandler = source.indexOf('const handleCreate = async');
    const createHandlerSource = source.slice(createHandler, source.indexOf('\n  return (', createHandler));

    expect(source).toContain("import { useEffect, useMemo, useState } from 'react';");
    expect(source).toContain('const [createdServiceNotification, setCreatedServiceNotification]');
    expect(source).toContain('if (!createdServiceNotification) return;');
    expect(notificationEffect).toBeGreaterThan(-1);
    expect(notificationEffect).toBeLessThan(createHandler);
    expect(createHandlerSource).toContain('setCreatedServiceNotification(created);');
    expect(createHandlerSource).not.toContain('notificationApi.success({');
  });

  it('mounts the notification holder through the persistent AdminShell slot', () => {
    const source = pageSource();

    expect(source).toContain(
      '<AdminShell title="Services" notificationHolder={notificationContextHolder}>',
    );
    expect(source).not.toContain('\n      {notificationContextHolder}\n');
  });
});
