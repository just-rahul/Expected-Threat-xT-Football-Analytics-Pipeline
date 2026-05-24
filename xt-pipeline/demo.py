"""Two-match demo: pick first 2 completed Bayern matches, run full pipeline."""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd

from pipeline.scrape import get_scraper, schedule, team_fixtures, safe_read_events_spadl as read_events_spadl
from pipeline.xt import load_xt, add_xt
from pipeline.plot import plot_xt_actions, plot_player_xt_bar

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def main():
    ws = get_scraper("GER-Bundesliga", "2025-2026", headless=True)
    sched = schedule(ws)
    bayern = team_fixtures(sched, "Bayern Munich")
    # Only completed matches (have a stage_id and a date in the past)
    dates = pd.to_datetime(bayern["date"], utc=True)
    bayern = bayern[dates < pd.Timestamp.utcnow()]
    bayern = bayern.head(2)
    print("Demo matches:")
    print(bayern[["home_team", "away_team", "date"]])

    xt_model = load_xt()

    for (_, _, game), row in bayern.iterrows():
        match_id = int(row["game_id"])
        label = f"{row['home_team']} vs {row['away_team']} ({row['date']})"
        print(f"\n--- {label} (match_id={match_id}) ---")
        actions = read_events_spadl(ws, match_id)
        if isinstance(actions, dict):
            actions = next(iter(actions.values()))
        print("Columns:", list(actions.columns))
        actions = add_xt(actions, xt_model)
        # Identify Bayern team_id from row
        bayern_team_id = row["home_team_id"] if row["home_team"] == "Bayern Munich" else row["away_team_id"]
        bayern_actions = actions[actions["team_id"] == bayern_team_id].copy()
        # Add display columns for plotting
        bayern_actions["team_name"] = "Bayern Munich"
        if "player_name" not in bayern_actions.columns:
            bayern_actions["player_name"] = bayern_actions["player_id"].astype(str)
        total = bayern_actions["xT_value"].sum()
        print(f"Bayern total xT: {total:.3f}  |  Bayern actions: {len(bayern_actions)}")
        slug = label.replace(" ", "_").replace("/", "-")
        plot_xt_actions(
            bayern_actions,
            f"Bayern xT — {label}",
            str(OUT / f"xt_{slug}.png"),
        )
        plot_player_xt_bar(
            bayern_actions,
            f"Bayern xT by player — {label}",
            str(OUT / f"xt_players_{slug}.png"),
        )

    print(f"\nOutputs in {OUT}")


if __name__ == "__main__":
    main()
