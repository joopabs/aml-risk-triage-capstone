"""Check that each deck has 8–12 slides (assignment recommendation); optionally dump .pptx text.

Usage: check_slide_counts.py DECK [DECK ...] [--dump-text] [--min 8] [--max 12] [--self-test]
Supports reveal.js HTML exported by nbconvert (counts top-level <section> elements) and .pptx
(counts ppt/slides/slideN.xml entries via zipfile; no extra dependency).
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path


def count_html(path: Path) -> int:
    html = path.read_text(encoding="utf-8", errors="ignore")
    slides = re.search(r'<div class="slides">(.*)</div>\s*</div>\s*<script', html, re.S)
    body = slides.group(1) if slides else html
    # top-level sections only: nbconvert nests vertical sub-slides inside a parent <section>
    depth, count = 0, 0
    for tag in re.finditer(r"<(/?)section\b", body):
        if tag.group(1) == "":
            if depth == 0:
                count += 1
            depth += 1
        else:
            depth -= 1
    return count


def pptx_slides(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        return sorted(
            (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
            key=lambda n: int(re.search(r"(\d+)", n).group(1)),
        )


def pptx_text(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        for i, name in enumerate(pptx_slides(path), 1):
            xml = z.read(name).decode("utf-8", errors="ignore")
            runs = re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)
            out.append(f"## Slide {i}\n" + "\n".join(runs))
    return "\n\n".join(out)


def count(path: Path) -> int:
    if path.suffix.lower() == ".pptx":
        return len(pptx_slides(path))
    if path.suffix.lower() in {".html", ".htm"}:
        return count_html(path)
    raise SystemExit(f"unsupported deck format: {path}")


def self_test() -> None:
    seven = '<div class="slides">' + "<section><h1>x</h1></section>" * 7 + "</div></div><script>"
    thirteen = (
        '<div class="slides">' + "<section><h1>x</h1></section>" * 13 + "</div></div><script>"
    )
    nested = (
        '<div class="slides">'
        + "<section><section>a</section><section>b</section></section>" * 9
        + "</div></div><script>"
    )
    import tempfile

    for html, expected in ((seven, 7), (thirteen, 13), (nested, 9)):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
            fh.write(html)
        assert count_html(Path(fh.name)) == expected, (count_html(Path(fh.name)), expected)
    assert not (8 <= 7 <= 12) and not (8 <= 13 <= 12) and (8 <= 9 <= 12)
    print("self-test OK: 7 rejected, 13 rejected, 9 (nested) accepted")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("decks", nargs="*")
    ap.add_argument("--min", type=int, default=8)
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument(
        "--dump-text",
        action="store_true",
        help="write <deck>.txt beside each .pptx for the vocabulary scan",
    )
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return 0
    rc = 0
    for d in a.decks:
        p = Path(d)
        if not p.exists():
            print(f"MISSING {p}")
            rc = 1
            continue
        n = count(p)
        ok = a.min <= n <= a.max
        print(f"{'OK ' if ok else 'BAD'} {p}: {n} slides (allowed {a.min}–{a.max})")
        rc |= 0 if ok else 1
        if a.dump_text and p.suffix.lower() == ".pptx":
            txt = p.with_suffix(".txt")
            txt.write_text(pptx_text(p), encoding="utf-8")
            print(f"    text dumped to {txt}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
