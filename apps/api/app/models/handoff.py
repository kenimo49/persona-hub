"""Persisted state for handoff token single-use enforcement."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HandoffJti(Base):
    """One row per issued handoff token, used to enforce single-use semantics.

    The JWT itself is stateless (signed claims with ``exp``), but single-use
    requires server-side state. We store the ``jti`` claim and mark it as
    consumed on first successful exchange.
    """

    __tablename__ = "handoff_jti"

    jti: Mapped[str] = mapped_column(String(26), primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )
    issued_by_api_key_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("source_api_keys.id"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_by_api_key_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("source_api_keys.id"), nullable=True
    )
