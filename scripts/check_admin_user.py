"""
Check admin user details.

Usage:
    poetry run python scripts/check_admin_user.py <email>
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text

from app.db.base import AsyncSessionLocal
from app.db.models import User


async def check_admin_user(email: str) -> None:
    """Check admin user details."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User with email '{email}' not found!")
            return

        role_result = await session.execute(
            text("SELECT role FROM geo_users WHERE id = :user_id"),
            {"user_id": user.id}
        )
        role_raw = role_result.scalar()

        print("=" * 60)
        print("USER DETAILS")
        print("=" * 60)
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Role (raw from DB): '{role_raw}'")
        print(f"Role (from model): {user.role}")
        print(f"Is Active: {user.is_active}")
        print(f"Email Verified: {user.email_verified}")
        print(f"Is Approved: {user.is_approved}")
        print(f"Onboarding Status: {user.onboarding_status}")
        print(f"Created At: {user.created_at}")
        print(f"Hashed Password (first 50 chars): {user.hashed_password[:50]}...")
        print("=" * 60)

        print("\nTo test password, run:")
        print(f"poetry run python -c \"from app.core.security import verify_password;"
              f"print(verify_password('YOUR_PASSWORD', '{user.hashed_password}'))\"")


def main() -> None:
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_admin_user.py <email>")
        print("Example: python scripts/check_admin_user.py admin@example.com")
        sys.exit(1)

    email = sys.argv[1]
    asyncio.run(check_admin_user(email))


if __name__ == "__main__":
    main()
