"""Publishable visuals — dark/inferno aesthetic, consistent across all six images."""
from __future__ import annotations
import json
import pickle
from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch

from socceraction.data.opta.parsers import WhoScoredParser
from socceraction.data.opta.loader import _eventtypesdf
from socceraction.spadl.opta import convert_to_actions
import socceraction.spadl as spadl
from pipeline.xt import load_xt, add_xt

# ════════════════════════════════════════════════════════════════════
# DARK THEME TOKENS
# ════════════════════════════════════════════════════════════════════
BG          = "#0d1117"
BG_PANEL    = "#161b22"
PITCH_LINE  = "#3a4150"
TEXT        = "#f0ece4"
TEXT2       = "#b0a89e"
TEXT3       = "#7c8794"
ACCENT      = "#e83050"   # warmer red for dark mode

# Inferno-derived bright colours for grids on dark
COL_BAYERN_HOT  = "#ff8c42"   # warm orange (inferno hot)
COL_ENG_HOT     = "#74b3ff"   # bright sky-blue (cool counterpart)

# Per-player palette, dark-theme tuned (more saturated, brighter)
COL_OLISE_BAY  = "#ff5470"    # right wing creator — Bayern
COL_DIAZ_BAY   = "#22d3ee"    # left wing creator — Bayern (cyan stands out)
COL_MUSIALA    = "#fbbf24"    # central #10

COL_JAMES      = "#ff5470"    # right-side creator — England
COL_RASHFORD   = "#22d3ee"    # left wing — England
COL_BELLINGHAM = "#fbbf24"    # central #10 — England

# Kane zone palette (consistent across both Bayern and England)
COL_PA   = "#34d399"   # emerald
COL_Z14  = "#c084fc"   # violet
COL_BTW  = "#f59e0b"   # amber
COL_DEEP = "#64748b"   # slate

