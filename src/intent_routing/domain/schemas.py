from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from intent_routing.domain.enums import Decision, ErrorCode, RiskType


class RuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    channel: str | None = None
    user_context: dict[str, Any] = Field(default_factory=dict)


class ClarifyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    display_name: str
    route_key: str
    confidence: float


class ClarifyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str
    message: str
    candidates: list[ClarifyCandidate] = Field(default_factory=list)


class RiskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_type: RiskType
    action: str
    message: str


class FallbackPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    retryable: bool | None = None
    recommended_action: str | None = None
    message: str | None = None


class RuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    decision: Decision
    request_id: str | None = None
    domain: str | None = None
    intent_id: str | None = None
    confidence: float | None = None
    route_key: str | None = None
    clarify_question: str | None = None
    fallback_policy: FallbackPolicy | None = None
    clarify: ClarifyPayload | None = None
    risk: RiskPayload | None = None
    release_version: str | None = None


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    retryable: bool
    category: str | None = None
    layer: str | None = None
    support_message: str | None = None
    safe_detail: str | None = None
    fallback_policy: FallbackPolicy | None = None


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["error"] = "error"
    trace_id: str
    error: ErrorInfo
    request_id: str | None = None
    release_version: str | None = None
