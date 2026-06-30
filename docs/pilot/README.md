# Pilot Fixtures

`it-helpdesk-pilot-catalog.json` is the deterministic local and Dify pilot catalog.
`it-helpdesk-pilot-cases.csv` is the default alias for the 50-row standard dataset.
The built-in pilot gate tiers are:

- `it-helpdesk-pilot-cases-30.csv`: minimum pilot gate.
- `it-helpdesk-pilot-cases-50.csv`: standard default.
- `it-helpdesk-pilot-cases-100.csv`: higher-confidence regression coverage.

Every pilot CSV follows the Sprint 0 CSV runner header:

```csv
case_id,query,expected_intent,case_type,memo
```

Supported case types are `positive`, `confusing`, `clarify`, `risk`, `off_topic`, and `fallback`.
Custom CSVs must keep the same header and pass the same parser, PII, risk coverage, and balanced gate checks before they are accepted as pilot evidence.

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

## CSV Baseline Regression Gate

`it-helpdesk-pilot-baseline.json` freezes the standard 50-row pilot CSV expectations for the `balanced` preset. It stores case IDs, expected results, decisions, intents, route keys, the CSV SHA-256, and the required pass-rate thresholds. It intentionally does not store raw `query` text or secret-bearing fields. `scripts/compare_csv_baseline.py compare --csv docs/pilot/it-helpdesk-pilot-cases.csv` verifies the current dataset SHA-256 before accepting a rehearsal comparison.

[`docs/pilot/csv-baseline-refresh-policy.md`](csv-baseline-refresh-policy.md) is the source of truth for the CSV Baseline Regression Gate, including refresh approval, required review evidence, freeze/compare commands, and rollback expectations.

[`docs/pilot/csv-baseline-freeze-approval-template.md`](csv-baseline-freeze-approval-template.md)
is the launch approval evidence template for keeping the checked-in baseline
frozen when no policy-approved refresh is accepted.
