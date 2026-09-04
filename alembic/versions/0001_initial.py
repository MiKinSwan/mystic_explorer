"""initial schema: pois + mining_runs

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-01

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "pois",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("super_category", sa.String(20), nullable=False),
        sa.Column("vibe_tags", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("history_and_lore", sa.Text, nullable=True),
        sa.Column("source_citations", postgresql.JSONB, nullable=False),
        sa.Column("review_highlights", postgresql.JSONB, nullable=False),
        sa.Column("google_rating", sa.Float, nullable=True),
        sa.Column("review_count", sa.Integer, nullable=True),
        sa.Column("specialties", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("is_hidden_gem", sa.Boolean, nullable=False),
        sa.Column("hidden_gem_score", sa.Float, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("google_place_id", sa.String(200), nullable=True),
        sa.Column("google_maps_url", sa.Text, nullable=False),
        sa.Column("is_publicly_accessible", sa.Boolean, nullable=False),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("google_place_id", name="uq_pois_google_place_id"),
    )
    op.create_index("ix_pois_state", "pois", ["state"])
    op.create_index(
        "ix_pois_state_super_category", "pois", ["state", "super_category"]
    )
    op.create_index(
        "ix_pois_location", "pois", ["location"], postgresql_using="gist"
    )

    op.create_table(
        "mining_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("venues_found", sa.Integer, nullable=False),
        sa.Column("venues_upserted", sa.Integer, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.UniqueConstraint("state", name="uq_mining_runs_state"),
    )


def downgrade() -> None:
    op.drop_table("mining_runs")
    op.drop_index("ix_pois_location", table_name="pois")
    op.drop_index("ix_pois_state_super_category", table_name="pois")
    op.drop_index("ix_pois_state", table_name="pois")
    op.drop_table("pois")
