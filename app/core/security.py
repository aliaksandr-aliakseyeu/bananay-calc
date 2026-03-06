"""Security utilities for JWT and password hashing."""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token with longer expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_driver_access_token(driver_id: str, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token for driver (subject_type=driver)."""
    data = {"sub": driver_id, "subject_type": "driver"}
    return create_access_token(data, expires_delta=expires_delta)


def create_driver_refresh_token(driver_id: str) -> str:
    """Create JWT refresh token for driver."""
    to_encode = {
        "sub": driver_id,
        "subject_type": "driver",
        "type": "refresh",
    }
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_dc_access_token(dc_id: str, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token for DC employee (subject_type=dc)."""
    data = {"sub": dc_id, "subject_type": "dc"}
    return create_access_token(data, expires_delta=expires_delta)


def create_dc_refresh_token(dc_id: str) -> str:
    """Create JWT refresh token for DC employee."""
    to_encode = {
        "sub": dc_id,
        "subject_type": "dc",
        "type": "refresh",
    }
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_id_from_token(token: str) -> int:
    """Extract user ID from JWT token (subject_type=user or no subject_type)."""
    payload = decode_token(token)
    subject_type = payload.get("subject_type")
    if subject_type in {"driver", "dc", "courier"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for this endpoint",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_driver_id_from_token(token: str) -> str:
    """Extract driver ID (UUID string) from JWT token. Requires subject_type=driver."""
    payload = decode_token(token)
    if payload.get("subject_type") != "driver":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Driver token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    driver_id: str | None = payload.get("sub")
    if not driver_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return driver_id


def get_dc_id_from_token(token: str) -> str:
    """Extract DC account ID (UUID string) from JWT token. Requires subject_type=dc."""
    payload = decode_token(token)
    if payload.get("subject_type") != "dc":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DC token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    dc_id: str | None = payload.get("sub")
    if not dc_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return dc_id


def create_courier_access_token(courier_id: str, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token for courier (subject_type=courier)."""
    data = {"sub": courier_id, "subject_type": "courier"}
    return create_access_token(data, expires_delta=expires_delta)


def create_courier_refresh_token(courier_id: str) -> str:
    """Create JWT refresh token for courier."""
    to_encode = {
        "sub": courier_id,
        "subject_type": "courier",
        "type": "refresh",
    }
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_courier_id_from_token(token: str) -> str:
    """Extract courier ID (UUID string) from JWT token. Requires subject_type=courier."""
    payload = decode_token(token)
    if payload.get("subject_type") != "courier":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Courier token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    courier_id: str | None = payload.get("sub")
    if not courier_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return courier_id
