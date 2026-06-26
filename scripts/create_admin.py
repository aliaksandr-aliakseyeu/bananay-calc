"""
Script to create an admin user.

Usage:
    poetry run python scripts/create_admin.py <email> <password>

example:
    poetry run python scripts/create_admin.py admin@example.com mypassword123
"""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import get_password_hash
from app.db.base import AsyncSessionLocal
from app.db.models import OnboardingStatus, User, UserRole


async def create_admin(email: str, password: str) -> None:
    """Create admin user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"❌ User with email '{email}' already exists!")
            print(f"   User ID: {existing_user.id}")
            print(f"   Is Active: {existing_user.is_active}")
            sys.exit(1)

        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            onboarding_status=OnboardingStatus.COMPLETED,
            is_active=True,
            email_verified=True,
            is_approved=True,
        )

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        print("✅ Admin user created successfully!")
        print(f"   User ID: {new_user.id}")
        print(f"   Email: {new_user.email}")
        print(f"   Role: {new_user.role.value}")
        print(f"   Onboarding Status: {new_user.onboarding_status.value}")
        print(f"   Is Active: {new_user.is_active}")
        print(f"   Created At: {new_user.created_at}")


def main() -> None:
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        print("Example: python scripts/create_admin.py admin@example.com mypassword123")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    if len(password) < 8:
        print("❌ Password must be at least 8 characters long!")
        sys.exit(1)

    asyncio.run(create_admin(email, password))


if __name__ == "__main__":
    main()
