"""Extractor VLM cloud via Gemini API (opsional: `uv sync --extra gemini`)."""

from __future__ import annotations

import base64
import time

import numpy as np

from visibon.extractors.base import ExtractionError, ExtractionResult, Extractor, parse_json_output
from visibon.extractors.prompt import RECEIPT_PROMPT
from visibon.preprocess import encode_jpeg
from visibon.schemas import Receipt


class GeminiVLMExtractor(Extractor):
    name = "gemini"

    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise ExtractionError("Install dulu: uv sync --extra gemini") from exc
            if not self.api_key:
                raise ExtractionError("GEMINI_API_KEY belum di-set di .env")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def extract(self, image: np.ndarray) -> ExtractionResult:
        client = self._get_client()
        image_b64 = base64.b64encode(encode_jpeg(image)).decode()
        start = time.perf_counter()
        try:
            interaction = client.interactions.create(
                model=self.model,
                input=[
                    {"type": "text", "text": RECEIPT_PROMPT},
                    {"type": "image", "data": image_b64, "mime_type": "image/jpeg"},
                ],
                store=False,  # struk berisi data pribadi -> jangan disimpan
            )
        except Exception as exc:
            raise ExtractionError(f"Gagal memanggil Gemini ({self.model}): {exc}") from exc
        latency = (time.perf_counter() - start) * 1000

        text = interaction.output_text or ""
        receipt = Receipt.model_validate(parse_json_output(text))
        return ExtractionResult(receipt, self.name, self.model, latency, text)

    def health(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "GEMINI_API_KEY belum di-set"
        return True, f"Gemini siap ({self.model})"
