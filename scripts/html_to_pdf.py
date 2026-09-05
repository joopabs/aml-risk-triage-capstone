"""Render an HTML file to PDF with xhtml2pdf (pure Python; used when pandoc is unavailable)."""

from __future__ import annotations

import sys
from pathlib import Path

from xhtml2pdf import pisa

PDF_CSS = """
@page { size: A4; margin: 14mm; }
body { font-family: Helvetica; font-size: 9.5pt; line-height: 1.35; color: #222; }
h1 { font-size: 18pt; } h2 { font-size: 14pt; margin-top: 14pt; -pdf-keep-with-next: true; }
h3 { font-size: 11.5pt; } h4 { font-size: 10pt; }
table { font-size: 7pt; border-collapse: collapse; width: 100%; }
th, td { border: 0.5pt solid #999; padding: 2pt 3pt; } th { background: #eee; }
img { max-width: 100%; }
blockquote { background: #fbeeec; border-left: 3pt solid #DD5143; padding: 4pt 8pt; }
code { font-family: Courier; font-size: 8.5pt; }
"""


def main(src: str, dst: str, page_break_h2: bool = False) -> None:
    html = Path(src).read_text(encoding="utf-8")
    css = PDF_CSS + ("h2 { page-break-before: always; }" if page_break_h2 else "")
    html = (
        html.replace("</head>", f"<style>{css}</style></head>", 1)
        if "</head>" in html
        else f"<style>{css}</style>" + html
    )
    with open(dst, "wb") as fh:
        status = pisa.CreatePDF(
            html, dest=fh, path=str(Path(src).resolve().parent), encoding="utf-8"
        )
    if status.err:
        raise SystemExit(f"xhtml2pdf reported {status.err} error(s) rendering {src}")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--page-break-h2" in sys.argv)
