import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';

export function TestRunDiagnosticsPanel() {
  return (
    <FutureFeatureNotice
      compact
      title="Test run diagnostics"
      phase="Future"
      backendRequirement="backend diagnostics plan docs/superpowers/plans/2026-07-20-test-run-diagnostics-ux.md is being implemented in another session and will be wired after it merges to main."
    />
  );
}
