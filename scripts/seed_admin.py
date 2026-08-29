"""Seed script: create the initial super_admin user.

Usage (inside container):
    python -m scripts.seed_admin

Or from docker:
    docker exec edpassare-build-api-1 python -m scripts.seed_admin
"""
import asyncio
import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import engine
from app.models.admin_user import AdminUser

SEED_EMAIL = "admin@edpassare.ng"
SEED_PASSWORD = "Edpassare@2026"
SEED_NAME = "Super Admin"
SEED_ROLE = "super_admin"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def main() -> None:
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        result = await db.execute(
            select(AdminUser).where(AdminUser.email == SEED_EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user already exists: {SEED_EMAIL} (role: {existing.role})")
            return

        user = AdminUser(
            id=uuid.uuid4(),
            email=SEED_EMAIL,
            full_name=SEED_NAME,
            hashed_password=hash_password(SEED_PASSWORD),
            role=SEED_ROLE,
        )
        db.add(user)
        await db.commit()
        print(f"Created super_admin: {SEED_EMAIL}")
        print(f"Password: {SEED_PASSWORD}")
        print("Change this password after first login!")


if __name__ == "__main__":
    asyncio.run(main())
