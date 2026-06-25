from __future__ import annotations

from dataclasses import dataclass

from intent_routing.domain.enums import RiskType


@dataclass(frozen=True, slots=True)
class RiskEvaluation:
    matched: bool
    risk_type: RiskType | None = None
    action: str | None = None
    message: str | None = None


class RiskPolicy:
    _PATTERNS: dict[RiskType, tuple[str, ...]] = {
        RiskType.abuse: (
            "멍청",
            "바보",
            "욕설",
            "비방",
            "협박",
            "죽여",
        ),
        RiskType.dangerous_command: (
            "rm -rf",
            "drop table",
            "delete from",
            "truncate",
            "shutdown",
            "format",
            "파일 삭제",
        ),
        RiskType.sensitive_data: (
            "주민번호",
            "계좌번호",
            "카드번호",
            "개인정보",
            "내부기밀",
            "고객정보",
        ),
        RiskType.credential_secret: (
            "비밀번호",
            "password",
            "api key",
            "api_key",
            "token",
            "secret",
            "인증서",
            "private key",
        ),
        RiskType.unauthorized_access: (
            "해킹",
            "권한 없이",
            "관리자 권한 탈취",
            "다른 고객",
            "우회 접속",
        ),
        RiskType.prompt_injection: (
            "이전 지시 무시",
            "system prompt",
            "developer message",
            "정책 우회",
            "프롬프트 탈취",
        ),
        RiskType.fraud_or_illegal: (
            "피싱",
            "사기",
            "불법",
            "규정 회피",
            "인증번호 탈취",
        ),
    }

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    @classmethod
    def default(cls) -> RiskPolicy:
        return cls(enabled=True)

    def evaluate(self, query: str) -> RiskEvaluation:
        if not self.enabled:
            return RiskEvaluation(matched=False)

        normalized_query = query.casefold()
        for risk_type in RiskType:
            for pattern in self._PATTERNS[risk_type]:
                if pattern.casefold() in normalized_query:
                    return RiskEvaluation(
                        matched=True,
                        risk_type=risk_type,
                        action="block",
                        message=f"Blocked by risk policy: {risk_type.value}",
                    )
        return RiskEvaluation(matched=False)