# Typography
mpl.rcParams.update({
    "font.family":      "sans-serif",
    "font.sans-serif":  ["DM Sans", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "axes.titlesize":   16,
    "axes.labelsize":   11,
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
    "savefig.dpi":      220,
})

OUT = Path("out")
CACHE_BAY = Path.home()/"soccerdata/data/WhoScored/events/GER-Bundesliga_2526"
CACHE_ENG = Path.home()/"soccerdata/data/WhoScored/events/INT-WCQ-UEFA_2025"

# ════════════════════════════════════════════════════════════════════
# IDS
# ════════════════════════════════════════════════════════════════════
KANE_ID    = 83532
OLISE_ID   = 371281
DIAZ_ID    = 377168
MUSIALA_ID = 395252

JAMES_ID      = 361330
RASHFORD_ID   = 300299
BELLINGHAM_ID = 379868

ENGLAND_ID = 345

BAY_PLAYERS = {
    OLISE_ID:   dict(name="Olise",   colour=COL_OLISE_BAY,  short="O"),
    DIAZ_ID:    dict(name="Díaz",    colour=COL_DIAZ_BAY,   short="D"),
    MUSIALA_ID: dict(name="Musiala", colour=COL_MUSIALA,    short="M"),
}
ENG_PLAYERS = {
    JAMES_ID:      dict(name="James",      colour=COL_JAMES,      short="J"),
    RASHFORD_ID:   dict(name="Rashford",   colour=COL_RASHFORD,   short="R"),
    BELLINGHAM_ID: dict(name="Bellingham", colour=COL_BELLINGHAM, short="B"),
}

GRID = (16, 11)

# ════════════════════════════════════════════════════════════════════
# DATA — Bayern
# ════════════════════════════════════════════════════════════════════
print("Loading Bayern cached data...")
xt_model = load_xt()
bayern_actions, kane_bay_touches = [], []
bay_player_actions = {pid: [] for pid in BAY_PLAYERS}

for f in sorted(CACHE_BAY.glob("*.json")):
    try:
        raw = json.loads(f.read_text())
        if "Bayern" not in raw["home"].get("name","") and "Bayern" not in raw["away"].get("name",""):
            continue
        home_id = int(raw["home"]["teamId"])
        team_id = home_id if "Bayern" in raw["home"].get("name","") else int(raw["away"]["teamId"])
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
        bayern_actions.append(team_acts)

        for pid in BAY_PLAYERS:
            pl = team_acts[team_acts["player_id"] == pid]
            prog = pl[
                pl["type_name"].isin(["dribble","pass","cross"]) &
                pl["result_name"].eq("success") &
                (pl["xT_value"] > 0.005)
            ]
            bay_player_actions[pid].append(prog)

        for ev in raw["events"]:
            if str(ev.get("playerId","")) != str(KANE_ID): continue
            if not ev.get("isTouch", False): continue
            x_raw, y_raw = ev.get("x"), ev.get("y")
            if x_raw is None or y_raw is None: continue
            xp, yp = (x_raw*105/100, y_raw*68/100) if is_home \
                     else ((100-x_raw)*105/100, (100-y_raw)*68/100)
            kane_bay_touches.append({"x": xp, "y": yp})
    except Exception:
        continue

bayern_pos = pd.concat(bayern_actions, ignore_index=True)
bayern_pos = bayern_pos[bayern_pos["xT_value"] > 0]
kane_bay   = pd.DataFrame(kane_bay_touches)

# ════════════════════════════════════════════════════════════════════
# DATA — England
# ════════════════════════════════════════════════════════════════════
print("Loading England cached data...")
england_actions, kane_eng_touches = [], []
eng_player_actions = {pid: [] for pid in ENG_PLAYERS}

for f in sorted(CACHE_ENG.glob("*.json")):
    try:
        raw = json.loads(f.read_text())
        if raw["home"].get("name") == "England":
            team_id = int(raw["home"]["teamId"]); is_home = True
        elif raw["away"].get("name") == "England":
            team_id = int(raw["away"]["teamId"]); is_home = False
        else:
            continue
        home_id = int(raw["home"]["teamId"])

        parser = WhoScoredParser(str(f), competition_id="INT-WCQ-UEFA",
                                 season_id="2025", game_id=int(f.stem))
        df_ev = (pd.DataFrame.from_dict(parser.extract_events(), orient="index")
                 .merge(_eventtypesdf, on="type_id", how="left")
                 .reset_index(drop=True))
        actions = convert_to_actions(df_ev, home_team_id=home_id)
        actions = spadl.add_names(actions)
        actions = add_xt(actions, xt_model)
        team_acts = actions[actions["team_id"] == team_id]
        england_actions.append(team_acts)

        for pid in ENG_PLAYERS:
            pl = team_acts[team_acts["player_id"] == pid]
            prog = pl[
                pl["type_name"].isin(["dribble","pass","cross"]) &
                pl["result_name"].eq("success") &
                (pl["xT_value"] > 0.005)
            ]
            eng_player_actions[pid].append(prog)

        for ev in raw["events"]:
            if str(ev.get("playerId","")) != str(KANE_ID): continue
            if not ev.get("isTouch", False): continue
            x_raw, y_raw = ev.get("x"), ev.get("y")
            if x_raw is None or y_raw is None: continue
            xp, yp = (x_raw*105/100, y_raw*68/100) if is_home \
                     else ((100-x_raw)*105/100, (100-y_raw)*68/100)
            kane_eng_touches.append({"x": xp, "y": yp})
    except Exception as e:
        print(f"England match {f.stem} error: {e}")
        continue

england_pos = pd.concat(england_actions, ignore_index=True)
england_pos = england_pos[england_pos["xT_value"] > 0]
kane_eng    = pd.DataFrame(kane_eng_touches)

def zone(row):
    x, y = row["x"], row["y"]
    if x > 88.5 and 13.84 <= y <= 54.16: return "PA"
    if 70 <= x <= 88.5 and 24.5 <= y <= 43.5: return "Z14"
    if 50 <= x <= 88.5: return "BTW"
    return "DEEP"

for df in (kane_bay, kane_eng):
    df["zone"] = df.apply(zone, axis=1)

bay_dfs = {pid: pd.concat(frames, ignore_index=True) for pid, frames in bay_player_actions.items()}
eng_dfs = {pid: pd.concat(frames, ignore_index=True) for pid, frames in eng_player_actions.items()}

print(f"\nBayern: {len(bayern_pos):,} pos-xT actions | Kane touches: {len(kane_bay)}")
print(f"England: {len(england_pos):,} pos-xT actions | Kane touches: {len(kane_eng)}")
for pid, info in BAY_PLAYERS.items():
    print(f"  Bay {info['name']}: {len(bay_dfs[pid])} prog actions")
for pid, info in ENG_PLAYERS.items():
    print(f"  Eng {info['name']}: {len(eng_dfs[pid])} prog actions")

# ════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════
def make_pitch(half: bool = False):
    return Pitch(pitch_type="custom", pitch_length=105, pitch_width=68,
                 pitch_color=BG, line_color=PITCH_LINE, linewidth=1.4,
                 goal_type="box", half=half, corner_arcs=True)

def style_axes(ax, pitch):
    pitch.draw(ax=ax)
    for s in ax.spines.values(): s.set_visible(False)

def alpha_cmap(colour: str) -> LinearSegmentedColormap:
    """Dark BG → opaque player colour."""
    rgb = mcolors.to_rgb(colour)
    bg  = mcolors.to_rgb(BG)
    return LinearSegmentedColormap.from_list(
        f"alpha_{colour}",
        [(*bg, 0.0), (*rgb, 0.55), (*rgb, 0.95)],
        N=256,
    )

def grid_layer(ax, pitch, x, y, colour, percentile_floor=55, zorder=3):
    if len(x) < 4: return
    bs = pitch.bin_statistic(x, y, statistic="count", bins=GRID)
    vals = bs["statistic"].astype(float)
    nonzero = vals[vals > 0]
    if len(nonzero) == 0: return
    floor = np.percentile(nonzero, percentile_floor)
    bs["statistic"] = np.where(vals < floor, np.nan, vals)
    pitch.heatmap(bs, ax=ax, cmap=alpha_cmap(colour),
                  edgecolors=BG, linewidth=0.6, zorder=zorder)

def value_grid_layer(ax, pitch, x, y, values, cmap_name="inferno",
                     percentile_floor=15, zorder=3):
    """Sums values per cell, uses inferno-style cmap."""
    if len(x) < 4: return
    bs = pitch.bin_statistic(x, y, values=values, statistic="sum", bins=GRID)
    vals = bs["statistic"].astype(float)
    nonzero = vals[vals > 0]
    if len(nonzero) == 0: return
    floor = np.percentile(nonzero, percentile_floor)
    bs["statistic"] = np.where(vals < floor, np.nan, vals)
    pitch.heatmap(bs, ax=ax, cmap=cmap_name,
                  edgecolors=BG, linewidth=0.5, zorder=zorder, alpha=0.95)

def add_zone_outline(ax, x, y, w, h, color, zorder=6):
    """Outline only — labels go OUTSIDE the pitch via callouts()."""
    ax.add_patch(patches.Rectangle((x,y), w, h, linewidth=1.4,
                                   edgecolor=color, facecolor="none",
                                   alpha=0.85, zorder=zorder, linestyle="--"))

def callouts_below(ax, items, y_below=-3.5):
    """Render zone-name pills BELOW the pitch at explicit x positions.
    items = [(label, color, x_position), …]"""
    for label, color, x in items:
        ax.text(x, y_below, label, color=color, fontsize=8.5,
                fontweight="bold", ha="center", va="top",
                family="sans-serif", zorder=10)
        # Tiny tick line linking label to pitch
        ax.plot([x, x], [0, y_below + 0.8], color=color,
                lw=0.7, alpha=0.5, clip_on=False, zorder=10)

def header(fig, eyebrow, title, subtitle, y0=0.965, x=0.05):
    fig.text(x, y0, eyebrow, color=ACCENT, fontsize=9.5,
             fontweight="bold", family="sans-serif")
    fig.text(x, y0-0.038, title, color=TEXT, fontsize=24,
             fontweight="bold", family="sans-serif")
    fig.text(x, y0-0.072, subtitle, color=TEXT2, fontsize=11.5,
             style="italic", family="sans-serif")

def footer(fig, txt, y0=0.025):
    fig.text(0.05, y0, txt, color=TEXT3, fontsize=8.5,
             style="italic", family="sans-serif")
    fig.text(0.95, y0,
             "Data: WhoScored / Opta  ·  xT model: Karun Singh (12×8)  ·  Depth of Field",
             color=TEXT3, fontsize=8.5, ha="right", family="sans-serif")

def attack_arrow(ax, half: bool = False, y=-3):
    if half:
        ax.annotate("", xy=(99, y), xytext=(78, y),
                    arrowprops=dict(arrowstyle="-|>", color=TEXT3, lw=1),
                    annotation_clip=False)
        ax.text(88.5, y-2, "Attacking direction", color=TEXT3,
                fontsize=8.5, ha="center", style="italic", va="top")
    else:
        ax.annotate("", xy=(75, y), xytext=(40, y),
                    arrowprops=dict(arrowstyle="-|>", color=TEXT3, lw=1),
                    annotation_clip=False)
        ax.text(57.5, y-2, "Attacking direction", color=TEXT3,
                fontsize=8.5, ha="center", style="italic", va="top")

def stats_panel(fig, items, x0=0.74, y0=0.93, dy=0.045):
    for i, (val, lbl, col) in enumerate(items):
        y = y0 - i * dy
        fig.text(x0, y, val, color=col, fontsize=18,
                 fontweight="bold", family="sans-serif")
        fig.text(x0+0.07, y+0.008, lbl, color=TEXT2, fontsize=10.5,
                 family="sans-serif")

def legend_swatch(fig, x, y, colour, val, label):
    fig.add_artist(patches.Rectangle((x, y-0.005), 0.018, 0.018,
                                     facecolor=colour, edgecolor=TEXT3,
                                     linewidth=0.4, transform=fig.transFigure))
    fig.text(x+0.025, y, val, color=TEXT, fontsize=11,
             fontweight="bold", family="sans-serif")
    fig.text(x+0.06, y+0.001, label, color=TEXT2, fontsize=10,
             family="sans-serif")

# ════════════════════════════════════════════════════════════════════
# IMAGE 1 — Bayern xT
# ════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 8.6), facecolor=BG)
pitch = make_pitch()
style_axes(ax, pitch)
value_grid_layer(ax, pitch, bayern_pos["start_x"], bayern_pos["start_y"],
                  bayern_pos["xT_value"], cmap_name="inferno")
header(fig, "BUNDESLIGA 25/26 · 33 MATCHES",
       "Bayern Munich — Cumulative xT",
       "Where on the pitch ball-progression generates threat")
stats_panel(fig, [
    (f"{bayern_pos['xT_value'].sum():.1f}", "Total Σ xT",          TEXT),
    (f"{len(bayern_pos):,}",                "Positive-xT actions", TEXT2),
    (f"{bayern_pos['xT_value'].sum()/33:.2f}", "Σ xT per match",   ACCENT),
])
attack_arrow(ax)
footer(fig, "Brighter cells = more cumulative ball-progression threat originates here.")
plt.subplots_adjust(left=0.04, right=0.98, top=0.85, bottom=0.10)
fig.savefig(OUT/"pub_bayern_xt.png", bbox_inches="tight")
plt.close()
print("Saved → pub_bayern_xt.png")

# ════════════════════════════════════════════════════════════════════
# IMAGE 2 — England xT
# ════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 8.6), facecolor=BG)
pitch = make_pitch()
style_axes(ax, pitch)
value_grid_layer(ax, pitch, england_pos["start_x"], england_pos["start_y"],
                  england_pos["xT_value"], cmap_name="inferno")
header(fig, "2026 WORLD CUP QUALIFYING (UEFA) · 8/8 MATCHES",
       "England — Cumulative xT",
       "Threat-generation map across the full qualifying campaign")
stats_panel(fig, [
    (f"{england_pos['xT_value'].sum():.1f}", "Total Σ xT",         TEXT),
    (f"{len(england_pos):,}",                "Positive-xT actions",TEXT2),
    (f"{england_pos['xT_value'].sum()/8:.2f}", "Σ xT per match",  ACCENT),
])
attack_arrow(ax)
footer(fig, "Brighter cells = more cumulative ball-progression threat originates here.")
plt.subplots_adjust(left=0.04, right=0.98, top=0.85, bottom=0.10)
fig.savefig(OUT/"pub_england_xt.png", bbox_inches="tight")
plt.close()
print("Saved → pub_england_xt.png")

# ════════════════════════════════════════════════════════════════════
# IMAGE 3 — Comparison side-by-side
# ════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(20, 8.6), facecolor=BG)
panels = [
    (axes[0], bayern_pos,  33, "BAYERN MUNICH",  "Bundesliga 25/26  ·  33 matches"),
    (axes[1], england_pos,  8, "ENGLAND",        "2026 WCQ · 8/8 matches"),
]
for ax, pos, n, label, sub in panels:
    pitch = make_pitch()
    style_axes(ax, pitch)
    value_grid_layer(ax, pitch, pos["start_x"], pos["start_y"],
                     pos["xT_value"]/n, cmap_name="inferno")
    ax.text(2.5, 71, label, color=TEXT, fontsize=15, fontweight="bold")
    ax.text(2.5, 75, sub,   color=TEXT2, fontsize=10, style="italic")
    ax.text(2.5, -3, f"Σ xT per match: {pos['xT_value'].sum()/n:.2f}",
            color=ACCENT, fontsize=10, fontweight="bold")
    attack_arrow(ax)

fig.text(0.04, 0.965, "STRUCTURAL COMPARISON",
         color=ACCENT, fontsize=10, fontweight="bold")
fig.text(0.04, 0.93, "xT footprint — Bayern Munich vs England",
         color=TEXT, fontsize=22, fontweight="bold")
fig.text(0.04, 0.895,
         "Per-match normalised: directly comparable shading despite different sample sizes",
         color=TEXT2, fontsize=11, style="italic")
footer(fig, "Read across: where each side concentrates ball-progression threat.")
plt.subplots_adjust(left=0.03, right=0.98, top=0.86, bottom=0.10, wspace=0.05)
fig.savefig(OUT/"pub_comparison.png", bbox_inches="tight")
plt.close()
print("Saved → pub_comparison.png")

# ════════════════════════════════════════════════════════════════════
# IMAGE 4 — Kane Touch Zones (Bayern)
# ════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 8.8), facecolor=BG)
pitch = make_pitch()
style_axes(ax, pitch)

deep = kane_bay[kane_bay.zone=="DEEP"]
btw  = kane_bay[kane_bay.zone=="BTW"]
z14  = kane_bay[kane_bay.zone=="Z14"]
pa   = kane_bay[kane_bay.zone=="PA"]

grid_layer(ax, pitch, deep["x"], deep["y"], COL_DEEP, percentile_floor=50)
grid_layer(ax, pitch, btw["x"],  btw["y"],  COL_BTW,  percentile_floor=45)
grid_layer(ax, pitch, z14["x"],  z14["y"],  COL_Z14,  percentile_floor=25)
grid_layer(ax, pitch, pa["x"],   pa["y"],   COL_PA,   percentile_floor=25)

add_zone_outline(ax, 88.5, 13.84, 16.5, 40.32, COL_PA)
add_zone_outline(ax, 70.0, 24.50, 18.5, 19.0,  COL_Z14)

# Zone labels OUTSIDE pitch — x positions match zone centres
callouts_below(ax, [
    ("DEEP BUILD-UP",  COL_DEEP, 25),
    ("BETWEEN LINES",  COL_BTW,  62),
    ("ZONE 14",        COL_Z14,  79.25),
    ("PENALTY AREA",   COL_PA,   96.75),
], y_below=-3)
attack_arrow(ax, y=-7.5)

header(fig, "BAYERN · 2025/26 BUNDESLIGA",
       "Harry Kane — Touch & Receive Zones",
       "Touch density grid by tactical zone, 33 matches")
stats_panel(fig, [
    (f"{len(kane_bay):,}", "Total touches", TEXT),
    (f"{len(pa)}",         "Penalty area",  COL_PA),
    (f"{len(z14)}",        "Zone 14",       COL_Z14),
    (f"{len(btw)}",        "Between lines", COL_BTW),
    (f"{len(deep)}",       "Deep build-up", COL_DEEP),
])
footer(fig, "Each colour grid = touch count in that zone category.  Brighter cell = more touches.")
plt.subplots_adjust(left=0.04, right=0.98, top=0.85, bottom=0.10)
fig.savefig(OUT/"pub_kane_zones.png", bbox_inches="tight")
plt.close()
print("Saved → pub_kane_zones.png")

# ════════════════════════════════════════════════════════════════════
# IMAGE 5 — Bayern wide creators → Kane (attacking half)
# ════════════════════════════════════════════════════════════════════
def render_creators_to_kane(out_path, *, players, player_dfs, kane_df, label_pack,
                             title_eyebrow, title_main, title_sub):
    fig, ax = plt.subplots(figsize=(13, 11), facecolor=BG)
    pitch = make_pitch(half=True)
    style_axes(ax, pitch)

    btw_ = kane_df[kane_df.zone=="BTW"]
    z14_ = kane_df[kane_df.zone=="Z14"]
    pa_  = kane_df[kane_df.zone=="PA"]

    # Wide creators destination grids
    for pid, info in players.items():
        df = player_dfs[pid].dropna(subset=["end_x","end_y"])
        grid_layer(ax, pitch, df["end_x"], df["end_y"],
                   info["colour"], percentile_floor=55)

    # Kane chain
    grid_layer(ax, pitch, btw_["x"], btw_["y"], COL_BTW, percentile_floor=60)
    grid_layer(ax, pitch, z14_["x"], z14_["y"], COL_Z14, percentile_floor=25)
    grid_layer(ax, pitch, pa_["x"],  pa_["y"],  COL_PA,  percentile_floor=25)

    add_zone_outline(ax, 88.5, 13.84, 16.5, 40.32, COL_PA)
    add_zone_outline(ax, 70.0, 24.50, 18.5, 19.0,  COL_Z14)

    # Centroids
    for pid, info in players.items():
        df = player_dfs[pid].dropna(subset=["start_x","start_y"])
        if df.empty: continue
        w  = df["xT_value"].clip(lower=0.001)
        cx = (df["start_x"]*w).sum() / w.sum()
        cy = (df["start_y"]*w).sum() / w.sum()
        if cx < 52.5: continue
        ax.scatter(cx, cy, s=420, color=info["colour"],
                   edgecolors=BG, linewidths=2.6, zorder=8)
        ax.text(cx, cy, info["short"], color=BG, fontsize=15,
                fontweight="bold", ha="center", va="center", zorder=9)

    # Zone labels below pitch — explicit x positions matching zone centres
    callouts_below(ax, [
        ("ZONE 14",      COL_Z14, 79.25),
        ("PENALTY AREA", COL_PA,  96.75),
    ], y_below=-3.5)
    attack_arrow(ax, half=True, y=-7.5)

    header(fig, title_eyebrow, title_main, title_sub)

    # Legend column
    y = 0.83
    for (label, val, colour) in label_pack:
        legend_swatch(fig, 0.05, y, colour, val, label)
        y -= 0.038

    fig.text(0.05, y - 0.02,
             "Lettered dots = each creator's xT-weighted creation point.",
             color=TEXT3, fontsize=9, style="italic")
    footer(fig,
           "Wide creators rarely enter the box; their grids end at the edge.  "
           "Kane occupies exactly that space.")
    plt.subplots_adjust(left=0.04, right=0.98, top=0.88, bottom=0.10)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"Saved → {out_path.name}")

