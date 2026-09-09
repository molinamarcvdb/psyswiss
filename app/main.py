"""FastAPI app: licensing guide + Swiss psychology jobs tracker."""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import guide, scraper

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("psyswiss")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / os.getenv("DB_FILE", "psyswiss.db")

INTERVAL_HOURS = float(os.getenv("SCRAPE_INTERVAL_HOURS", "12"))
SCRAPE_COOLDOWN_SECS = int(os.getenv("SCRAPE_COOLDOWN_SECS", "1800"))
RUN_ON_STARTUP = os.getenv("RUN_ON_STARTUP", "0") == "1"

scheduler = BackgroundScheduler()


class SearchIn(BaseModel):
    name: str
    term: str = ""
    lang: str = "en"
    pages: int = 2
    active: bool = True


class SearchPatch(BaseModel):
    name: str | None = None
    term: str | None = None
    lang: str | None = None
    pages: int | None = None
    active: bool | None = None


def _cooldown_remaining(db, search_id: int) -> float | None:
    s = scraper.get_search(db, search_id)
    if not s or not s.get("last_run_at"):
        return None
    try:
        from datetime import datetime, timezone as _tz
        last = datetime.fromisoformat(s["last_run_at"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=_tz.utc)
        remaining = SCRAPE_COOLDOWN_SECS - (datetime.now(_tz.utc) - last).total_seconds()
        return remaining if remaining > 0 else None
    except ValueError:
        return None


def run_all_active(force: bool = False) -> dict:
    db = scraper.get_db(DB_PATH)
    try:
        out: dict = {"searches": []}
        for s in scraper.ensure_defaults(db):
            if not s["active"]:
                continue
            if not force and _cooldown_remaining(db, s["id"]):
                out["searches"].append({"search_id": s["id"], "name": s["name"],
                                        "error": "cooldown"})
                continue
            try:
                out["searches"].append(scraper.run_search(db, s))
            except Exception as e:  # noqa: BLE001
                log.exception("scrape failed %s", s["id"])
                out["searches"].append({"search_id": s["id"], "name": s["name"],
                                        "error": str(e)})
        return out
    finally:
        db.close()


def run_one(search_id: int, pages: int | None = None, force: bool = False) -> dict:
    db = scraper.get_db(DB_PATH)
    try:
        s = scraper.get_search(db, search_id)
        if not s:
            return {"error": f"no search {search_id}"}
        if not force and _cooldown_remaining(db, search_id):
            return {"error": "cooldown", "search_id": search_id}
        return scraper.run_search(db, s, pages=pages)
    finally:
        db.close()


app = FastAPI(title="PsySwiss — Swiss psychology jobs + licensing guide")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def _startup():
    db = scraper.get_db(DB_PATH)
    scraper.ensure_defaults(db)
    db.close()
    if os.getenv("DISABLE_SCHEDULER") != "1":
        from functools import partial
        scheduler.add_job(partial(run_all_active, force=True), "interval",
                          hours=INTERVAL_HOURS, id="scrape", replace_existing=True)
        scheduler.start()
    if RUN_ON_STARTUP:
        run_all_active(force=True)


@app.on_event("shutdown")
def _shutdown():
    if scheduler.running:
        scheduler.shutdown()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {})


@app.get("/health")
def health():
    return {"ok": True, "db": str(DB_PATH)}


@app.get("/api/guide")
def api_guide():
    return {"steps": guide.STEPS, "sections": guide.SECTIONS,
            "sources": guide.SOURCES, "portals": guide.PORTALS}


@app.get("/api/searches")
def api_searches():
    db = scraper.get_db(DB_PATH)
    try:
        return scraper.ensure_defaults(db)
    finally:
        db.close()


@app.post("/api/searches")
def api_create(body: SearchIn):
    db = scraper.get_db(DB_PATH)
    try:
        if body.lang not in ("en", "de", "fr", "it"):
            return JSONResponse({"error": "lang must be en|de|fr|it"}, status_code=400)
        return scraper.create_search(db, scraper.Search(
            name=body.name[:120], term=body.term[:120], lang=body.lang,
            pages=max(1, min(10, body.pages)), active=body.active)).__dict__
    finally:
        db.close()


@app.patch("/api/searches/{search_id}")
def api_update(search_id: int, body: SearchPatch):
    db = scraper.get_db(DB_PATH)
    try:
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        s = scraper.update_search(db, search_id, fields)
        return s or JSONResponse({"error": "not found"}, status_code=404)
    finally:
        db.close()


@app.delete("/api/searches/{search_id}")
def api_delete(search_id: int):
    db = scraper.get_db(DB_PATH)
    try:
        scraper.delete_search(db, search_id)
        return {"ok": True}
    finally:
        db.close()


@app.post("/api/scrape")
def trigger_scrape(search_id: int | None = Query(None), pages: int | None = Query(None),
                   force: bool = Query(False)):
    if search_id is not None:
        return JSONResponse(run_one(search_id, pages, force=force))
    return JSONResponse(run_all_active(force=force))


@app.get("/api/runs")
def api_runs(limit: int = Query(20, ge=1, le=100)):
    db = scraper.get_db(DB_PATH)
    try:
        return [dict(r) for r in db.execute(
            "SELECT r.*, s.name AS search_name FROM runs r"
            " LEFT JOIN searches s ON s.id=r.search_id"
            " ORDER BY r.id DESC LIMIT ?", (limit,))]
    finally:
        db.close()


