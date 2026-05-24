"""Gridded heatmap version: colour-coded per metric, intensity by density."""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from mplsoccer import Pitch

from socceraction.data.opta.parsers import WhoScoredParser
from socceraction.data.opta.loader import _eventtypesdf
from socceraction.spadl.opta import convert_to_actions
import socceraction.spadl as spadl
from pipeline.xt import load_xt, add_xt

# ── Constants ────────────────────────────────────────────────────────
OUT   = Path("out")
CACHE = Path.home() / "soccerdata/data/WhoScored/events/GER-Bundesliga_2526"

KANE_ID    = 83532
OLISE_ID   = 371281
DIAZ_ID    = 377168
MUSIALA_ID = 395252

BG          = "#0e1117"
PITCH_LINE  = "#2a3340"
TEXT_PRIMARY= "#f5f5f5"
TEXT_DIM    = "#7c8794"

COL_OLISE   = "#ef4444"
COL_DIAZ    = "#10b981"
COL_MUSIALA = "#facc15"
COL_PA      = "#22d3ee"
COL_Z14     = "#a855f7"
COL_BTW     = "#f59e0b"
COL_DEEP    = "#64748b"

PLAYERS = {
    OLISE_ID:   dict(name="Olise",   colour=COL_OLISE,   short="O"),
    DIAZ_ID:    dict(name="Díaz",    colour=COL_DIAZ,    short="D"),
    MUSIALA_ID: dict(name="Musiala", colour=COL_MUSIALA, short="M"),
}

GRID = (16, 11)  # like the xT heatmaps

# ── Data load ────────────────────────────────────────────────────────
print("Loading cached match data...")
xt_model = load_xt()
kane_touches = []
player_actions = {pid: [] for pid in PLAYERS}

for f in sorted(CACHE.glob("*.json")):
    try:
        raw = json.loads(f.read_text())
        home_name = raw["home"].get("name","")
        away_name = raw["away"].get("name","")
        if "Bayern" not in home_name and "Bayern" not in away_name:
            continue
        home_id = int(raw["home"]["teamId"])
        team_id = home_id if "Bayern" in home_name else int(raw["away"]["teamId"])
        is_home = (team_id == home_id)

        parser = WhoScoredParser(str(f), competition_id="GER-Bundesliga",
                                 season_id="2526", game_id=int(f.stem))
        df_ev = (pd.DataFrame.from_dict(parser.extract_events(), orient="index")
                 .merge(_eventtypesdf, on="type_id", how="left")
                 .reset_index(drop=True))
        actions = convert_to_actions(df_ev, home_team_id=home_id)
        actions = spadl.add_names(actions)
        actions = add_xt(actions, xt_model)
        team_acts = actions[actions["team_id"] == team_id]

        for pid in PLAYERS:
            pl = team_acts[team_acts["player_id"] == pid]
            prog = pl[
                pl["type_name"].isin(["dribble","pass","cross"]) &
                pl["result_name"].eq("success") &
                (pl["xT_value"] > 0.005)
            ]
            player_actions[pid].append(prog)

        for ev in raw["events"]:
            if str(ev.get("playerId","")) != str(KANE_ID): continue
            if not ev.get("isTouch", False): continue
            x_raw, y_raw = ev.get("x"), ev.get("y")
            if x_raw is None or y_raw is None: continue
            if is_home:
                xp, yp = x_raw*105/100, y_raw*68/100
            else:
                xp, yp = (100-x_raw)*105/100, (100-y_raw)*68/100
            kane_touches.append({"x": xp, "y": yp})
    except Exception:
        continue

kane_df = pd.DataFrame(kane_touches)

def zone(row):
    x, y = row["x"], row["y"]
    if x > 88.5 and 13.84 <= y <= 54.16: return "PA"
    if 70 <= x <= 88.5 and 24.5 <= y <= 43.5: return "Z14"
    if 50 <= x <= 88.5: return "BTW"
    return "DEEP"
kane_df["zone"] = kane_df.apply(zone, axis=1)
player_dfs = {pid: pd.concat(frames, ignore_index=True)
              for pid, frames in player_actions.items()}

print(f"Kane touches: {len(kane_df)} | "
      f"PA={sum(kane_df.zone=='PA')} Z14={sum(kane_df.zone=='Z14')} "
      f"BTW={sum(kane_df.zone=='BTW')} DEEP={sum(kane_df.zone=='DEEP')}")
for pid, info in PLAYERS.items():
    print(f"  {info['name']}: {len(player_dfs[pid])} progressive actions")

# ── Helpers ──────────────────────────────────────────────────────────
def make_pitch(half: bool = False):
    return Pitch(pitch_type="custom", pitch_length=105, pitch_width=68,
                 pitch_color=BG, line_color=PITCH_LINE, linewidth=1.2,
                 goal_type="box", half=half)

