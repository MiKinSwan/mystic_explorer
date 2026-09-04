"""SQLAlchemy models for the mined POI dataset.

No LLM-invented content lives here without a citation: `review_highlights`
entries always carry a `source` + `retrieved_at`, and `history_and_lore` is
only ever populated alongside a `source_citations` URL. If the mining
pipeline can't find a real source, the field stays empty rather than being
filled by an LLM guess.
"""

from __future__ import annotations

import datetime
import uuid

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class POI(Base):
    """A single mined venue (Stay / Shop / Explore)."""

    __tablename__ = "pois"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    super_category: Mapped[str] = mapped_column(String(20), nullable=False)
    vibe_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )

    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )

    # Only ever set alongside a matching entry in source_citations.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_and_lore: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_citations: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # [{quote, rating, source: "google_places", retrieved_at}, ...] - real
    # Google Places reviews only, never LLM-generated.
    review_highlights: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    google_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    specialties: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )

    is_hidden_gem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hidden_gem_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    google_place_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True
    )
    google_maps_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_publicly_accessible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Places API content (incl. reviews) must be periodically re-fetched per
    # Google's ToS, not cached indefinitely - this drives that refresh cycle.
    last_verified: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_pois_location", "location", postgresql_using="gist"),
        Index("ix_pois_state_super_category", "state", "super_category"),
    )


class MiningRun(Base):
    """Per-state status row so a full 50-state mining run is resumable."""

    __tablename__ = "mining_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | running | success | failed
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    venues_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    venues_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("state", name="uq_mining_runs_state"),)
