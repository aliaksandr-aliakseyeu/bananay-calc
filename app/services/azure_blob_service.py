"""Azure Blob Storage for driver documents/photos."""
from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_blob_service_client():
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        return None
    try:
        from azure.storage.blob import BlobServiceClient
        return BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
    except Exception as e:
        logger.warning("Azure Blob client init failed: %s", e)
        return None


def upload_driver_document(
    driver_id: str,
    kind: str,
    content: bytes,
    content_type: str,
) -> tuple[str, Optional[str]]:
    """
    Upload file to Azure Blob. Path: drivers/{driver_id}/{kind}/{uuid}.ext
    Returns (blob_path, sha256_hex or None).
    """
    client = _get_blob_service_client()
    if not client:
        raise RuntimeError("Azure Blob Storage is not configured (AZURE_STORAGE_CONNECTION_STRING)")

    container = settings.AZURE_STORAGE_CONTAINER_DRIVERS
    ext = _content_type_to_ext(content_type)
    blob_name = f"drivers/{driver_id}/{kind}/{uuid.uuid4().hex}{ext}"

    blob_client = client.get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(content, overwrite=True)

    sha = hashlib.sha256(content).hexdigest()
    return blob_name, sha


def upload_vehicle_photo(
    driver_id: str,
    vehicle_id: str,
    content: bytes,
    content_type: str,
) -> tuple[str, Optional[str]]:
    """
    Upload vehicle photo to Azure Blob. Path: drivers/{driver_id}/vehicles/{vehicle_id}/{uuid}.ext
    Returns (blob_path, sha256_hex or None).
    """
    client = _get_blob_service_client()
    if not client:
        raise RuntimeError("Azure Blob Storage is not configured (AZURE_STORAGE_CONNECTION_STRING)")

    container = settings.AZURE_STORAGE_CONTAINER_DRIVERS
    ext = _content_type_to_ext(content_type)
    blob_name = f"drivers/{driver_id}/vehicles/{vehicle_id}/{uuid.uuid4().hex}{ext}"

    blob_client = client.get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(content, overwrite=True)

    sha = hashlib.sha256(content).hexdigest()
    return blob_name, sha


def upload_vehicle_document(
    driver_id: str,
    vehicle_id: str,
    kind: str,
    content: bytes,
    content_type: str,
) -> tuple[str, Optional[str]]:
    """
    Upload vehicle document (e.g. STS) to Azure Blob.
    Path: drivers/{driver_id}/vehicles/{vehicle_id}/{kind}/{uuid}.ext
    Returns (blob_path, sha256_hex or None).
    """
    client = _get_blob_service_client()
    if not client:
        raise RuntimeError("Azure Blob Storage is not configured (AZURE_STORAGE_CONNECTION_STRING)")

    container = settings.AZURE_STORAGE_CONTAINER_DRIVERS
    ext = _content_type_to_ext(content_type)
    blob_name = f"drivers/{driver_id}/vehicles/{vehicle_id}/{kind}/{uuid.uuid4().hex}{ext}"

    blob_client = client.get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(content, overwrite=True)

    sha = hashlib.sha256(content).hexdigest()
    return blob_name, sha


def upload_driver_task_photo(
    driver_id: str,
    task_id: int,
    kind: str,
    content: bytes,
    content_type: str,
) -> tuple[str, Optional[str]]:
    """
    Upload delivery task photo (e.g. loading) to Azure Blob.
    Path: drivers/{driver_id}/tasks/{task_id}/{kind}/{uuid}.ext
    Returns (blob_path, sha256_hex or None).
    """
    client = _get_blob_service_client()
    if not client:
        raise RuntimeError("Azure Blob Storage is not configured (AZURE_STORAGE_CONNECTION_STRING)")

    container = settings.AZURE_STORAGE_CONTAINER_DRIVERS
    ext = _content_type_to_ext(content_type)
    blob_name = f"drivers/{driver_id}/tasks/{task_id}/{kind}/{uuid.uuid4().hex}{ext}"

    blob_client = client.get_blob_client(container=container, blob=blob_name)
    blob_client.upload_blob(content, overwrite=True)

    sha = hashlib.sha256(content).hexdigest()
    return blob_name, sha


def _content_type_to_ext(content_type: str) -> str:
    m = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "application/pdf": ".pdf",
    }
    return m.get((content_type or "").split(";")[0].strip().lower(), ".bin")


def download_blob(blob_path: str) -> Optional[tuple[bytes, str]]:
    """
    Download blob content. Returns (content, content_type) or None if not configured.
    content_type is taken from blob metadata or defaults to application/octet-stream.
    """
    client = _get_blob_service_client()
    if not client:
        return None
    try:
        container = settings.AZURE_STORAGE_CONTAINER_DRIVERS
        blob_client = client.get_blob_client(container=container, blob=blob_path)
        data = blob_client.download_blob().readall()
        props = blob_client.get_blob_properties()
        content_type = getattr(props, "content_settings", None) and props.content_settings.content_type
        return (data, content_type or "application/octet-stream")
    except Exception as e:
        logger.warning("Blob download failed for %s: %s", blob_path, e)
        return None


def get_document_url(blob_path: str) -> Optional[str]:
    """Return SAS or public URL for blob if needed. For now returns None (client uses API to stream)."""
    return None


def upload_blob(
    blob_path: str,
    content: bytes,
    content_type: str,
) -> str:
    """
    Upload content to Azure Blob at specified path.
    Returns the blob_path on success.
    """
    from azure.storage.blob import ContentSettings

    client = _get_blob_service_client()
    if not client:
        raise RuntimeError("Azure Blob Storage is not configured (AZURE_STORAGE_CONNECTION_STRING)")

    container = settings.AZURE_STORAGE_CONTAINER_DRIVERS
    ext = _content_type_to_ext(content_type)
    full_path = f"{blob_path}{ext}"

    blob_client = client.get_blob_client(container=container, blob=full_path)
    blob_client.upload_blob(
        content,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )

    return full_path
