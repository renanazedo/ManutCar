"""Add Clerk organization ID mapping.

Revision ID: a9e31c42d6f0
Revises: f3c54f4950d2
Create Date: 2026-11-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9e31c42d6f0"
down_revision: str | None = "f3c54f4950d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "clerk_organization_id",
            sa.String(length=255),
            nullable=True,
            comment="ID da organização no Clerk",
        ),
    )
    op.create_index(
        "ix_organizations_clerk_organization_id",
        "organizations",
        ["clerk_organization_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organizations_clerk_organization_id",
        table_name="organizations",
    )
    op.drop_column("organizations", "clerk_organization_id")
