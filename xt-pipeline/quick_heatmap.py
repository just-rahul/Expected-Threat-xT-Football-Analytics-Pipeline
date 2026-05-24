"""Aggregate xT heatmap — reads cached event JSON directly.
No schedule re-fetch. No Chrome. Runs in seconds."""
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from socceraction.data.opta.parsers import WhoScoredParser
from socceraction.spadl.opta import convert_to_actions
import socceraction.spadl as spadl
from pipeline.xt import load_xt, add_xt

CACHE = Path.home() / "soccerdata/data/WhoScored/events/GER-Bundesliga_2526"
OUT   = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

TEAM        = "Bayern Munich"
TEAM_SEARCH = "Bayern"   # partial match on the name stored in JSON

xt_model = load_xt()
all_actions = []

event_files = sorted(CACHE.glob("*.json"))
print(f"Processing {len(event_files)} cached match files...")

# Also need the _eventtypesdf that soccerdata uses internally
from socceraction.data.opta.loader import _eventtypesdf

for f in event_files:
    try:
        raw = json.loads(f.read_text())
        home_id   = int(raw["home"]["teamId"])
        home_name = raw["home"].get("name", "")
        away_id   = int(raw["away"]["teamId"])
        away_name = raw["away"].get("name", "")

        if TEAM_SEARCH in home_name:
            team_id = home_id
        elif TEAM_SEARCH in away_name:
            team_id = away_id
        else:
            continue  # Bayern not in this match

        parser = WhoScoredParser(
            str(f),
            competition_id="GER-Bundesliga",
            season_id="2526",
            game_id=int(f.stem),
        )
        df_events = (
            pd.DataFrame.from_dict(parser.extract_events(), orient="index")
            .merge(_eventtypesdf, on="type_id", how="left")
            .reset_index(drop=True)
        )
        actions = convert_to_actions(df_events, home_team_id=home_id)
        actions = spadl.add_names(actions)
        actions = add_xt(actions, xt_model)
        team_actions = actions[actions["team_id"] == team_id]
        all_actions.append(team_actions)
        print(f"  {f.stem}  {home_name} vs {away_name}  → {len(team_actions)} Bayern actions")

    except Exception as e:
        print(f"  {f.stem} skipped: {e}")

if not all_actions:
    print("No actions loaded.")
    exit(1)

agg = pd.concat(all_actions, ignore_index=True)
pos = agg[agg["xT_value"] > 0]
n   = len(all_actions)
print(f"\n{n} matches | {len(pos):,} positive-xT actions | total Σ xT = {pos['xT_value'].sum():.2f}")

# ── Plot ──────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 8), facecolor="#0d1117")
pitch = Pitch(pitch_type="custom", pitch_length=105, pitch_width=68,
              pitch_color="#0d1117", line_color="#3a3a3a")
pitch.draw(ax=ax)

bin_stat = pitch.bin_statistic(
    pos["start_x"], pos["start_y"],
    values=pos["xT_value"], statistic="sum", bins=(16, 12),
)
hm = pitch.heatmap(bin_stat, ax=ax, cmap="inferno",
                   edgecolors="#0d1117", alpha=0.92)
cbar = plt.colorbar(hm, ax=ax, shrink=0.55, pad=0.02)
cbar.set_label("Σ xT per zone", color="white", fontsize=10)
cbar.ax.yaxis.set_tick_params(color="white")
plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

ax.set_title(
    f"Bayern Munich — Cumulative xT  |  Bundesliga 25/26  |  {n} matches",
    color="white", fontsize=15, pad=14, fontweight="bold",
)
ax.annotate("← Defending          Attacking →", xy=(0.5, -0.03),
            xycoords="axes fraction", color="#888888", fontsize=9, ha="center")

out_path = OUT / "xt_heatmap_season_aggregate.png"
fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"\nSaved → {out_path}")
