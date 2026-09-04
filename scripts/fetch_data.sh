#!/usr/bin/env bash
# Fetch the PaySim CSV into data/raw/ and verify its SHA-256 against configs/data_source.yaml.
#
#   scripts/fetch_data.sh            # Kaggle API if KAGGLE_USERNAME/KAGGLE_KEY are set, else manual steps
#   scripts/fetch_data.sh --record   # after a first download: write filename/sha256/size/date to the config
#   scripts/fetch_data.sh --dry-run  # print what would happen; touch nothing
#
# Exit codes: 0 ok · 2 checksum mismatch / config problem · 3 data tracked by git · 4 file missing
set -euo pipefail
cd "$(dirname "$0")/.."

CFG=configs/data_source.yaml
RAW_DIR=data/raw
PY=${PY:-.venv/bin/python}
[ -x "$PY" ] || PY=python3
DRY=0; RECORD=0
for a in "$@"; do case "$a" in --dry-run) DRY=1;; --record) RECORD=1;; *) echo "unknown option $a" >&2; exit 2;; esac; done

yq_get() { "$PY" -c "import sys,yaml;v=yaml.safe_load(open('$CFG')).get('$1');print('' if v is None else v)"; }
URL=$(yq_get url); SLUG=$(yq_get kaggle_dataset); FILENAME=$(yq_get filename); SHA=$(yq_get sha256)

# Guard: raw data must never be tracked (constitution Principle II).
if git ls-files "$RAW_DIR" | grep -vq '\.gitkeep$'; then
  echo "ERROR: files under $RAW_DIR are tracked by git; untrack them before fetching." >&2; exit 3
fi

# Load optional .env without echoing values.
if [ -f .env ]; then set -a; . ./.env; set +a; fi

find_csv() { find "$RAW_DIR" -maxdepth 1 -name '*.csv' | head -n1; }

if [ "$DRY" = 1 ]; then
  echo "dry run:"; echo "  source: $URL"; echo "  target dir: $RAW_DIR"
  if [ -n "${KAGGLE_USERNAME:-}" ] && [ -n "${KAGGLE_KEY:-}" ]; then echo "  method: Kaggle API (credentials present)"; else echo "  method: manual download (no Kaggle credentials in env or .env)"; fi
  echo "  recorded sha256: ${SHA:-<none yet>}"; exit 0
fi

CSV=$(find_csv || true)
if [ -z "$CSV" ]; then
  if [ -n "${KAGGLE_USERNAME:-}" ] && [ -n "${KAGGLE_KEY:-}" ]; then
    echo "downloading via Kaggle API ..."
    ZIP="$RAW_DIR/paysim1.zip"
    curl -fL --retry 3 -u "$KAGGLE_USERNAME:$KAGGLE_KEY" -o "$ZIP" "https://www.kaggle.com/api/v1/datasets/download/$SLUG"
    "$PY" -c "import zipfile;zipfile.ZipFile('$ZIP').extractall('$RAW_DIR')"
    rm -f "$ZIP"
    CSV=$(find_csv || true)
  else
    cat >&2 <<MSG
No CSV in $RAW_DIR and no Kaggle credentials found.

Manual steps (one time, requires a Kaggle login):
  1. Open $URL
  2. Read the License shown on the page. Copy it verbatim into $CFG
     (license_text_verbatim, license_verified_on, license_permits_educational_use).
     If it does not permit educational use, STOP: do not use the dataset.
  3. Click Download, unzip, and move the CSV into $RAW_DIR/
  4. Re-run: scripts/fetch_data.sh --record   (records filename, sha256, size, date)
Alternatively export KAGGLE_USERNAME and KAGGLE_KEY (or put them in an untracked .env) and re-run.
MSG
    exit 4
  fi
fi
[ -n "$CSV" ] || { echo "ERROR: download finished but no CSV found in $RAW_DIR" >&2; exit 4; }

ACTUAL=$("$PY" -c "from aml_triage.utils.io import sha256_file;print(sha256_file('$CSV'))")
SIZE=$(stat -f%z "$CSV" 2>/dev/null || stat -c%s "$CSV")
BASENAME=$(basename "$CSV")

if [ -z "$SHA" ]; then
  if [ "$RECORD" = 1 ]; then
    "$PY" - "$CFG" "$BASENAME" "$ACTUAL" "$SIZE" <<'PYEOF'
import sys, yaml, datetime
cfg, name, sha, size = sys.argv[1:]
d = yaml.safe_load(open(cfg))
d.update(filename=name, sha256=sha, size_bytes=int(size), downloaded_on=datetime.date.today().isoformat())
text = open(cfg).read()
import re
for k in ("filename", "sha256", "size_bytes", "downloaded_on"):
    text = re.sub(rf"^{k}:.*$", f"{k}: {d[k]}", text, count=1, flags=re.M)
open(cfg, "w").write(text)
PYEOF
    echo "recorded: filename=$BASENAME sha256=$ACTUAL size_bytes=$SIZE in $CFG"
    echo "NEXT: fill license_text_verbatim / license_verified_on / license_permits_educational_use in $CFG and data/README.md, then set paths.raw_csv: $RAW_DIR/$BASENAME in configs/base.yaml"
  else
    echo "no sha256 recorded yet. file=$BASENAME sha256=$ACTUAL"
    echo "run: scripts/fetch_data.sh --record   to record it"
  fi
  exit 0
fi

if [ "$ACTUAL" != "$SHA" ]; then
  echo "ERROR: checksum mismatch for $BASENAME" >&2
  echo "  expected $SHA" >&2; echo "  actual   $ACTUAL" >&2
  exit 2
fi
[ -z "$FILENAME" ] || [ "$FILENAME" = "$BASENAME" ] || { echo "ERROR: filename $BASENAME differs from recorded $FILENAME" >&2; exit 2; }
echo "checksum OK: $BASENAME ($SIZE bytes)"
