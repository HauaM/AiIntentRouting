import { describe, expect, it } from 'vitest';

import { formatLatencyMs } from './metricDisplay';

describe('formatLatencyMs', () => {
  it('shows a dash when latency is missing', () => {
    expect(formatLatencyMs(null)).toBe('-');
    expect(formatLatencyMs(undefined)).toBe('-');
  });

  it('shows measured latency with an ms suffix', () => {
    expect(formatLatencyMs(0)).toBe('0 ms');
    expect(formatLatencyMs(27)).toBe('27 ms');
  });
});
