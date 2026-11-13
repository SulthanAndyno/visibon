"""Extractor VLM lokal via Ollama (gratis, offline, data struk tidak keluar dari laptop)."""

from __future__ import annotations

import base64
import time

import httpx
import numpy as np

from visibon.extractors.base import ExtractionError, ExtractionResult, Extractor, parse_json_output
from visibon.extractors.prompt import RECEIPT_PROMPT
from visibon.preprocess import encode_jpeg
from visibon.schemas import Receipt


class OllamaVLMExtractor(Extractor):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def extract(self, image: np.ndarray) -> ExtractionResult:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096},
            "messages": [
                {
                    "role": "user",
                    "content": RECEIPT_PROMPT,
                    "images": [base64.b64encode(encode_jpeg(image)).decode()],
                }
            ],
        }
        start = time.perf_counter()
        try:
            resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExtractionError(f"Gagal memanggil Ollama ({self.model}): {exc}") from exc
        latency = (time.perf_counter() - start) * 1000

        msg = resp.json().get("message", {})
        text = msg.get("content") or ""
        # Jika model reasoning meletakkan JSON di dalam thinking block
        if not text.strip() or "{" not in text:
            text = msg.get("thinking") or text

        receipt = Receipt.model_validate(parse_json_output(text))
        return ExtractionResult(receipt, self.name, self.model, latency, text)

    def health(self) -> tuple[bool, str]:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except httpx.HTTPError:
            return False, f"Ollama tidak jalan di {self.base_url}. Jalankan: ollama serve"
        names = {m.get("name", "") for m in resp.json().get("models", [])}
        wanted = self.model if ":" in self.model else f"{self.model}:latest"
        if wanted not in names:
            return False, f"Model '{self.model}' belum ada. Jalankan: ollama pull {self.model}"
        return True, f"Ollama siap dengan model {self.model}"
