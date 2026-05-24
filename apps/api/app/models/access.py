"""Access grants linking API keys to personas."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.persona import Persona


class PersonaAccess(Base):
    """Composite-PK row granting one API key access to one persona.

    Grants come from one of two sources:
      - ``creator``: the API key that called ``POST /personas``.
      - ``handoff_token``: an API key that consumed a valid handoff JWT
        for this persona.
    """

    __tablename__ = "persona_access"

    persona_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("personas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    api_key_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("source_api_keys.id"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    granted_via: Mapped[str] = mapped_column(String(32), nullable=False)

    persona: Mapped["Persona"] = relationship(back_populates="access_entries")
