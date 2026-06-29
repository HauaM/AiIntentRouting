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

The local pilot uses `EMBEDDING_PROVIDER=fake` for repeatability. Closed-network pilot runs may switch to `EMBEDDING_PROVIDER=bge-m3` after mounting the local BGE-M3 model path and setting `BGE_M3_MODEL_PATH`.
Use `docs/ops/bge-m3-closed-network.md` to validate the local model path, checksum evidence, CPU-only expectation, and 256-token pilot benchmark before enabling Dify traffic.

Password examples in the catalog are seed examples for embedding separation only. Runtime positive CSV or smoke cases should use non-secret/account-lock wording such as `계정 잠금` to avoid risk-policy matches.

## CSV Baseline Regression Gate

`it-helpdesk-pilot-baseline.json` freezes the standard 50-row pilot CSV expectations for the `balanced` preset. It stores case IDs, expected results, decisions, intents, route keys, the CSV SHA-256, and the required pass-rate thresholds. It intentionally does not store raw `query` text or secret-bearing fields. `scripts/compare_csv_baseline.py compare --csv docs/pilot/it-helpdesk-pilot-cases.csv` verifies the current dataset SHA-256 before accepting a rehearsal comparison.

Refresh the baseline only when a reviewer intentionally accepts changed pilot behavior, such as a curated CSV update, catalog route change, or threshold policy change. Do not refresh it merely to make a failing rehearsal pass.

Pull requests that modify the baseline should review the CSV/catalog diff and the baseline diff together. Treat new `FAIL`/disallowed `REVIEW` cases, pass-rate regressions, risk pass-rate regressions, and decision/intent/route-key drift as release-blocking until the behavior change is explained and accepted.
