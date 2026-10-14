"""hash plain passwords

Пароли, записанные миграцией b7e4c2d91f3a открытым текстом ('builder_pass'),
заменяются хешем PBKDF2-SHA256: вход ЛР4 сравнивает пароль только с хешем.

Revision ID: c4a8d2e6f1b9
Revises: b7e4c2d91f3a
Create Date: 2026-10-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core.security import ALGORITHM, hash_password


revision: str = "c4a8d2e6f1b9"
down_revision: Union[str, Sequence[str], None] = "b7e4c2d91f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, password FROM users WHERE password NOT LIKE :prefix"),
        {"prefix": f"{ALGORITHM}$%"},
    ).all()
    for user_id, password in rows:
        conn.execute(
            sa.text("UPDATE users SET password = :password WHERE id = :id"),
            {"password": hash_password(password), "id": user_id},
        )


def downgrade() -> None:
    # Хеш необратим: вернуть открытые пароли нельзя
    pass
