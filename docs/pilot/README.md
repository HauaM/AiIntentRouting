# Pilot Fixtures

`it-helpdesk-pilot-catalog.json` is the deterministic local and Dify pilot catalog.
`it-helpdesk-pilot-cases.csv` is the default alias for the 50-row standard dataset.
The built-in pilot gate tiers are:

- `it-helpdesk-pilot-cases-30.csv`: minimum pilot gate.
- `it-helpdesk-pilot-cases-50.csv`: standard default.
- `it-helpdesk-pilot-cases-100.csv`: higher-confidence regression coverage.

기존 pilot CSV는 baseline과 rehearsal에 연결된 legacy fixture라서 5컬럼을
사용합니다. backend/API는 migration 기간 동안 이 legacy CSV도 계속 읽습니다.
새 사용자용 normal CSV의 header는 다음 4컬럼으로 고정합니다.

```csv
case_id,query,expected_intent,memo
```

Admin Console의 Test Run import/export는 4컬럼만 사용합니다. 일반 Test Run CSV는
"이 문장은 어느 Intent로 가야 하는가"만 적는다. 그래서 `expected_intent`는 항상
필요하다. 사용자는 `case_type`, `expected_decision`, `expected_route_key`,
`expected_risk_type`를 입력하지 않는다. 시스템은 내부적으로
`case_type=positive`, `expected_decision=confident`로 저장하고, 선택한 Catalog에서
expected route_key를 찾아 실제 route_key까지 비교한다.

Risk는 Intent Catalog에 등록하지 않는다. 새 Test Run에는 공통 risk pack이 자동
포함되며, 서비스별로 더 필요한 위험 문장은 별도 risk CSV로 추가한다.

기존 `docs/pilot/it-helpdesk-pilot-cases*.csv`는 baseline hash와 rehearsal
스크립트에 연결된 legacy fixture이므로 이번 변경에서 즉시 변환하지 않는다.
새 4컬럼 예시는
`docs/pilot/it-helpdesk-pilot-classification-cases-v2.csv`를 참고한다. legacy
pilot fixture를 변환하려면 baseline 재생성과 rehearsal 검증을 같은 변경에
포함해야 한다.

Common risk pack은 모든 `RiskType`을 한 번씩 포함하며, release-quality Test Run은
`risk_policy.enabled=True`일 때만 risk 행을 평가한다. risk case가 하나 이상이고
risk pass rate가 100%여야 release eligibility를 통과한다. `review_rate > 0.15`는
이번 변경에서도 advisory다.

Legacy pilot CSV에서 사용하는 `positive`, `confusing`, `clarify`, `risk`,
`off_topic`, `fallback` case type은 backend/API migration 호환성을 위해 유지된다.

## 미등록 업무 Fallback 보호

`case_type=fallback`은 등록된 Intent에 없는 질문입니다. 파일럿에서는
회의실 예약, 프린터 토너, 출장 정산, 명함 제작처럼 현재 카탈로그에 없는
사내 업무를 기존 Intent로 억지 분류하지 않습니다.

개발자는 CSV와 예시를 기준으로 다음 조치 중 하나를 선택합니다.

- 처리해야 하는 새 업무라면 새 Intent와 positive example을 추가합니다.
- 기존 Intent로 가면 안 되는 헷갈리는 질문이면 negative example을 추가합니다.
- 현재 파일럿 범위 밖이면 `case_type=fallback`으로 유지합니다.

## Closed-Network Pilot Runtime

The local pilot uses `EMBEDDING_PROVIDER=fake` for repeatability. Closed-network pilot runs may switch to `EMBEDDING_PROVIDER=bge-m3` after mounting the local BGE-M3 model path and setting `BGE_M3_MODEL_PATH`.
Use `docs/ops/bge-m3-closed-network.md` to validate the local model path, checksum evidence, CPU-only expectation, and 256-token pilot benchmark before enabling Dify traffic.

Password examples in the catalog are seed examples for embedding separation only. Runtime positive CSV or smoke cases should use non-secret/account-lock wording such as `계정 잠금` to avoid risk-policy matches.

`off_topic_other_subject`와 같은 서비스별 업무 범위 밖 Intent가 선택한 Catalog에
등록되어 있으면 일반 expected Intent로 테스트한다. risk가 모든 routing보다 먼저
처리되지만, service `off_topic_policy`가 등록된 Catalog의 확실한 match를 막아서는
안 된다.

## CSV Baseline Regression Gate

`it-helpdesk-pilot-baseline.json` freezes the standard 50-row pilot CSV expectations for the `balanced` preset. It stores case IDs, expected results, decisions, intents, route keys, the CSV SHA-256, and the required pass-rate thresholds. It intentionally does not store raw `query` text or secret-bearing fields. `scripts/compare_csv_baseline.py compare --csv docs/pilot/it-helpdesk-pilot-cases.csv` verifies the current dataset SHA-256 before accepting a rehearsal comparison.

[`docs/pilot/csv-baseline-refresh-policy.md`](csv-baseline-refresh-policy.md) is the source of truth for the CSV Baseline Regression Gate, including refresh approval, required review evidence, freeze/compare commands, and rollback expectations.

[`docs/pilot/csv-baseline-freeze-approval-template.md`](csv-baseline-freeze-approval-template.md)
is the launch approval evidence template for keeping the checked-in baseline
frozen when no policy-approved refresh is accepted.
