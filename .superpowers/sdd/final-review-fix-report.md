# Test Run Actionable Diagnostics Final Review Fix Report

## 수정 범위

- 결과 행 로드 상태를 `not_loaded`, `loading`, `error`, `loaded`로 분리했다.
  - 결과 조회 중이거나 실패했을 때 인사이트 패널이 `실패 케이스가 없습니다.`를 표시하지 않는다.
  - 상세 결과 테이블도 각 상태에 맞는 한국어 안내를 표시한다.
- Catalog / Vector 패널이 진단 로딩 및 오류 상태를 함께 받아, 조회 중 또는 오류 시 빈 Catalog 상태로 오인하지 않는다.
- 모든 알려진 진단 이슈 코드에 한국어 다음 조치를 매핑하고, `primary_issue`의 조치를 패턴 기반 조치보다 먼저 표시한다.
  - `catalog_version_has_no_ready_vector_index` 차단 이슈를 단위 테스트로 검증했다.
- 실패 패턴은 종류를 먼저 분류하고, `decision_mismatch`는 기대 결정에서 실제 결정으로 집계한다.
  - 패턴 키에 종류를 포함해 같은 값 쌍의 서로 다른 패턴이 합쳐지지 않는다.
  - 진단 패널의 결정 값은 한국어 라벨로 표시하고 원본 값은 툴팁으로만 보존한다.
- 결과 화면의 순서를 테스트 요약, 가장 먼저 확인할 문제, 실패 패턴 요약, 다음 조치, 상세 결과, Catalog / Vector 상태로 고정했다.
  - 실제 결정 분포와 진단 이슈 태그를 실패 패턴 요약 안으로 넣었다.
- 알 수 없는 결정, 차단 사유, 권장 조치의 표시 문구를 한국어 일반 안내로 변경했다.

## 검증

- `npm run test:unit -- testRunResultCopy.test.ts` (8 passed)
- `npm run test:unit -- testRunResultInsights.test.ts` (7 passed)
- `npm run test:unit -- testRunDiagnosticsPanelContract.test.ts` (9 passed)
- `npm run test:unit -- testRunCatalogStatusPanelContract.test.ts` (3 passed)
- `npm run test:unit -- testRunsPageContract.test.ts` (21 passed)
- `npm run typecheck` (passed)
- `npm run test:unit -- TestRuns` (12 files, 78 passed)
- `git diff --check` (passed)

## 남은 확인 사항

- 백엔드가 새 진단 이슈 코드를 추가하면 일반 한국어 안내가 표시된다. 새 코드에 맞는 구체 조치는 프런트엔드 매핑과 테스트에 추가해야 한다.
