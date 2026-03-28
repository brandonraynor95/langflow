"""Add A2A metadata fields to flow table

Revision ID: a2a0001fields
Revises: 0e6138e7a0c2
Create Date: 2026-03-27 12:00:01.000000

Adds fields for A2A agent exposure:
- a2a_enabled: opt-in toggle per flow
- a2a_name: public agent name (overrides flow.name)
- a2a_description: public agent description
- a2a_agent_slug: URL-safe identifier for the agent
- a2a_input_mode: input contract mode (default "chat")
- a2a_output_mode: output contract mode (default "text")
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2a0001fields"
down_revision: str | None = "0e6138e7a0c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)  # type: ignore[union-attr]
    column_names = [column["name"] for column in inspector.get_columns("flow")]

    with op.batch_alter_table("flow", schema=None) as batch_op:
        if "a2a_enabled" not in column_names:
            batch_op.add_column(sa.Column("a2a_enabled", sa.Boolean(), nullable=True))
        if "a2a_name" not in column_names:
            batch_op.add_column(sa.Column("a2a_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        if "a2a_description" not in column_names:
            batch_op.add_column(sa.Column("a2a_description", sa.Text(), nullable=True))
        if "a2a_agent_slug" not in column_names:
            batch_op.add_column(sa.Column("a2a_agent_slug", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        if "a2a_input_mode" not in column_names:
            batch_op.add_column(sa.Column("a2a_input_mode", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        if "a2a_output_mode" not in column_names:
            batch_op.add_column(sa.Column("a2a_output_mode", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # Add index on a2a_agent_slug for fast lookup
    if "a2a_agent_slug" not in column_names:
        with op.batch_alter_table("flow", schema=None) as batch_op:
            batch_op.create_index("ix_flow_a2a_agent_slug", ["a2a_agent_slug"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)  # type: ignore[union-attr]
    column_names = [column["name"] for column in inspector.get_columns("flow")]

    with op.batch_alter_table("flow", schema=None) as batch_op:
        indexes = [idx["name"] for idx in inspector.get_indexes("flow")]
        if "ix_flow_a2a_agent_slug" in indexes:
            batch_op.drop_index("ix_flow_a2a_agent_slug")

        if "a2a_output_mode" in column_names:
            batch_op.drop_column("a2a_output_mode")
        if "a2a_input_mode" in column_names:
            batch_op.drop_column("a2a_input_mode")
        if "a2a_agent_slug" in column_names:
            batch_op.drop_column("a2a_agent_slug")
        if "a2a_description" in column_names:
            batch_op.drop_column("a2a_description")
        if "a2a_name" in column_names:
            batch_op.drop_column("a2a_name")
        if "a2a_enabled" in column_names:
            batch_op.drop_column("a2a_enabled")
