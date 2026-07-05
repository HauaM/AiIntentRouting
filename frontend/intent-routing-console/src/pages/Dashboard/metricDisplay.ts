export function formatLatencyMs(value: number | null | undefined) {
  return value == null ? '-' : `${value} ms`;
}
