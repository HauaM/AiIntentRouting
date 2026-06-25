"""Initial intent-routing database schema.

Revision ID: 0001_initial_intent_routing
Revises:
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_intent_routing"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()
TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "services",
        sa.Column("service_id", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("environment", sa.Text(), nullable=False),
        sa.Column(
            "default_threshold_preset",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'balanced'"),
        ),
        sa.Column(
            "max_input_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("256"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
    )

    op.create_table(
        "api_keys",
        sa.Column("key_id", sa.Text(), primary_key=True),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.Text(), nullable=False),
        sa.Column("environment", sa.Text(), nullable=False),
        sa.Column("app_id", sa.Text(), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column(
            "allowed_intents",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "allowed_route_keys",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("expires_at", TIMESTAMPTZ, nullable=False),
        sa.Column("revoked_at", TIMESTAMPTZ, nullable=True),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
    )

    op.create_table(
        "intents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("route_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "include_keywords",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "exclude_keywords",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
        sa.UniqueConstraint("service_id", "intent_id"),
        sa.UniqueConstraint("service_id", "route_key"),
    )

    op.create_table(
        "intent_examples",
        sa.Column("example_id", UUID, primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("example_type", sa.Text(), nullable=False),
        sa.Column("text_raw_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_encrypted_dek", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_encrypted_dek_iv", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_encrypted_dek_auth_tag", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_key_id", sa.Text(), nullable=False),
        sa.Column("text_raw_iv", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_auth_tag", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_algorithm", sa.Text(), nullable=False),
        sa.Column("text_masked", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("test_case_id", sa.Text(), nullable=True),
        sa.Column(
            "approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(
            ["service_id", "intent_id"],
            ["intents.service_id", "intents.intent_id"],
        ),
    )

    op.create_table(
        "policy_versions",
        sa.Column("policy_version", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("threshold_preset", sa.Text(), nullable=False),
        sa.Column("threshold_value", sa.Numeric(), nullable=False),
        sa.Column("clarify_margin", sa.Numeric(), nullable=False),
        sa.Column("min_candidate_score", sa.Numeric(), nullable=False),
        sa.Column("fallback_score", sa.Numeric(), nullable=False),
        sa.Column("risk_policy", JSONB, nullable=False),
        sa.Column("off_topic_policy", JSONB, nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
    )

    op.create_table(
        "intent_catalog_versions",
        sa.Column("intent_catalog_version", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
    )

    op.create_table(
        "vector_index_versions",
        sa.Column("vector_index_version", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("intent_catalog_version", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
    )

    op.create_table(
        "test_datasets",
        sa.Column("test_dataset_version", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
    )

    op.create_table(
        "test_cases",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("test_dataset_version", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("expected_intent", sa.Text(), nullable=True),
        sa.Column("case_type", sa.Text(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_dataset_version"],
            ["test_datasets.test_dataset_version"],
        ),
        sa.UniqueConstraint("test_dataset_version", "case_id"),
    )

    op.create_table(
        "test_runs",
        sa.Column("test_run_id", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("test_dataset_version", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("intent_catalog_version", sa.Text(), nullable=False),
        sa.Column("threshold_preset", sa.Text(), nullable=False),
        sa.Column("threshold_value", sa.Numeric(), nullable=False),
        sa.Column("pass_rate", sa.Numeric(), nullable=False),
        sa.Column("review_rate", sa.Numeric(), nullable=False),
        sa.Column("risk_pass_rate", sa.Numeric(), nullable=False),
        sa.Column("gate_passed", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
        sa.ForeignKeyConstraint(
            ["test_dataset_version"],
            ["test_datasets.test_dataset_version"],
        ),
        sa.ForeignKeyConstraint(["policy_version"], ["policy_versions.policy_version"]),
        sa.ForeignKeyConstraint(
            ["intent_catalog_version"],
            ["intent_catalog_versions.intent_catalog_version"],
        ),
    )

    op.create_table(
        "test_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("test_run_id", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("query_masked", sa.Text(), nullable=False),
        sa.Column("case_type", sa.Text(), nullable=False),
        sa.Column("expected_decision", sa.Text(), nullable=False),
        sa.Column("expected_intent", sa.Text(), nullable=True),
        sa.Column("actual_decision", sa.Text(), nullable=False),
        sa.Column("actual_intent", sa.Text(), nullable=True),
        sa.Column("actual_route_key", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["test_run_id"], ["test_runs.test_run_id"]),
    )

    op.create_table(
        "releases",
        sa.Column("release_version", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("environment", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("intent_catalog_version", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("vector_index_version", sa.Text(), nullable=False),
        sa.Column("test_dataset_version", sa.Text(), nullable=False),
        sa.Column("test_run_id", sa.Text(), nullable=False),
        sa.Column("pass_rate", sa.Numeric(), nullable=False),
        sa.Column("risk_pass_rate", sa.Numeric(), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("released_by", sa.Text(), nullable=False),
        sa.Column("released_at", TIMESTAMPTZ, nullable=False),
        sa.Column("rollback_target", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
        sa.ForeignKeyConstraint(["policy_version"], ["policy_versions.policy_version"]),
        sa.ForeignKeyConstraint(
            ["intent_catalog_version"],
            ["intent_catalog_versions.intent_catalog_version"],
        ),
        sa.ForeignKeyConstraint(
            ["test_dataset_version"],
            ["test_datasets.test_dataset_version"],
        ),
        sa.ForeignKeyConstraint(["test_run_id"], ["test_runs.test_run_id"]),
    )

    op.create_table(
        "runtime_logs",
        sa.Column("trace_id", sa.Text(), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("app_id", sa.Text(), nullable=True),
        sa.Column("service_id", sa.Text(), nullable=True),
        sa.Column("release_version", sa.Text(), nullable=True),
        sa.Column("policy_version", sa.Text(), nullable=True),
        sa.Column("intent_catalog_version", sa.Text(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("vector_index_version", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("intent_id", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("margin", sa.Numeric(), nullable=True),
        sa.Column("threshold_preset", sa.Text(), nullable=True),
        sa.Column("threshold_value", sa.Numeric(), nullable=True),
        sa.Column("route_key", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_category", sa.Text(), nullable=True),
        sa.Column("error_layer", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("query_raw_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("query_raw_encrypted_dek", sa.LargeBinary(), nullable=True),
        sa.Column("query_raw_encrypted_dek_iv", sa.LargeBinary(), nullable=True),
        sa.Column("query_raw_encrypted_dek_auth_tag", sa.LargeBinary(), nullable=True),
        sa.Column("query_raw_key_id", sa.Text(), nullable=True),
        sa.Column("query_raw_iv", sa.LargeBinary(), nullable=True),
        sa.Column("query_raw_auth_tag", sa.LargeBinary(), nullable=True),
        sa.Column("query_raw_algorithm", sa.Text(), nullable=True),
        sa.Column("query_masked", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", UUID, primary_key=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("view_reason", sa.Text(), nullable=True),
        sa.Column("source_ip", sa.Text(), nullable=True),
        sa.Column("before_state", JSONB, nullable=True),
        sa.Column("after_state", JSONB, nullable=True),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("runtime_logs")
    op.drop_table("releases")
    op.drop_table("test_results")
    op.drop_table("test_runs")
    op.drop_table("test_cases")
    op.drop_table("test_datasets")
    op.drop_table("vector_index_versions")
    op.drop_table("intent_catalog_versions")
    op.drop_table("policy_versions")
    op.drop_table("intent_examples")
    op.drop_table("intents")
    op.drop_table("api_keys")
    op.drop_table("services")
