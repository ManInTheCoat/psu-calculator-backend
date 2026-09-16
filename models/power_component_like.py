from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PowerComponentLike(Base):
    __tablename__ = "power_component_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "power_component_id", name="uq_user_component_like"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    power_component_id: Mapped[int] = mapped_column(ForeignKey("power_components.id"))
