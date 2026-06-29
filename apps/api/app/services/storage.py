"""Blob storage abstraction backed by Azure Blob (Azurite locally)."""
from __future__ import annotations

import logging
from functools import lru_cache

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


class BlobStorage:
    """Thin wrapper over Azure Blob; container auto-created on first use."""

    def __init__(self) -> None:
        # Prefer real Azure (account name + key); fall back to the Azurite
        # connection string for local dev.
        account_url = settings.azure_blob_account_url
        if account_url and settings.azure_account_key:
            self._client = BlobServiceClient(
                account_url=account_url, credential=settings.azure_account_key
            )
            logger.info("Blob storage: Azure account %s", settings.azure_account_name)
        else:
            self._client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
            logger.info("Blob storage: Azurite (local dev)")
        self._container = settings.azure_blob_container
        self._ensure_container()

    def _ensure_container(self) -> None:
        try:
            self._client.create_container(self._container)
        except ResourceExistsError:
            pass
        except Exception as exc:  # pragma: no cover - storage offline
            logger.warning("Could not ensure blob container: %s", exc)

    def upload(self, path: str, data: bytes, content_type: str) -> str:
        """Upload bytes to `path`; returns the blob path stored in the DB."""
        blob = self._client.get_blob_client(self._container, path)
        blob.upload_blob(
            data, overwrite=True, content_settings=ContentSettings(content_type=content_type)
        )
        return path

    def download(self, path: str) -> bytes:
        blob = self._client.get_blob_client(self._container, path)
        return blob.download_blob().readall()

    def delete(self, path: str) -> None:
        blob = self._client.get_blob_client(self._container, path)
        try:
            blob.delete_blob()
        except Exception:  # pragma: no cover
            pass


@lru_cache
def get_storage() -> BlobStorage:
    return BlobStorage()