def style_axes(ax, pitch):
    pitch.draw(ax=ax)
    for s in ax.spines.values(): s.set_visible(False)

def alpha_cmap(colour: str) -> LinearSegmentedColormap:
    """Colormap from fully-transparent → fully-opaque at `colour`."""
    rgb = mcolors.to_rgb(colour)
    return LinearSegmentedColormap.from_list(
        f"alpha_{colour}",
        [(*rgb, 0.0), (*rgb, 0.45), (*rgb, 0.85), (*rgb, 1.0)],
        N=256,
    )

def grid_layer(ax, pitch, x, y, colour, percentile_floor=55,
               edgecolor=BG, linewidth=0.5):
    """Render a binned-grid heatmap for these (x,y) points in `colour`.
    Cells below `percentile_floor` of nonzero values are masked transparent."""
    if len(x) < 4: return
    bs = pitch.bin_statistic(x, y, statistic="count", bins=GRID)
    vals = bs["statistic"].astype(float)
    nonzero = vals[vals > 0]
    if len(nonzero) == 0: return
    floor = np.percentile(nonzero, percentile_floor)
    masked = np.where(vals < floor, np.nan, vals)
    bs["statistic"] = masked
    pitch.heatmap(bs, ax=ax, cmap=alpha_cmap(colour),
                  edgecolors=edgecolor, linewidth=linewidth, zorder=3)

def add_zone_box(ax, x, y, w, h, color, label):
    ax.add_patch(patches.Rectangle((x,y), w, h, linewidth=1.6,
                                   edgecolor=color, facecolor="none",
                                   alpha=0.75, zorder=5, linestyle="--"))
    ax.text(x + w/2, y - 1.8, label, color=color,
            fontsize=8.5, fontweight="bold", ha="center",
            alpha=0.9, zorder=6)

def add_pitch_orientation(ax):
    ax.annotate("", xy=(72, -3), xytext=(33, -3),
                arrowprops=dict(arrowstyle="-|>", color=TEXT_DIM, lw=0.9),
                annotation_clip=False)
    ax.text(52.5, -5, "Direction of attack", color=TEXT_DIM,
            fontsize=8, ha="center", style="italic")

# ════════════════════════════════════════════════════════════════════
# IMAGE 1: Kane Touch Zones — gridded, per-zone colour
# ════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 8.5), facecolor=BG)
pitch = make_pitch()
style_axes(ax, pitch)

deep = kane_df[kane_df.zone=="DEEP"]
btw  = kane_df[kane_df.zone=="BTW"]
z14  = kane_df[kane_df.zone=="Z14"]
pa   = kane_df[kane_df.zone=="PA"]

# Layer order: deep → btw → z14 → pa (least to most attacking)
grid_layer(ax, pitch, deep["x"], deep["y"], COL_DEEP, percentile_floor=50)
grid_layer(ax, pitch, btw["x"],  btw["y"],  COL_BTW,  percentile_floor=45)
grid_layer(ax, pitch, z14["x"],  z14["y"],  COL_Z14,  percentile_floor=30)
grid_layer(ax, pitch, pa["x"],   pa["y"],   COL_PA,   percentile_floor=30)

add_zone_box(ax, 88.5, 13.84, 16.5, 40.32, COL_PA,  "PENALTY AREA")
add_zone_box(ax, 70.0, 24.50, 18.5, 19.0,  COL_Z14, "ZONE 14")

# Title
fig.text(0.05, 0.96, "HARRY KANE", color=TEXT_PRIMARY,
         fontsize=22, fontweight="bold")
fig.text(0.05, 0.925,
         "Touch Density Grid by Zone  ·  Bundesliga 25/26  ·  33 matches",
         color=TEXT_DIM, fontsize=11)

panel = [
    ("1140",                     "Total touches",       TEXT_PRIMARY),
    (f"{len(pa)}",   "Penalty area",  COL_PA),
    (f"{len(z14)}",  "Zone 14",       COL_Z14),
    (f"{len(btw)}",  "Between lines", COL_BTW),
    (f"{len(deep)}", "Deep build-up", COL_DEEP),
]
for i, (val, lbl, col) in enumerate(panel):
    y = 0.96 - i * 0.045
    fig.text(0.74, y,        val, color=col,        fontsize=15, fontweight="bold")
    fig.text(0.80, y+0.005, lbl, color=TEXT_DIM,   fontsize=10)

fig.text(0.05, 0.04,
         "Each colour grid = touch count in that zone category. "
         "Darker cell = more touches.",
         color=TEXT_DIM, fontsize=9, style="italic")

add_pitch_orientation(ax)
plt.subplots_adjust(left=0.04, right=0.98, top=0.86, bottom=0.10)
fig.savefig(OUT / "kane_touch_zones_clean.png", dpi=200,
            facecolor=fig.get_facecolor(), bbox_inches="tight")
