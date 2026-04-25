import asyncio
from pathlib import Path

from argus_core.logging import get_logger
from argus_core.settings import get_settings

logger = get_logger(__name__)


class RawStore:
    def __init__(self, backend: str | None = None, local_path: Path | None = None) -> None:
        settings = get_settings()
        self.backend = backend or settings.raw_store_backend
        self.local_path = Path(local_path) if local_path else Path(settings.raw_store_local_path)

    async def put(self, content_hash: str, payload: bytes) -> None:
        if self.backend == "local":
            await asyncio.to_thread(self._put_local, content_hash, payload)
            return
        if self.backend == "s3":
            raise NotImplementedError("S3 backend not yet implemented")
        raise ValueError(f"Unknown raw_store backend: {self.backend}")

    async def get(self, content_hash: str) -> bytes:
        if self.backend == "local":
            return await asyncio.to_thread(self._get_local, content_hash)
        if self.backend == "s3":
            raise NotImplementedError("S3 backend not yet implemented")
        raise ValueError(f"Unknown raw_store backend: {self.backend}")

    def _path_for(self, content_hash: str) -> Path:
        return self.local_path / content_hash[:2] / content_hash

    def _put_local(self, content_hash: str, payload: bytes) -> None:
        target = self._path_for(content_hash)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def _get_local(self, content_hash: str) -> bytes:
        return self._path_for(content_hash).read_bytes()
