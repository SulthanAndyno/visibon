"""Pipeline end-to-end: gambar -> preprocessing -> ekstraksi -> validasi."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel

from visibon.config import Settings, get_settings
from visibon.extractors import Extractor, get_extractor
from visibon.preprocess import preprocess
from visibon.schemas import Receipt
from visibon.validator import ValidationReport, validate_receipt


class ScanResult(BaseModel):
    receipt: Receipt
    validation: ValidationReport
    extractor: str
    model: str
    latency_ms: float
    blur_score: float
    is_blurry: bool
    warped: bool


def scan(
    image: np.ndarray,
    extractor: Extractor | None = None,
    settings: Settings | None = None,
    debug_dir: Path | None = None,
) -> ScanResult:
    settings = settings or get_settings()
    extractor = extractor or get_extractor(settings=settings)

    pre = preprocess(
        image,
        max_side=settings.max_image_side,
        blur_threshold=settings.blur_threshold,
        keep_debug=debug_dir is not None,
    )
    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
        for name, img in pre.debug.items():
            cv2.imwrite(str(debug_dir / f"{name}.jpg"), img)

    result = extractor.extract(pre.image)
    return ScanResult(
        receipt=result.receipt,
        validation=validate_receipt(result.receipt),
        extractor=result.extractor,
        model=result.model,
        latency_ms=round(result.latency_ms, 1),
        blur_score=round(pre.blur_score, 1),
        is_blurry=pre.is_blurry,
        warped=pre.warped,
    )