plt.close()
print("Saved → out/kane_touch_zones_clean.png")

# ════════════════════════════════════════════════════════════════════
# IMAGE 2: Wide Creators → Kane — attacking half, full chain
# ════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 11), facecolor=BG)
pitch = make_pitch(half=True)
style_axes(ax, pitch)

# Per-player progression-endpoint grids (wide-feed origins of the chain)
for pid, info in PLAYERS.items():
    df = player_dfs[pid].dropna(subset=["end_x","end_y"])
    grid_layer(ax, pitch, df["end_x"], df["end_y"],
               info["colour"], percentile_floor=55)

# Kane chain — between-lines (amber bridge) → Z14 → Penalty area
grid_layer(ax, pitch, btw["x"], btw["y"], COL_BTW, percentile_floor=60)
grid_layer(ax, pitch, z14["x"], z14["y"], COL_Z14, percentile_floor=25)
grid_layer(ax, pitch, pa["x"],  pa["y"],  COL_PA,  percentile_floor=25)

add_zone_box(ax, 88.5, 13.84, 16.5, 40.32, COL_PA,  "PENALTY AREA")
add_zone_box(ax, 70.0, 24.50, 18.5, 19.0,  COL_Z14, "ZONE 14")

# Player position markers (xT-weighted creation centroids)
for pid, info in PLAYERS.items():
    df = player_dfs[pid].dropna(subset=["start_x","start_y"])
    if df.empty: continue
    w  = df["xT_value"].clip(lower=0.001)
    cx = (df["start_x"]*w).sum() / w.sum()
    cy = (df["start_y"]*w).sum() / w.sum()
    # Skip markers that fall outside the half-pitch view
    if cx < 52.5: continue
    ax.scatter(cx, cy, s=380, color=info["colour"],
               edgecolors=BG, linewidths=2.4, zorder=8)
    ax.text(cx, cy, info["short"], color=BG, fontsize=15,
            fontweight="bold", ha="center", va="center", zorder=9)

# Title
fig.text(0.05, 0.965, "BAYERN BUILD KANE'S ENVIRONMENT",
         color=TEXT_PRIMARY, fontsize=22, fontweight="bold")
fig.text(0.05, 0.935,
         "Wide creators → Kane link → Kane finish  ·  the full chain in attacking half",
         color=TEXT_DIM, fontsize=11)

legend_elements = [
    Line2D([0],[0], marker="s", color="none",
           markerfacecolor=COL_OLISE,   markersize=13,
           label=f"Olise progressions END here ({len(player_dfs[OLISE_ID])})"),
    Line2D([0],[0], marker="s", color="none",
           markerfacecolor=COL_DIAZ,    markersize=13,
           label=f"Díaz progressions END here ({len(player_dfs[DIAZ_ID])})"),
    Line2D([0],[0], marker="s", color="none",
           markerfacecolor=COL_MUSIALA, markersize=13,
           label=f"Musiala progressions END here ({len(player_dfs[MUSIALA_ID])})"),
    Line2D([0],[0], marker="s", color="none",
           markerfacecolor=COL_BTW,     markersize=13,
           label=f"Kane between-lines link ({len(btw)})"),
    Line2D([0],[0], marker="s", color="none",
           markerfacecolor=COL_Z14,     markersize=13,
           label=f"Kane zone 14 ({len(z14)})"),
    Line2D([0],[0], marker="s", color="none",
           markerfacecolor=COL_PA,      markersize=13,
           label=f"Kane penalty area ({len(pa)})"),
]
ax.legend(handles=legend_elements, loc="upper left",
          fontsize=10, framealpha=0.0, labelcolor=TEXT_PRIMARY,
          handlelength=1.2, borderpad=1, handletextpad=0.7,
          bbox_to_anchor=(-0.02, 1.02))

fig.text(0.05, 0.04,
         "The chain reads bottom-up: red/green/yellow grids = wide-creator landing zones.  "
         "Amber → purple → cyan = Kane's link, occupy, finish sequence.",
         color=TEXT_DIM, fontsize=9.5, style="italic")

# Half-pitch direction arrow (compact, pointing right)
ax.annotate("", xy=(98, -2), xytext=(78, -2),
            arrowprops=dict(arrowstyle="-|>", color=TEXT_DIM, lw=0.9),
            annotation_clip=False)
ax.text(88, -4, "Attacking direction", color=TEXT_DIM,
        fontsize=8.5, ha="center", style="italic")

plt.subplots_adjust(left=0.04, right=0.98, top=0.88, bottom=0.10)
fig.savefig(OUT / "wide_creators_kane_clean.png", dpi=200,
            facecolor=fig.get_facecolor(), bbox_inches="tight")
plt.close()
print("Saved → out/wide_creators_kane_clean.png")
