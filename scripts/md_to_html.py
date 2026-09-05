"""Render a Markdown report to a self-contained HTML page (images embedded as data URIs)."""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

import mistune

CSS = """
body{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:960px;margin:2rem auto;padding:0 1.5rem;color:#222;line-height:1.45;font-size:11.5pt}
h1{font-size:1.9em;border-bottom:2px solid #333;padding-bottom:.2em} h2{font-size:1.5em;margin-top:2.2em;border-bottom:1px solid #999;padding-bottom:.15em;page-break-before:always}
h3{font-size:1.2em;margin-top:1.6em} h4{font-size:1.05em} table{border-collapse:collapse;font-size:9pt;margin:.8em 0;width:100%}
th,td{border:1px solid #bbb;padding:3px 6px;vertical-align:top} th{background:#f0f0f0} img{max-width:100%;page-break-inside:avoid}
blockquote{border-left:4px solid #DD5143;background:#fbeeec;padding:.5em 1em;margin:1em 0} code{background:#f4f4f4;padding:0 3px;font-size:.92em}
pre{background:#f4f4f4;padding:.6em;overflow-x:auto} hr{margin:2em 0} .toc{page-break-before:avoid}
@page{size:A4;margin:16mm}
"""


def embed_images(html: str, base: Path) -> str:
    def repl(m: re.Match[str]) -> str:
        src = m.group(1)
        p = (base / src).resolve()
        if p.exists() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}:
            mime = (
                "image/svg+xml"
                if p.suffix.lower() == ".svg"
                else f"image/{p.suffix.lower().lstrip('.').replace('jpg', 'jpeg')}"
            )
            data = base64.b64encode(p.read_bytes()).decode()
            return f'src="data:{mime};base64,{data}"'
        return m.group(0)

    return re.sub(r'src="([^"]+)"', repl, html)


def absolutize_images(html: str, base: Path) -> str:
    return re.sub(
        r'src="([^"]+)"',
        lambda m: (
            f'src="{(base / m.group(1)).resolve()}"'
            if not m.group(1).startswith(("http", "data:"))
            else m.group(0)
        ),
        html,
    )


def main(src: str, dst: str, mode: str = "embed") -> None:
    md = Path(src)
    html_body = mistune.html(md.read_text(encoding="utf-8"))
    html_body = (
        embed_images(html_body, md.parent)
        if mode == "embed"
        else absolutize_images(html_body, md.parent)
    )
    title = re.search(r"<h1>(.*?)</h1>", html_body)
    doc = f"<!doctype html><html><head><meta charset='utf-8'><title>{title.group(1) if title else md.stem}</title><style>{CSS}</style></head><body>{html_body}</body></html>"
    Path(dst).write_text(doc, encoding="utf-8")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "embed")
