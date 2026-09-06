"""Render deployment/demo/demo.gif: a terminal-style transcript of real API responses.

Usage: render_demo_gif.py TRANSCRIPT.json OUT.gif
TRANSCRIPT.json is a list of {"cmd": "...", "out": "..."} captured from the running service.
Pure Python (Pillow); no screen recorder required.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, PAD, LH = 1100, 640, 24, 22
BG, FG, PROMPT, DIM = (18, 22, 30), (220, 224, 230), (120, 200, 140), (140, 150, 165)


def font(size: int = 15):
    for candidate in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def frame(lines: list[tuple[str, tuple[int, int, int]]], f) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text(
        (PAD, 6),
        "aml-triage demo · synthetic PaySim data · educational prototype · no AML determination",
        fill=DIM,
        font=font(12),
    )
    y = PAD + 16
    for text, colour in lines[-((H - PAD * 2 - 16) // LH) :]:
        d.text((PAD, y), text, fill=colour, font=f)
        y += LH
    return img


def main(transcript: str, out: str) -> None:
    steps = json.loads(Path(transcript).read_text())
    f = font()
    frames: list[Image.Image] = []
    durations: list[int] = []
    lines: list[tuple[str, tuple[int, int, int]]] = []
    for step in steps:
        cmd = step["cmd"]
        for i in range(1, len(cmd) + 1, max(1, len(cmd) // 12)):  # typing effect
            frames.append(frame([*lines, ("$ " + cmd[:i], PROMPT)], f))
            durations.append(45)
        lines.append(("$ " + cmd, PROMPT))
        frames.append(frame(lines, f))
        durations.append(500)
        for raw in step["out"].splitlines():
            for wrapped in textwrap.wrap(raw, 118) or [""]:
                lines.append((wrapped, FG))
        frames.append(frame(lines, f))
        durations.append(int(step.get("hold_ms", 3200)))
        lines.append(("", FG))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        out, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True
    )
    print(f"wrote {out}: {len(frames)} frames, {sum(durations) / 1000:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
