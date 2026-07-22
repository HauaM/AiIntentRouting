export function testRunCreateErrorMessage(error: any): string {
  const payload = error?.response?.data ?? error?.data;
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.error?.message) return detail.error.message;
  if (payload?.error?.message) return payload.error.message;
  return error?.message ?? '테스트 실행 생성에 실패했습니다.';
}
