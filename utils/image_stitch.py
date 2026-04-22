from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable, List

from PIL import Image


def stitch(
    images: Iterable[bytes],
    orientation: str = "horizontal",
    gap: int = 4,
    bg: tuple = (255, 255, 255),
) -> Image.Image:
    frames: List[Image.Image] = [Image.open(BytesIO(b)).convert("RGB") for b in images]
    if not frames:
        raise ValueError("stitch() requires at least one image")

    if orientation == "horizontal":
        total_w = sum(f.width for f in frames) + gap * (len(frames) - 1)
        max_h = max(f.height for f in frames)
        canvas = Image.new("RGB", (total_w, max_h), bg)
        x = 0
        for f in frames:
            canvas.paste(f, (x, 0))
            x += f.width + gap
    elif orientation == "vertical":
        max_w = max(f.width for f in frames)
        total_h = sum(f.height for f in frames) + gap * (len(frames) - 1)
        canvas = Image.new("RGB", (max_w, total_h), bg)
        y = 0
        for f in frames:
            canvas.paste(f, (0, y))
            y += f.height + gap
    else:
        raise ValueError(f"orientation must be 'horizontal' or 'vertical', got {orientation!r}")

    return canvas


def stitch_to_file(
    images: Iterable[bytes],
    output_path: str | Path,
    orientation: str = "horizontal",
    gap: int = 4,
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    stitch(images, orientation=orientation, gap=gap).save(out, format="PNG")
    return out
