"""Scope answer_cache uniqueness by provider and model.

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-30
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("answer_cache") as batch_op:
        batch_op.drop_constraint("uq_answer_cache_q", type_="unique")
        batch_op.create_unique_constraint(
            "uq_answer_cache_q_provider_model",
            ["repository_id", "question_hash", "provider_name", "model_name"],
        )


def downgrade() -> None:
    with op.batch_alter_table("answer_cache") as batch_op:
        batch_op.drop_constraint("uq_answer_cache_q_provider_model", type_="unique")
        batch_op.create_unique_constraint(
            "uq_answer_cache_q",
            ["repository_id", "question_hash"],
        )
