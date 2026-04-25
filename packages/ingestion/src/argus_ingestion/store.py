from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from argus_core.logging import get_logger
from argus_core.settings import get_settings

logger = get_logger(__name__)


class RawStore:
    """Content-addressed blob store. Backends: local filesystem or S3-compatible.

    Keys: `<hash[0:2]>/<hash>` — sharded by first two hex chars.
    """

    def __init__(
        self,
        backend: str | None = None,
        local_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.backend = (backend or settings.raw_store_backend).lower()
        self.local_path = (
            Path(local_path) if local_path else Path(settings.raw_store_local_path)
        )
        self._settings = settings

    async def put(self, content_hash: str, payload: bytes) -> None:
        if self.backend == "local":
            await asyncio.to_thread(self._put_local, content_hash, payload)
            return
        if self.backend == "s3":
            await self._put_s3(content_hash, payload)
            return
        raise ValueError(f"Unknown raw_store backend: {self.backend}")

    async def get(self, content_hash: str) -> bytes:
        if self.backend == "local":
            return await asyncio.to_thread(self._get_local, content_hash)
        if self.backend == "s3":
            return await self._get_s3(content_hash)
        raise ValueError(f"Unknown raw_store backend: {self.backend}")

    # ---------------------------- local ------------------------------------

    def _path_for(self, content_hash: str) -> Path:
        return self.local_path / content_hash[:2] / content_hash

    def _put_local(self, content_hash: str, payload: bytes) -> None:
        target = self._path_for(content_hash)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def _get_local(self, content_hash: str) -> bytes:
        return self._path_for(content_hash).read_bytes()

    # ---------------------------- s3 ---------------------------------------

    def _key_for(self, content_hash: str) -> str:
        return f"{content_hash[:2]}/{content_hash}"

    def _s3_session(self) -> Any:
        import aioboto3

        return aioboto3.Session()

    def _s3_client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "aws_access_key_id": self._settings.s3_access_key,
            "aws_secret_access_key": self._settings.s3_secret_key,
            "region_name": self._settings.s3_region,
        }
        if self._settings.s3_endpoint_url:
            kwargs["endpoint_url"] = self._settings.s3_endpoint_url
        return kwargs

    async def _put_s3(self, content_hash: str, payload: bytes) -> None:
        bucket = self._settings.s3_bucket_raw
        key = self._key_for(content_hash)
        session = self._s3_session()
        async with session.client("s3", **self._s3_client_kwargs()) as client:
            await client.put_object(Bucket=bucket, Key=key, Body=payload)
        logger.debug("raw_store.put_s3", bucket=bucket, key=key, bytes=len(payload))

    async def _get_s3(self, content_hash: str) -> bytes:
        bucket = self._settings.s3_bucket_raw
        key = self._key_for(content_hash)
        session = self._s3_session()
        async with session.client("s3", **self._s3_client_kwargs()) as client:
            resp = await client.get_object(Bucket=bucket, Key=key)
            body = resp["Body"]
            data = await body.read()
        return bytes(data)
