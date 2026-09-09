"""Swiss psychology jobs tracker — jobup.ch scraper + SQLite snapshots.

Pipeline (verified 2026-09-09):
  search pages  https://www.jobup.ch/<lang>/jobs/?term=<q>&page=N
    -> collect /jobs/detail/<uuid>/ links
  detail pages  carry full schema.org JobPosting JSON-LD -> parse it
"""
from __future__ import annotations

import html
import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from scrapling.fetchers import Fetcher
from scrapling.parser import Selector

log = logging.getLogger("psyswiss")

BASE = "https://www.jobup.ch"
DETAIL_RE = re.compile(r"/(?:en|de|fr|it)/jobs/detail/([0-9a-f-]{36})/")


@dataclass
class Job:
    portal: str = "jobup"
    ext_id: str = ""
    title: str = ""
    company: str = ""
    city: str = ""
    postcode: str = ""
    region: str = ""
    employment_type: str = ""
    posted_date: str = ""
    description: str = ""
    url: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class Search:
    id: int | None = None
    name: str = ""
    term: str = ""
    lang: str = "en"  # jobup site language for list pages
    pages: int = 2
    active: bool = True
    created_at: str = ""
    last_run_at: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def list_url(term: str, lang: str = "en", page: int = 1) -> str:
    params = {"term": term}
    if page > 1:
        params["page"] = page
    return f"{BASE}/{lang}/jobs/?{urlencode(params)}"


def collect_detail_ids(term: str, lang: str = "en", max_pages: int = 2,
                       delay: float = 1.5) -> tuple[list[str], int]:
    """Walk search pages, return (detail uuids in order, pages_fetched)."""
    seen: list[str] = []
    known: set[str] = set()
    for pg in range(1, max_pages + 1):
        url = list_url(term, lang, pg)
        page = Fetcher.get(url, impersonate="chrome", stealthy_headers=True, timeout=30)
        if page.status != 200:
            log.warning("list page %d status=%s", pg, page.status)
            break
        hrefs = Selector(page.html_content or "").css("a::attr(href)").getall()
        fresh = 0
        for h in hrefs:
            m = DETAIL_RE.search(h or "")
            if m and m.group(1) not in known:
                known.add(m.group(1))
                seen.append(m.group(1))
                fresh += 1
        log.info("term=%s page=%d +%d ids (total %d)", term, pg, fresh, len(seen))
        if fresh == 0:
            break
        time.sleep(delay)
    return seen, min(pg, max_pages)


def _clean_text(html_blob: str, limit: int = 3000) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html_blob or "")
    text = re.sub(r"</(p|li|ul|ol|h[1-6]|div|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return text[:limit]


def parse_jobposting(html_blob: str, url: str) -> Job | None:
    sel = Selector(html_blob or "")
    for s in sel.css('script[type="application/ld+json"]'):
        try:
            d = json.loads(s.text or "")
        except (TypeError, ValueError):
            continue
        items = d if isinstance(d, list) else [d]
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "JobPosting":
                return _job_from_posting(it, url)
    return None


EMPLOYMENT_LABELS = {
    "FULL_TIME": "Full time", "PART_TIME": "Part time", "CONTRACTOR": "Contract",
    "TEMPORARY": "Temporary", "INTERN": "Internship", "VOLUNTEER": "Volunteer",
    "PER_DIEM": "Per diem", "OTHER": "Other",
}


def _one(v):
    """First non-empty string of a str-or-list JSON-LD value."""
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str) and x.strip():
                return x.strip()
        return ""
    return (v or "").strip() if isinstance(v, str) else ""


def _join(v, sep=", "):
    if isinstance(v, list):
        return sep.join(str(x).strip() for x in v if str(x).strip())
    return (v or "").strip() if isinstance(v, str) else ""


def _job_from_posting(it: dict, url: str) -> Job:
    m = DETAIL_RE.search(url or "")
    org = it.get("hiringOrganization") or {}
    loc = it.get("jobLocation") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = loc.get("address") or {} if isinstance(loc, dict) else {}
    if isinstance(addr, list):
        addr = addr[0] if addr else {}
    etype = _join(it.get("employmentType"))
    etype = ", ".join(EMPLOYMENT_LABELS.get(p.strip(), p.strip())
                      for p in etype.split(",") if p.strip())
    return Job(
        ext_id=m.group(1) if m else _one(it.get("identifier")),
        title=_one(it.get("title")),
        company=(org.get("name") or "").strip() if isinstance(org, dict) else "",
        city=_one(addr.get("addressLocality") or addr.get("addressRegion")),
        postcode=_one(addr.get("postalCode")),
        region=_one(addr.get("addressRegion")),
        employment_type=etype,
        posted_date=_one(it.get("datePosted"))[:19],
        description=_clean_text(_one(it.get("description"))),
        url=url.split("?")[0],
        raw={"skills": it.get("skills"), "industry": it.get("industry"),
             "occupationalCategory": it.get("occupationalCategory")},
    )


