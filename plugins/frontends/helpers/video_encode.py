"""Stitch rendered frames into an animated GIF (Pillow-only)."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from PIL import Image

SUPPORTED_FORMATS = {"gif"}


def encode_frames(frame_paths, *, fps: int, fmt: str, out_dir) -> tuple[Path, str]:
    """Encode ordered frame images into an animated file under ``out_dir``.

    Returns ``(output_path, suggested_download_name)``. Raises ``ValueError``
    on an unsupported format or fewer than two frames.
    """
    fmt = (fmt or "gif").lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported video format: {fmt!r}")
    paths = [Path(p) for p in frame_paths]
    if len(paths) < 2:
        raise ValueError("need at least 2 frames to make a video")

    fps_i = max(1, int(fps))
    duration_ms = max(1, round(1000 / fps_i))  # per-frame display time

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

    # Decode every frame up front. ``convert`` returns a fresh image that
    # outlives the closed file handle, so the source PNGs aren't held open.
    frames = []
    try:
        for p in paths:
            with Image.open(p) as im:
                frames.append(im.convert("RGBA"))

        out = out_dir / f"{stem}.gif"
        paletted = [f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=256) for f in frames]
        paletted[0].save(
            out, format="GIF", save_all=True, append_images=paletted[1:],
            duration=duration_ms, loop=0, disposal=2, optimize=True,
        )
        _require_animation(out, "GIF")
        name = "secondbrain-animation.gif"
    finally:
        for f in frames:
            try:
                f.close()
            except Exception:
                pass
    return out, name


def _require_animation(path: Path, label: str) -> None:
    with Image.open(path) as im:
        if int(getattr(im, "n_frames", 1) or 1) < 2:
            raise ValueError(f"{label} encoder produced a still image")