# Bayern wide creators
render_creators_to_kane(
    OUT/"pub_wide_creators_kane.png",
    players=BAY_PLAYERS, player_dfs=bay_dfs, kane_df=kane_bay,
    label_pack=[
        (f"Olise progressions land",   str(len(bay_dfs[OLISE_ID])),   COL_OLISE_BAY),
        (f"Díaz progressions land",    str(len(bay_dfs[DIAZ_ID])),    COL_DIAZ_BAY),
        (f"Musiala progressions land", str(len(bay_dfs[MUSIALA_ID])), COL_MUSIALA),
        (f"Kane: between-lines link",  str(len(kane_bay[kane_bay.zone=='BTW'])), COL_BTW),
        (f"Kane: zone 14 turn",        str(len(kane_bay[kane_bay.zone=='Z14'])), COL_Z14),
        (f"Kane: penalty-area touch",  str(len(kane_bay[kane_bay.zone=='PA'])),  COL_PA),
    ],
    title_eyebrow="STRUCTURAL READ · BAYERN 2025/26",
    title_main="Bayern build Kane's environment",
    title_sub="Wide creators  ·  between-lines link  ·  finishing zone — the full chain",
)

# ════════════════════════════════════════════════════════════════════
# IMAGE 6 — England fail to utilise Kane
# ════════════════════════════════════════════════════════════════════
render_creators_to_kane(
    OUT/"pub_england_kane_failure.png",
    players=ENG_PLAYERS, player_dfs=eng_dfs, kane_df=kane_eng,
    label_pack=[
        (f"James progressions land",      str(len(eng_dfs[JAMES_ID])),      COL_JAMES),
        (f"Rashford progressions land",   str(len(eng_dfs[RASHFORD_ID])),   COL_RASHFORD),
        (f"Bellingham progressions land", str(len(eng_dfs[BELLINGHAM_ID])), COL_BELLINGHAM),
        (f"Kane: between-lines link",     str(len(kane_eng[kane_eng.zone=='BTW'])), COL_BTW),
        (f"Kane: zone 14 turn",           str(len(kane_eng[kane_eng.zone=='Z14'])), COL_Z14),
        (f"Kane: penalty-area touch",     str(len(kane_eng[kane_eng.zone=='PA'])),  COL_PA),
    ],
    title_eyebrow="STRUCTURAL READ · ENGLAND 2026 WCQ",
    title_main="England fail to utilise Kane",
    title_sub="Same chart, same player — but the chain breaks at the wide-creator stage",
)

print("\nAll 6 publishable visuals rendered.")
