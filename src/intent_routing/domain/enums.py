from enum import StrEnum


class Decision(StrEnum):
    confident = "confident"
    clarify = "clarify"
    fallback = "fallback"
    off_topic = "off_topic"
    risk = "risk"
    unauthorized = "unauthorized"


class RiskType(StrEnum):
    abuse = "abuse"
    dangerous_command = "dangerous_command"
    sensitive_data = "sensitive_data"
    credential_secret = "credential_secret"
    unauthorized_access = "unauthorized_access"
    prompt_injection = "prompt_injection"
    fraud_or_illegal = "fraud_or_illegal"


class ThresholdPreset(StrEnum):
    strict = "strict"
    balanced = "balanced"
    exploratory = "exploratory"

    @property
    def threshold(self) -> float:
        return {
            ThresholdPreset.strict: 1.0,
            ThresholdPreset.balanced: 0.8,
            ThresholdPreset.exploratory: 0.6,
        }[self]


class ExampleType(StrEnum):
    positive = "positive"
    negative = "negative"


class IntentStatus(StrEnum):
    draft = "draft"
    active = "active"
    deprecated = "deprecated"


class ApiKeyStatus(StrEnum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    SERVICE_SCOPE_DENIED = "SERVICE_SCOPE_DENIED"
    ACTIVE_RELEASE_NOT_FOUND = "ACTIVE_RELEASE_NOT_FOUND"
    ROUTING_TIMEOUT = "ROUTING_TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EMBEDDING_MODEL_UNAVAILABLE = "EMBEDDING_MODEL_UNAVAILABLE"
    VECTOR_STORE_UNAVAILABLE = "VECTOR_STORE_UNAVAILABLE"
    POLICY_LOAD_FAILED = "POLICY_LOAD_FAILED"
    RAW_QUERY_UNAVAILABLE = "RAW_QUERY_UNAVAILABLE"
