"""Persona aggregate root."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.access import PersonaAccess
    from app.models.signal import Signal


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_api_key_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("source_api_keys.id"), nullable=False
    )

    signals: Mapped[list["Signal"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        order_by="Signal.created_at",
    )
    access_entries: Mapped[list["PersonaAccess"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
    )
