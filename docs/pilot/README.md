# Pilot Fixtures

`it-helpdesk-pilot-catalog.json` is the deterministic local and Dify pilot catalog.
`it-helpdesk-pilot-cases.csv` follows the Sprint 0 CSV runner header:

```csv
case_id,query,expected_intent,case_type,memo
```

The local pilot uses `EMBEDDING_PROVIDER=fake` for repeatability. Closed-network pilot runs may switch to `EMBEDDING_PROVIDER=bge-m3` after mounting the local BGE-M3 model path and setting `BGE_M3_MODEL_PATH`.

Password examples in the catalog are seed examples for embedding separation only. Runtime positive CSV or smoke cases should use non-secret/account-lock wording such as `계정 잠금` to avoid risk-policy matches.
