#!/usr/bin/env bash
# Export reports/final_report.md to PDF. Preference: pandoc -> xhtml2pdf (pure Python) -> instructions.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
SRC=reports/final_report.md; HTML=reports/final_report.html; PDFHTML=reports/.final_report_pdf.html; OUT=reports/final_report.pdf
[ -f "$SRC" ] || { echo "ERROR: $SRC not found; run: python -m aml_triage build-report" >&2; exit 4; }
if command -v pandoc >/dev/null 2>&1; then
  pandoc "$SRC" -o "$OUT" --resource-path=reports --pdf-engine=xelatex -V geometry:margin=2cm && echo "wrote $OUT (pandoc)"; exit 0
fi
"$PY" scripts/md_to_html.py "$SRC" "$HTML" embed          # self-contained HTML (shareable)
"$PY" scripts/md_to_html.py "$SRC" "$PDFHTML" abs         # absolute image paths for the PDF renderer
if "$PY" scripts/html_to_pdf.py "$PDFHTML" "$OUT"; then rm -f "$PDFHTML"; exit 0; fi
echo "PDF render failed. Open $HTML in a browser and print to PDF as $OUT, or install pandoc (brew install pandoc)." >&2
exit 3
