from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from visibon.schemas import Receipt


@dataclass
class ExtractionResult:
    receipt: Receipt
    extractor: str
    model: str
    latency_ms: float
    raw_output: str


class ExtractionError(RuntimeError):
    pass


class Extractor(ABC):
    """Interface pluggable: VLM lokal, VLM cloud, OCR+rules, Donut, dst."""

    name: str = "base"

    @abstractmethod
    def extract(self, image: np.ndarray) -> ExtractionResult: ...

    def health(self) -> tuple[bool, str]:
        return True, "ok"


def parse_json_output(text: str) -> dict:
    """Ambil objek JSON dari output model (toleran terhadap ```json fences / teks tambahan)."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ExtractionError(f"Output model bukan JSON: {text[:200]!r}")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"JSON tidak valid dari model: {exc}") from exc
