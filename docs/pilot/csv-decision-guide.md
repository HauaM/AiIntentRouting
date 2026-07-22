# CSV Decision Guide

## 일반 Test Run CSV

일반 Test Run CSV는 "이 문장은 어느 Intent로 가야 하는가"만 적는다.
그래서 `expected_intent`는 항상 필요하다. 시스템은 내부적으로
`case_type=positive`, `expected_decision=confident`로 저장하고,
선택한 Catalog에서 expected route_key를 찾아 실제 route_key까지 비교한다.

정상 CSV의 header는 정확히 다음과 같다.

```csv
case_id,query,expected_intent,memo
```

Admin Console import/export는 네 컬럼만 사용한다. 사용자는 `case_type`,
`expected_decision`, `expected_route_key`, `expected_risk_type`를 적지 않는다.
query만 넣는 테스트는 이 프로젝트의 normal CSV 범위가 아니다.

## Risk 추가

Risk는 Intent Catalog에 등록하지 않는다. 새 Test Run에는 공통 risk pack이
자동 포함되며, 서비스별로 더 필요한 위험 문장은 별도 risk CSV로 추가한다.
release-quality Test Run에 common 또는 custom risk row가 있으면
`risk_policy.enabled=True`가 필요하다. risk case가 하나 이상이고 risk pass rate가
100%여야 release eligibility를 통과한다.

`off_topic_other_subject`와 같은 서비스별 out-of-business Intent는 선택한 Catalog에
등록되어 있을 때 normal expected Intent로 적는다. Risk는 모든 routing보다 먼저
처리되며, service `off_topic_policy`는 등록된 Catalog match를 막지 않는다.

## Legacy migration

backend/API는 migration 기간 동안 기존 5컬럼 CSV도 계속 parse한다. 기존
`docs/pilot/it-helpdesk-pilot-cases*.csv`와
`docs/pilot/it-helpdesk-pilot-baseline.json`은 baseline hash와 rehearsal 검증에
연결되어 있으므로 이번 변경에서 다시 쓰지 않는다. 새 4컬럼 예시는
`docs/pilot/it-helpdesk-pilot-classification-cases-v2.csv`를 사용한다.

legacy fixture를 변환하려면 baseline 재생성과 rehearsal 검증을 같은 변경에
포함해야 한다. `review_rate > 0.15`는 advisory이며, clarify/review volume을
blocking gate로 만들지는 않는다.
