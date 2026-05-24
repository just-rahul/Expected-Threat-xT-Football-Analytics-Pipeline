"""Full-season pull. Run with: .venv/bin/python run_all.py

Pulls every completed Bayern Munich match in Bundesliga 25-26 and produces
per-match + season-aggregate xT plots.

England WCQ extension: WhoScored doesn't expose World Cup qualifying in
soccerdata's default league dict. To add it:

  1) Open the WhoScored page for the 2026 European WCQ tournament; note the
     `tournamentId`, `regionId` (the URL contains `/regions/<R>/tournaments/<T>`).
  2) Edit ~/soccerdata/config/league_dict.json and add an entry like:
        {
          "INT-WCQ-Europe": {
            "WhoScored": {
              "id": "<tournamentId>",
              "url_id": "<tournamentId>",
              "country": "Europe"
            }
          }
        }
  3) Re-run with `leagues="INT-WCQ-Europe"`, `seasons="2025-2026"`, team="England".

You will likely need to hand-resolve the seasonId since WCQ spans years.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from pipeline.scrape import (
    get_scraper, schedule, team_fixtures, safe_read_events_spadl as read_events_spadl,
)
from pipeline.xt import load_xt, add_xt
from pipeline.plot import plot_xt_actions, plot_player_xt_bar

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def run(league: str, season: str, team: str):
    ws = get_scraper(league, season, headless=True)
    sched = schedule(ws)
    fixtures = team_fixtures(sched, team)
    dates = pd.to_datetime(fixtures["date"], utc=True)
    fixtures = fixtures[dates < pd.Timestamp.utcnow()]
    print(f"{team}: {len(fixtures)} completed matches in {league} {season}")

    xt_model = load_xt()
    season_actions = []

    for (_, _, _), row in fixtures.iterrows():
        match_id = int(row["game_id"])
        label = f"{row['home_team']} vs {row['away_team']} ({row['date']})"
        print(f"--- {label} (match_id={match_id}) ---", flush=True)
        try:
            actions = read_events_spadl(ws, match_id)
            if isinstance(actions, dict):
                actions = next(iter(actions.values()))
            actions = add_xt(actions, xt_model)
            team_id = row["home_team_id"] if row["home_team"] == team else row["away_team_id"]
            team_actions = actions[actions["team_id"] == team_id].copy()
            team_actions["team_name"] = team
            if "player_name" not in team_actions.columns:
                team_actions["player_name"] = team_actions.get("player", team_actions["player_id"]).astype(str)

            slug = label.replace(" ", "_").replace("/", "-").replace(":", "-")
            plot_xt_actions(team_actions, f"{team} xT — {label}", str(OUT / f"xt_{slug}.png"))
            season_actions.append(team_actions)
        except Exception as e:
            print(f"  skipped: {type(e).__name__}: {e}")
            continue

    if season_actions:
        agg = pd.concat(season_actions, ignore_index=True)
        plot_xt_actions(agg, f"{team} xT — {league} {season} (season)",
                        str(OUT / f"xt_season_{team.replace(' ', '_')}.png"), top_n=80)
        plot_player_xt_bar(agg, f"{team} xT by player — {league} {season}",
                           str(OUT / f"xt_players_season_{team.replace(' ', '_')}.png"))
        agg.to_parquet(OUT / f"actions_{team.replace(' ', '_')}_{season}.parquet")


if __name__ == "__main__":
    run("GER-Bundesliga", "2025-2026", "Bayern Munich")
    # After adding INT-WCQ-Europe to league_dict.json:
    # run("INT-WCQ-Europe", "2025-2026", "England")
