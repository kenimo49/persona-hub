"""Individual evaluated signal contributing to a persona."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.persona import Persona


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    persona_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    answers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_by_api_key_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("source_api_keys.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    persona: Mapped["Persona"] = relationship(back_populates="signals")
