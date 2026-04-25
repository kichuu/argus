import re

from simhash import Simhash, SimhashIndex

from argus_core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _features(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class SimHashDedup:
    def __init__(self, k: int = 3, f: int = 64) -> None:
        self._k = k
        self._f = f
        self._index: SimhashIndex = SimhashIndex([], k=k, f=f)
        self._hashes: dict[str, Simhash] = {}

    def add(self, content_hash: str, text: str) -> None:
        if content_hash in self._hashes:
            return
        sh = Simhash(_features(text), f=self._f)
        self._hashes[content_hash] = sh
        self._index.add(content_hash, sh)

    def is_near_duplicate(self, text: str, threshold: int = 3) -> bool:
        sh = Simhash(_features(text), f=self._f)
        if threshold == self._k:
            return bool(self._index.get_near_dups(sh))
        for stored in self._hashes.values():
            if sh.distance(stored) <= threshold:
                return True
        return False
