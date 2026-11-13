"""Preprocessing foto struk dengan OpenCV klasik.

Alur:
    1. Cek blur (variance of Laplacian) -> tolak foto buram.
    2. Cari kontur kertas struk (Otsu + morfologi, fallback Canny).
    3. Koreksi perspektif (4 titik) -> struk jadi lurus & rata.
    4. Enhancement (CLAHE) + resize agar hemat token/VRAM untuk VLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

_DETECT_HEIGHT = 800  # resolusi kerja untuk deteksi kontur (lebih cepat)
_MIN_AREA_RATIO = 0.15  # kontur harus menutupi >= 15% gambar


@dataclass
class PreprocessResult:
    image: np.ndarray  # hasil akhir (BGR) yang dikirim ke extractor
    blur_score: float
    is_blurry: bool
    warped: bool
    corners: np.ndarray | None = None  # 4 titik di koordinat gambar asli
    debug: dict[str, np.ndarray] = field(default_factory=dict)


def load_image(source: str | Path | bytes) -> np.ndarray:
    if isinstance(source, (bytes, bytearray)):
        buf = np.frombuffer(source, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Gambar tidak bisa dibaca (format tidak didukung / file rusak).")
    return img


def blur_score(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def order_points(pts: np.ndarray) -> np.ndarray:
    """Urutkan 4 titik: kiri-atas, kanan-atas, kanan-bawah, kiri-bawah."""
    pts = pts.reshape(4, 2).astype("float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array(
        [pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
        dtype="float32",
    )


def four_point_transform(img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    tl, tr, br, bl = rect = order_points(pts)
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], "float32")
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, matrix, (width, height), flags=cv2.INTER_CUBIC)


def _quad_from_contour(contour: np.ndarray) -> np.ndarray:
    peri = cv2.arcLength(contour, True)
    for eps in (0.02, 0.03, 0.04, 0.05):
        approx = cv2.approxPolyDP(contour, eps * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
    # Struk sering melengkung/kusut -> pakai kotak minimum sebagai fallback.
    return cv2.boxPoints(cv2.minAreaRect(contour))


def find_receipt_corners(img: np.ndarray) -> np.ndarray | None:
    """Cari 4 sudut struk. Return None kalau tidak yakin."""
    scale = _DETECT_HEIGHT / img.shape[0]
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    min_area = _MIN_AREA_RATIO * small.shape[0] * small.shape[1]

    # Kandidat 1: kertas putih vs latar lebih gelap (Otsu + closing).
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Kandidat 2: tepi (Canny) untuk latar terang.
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=2)

    for candidate in (mask, edges):
        contours, _ = cv2.findContours(candidate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        biggest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(biggest)
        # Kontur yang = seluruh frame berarti struk memenuhi foto -> tidak perlu warp.
        if min_area <= area <= 0.97 * small.shape[0] * small.shape[1]:
            return (_quad_from_contour(biggest) / scale).astype("float32")
    return None


def enhance(img: np.ndarray) -> np.ndarray:
    """CLAHE pada kanal luminance — teks thermal pudar jadi lebih kontras."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    l_chan = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l_chan)
    return cv2.cvtColor(cv2.merge((l_chan, a_chan, b_chan)), cv2.COLOR_LAB2BGR)


def binarize(img: np.ndarray) -> np.ndarray:
    """Versi hitam-putih untuk pipeline OCR klasik (dipakai di minggu 5)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def resize_max_side(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_side:
        return img
    scale = max_side / max(h, w)
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def preprocess(
    img: np.ndarray,
    max_side: int = 1280,
    blur_threshold: float = 60.0,
    keep_debug: bool = False,
) -> PreprocessResult:
    score = blur_score(resize_max_side(img, 1600))
    corners = find_receipt_corners(img)

    out = four_point_transform(img, corners) if corners is not None else img.copy()
    out = enhance(out)
    out = resize_max_side(out, max_side)

    debug: dict[str, np.ndarray] = {}
    if keep_debug:
        overlay = img.copy()
        if corners is not None:
            cv2.polylines(overlay, [order_points(corners).astype(int)], True, (0, 255, 0), 6)
        debug = {"01_detected": overlay, "02_final": out, "03_binary": binarize(out)}

    return PreprocessResult(
        image=out,
        blur_score=score,
        is_blurry=score < blur_threshold,
        warped=corners is not None,
        corners=corners,
        debug=debug,
    )


def encode_jpeg(img: np.ndarray, quality: int = 90) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Gagal encode JPEG.")
    return buf.tobytes()
