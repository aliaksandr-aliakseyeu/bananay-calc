"""Verification token service."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


class VerificationService:
    """Service for creating and verifying email verification tokens."""

    @staticmethod
    def create_email_verification_token(user_id: int) -> str:
        """
        Create email verification token.

        Args:
            user_id: User ID

        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)

        to_encode = {
            "sub": str(user_id),
            "type": "email_verification",
            "exp": expire,
            "iat": now,
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    @staticmethod
    def verify_email_verification_token(token: str) -> int:
        """
        Verify email verification token and extract user ID.

        Args:
            token: JWT token string

        Returns:
            User ID

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )

            token_type: str | None = payload.get("type")
            if token_type != "email_verification":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type",
                )

            user_id: str | None = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token",
                )

            return int(user_id)

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )


verification_service = VerificationService()