def fetch_job(ext_id: str, lang: str = "en") -> Job | None:
    url = f"{BASE}/{lang}/jobs/detail/{ext_id}/"
    page = Fetcher.get(url, impersonate="chrome", stealthy_headers=True, timeout=30)
    if page.status != 200:
        log.warning("detail %s status=%s", ext_id, page.status)
        return None
    return parse_jobposting(page.html_content or "", page.url or url)


def scrape_search(term: str, lang: str = "en", max_pages: int = 2,
                  delay: float = 1.5) -> list[Job]:
    ids, _ = collect_detail_ids(term, lang, max_pages, delay)
    out: list[Job] = []
    for i, ext_id in enumerate(ids):
        try:
            job = fetch_job(ext_id, lang)
            if job and job.title:
                out.append(job)
            else:
                log.warning("detail %s: no JobPosting parsed", ext_id)
        except Exception as e:  # noqa: BLE001 — one bad page must not kill the run
            log.warning("detail %s failed: %s", ext_id, e)
        if i < len(ids) - 1:
            time.sleep(delay)
    # de-dupe
    seen, uniq = set(), []
    for j in out:
        if j.ext_id not in seen:
            seen.add(j.ext_id)
            uniq.append(j)
    return uniq


# ---------------- storage ----------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  term TEXT NOT NULL DEFAULT '',
  lang TEXT NOT NULL DEFAULT 'en',
  pages INTEGER NOT NULL DEFAULT 2,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  last_run_at TEXT
);
CREATE TABLE IF NOT EXISTS snapshots(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  search_id INTEGER,
  portal TEXT NOT NULL,
  ext_id TEXT NOT NULL,
  title TEXT,
  company TEXT,
  city TEXT,
  postcode TEXT,
  region TEXT,
  employment_type TEXT,
  posted_date TEXT,
  description TEXT,
  url TEXT,
  scraped_at TEXT NOT NULL,
  UNIQUE(portal, ext_id, scraped_at)
);
CREATE INDEX IF NOT EXISTS idx_job_lookup ON snapshots(portal, ext_id, scraped_at);
CREATE INDEX IF NOT EXISTS idx_job_search ON snapshots(search_id, scraped_at);
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  search_id INTEGER, started_at TEXT, finished_at TEXT,
  pages INTEGER, listings INTEGER, new_count INTEGER,
  removed_count INTEGER
);
"""


def get_db(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    db.commit()
    return db


def create_search(db: sqlite3.Connection, s: Search) -> Search:
    s.created_at = s.created_at or _now()
    cur = db.execute(
        "INSERT INTO searches(name,term,lang,pages,active,created_at) VALUES(?,?,?,?,?,?)",
        (s.name, s.term, s.lang, s.pages, int(s.active), s.created_at))
    db.commit()
    s.id = cur.lastrowid
    return s


def list_searches(db: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM runs r WHERE r.search_id=s.id) AS run_count,"
        " (SELECT MAX(started_at) FROM runs r WHERE r.search_id=s.id) AS last_snapshot"
        " FROM searches s ORDER BY s.id")]


def get_search(db: sqlite3.Connection, search_id: int) -> dict | None:
    row = db.execute("SELECT * FROM searches WHERE id=?", (search_id,)).fetchone()
    return dict(row) if row else None


def update_search(db: sqlite3.Connection, search_id: int, fields: dict) -> dict | None:
    allowed = {"name", "term", "lang", "pages", "active"}
    sets, args = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            args.append(int(v) if k == "active" else v)
    if sets:
        args.append(search_id)
        db.execute(f"UPDATE searches SET {', '.join(sets)} WHERE id=?", args)
        db.commit()
    return get_search(db, search_id)


def delete_search(db: sqlite3.Connection, search_id: int) -> None:
    db.execute("DELETE FROM snapshots WHERE search_id=?", (search_id,))
    db.execute("DELETE FROM runs WHERE search_id=?", (search_id,))
    db.execute("DELETE FROM searches WHERE id=?", (search_id,))
    db.commit()


def ensure_defaults(db: sqlite3.Connection) -> list[dict]:
    """Seed defaults ONLY on a truly fresh DB (nothing ever stored)."""
    if not list_searches(db):
        used = (db.execute("SELECT COUNT(*) c FROM snapshots").fetchone()["c"] > 0
                or db.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] > 0)
        if not used:
            for name, term in (("Psychotherapie (DE)", "psychotherapie"),
                               ("Psychology (EN)", "psychology")):
                create_search(db, Search(name=name, term=term, lang="en", pages=2))
    return list_searches(db)


def store_snapshot(db: sqlite3.Connection, jobs: list[Job],
                   search_id: int) -> str:
    ts = _now()
    db.executemany(
        """INSERT OR IGNORE INTO snapshots(search_id,portal,ext_id,title,company,city,
        postcode,region,employment_type,posted_date,description,url,scraped_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(search_id, j.portal, j.ext_id, j.title, j.company, j.city, j.postcode,
          j.region, j.employment_type, j.posted_date, j.description, j.url, ts)
         for j in jobs])
    db.commit()
    return ts


