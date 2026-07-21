import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const srcRoot = resolve(process.cwd(), 'src');

const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });

const sourceFiles = () =>
  walk(srcRoot)
    .filter((file) => /\.(tsx?|less)$/.test(file))
    .filter((file) => !/\.test\.tsx?$/.test(file))
    .filter((file) => !/\.d\.ts$/.test(file));

const sourceText = (file: string) => readFileSync(file, 'utf8');

const sourceLocation = (file: string, text: string, index: number) => {
  const line = text.slice(0, index).split('\n').length;
  return `${relative(srcRoot, file)}:${line}`;
};

const relativeLuminance = (hex: string) => {
  const normalized = hex.slice(0, 6);
  const channels = [0, 2, 4].map((start) => {
    const value = Number.parseInt(normalized.slice(start, start + 2), 16) / 255;
    return value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
};

const isAllowedNearBlackSurface = (file: string, line: string) =>
  relative(srcRoot, file) === 'components/AdminShell.tsx' &&
  /\b(siderBg|darkItemBg|darkSubMenuItemBg)\b/.test(line);

describe('Admin UI color guard', () => {
  it('keeps runtime pages on light Ant Design surfaces', () => {
    const offenders = sourceFiles().flatMap((file) => {
      const text = sourceText(file);
      return [...text.matchAll(/darkAlgorithm|color-scheme:\s*dark/g)].map((match) =>
        sourceLocation(file, text, match.index ?? 0),
      );
    });

    expect(offenders).toEqual([]);
  });

  it('uses StatusTag instead of Ant Design preset Tag colors', () => {
    const offenders = sourceFiles().flatMap((file) => {
      const text = sourceText(file);
      return [...text.matchAll(/<Tag\b[^>]*\bcolor\s*=/g)].map((match) =>
        sourceLocation(file, text, match.index ?? 0),
      );
    });

    expect(offenders).toEqual([]);
  });

  it('blocks near-black content backgrounds outside the explicit shell sidebar', () => {
    const backgroundPattern =
      /\b(?:background|background-color|backgroundColor|siderBg|darkItemBg|darkSubMenuItemBg)\b\s*:\s*['"]?#([0-9a-fA-F]{6,8})/g;
    const offenders = sourceFiles().flatMap((file) => {
      const text = sourceText(file);
      return [...text.matchAll(backgroundPattern)].flatMap((match) => {
        const index = match.index ?? 0;
        const lineEnd = text.indexOf('\n', index);
        const line = text.slice(
          text.lastIndexOf('\n', index) + 1,
          lineEnd === -1 ? undefined : lineEnd,
        );
        if (relativeLuminance(match[1]) >= 0.04) return [];
        if (isAllowedNearBlackSurface(file, line)) return [];
        return sourceLocation(file, text, index);
      });
    });

    expect(offenders).toEqual([]);
  });

  it('pins risky Ant Design overlay and status surfaces to light backgrounds', () => {
    const globalLess = sourceText(join(srcRoot, 'global.less'));

    expect(globalLess).toContain(
      '.ant-select-dropdown .ant-select-item-option-selected',
    );
    expect(globalLess).toContain('.admin-page-content .ant-alert-error');
    expect(globalLess).toContain('.admin-page-content .ant-steps .ant-steps-item-finish');
  });
});
