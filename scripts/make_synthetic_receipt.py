"""Bikin foto struk sintetis (miring, di atas meja gelap) untuk uji preprocessing.

uv run python scripts/make_synthetic_receipt.py data/raw/synthetic_01.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

LINES = [
    "INDOMARET",
    "JL. MARGONDA RAYA 21",
    "13.11.2026  19:42",
    "--------------------------",
    "INDOMIE GORENG   3  10.500",
    "AQUA 600ML       1   4.000",
    "ROTI SARI COKLAT 1   6.500",
    "--------------------------",
    "TOTAL ITEM 5       21.000",
    "QRIS               21.000",
    "PPN 11% TERMASUK    2.081",
]


def make_receipt(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    paper_h, paper_w = 40 + 38 * len(LINES), 420
    paper = np.full((paper_h, paper_w, 3), 245, np.uint8)
    for i, line in enumerate(LINES):
        cv2.putText(paper, line, (18, 50 + 38 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (40, 40, 40), 2)

    canvas_h, canvas_w = 900, 700
    canvas = np.full((canvas_h, canvas_w, 3), (60, 45, 35), np.uint8)
    canvas = cv2.add(canvas, rng.integers(0, 20, canvas.shape, dtype=np.uint8))

    src = np.float32([[0, 0], [paper_w, 0], [paper_w, paper_h], [0, paper_h]])
    cx, cy = canvas_w / 2, canvas_h / 2
    dst = np.float32(
        [
            [cx - 190, cy - 280],
            [cx + 170, cy - 250],
            [cx + 200, cy + 290],
            [cx - 210, cy + 260],
        ]
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(paper, matrix, (canvas_w, canvas_h))
    mask = cv2.warpPerspective(
        np.full(paper.shape[:2], 255, np.uint8), matrix, (canvas_w, canvas_h)
    )
    canvas[mask > 0] = warped[mask > 0]
    return canvas


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/synthetic_01.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), make_receipt())
    print(f"Disimpan: {out}")
