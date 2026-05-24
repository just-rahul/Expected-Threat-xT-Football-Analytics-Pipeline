"""WhoScored scraping via soccerdata."""
from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd
import soccerdata as sd

CACHE = Path.home() / "soccerdata" / "data" / "WhoScored"


def clean_cache():
    """Strip <html><body>...</body></html> wrapper from cached JSON files.
    soccerdata 1.8.8 sometimes saves the wrapped page instead of raw JSON."""
    for sub in ["matches", "events", "previews"]:
        d = CACHE / sub
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                txt = f.read_text(errors="ignore")
            except Exception:
                continue
            if txt.startswith("<"):
                m = re.search(r"(\{.*\})", txt, re.DOTALL)
                if m:
                    try:
                        json.loads(m.group(1))
                        f.write_text(m.group(1))
                    except Exception:
                        f.unlink(missing_ok=True)
                else:
                    f.unlink(missing_ok=True)


def get_scraper(league: str, season: str, headless: bool = True) -> sd.WhoScored:
    return sd.WhoScored(leagues=league, seasons=season, headless=headless)


def schedule(ws: sd.WhoScored, max_retries: int = 8) -> pd.DataFrame:
    last_err = None
    for _ in range(max_retries):
        try:
            return ws.read_schedule()
        except json.JSONDecodeError as e:
            last_err = e
            clean_cache()
    raise RuntimeError(f"schedule failed after retries: {last_err}")


def safe_read_events_spadl(ws: sd.WhoScored, match_id: int, max_retries: int = 5):
    last_err = None
    for _ in range(max_retries):
        try:
            return ws.read_events(match_id=match_id, output_fmt="spadl")
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            clean_cache()
    raise RuntimeError(f"events failed after retries: {last_err}")


def team_fixtures(sched: pd.DataFrame, team: str) -> pd.DataFrame:
    mask = sched["home_team"].eq(team) | sched["away_team"].eq(team)
    return sched[mask].copy()


def read_events(ws: sd.WhoScored, match_id: int) -> pd.DataFrame:
    return ws.read_events(match_id=match_id, output_fmt="events")


def read_events_spadl(ws: sd.WhoScored, match_id: int):
    return ws.read_events(match_id=match_id, output_fmt="spadl")
