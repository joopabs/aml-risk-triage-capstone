"""Render deployment/ui/demo_ui.gif for the optional batch-triage UI (task T037, research R-10).

Two sources, in order of preference:

1. Browser screenshots: if deployment/ui/shots/*.png exist (captured by a person from the running
   app with the synthetic example), they are composed into the GIF with a caption strip carrying the
   disclaimer.
2. Headless capture: otherwise the app is driven with streamlit.testing.v1.AppTest against the
   released bundle in process (empty state, example loaded, scored queue, explanation panel, exports)
   and each state's real rendered text is drawn as a frame, the same "rendered transcript" approach
   as deployment/demo/demo.gif. No browser or screen recorder is involved.

Only the synthetic example batch is ever shown. Usage:
  python scripts/render_ui_demo.py [SHOTS_DIR] [OUT.gif]
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from aml_triage.constants import DISCLAIMER

W, H, PAD, LH = 1200, 760, 24, 21
BG, FG, ACCENT, DIM = (250, 250, 252), (30, 34, 42), (28, 100, 180), (110, 118, 130)
STRIP = (238, 240, 245)


def font(size: int = 15, bold: bool = False):
    for candidate in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def caption_strip(img: Image.Image) -> Image.Image:
    """Append a strip with the disclaimer under a frame."""
    f = font(13)
    lines = textwrap.wrap(DISCLAIMER, width=int(img.width / 8.2))
    strip_h = 16 + LH * len(lines)
    out = Image.new("RGB", (img.width, img.height + strip_h), STRIP)
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    y = img.height + 8
    for ln in lines:
        d.text((PAD, y), ln, fill=DIM, font=f)
        y += LH
    return out


def frame_from_text(title: str, lines: list[str]) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 44], fill=ACCENT)
    d.text((PAD, 12), title, fill=(255, 255, 255), font=font(16, bold=True))
    y = 60
    f = font(14)
    for raw in (piece for block in lines for piece in (str(block).splitlines() or [""])):
        for ln in textwrap.wrap(raw, width=int((W - 2 * PAD) / 8.6)) or [""]:
            if y > H - LH - 8:
                d.text((PAD, y), "…", fill=DIM, font=f)
                y += LH
                break
            d.text((PAD, y), ln, fill=FG, font=f)
            y += LH
        if y > H - LH - 8:
            break
    return caption_strip(img)


def frames_from_shots(shots_dir: Path) -> list[Image.Image]:
    frames = []
    for p in sorted(shots_dir.glob("*.png")):
        img = Image.open(p).convert("RGB")
        if img.width > W:
            img = img.resize((W, int(img.height * W / img.width)))
        frames.append(caption_strip(img))
    return frames


def _texts(at, container=None) -> list[str]:
    src = container if container is not None else at
    out: list[str] = []
    for kind in ("title", "header", "subheader", "markdown", "caption", "info", "error", "success"):
        for el in getattr(src, kind):
            val = str(el.value)
            if val and val != DISCLAIMER:
                out.append(("## " if kind in ("title", "header", "subheader") else "") + val)
    return out


def frames_from_apptest(models_dir: str = "models") -> list[Image.Image]:
    from fastapi.testclient import TestClient
    from streamlit.testing.v1 import AppTest

    from aml_triage.api.main import create_app
    from aml_triage.ui.client import BadRequest, BatchTooLarge, ServiceUnavailable

    class InProcess:
        base_url = "http://127.0.0.1:8000 (in-process for this capture)"

        def __init__(self, c):
            self.c = c

        @staticmethod
        def _strip(row):
            return {k: v for k, v in row.items() if k != "input_row"}

        def config(self):
            return self.c.get("/triage-config").json()

        def score_batch(self, rows, explain="high"):
            r = self.c.post(
                "/score-batch",
                json={"transactions": [self._strip(x) for x in rows], "explain": explain},
            )
            if r.status_code == 413:
                raise BatchTooLarge(r.json().get("detail", ""))
            if r.status_code >= 400:
                raise BadRequest(r.text)
            return r.json()

        def score_one(self, row):
            r = self.c.post("/score", json=self._strip(row))
            if r.status_code >= 400:
                raise ServiceUnavailable(self.base_url)
            return r.json()

    frames = []
    with TestClient(create_app(models_dir)) as c:
        at = AppTest.from_file("src/aml_triage/ui/app.py", default_timeout=300)
        at.session_state["client"] = InProcess(c)
        at.run()
        frames.append(
            frame_from_text(
                "1 · Empty state (sidebar: service, model, K, threshold, limit)",
                _texts(at, at.sidebar) + [""] + _texts(at),
            )
        )
        at.button(key="example").click().run()
        frames.append(frame_from_text("2 · Synthetic example loaded", _texts(at)[-4:]))
        at.button(key="score").click().run()
        table = at.dataframe[0].value
        head = table.head(8).to_string(index=False).splitlines()
        frames.append(
            frame_from_text("3 · Ranked review queue (first rows)", _texts(at)[-6:-1] + [""] + head)
        )
        top = str(int(table.iloc[0]["input_row"]))
        at.selectbox(key="explain_select").select(top).run()
        panel = [
            m.value for m in at.markdown if "log-odds" in str(m.value) or "Rank" in str(m.value)
        ]
        frames.append(frame_from_text(f"4 · Why is input row {top} where it is?", panel))
        downloads = [f"[download] {d.label}" for d in at.download_button]
        frames.append(
            frame_from_text(
                "5 · Exports (CSV, disclaimer on the first line)",
                downloads + ["", "Clear batch → empty state; nothing was written to disk."],
            )
        )
    return frames


def main(shots_dir: str = "deployment/ui/shots", out: str = "deployment/ui/demo_ui.gif") -> int:
    shots = Path(shots_dir)
    frames = frames_from_shots(shots) if shots.exists() and any(shots.glob("*.png")) else []
    source = "browser screenshots" if frames else "headless AppTest capture"
    if not frames:
        frames = frames_from_apptest()
    # normalise sizes for GIF
    w = max(f.width for f in frames)
    h = max(f.height for f in frames)
    norm = []
    for f in frames:
        canvas = Image.new("RGB", (w, h), STRIP)
        canvas.paste(f, (0, 0))
        norm.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=128))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    norm[0].save(
        out,
        save_all=True,
        append_images=norm[1:],
        duration=[3500] * len(norm),
        loop=0,
        optimize=True,
    )
    size = os.path.getsize(out)
    print(f"wrote {out}: {len(norm)} frames from {source}, {size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    raise SystemExit(main(*args))
