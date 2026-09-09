"""CLI: scrape / searches / enrich-check for cron use."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DISABLE_SCHEDULER", "1")

from app import main, scraper  # noqa: E402

logging.basicConfig(level=logging.INFO)


def cmd_scrape(args):
    if args.search:
        out = main.run_one(args.search, args.pages, force=args.force)
        print(json.dumps(out, indent=1)[:2000])
        return 0 if "error" not in out else 1
    out = main.run_all_active(force=args.force)
    print(json.dumps(out, indent=1)[:4000])
    return 1 if any("error" in s for s in out["searches"]) else 0


def cmd_searches(_args):
    db = scraper.get_db(main.DB_PATH)
    try:
        print(json.dumps(scraper.list_searches(db), indent=1))
    finally:
        db.close()
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="PsySwiss CLI (cron-friendly)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scrape")
    s.add_argument("--search", type=int, default=None)
    s.add_argument("--pages", type=int, default=None)
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_scrape)
    l = sub.add_parser("searches")
    l.set_defaults(fn=cmd_searches)
    return p


def entry():
    args = build_parser().parse_args()
    raise SystemExit(args.fn(args))


if __name__ == "__main__":
    entry()
