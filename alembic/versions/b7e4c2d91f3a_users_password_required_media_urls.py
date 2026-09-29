"""users password, required media urls, column lengths

Revision ID: b7e4c2d91f3a
Revises: 9af21a825ea3
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c2d91f3a"
down_revision: Union[str, Sequence[str], None] = "9af21a825ea3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Пароль. Сначала nullable, заполняем существующих пользователей, потом NOT NULL.
    # Хеширование появится вместе с авторизацией в ЛР4.
    op.add_column("users", sa.Column("password", sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET password = 'builder_pass' WHERE password IS NULL")
    op.alter_column("users", "password", existing_type=sa.String(length=255), nullable=False)

    # URL фото и видео обязательные. Пустая строка = показать заглушку по умолчанию.
    for column in ("image_url", "video_url"):
        op.execute(f"UPDATE power_components SET {column} = '' WHERE {column} IS NULL")
        op.alter_column(
            "power_components",
            column,
            existing_type=sa.String(),
            type_=sa.String(length=255),
            nullable=False,
            server_default="",
        )

    # Длины строк как в ER-диаграмме.
    op.alter_column("users", "login", existing_type=sa.String(), type_=sa.String(length=50))
    op.alter_column("power_components", "title", existing_type=sa.String(), type_=sa.String(length=100))
    op.alter_column("power_components", "description", existing_type=sa.String(), type_=sa.String(length=500))
    op.alter_column("power_components", "status", existing_type=sa.String(), type_=sa.String(length=20))


def downgrade() -> None:
    op.alter_column("power_components", "status", existing_type=sa.String(length=20), type_=sa.String())
    op.alter_column("power_components", "description", existing_type=sa.String(length=500), type_=sa.String())
    op.alter_column("power_components", "title", existing_type=sa.String(length=100), type_=sa.String())
    op.alter_column("users", "login", existing_type=sa.String(length=50), type_=sa.String())

    for column in ("image_url", "video_url"):
        op.alter_column(
            "power_components",
            column,
            existing_type=sa.String(length=255),
            type_=sa.String(),
            nullable=True,
            server_default=None,
        )

    op.drop_column("users", "password")
