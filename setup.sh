#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo "→ installing uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
echo "→ uv sync…"
uv sync
echo "→ initialising database…"
DATA_DIR="${DATA_DIR:-./data}" DB_FILE="${DB_FILE:-psyswiss.db}" uv run python -c "
from app import scraper
from pathlib import Path
import os
d = Path(os.environ.get('DATA_DIR', './data')); d.mkdir(parents=True, exist_ok=True)
db = scraper.get_db(d / os.environ.get('DB_FILE', 'psyswiss.db'))
n = len(scraper.ensure_defaults(db)); db.close()
print(f'db ready, {n} saved searches')
"
echo ""
echo "✓ done. Run:  make dev   (then open http://127.0.0.1:8001)"