def _latest(search_id: int):
    db = scraper.get_db(DB_PATH)
    try:
        return scraper.latest_two(db, search_id)
    finally:
        db.close()


@app.get("/api/changes")
def changes(search_id: int = Query(...)):
    db = scraper.get_db(DB_PATH)
    try:
        latest, prev = scraper.latest_two(db, search_id)
        if not latest:
            return {"detail": "no snapshots yet — POST /api/scrape first"}
        return scraper.diff_snapshots(db, search_id, latest, prev)
    finally:
        db.close()


@app.get("/api/listings")
def listings(search_id: int = Query(...), q: str = Query(""),
             type_: str = Query("", alias="type"), sort: str = Query("newest"),
             limit: int = Query(200, ge=1, le=500), count_only: bool = Query(False)):
    db = scraper.get_db(DB_PATH)
    try:
        latest, _ = scraper.latest_two(db, search_id)
        if not latest:
            return {"count": 0} if count_only else []
        sql = "SELECT * FROM snapshots WHERE search_id=? AND scraped_at=?"
        args: list = [search_id, latest]
        if q:
            sql += " AND (title LIKE ? OR company LIKE ? OR city LIKE ? OR description LIKE ?)"
            args += [f"%{q}%"] * 4
        if type_:
            sql += " AND employment_type=?"
            args.append(type_)
        if count_only:
            return {"count": db.execute(f"SELECT COUNT(*) c FROM ({sql})", args).fetchone()["c"]}
        sql += " ORDER BY posted_date DESC" if sort == "newest" else " ORDER BY title"
        sql += " LIMIT ?"
        args.append(limit)
        return [dict(r) for r in db.execute(sql, args)]
    finally:
        db.close()


@app.get("/api/facets")
def facets(search_id: int = Query(...)):
    db = scraper.get_db(DB_PATH)
    try:
        latest, _ = scraper.latest_two(db, search_id)
        if not latest:
            return {"detail": "no snapshots yet"}
        scope = "search_id=? AND scraped_at=?"
        args = [search_id, latest]
        types = [dict(r) for r in db.execute(
            f"SELECT employment_type AS value, COUNT(*) n FROM snapshots WHERE {scope}"
            " AND employment_type<>'' GROUP BY 1 ORDER BY n DESC", args)]
        cities = [dict(r) for r in db.execute(
            f"SELECT city AS value, COUNT(*) n FROM snapshots WHERE {scope}"
            " AND city<>'' GROUP BY 1 ORDER BY n DESC LIMIT 25", args)]
        total = db.execute(f"SELECT COUNT(*) c FROM snapshots WHERE {scope}", args).fetchone()["c"]
        return {"types": types, "cities": cities, "total": total}
    finally:
        db.close()


@app.get("/api/stats")
def stats(search_id: int = Query(...)):
    db = scraper.get_db(DB_PATH)
    try:
        latest, prev = scraper.latest_two(db, search_id)
        if not latest:
            return {"detail": "no snapshots yet"}
        total = db.execute(
            "SELECT COUNT(*) c FROM snapshots WHERE search_id=? AND scraped_at=?",
            (search_id, latest)).fetchone()["c"]
        by_type = [dict(r) for r in db.execute(
            "SELECT employment_type, COUNT(*) n FROM snapshots"
            " WHERE search_id=? AND scraped_at=? GROUP BY 1 ORDER BY n DESC",
            (search_id, latest))]
        diff = scraper.diff_snapshots(db, search_id, latest, prev)
        snaps = db.execute(
            "SELECT scraped_at, COUNT(*) n FROM snapshots WHERE search_id=?"
            " GROUP BY 1 ORDER BY 1", (search_id,)).fetchall()
        runs = [dict(r) for r in db.execute(
            "SELECT * FROM runs WHERE search_id=? ORDER BY id DESC LIMIT 10", (search_id,))]
        return {"latest": latest, "prev": prev, "total": total, "by_type": by_type,
                "new": len(diff["new"]), "returning": len(diff["returning"]),
                "removed": len(diff["removed_confirmed"]),
                "removed_watch": len(diff["removed_watch"]),
                "trend": [{"scraped_at": r["scraped_at"], "n": r["n"]} for r in snaps],
                "runs": runs}
    finally:
        db.close()


@app.get("/api/job/{ext_id}")
def job_detail(ext_id: str, search_id: int = Query(...)):
    db = scraper.get_db(DB_PATH)
    try:
        latest, _ = scraper.latest_two(db, search_id)
        rows = db.execute(
            "SELECT * FROM snapshots WHERE search_id=? AND ext_id=? ORDER BY scraped_at",
            (search_id, ext_id)).fetchall()
        pts = [dict(r) for r in rows]
        cur = pts[-1] if pts else None
        if latest and (not cur or cur["scraped_at"] != latest):
            cur = db.execute(
                "SELECT * FROM snapshots WHERE search_id=? AND scraped_at=? AND ext_id=?",
                (search_id, latest, ext_id)).fetchone()
            cur = dict(cur) if cur else (pts[-1] if pts else None)
        return {"job": cur, "sightings": len(pts),
                "first_seen": pts[0]["scraped_at"] if pts else None,
                "last_seen": pts[-1]["scraped_at"] if pts else None}
    finally:
        db.close()
