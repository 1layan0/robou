#!/usr/bin/env python3
"""
Export Robou wordmark RGB assets to transparent PNG.

Uses smooth alpha (no hard 0/255 cut) plus white decontamination on edges so
the logo composites cleanly on dark or colored backgrounds.

Best source: lossless PNG from design tools. JPEG inputs are optionally
median-filtered to reduce compression speckle before matting.

Usage (from repo root):
  python3 raboo3-frontend/scripts/export_robou_wordmark_transparent.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

BRAND = Path(__file__).resolve().parents[1] / "public" / "brand"


def smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def build_alpha(
    rgb: np.ndarray,
    *,
    sat_thr: float = 14.0,
    m0: float = 232.0,
    m1: float = 254.0,
) -> np.ndarray:
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    lo = np.minimum(np.minimum(r, g), b)
    hi = np.maximum(np.maximum(r, g), b)
    sat = hi - lo
    colored = sat > sat_thr
    t = (lo - m0) / (m1 - m0)
    t = smoothstep(t)
    alpha_gray = 255.0 * (1.0 - t)
    alpha = np.where(colored, 255.0, alpha_gray)
    alpha = np.where(lo < (m0 - 2.0), 255.0, alpha)
    return np.clip(alpha, 0.0, 255.0).astype(np.uint8)


def decontaminate_white(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = alpha.astype(np.float32) / 255.0
    a3 = np.maximum(a[..., None], 1e-3)
    x = rgb.astype(np.float32)
    out = (x - (1.0 - a3) * 255.0) / a3
    out = np.clip(out, 0.0, 255.0)
    out[alpha == 0] = 0
    return np.round(out).astype(np.uint8)


def mild_denoise_rgb(rgb: np.ndarray) -> np.ndarray:
    return np.array(Image.fromarray(rgb).filter(ImageFilter.MedianFilter(size=3)))


def rgb_to_transparent_png(
    rgb: np.ndarray,
    out_path: Path,
    *,
    compress_level: int = 6,
) -> None:
    alpha = build_alpha(rgb)
    rgb2 = decontaminate_white(rgb, alpha)
    rgba = np.dstack([rgb2, alpha])
    Image.fromarray(rgba).save(out_path, format="PNG", compress_level=compress_level)


def main() -> None:
    solo_jpg = BRAND / "robou-wordmark-solo-4k.jpg"
    hd_jpg = BRAND / "robou-wordmark-hd.jpg"
    solo_png = BRAND / "robou-wordmark-solo-4k.png"
    hd_png = BRAND / "robou-wordmark-hd.png"

    if solo_jpg.is_file():
        rgb = np.array(Image.open(solo_jpg).convert("RGB"))
        rgb_to_transparent_png(mild_denoise_rgb(rgb), solo_png)
        print(f"Wrote {solo_png}")
    else:
        print(f"Skip solo (missing {solo_jpg})")

    if hd_jpg.is_file():
        rgb = np.array(Image.open(hd_jpg).convert("RGB"))
        rgb_to_transparent_png(mild_denoise_rgb(rgb), hd_png)
        print(f"Wrote {hd_png}")
    else:
        print(f"Skip HD (missing {hd_jpg})")


if __name__ == "__main__":
    main()
