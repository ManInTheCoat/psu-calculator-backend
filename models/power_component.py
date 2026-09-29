from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class PowerComponent(Base):
    __tablename__ = "power_components"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'deleted')",
            name="ck_power_components_status",
        ),
        Index(
            "uq_one_draft_per_creator",
            "creator_id",
            unique=True,
            postgresql_where=text("status = 'draft'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    image_url: Mapped[str] = mapped_column(String(255), default="", server_default="")
    video_url: Mapped[str] = mapped_column(String(255), default="", server_default="")
    power_watt: Mapped[int | None] = mapped_column(nullable=True)
    weight_gram: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    formed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    creator: Mapped["User"] = relationship()
