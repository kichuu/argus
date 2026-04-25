from typing import Any

from argus_core.logging import get_logger

logger = get_logger(__name__)


class GLiNERPrePass:
    def __init__(self, model_name: str = "urchade/gliner_medium-v2.1") -> None:
        self._model_name = model_name
        self._model: Any | None = None
        self._load_failed = False

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._load_failed:
            return False
        try:
            from gliner import GLiNER

            self._model = GLiNER.from_pretrained(self._model_name)
            return True
        except Exception as e:
            self._load_failed = True
            logger.warning("gliner_load_failed", error=str(e), model=self._model_name)
            return False

    def find_entities(
        self,
        text: str,
        labels: list[str],
    ) -> list[tuple[str, int, int, str]]:
        if not self._ensure_loaded() or self._model is None:
            return []
        try:
            predictions = self._model.predict_entities(text, labels)
        except Exception as e:
            logger.warning("gliner_predict_failed", error=str(e))
            return []

        results: list[tuple[str, int, int, str]] = []
        for pred in predictions:
            span_text = pred.get("text", "")
            start = int(pred.get("start", -1))
            end = int(pred.get("end", -1))
            label = pred.get("label", "")
            if start < 0 or end <= start or not span_text:
                continue
            results.append((span_text, start, end, label))
        return results
