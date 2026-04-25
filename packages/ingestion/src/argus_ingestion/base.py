import hashlib
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from bs4 import BeautifulSoup

from argus_core.schemas import Source


_WHITESPACE_RE = re.compile(r"\s+")


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    stripped = soup.get_text(separator=" ")
    return _WHITESPACE_RE.sub(" ", stripped).strip()


class SourceConnector(ABC):
    @abstractmethod
    def fetch(self) -> AsyncIterator[Source]:
        """Yield Source records; implementations are async generators."""
        ...