def latest_two(db: sqlite3.Connection, search_id: int) -> tuple[str | None, str | None]:
    rows = db.execute(
        "SELECT DISTINCT scraped_at FROM snapshots WHERE search_id=? ORDER BY scraped_at DESC LIMIT 2",
        (search_id,)).fetchall()
    vals = [r["scraped_at"] for r in rows] + [None, None]
    return vals[0], vals[1]


def _rows(db: sqlite3.Connection, search_id: int, ts: str) -> dict:
    return {r["ext_id"]: dict(r) for r in db.execute(
        "SELECT * FROM snapshots WHERE search_id=? AND scraped_at=?", (search_id, ts))}


def seen_before(db: sqlite3.Connection, search_id: int, ext_id: str, before_ts: str) -> bool:
    return db.execute(
        "SELECT COUNT(*) c FROM snapshots WHERE search_id=? AND ext_id=? AND scraped_at<?",
        (search_id, ext_id, before_ts)).fetchone()["c"] > 0


def diff_snapshots(db: sqlite3.Connection, search_id: int,
                   latest_ts: str, prev_ts: str | None) -> dict:
    """History-aware diff: new = never seen before; gone = missing 2 runs in a row."""
    latest = _rows(db, search_id, latest_ts)
    prev = _rows(db, search_id, prev_ts) if prev_ts else {}
    new, returning = [], []
    for k, v in latest.items():
        if k not in prev:
            (returning if seen_before(db, search_id, k, prev_ts or latest_ts) else new).append(v)
    gone_confirmed, gone_watch = [], []
    for k, v in prev.items():
        if k not in latest:
            older = db.execute(
                "SELECT DISTINCT scraped_at FROM snapshots WHERE search_id=? AND scraped_at<?"
                " ORDER BY scraped_at DESC LIMIT 1",
                (search_id, prev_ts or latest_ts)).fetchone()
            still = seen_before(db, search_id, k, older["scraped_at"]) if older else True
            (gone_watch if still else gone_confirmed).append(v)
    return {"new": new, "returning": returning,
            "removed": gone_confirmed + gone_watch,
            "removed_confirmed": gone_confirmed, "removed_watch": gone_watch,
            "prev_ts": prev_ts, "latest_ts": latest_ts}


def run_search(db: sqlite3.Connection, search: dict, pages: int | None = None,
               delay: float = 1.5) -> dict:
    started = _now()
    jobs = scrape_search(search["term"], search.get("lang", "en") or "en",
                         max_pages=pages or search.get("pages", 2) or 2, delay=delay)
    ts = store_snapshot(db, jobs, search["id"])
    _, prev = latest_two(db, search["id"])
    # latest_two returns (latest=ts, prev); recompute properly:
    rows = db.execute(
        "SELECT DISTINCT scraped_at FROM snapshots WHERE search_id=? ORDER BY scraped_at DESC LIMIT 2",
        (search["id"],)).fetchall()
    latest_ts = rows[0]["scraped_at"]
    prev_ts = rows[1]["scraped_at"] if len(rows) > 1 else None
    diff = diff_snapshots(db, search["id"], latest_ts, prev_ts)
    finished = _now()
    db.execute(
        "INSERT INTO runs(search_id,started_at,finished_at,pages,listings,new_count,removed_count)"
        " VALUES(?,?,?,?,?,?,?)",
        (search["id"], started, finished, pages or search.get("pages", 2),
         len(jobs), len(diff["new"]), len(diff["removed_confirmed"])))
    db.execute("UPDATE searches SET last_run_at=? WHERE id=?", (finished, search["id"]))
    db.commit()
    _ = prev  # (kept for clarity of the two-step lookup above)
    return {"search_id": search["id"], "name": search["name"], "listings": len(jobs),
            "snapshot_at": ts, "new": len(diff["new"]),
            "returning": len(diff["returning"]),
            "removed": len(diff["removed_confirmed"]),
            "removed_watch": len(diff["removed_watch"])}
