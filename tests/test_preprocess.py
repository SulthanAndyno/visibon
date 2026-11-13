import cv2
import numpy as np
from make_synthetic_receipt import make_receipt  # dari scripts/ (lihat conftest.py)

from visibon.preprocess import (
    blur_score,
    encode_jpeg,
    load_image,
    order_points,
    preprocess,
    resize_max_side,
)


def test_order_points():
    pts = np.array([[10, 100], [100, 0], [0, 0], [100, 100]], dtype="float32")
    ordered = order_points(pts)
    assert ordered.tolist() == [[0, 0], [100, 0], [100, 100], [10, 100]]


def test_detects_and_warps_tilted_receipt():
    img = make_receipt()
    result = preprocess(img, max_side=1280, keep_debug=True)
    assert result.warped
    h, w = result.image.shape[:2]
    assert h > w * 1.2, "struk hasil warp harus tegak (lebih tinggi dari lebar)"
    # Background gelap harus sudah terpotong -> hasil didominasi kertas terang.
    assert result.image.mean() > 180
    assert {"01_detected", "02_final", "03_binary"} <= result.debug.keys()


def test_blurry_image_flagged():
    sharp = make_receipt()
    blurry = cv2.GaussianBlur(sharp, (31, 31), 0)
    assert blur_score(sharp) > blur_score(blurry)
    assert preprocess(blurry, blur_threshold=60).is_blurry


def test_resize_and_roundtrip():
    img = np.zeros((3000, 1000, 3), np.uint8)
    assert max(resize_max_side(img, 1280).shape[:2]) == 1280
    decoded = load_image(encode_jpeg(make_receipt()))
    assert decoded.shape == (900, 700, 3)
