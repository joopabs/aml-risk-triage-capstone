#!/usr/bin/env bash
# Package the submission files (task T101, CAPSTONE_BRIEF.md §8): approved formats only (.pdf, .pptx),
# named `Your_Name_Assignment name`. Output goes to submission/ (gitignored).
#   scripts/package_submission.sh [Your_Name]      # default: Julius_Pabular
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:-Julius_Pabular}
PY=${PY:-.venv/bin/python}
OUT=submission
PREFIX="${NAME}_Pillar5_Capstone"
# owner/repo from any remote form (https://github.com/o/r.git, git@github.com:o/r.git, git@<alias>:o/r)
REPO_URL=$(git remote get-url origin 2>/dev/null | sed -E 's#\.git$##; s#.*[:/]([^/]+/[^/]+)$#https://github.com/\1#')
VERSION=$(cat models/LATEST)
for f in reports/final_report.pdf reports/slides/technical_deck.pdf reports/slides/business_deck.pptx reports/slides/business_deck.pdf; do
  [ -f "$f" ] || { echo "ERROR: $f missing; run make report / make slides first" >&2; exit 4; }
done
rm -rf "$OUT"; mkdir -p "$OUT"
cp reports/final_report.pdf            "$OUT/${PREFIX}_Report.pdf"
cp reports/slides/technical_deck.pdf   "$OUT/${PREFIX}_Technical_Deck.pdf"
cp reports/slides/business_deck.pptx   "$OUT/${PREFIX}_Business_Deck.pptx"
cp reports/slides/business_deck.pdf    "$OUT/${PREFIX}_Business_Deck.pdf"
# One-page repository note in an approved format (PDF), rendered with the report toolchain.
NOTE_MD="$OUT/.repository_note.md"; NOTE_HTML="$OUT/.repository_note.html"
cat > "$NOTE_MD" <<EOF
# ${NAME//_/ } — Pillar 5 Capstone: repository

**Project:** Explainable AML Transaction-Risk Triage for SME and Corporate Banking (synthetic PaySim data)

**Public GitHub repository:** ${REPO_URL}

**Released model version:** \`${VERSION}\` (\`models/LATEST\`)

**Reproduce:** \`make setup && make data && make pipeline EVALUATE_FLAGS='--force-reevaluate --reason "reproducibility run"' && make report\` (see README.md)

**Files in this submission:** ${PREFIX}_Report.pdf, ${PREFIX}_Technical_Deck.pdf, ${PREFIX}_Business_Deck.pptx (+ .pdf export)

> Educational decision-support prototype trained on synthetic PaySim data. Outputs are risk scores and review priorities that help human investigators decide what to review first. This system makes no fraud or AML determination and performs no automatic blocking, account closure, customer risk rating, or regulatory reporting. Results on synthetic data do not establish real-world detection effectiveness, fairness, or regulatory suitability.
EOF
"$PY" scripts/md_to_html.py "$NOTE_MD" "$NOTE_HTML" abs
"$PY" scripts/html_to_pdf.py "$NOTE_HTML" "$OUT/${PREFIX}_Repository.pdf"
rm -f "$NOTE_MD" "$NOTE_HTML"
echo "packaged into $OUT/:"; ls -la "$OUT" | awk 'NR>1 && $NF != "." && $NF != ".." {print "  " $5 "\t" $NF}'
echo "license_verified_on: $(grep license_verified_on configs/data_source.yaml | awk '{print $2}')  (re-verify on the submission date)"
