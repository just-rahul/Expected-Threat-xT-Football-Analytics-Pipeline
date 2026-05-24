"""Pizza chart: Kane for Bayern Munich vs Kane for England WCQ — side by side.

Metrics extracted from WhoScored raw event JSON; percentiles estimated
against top-striker benchmarks from public Opta aggregate data.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge, Circle
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
from socceraction.data.opta.parsers import WhoScoredParser
from socceraction.data.opta.loader import _eventtypesdf
from socceraction.spadl.opta import convert_to_actions
import socceraction.spadl as spadl
from pipeline.xt import load_xt, add_xt

KANE_ID   = 83532

# ── Depth of Field dark theme tokens ─────────────────────────────────────────
BG        = "#111010"   # --bg
SURFACE   = "#1c1a17"   # --surface
TEXT_PRI  = "#f0ece4"   # --text
TEXT_SEC  = "#b0a89e"   # --text2
TEXT_DIM  = "#625d56"   # --text3
ACCENT    = "#e83050"   # --accent  DoF red
BORDER    = "rgba(240,236,228,0.08)"

# ── Category colours — adapted for dark background ────────────────────────────
COL_ATT  = "#4a8fdb"   # blue         — attacking
COL_DEF  = "#c04878"   # wine-pink    — defensive
COL_POSS = "#2aaa88"   # teal         — possession
COL_PROG = "#e09020"   # amber        — progression

BAY_CACHE = Path.home() / "soccerdata/data/WhoScored/events/GER-Bundesliga_2526"
ENG_CACHE = Path.home() / "soccerdata/data/WhoScored/events/INT-WCQ-UEFA_2025"
OUT = Path("out")
OUT.mkdir(exist_ok=True)

# ── Metric definitions ────────────────────────────────────────────────────────
# (display_name, colour, stat_key)
METRICS = [
    ("Goal\nthreat",       COL_ATT,  "shots_p90"),
    ("Box\npresence",      COL_ATT,  "pa_touches_p90"),
    ("Aerial\nvolume",     COL_DEF,  "aerials_p90"),
    ("Defensive\nactions", COL_DEF,  "def_actions_p90"),
    ("Fouls\ndrawn",       COL_DEF,  "fouls_drawn_p90"),
    ("Ball\nretention",    COL_POSS, "pass_comp_pct"),
    ("Link-up\nplay",      COL_POSS, "passes_p90"),
    ("Zone 14\npresence",  COL_POSS, "z14_touches_p90"),
    ("Pass\nprogression",  COL_PROG, "prog_pass_p90"),
    ("Carry\nprogression", COL_PROG, "prog_carry_p90"),
    ("Shot\naccuracy",    COL_PROG, "shot_acc_pct"),
]

# Top-striker benchmarks: (max_value, min_value) for 0–100 scaling
# Based on typical Opta ranges for elite forwards in top-5 leagues
BENCH = {
    "shots_p90":       (5.5,  0.5),
    "pa_touches_p90":  (10.0, 1.0),
    "aerials_p90":     (9.0,  0.5),
    "def_actions_p90": (3.5,  0.1),
    "fouls_drawn_p90": (4.0,  0.2),
    "pass_comp_pct":   (88.0, 48.0),
    "passes_p90":      (28.0, 4.0),
    "z14_touches_p90": (9.0,  0.5),
    "prog_pass_p90":   (4.0,  0.1),
    "prog_carry_p90":  (5.0,  0.1),
    "shot_acc_pct":    (75.0, 20.0),
}


def to_pct(val: float, key: str) -> float:
    hi, lo = BENCH[key]
    return float(np.clip((val - lo) / (hi - lo) * 100, 2, 99))


def extract_stats(cache: Path, competition_id: str, season_id: str,
                  team_search: str) -> tuple[dict, int, float]:
    """Return (raw_stats, n_matches, total_minutes) for Kane in this context."""
    xt_model = load_xt()

    counts: dict[str, float] = {k: 0.0 for k in BENCH}
    pass_total  = 0
    pass_succ   = 0
    shot_total  = 0
    shot_on_tgt = 0
    matches     = 0
    minutes     = 0.0

    for f in sorted(cache.glob("*.json")):
        try:
            raw = json.loads(f.read_text())
            home_name = raw["home"].get("name", "")
            away_name = raw["away"].get("name", "")
            home_id   = int(raw["home"]["teamId"])
            away_id   = int(raw["away"]["teamId"])

            if team_search and team_search not in home_name and team_search not in away_name:
                continue

            kane_raw = [e for e in raw["events"]
                        if str(e.get("playerId", "")) == str(KANE_ID)]
            if len(kane_raw) < 5:
                continue

            # Minutes played this match
            sub_off = next(
                (e for e in kane_raw
                 if e.get("type", {}).get("displayName") == "SubstitutionOff"),
                None
            )
            match_mins = sub_off["minute"] if sub_off else 90
            match_mins = max(10, min(match_mins, 95))

            # Coordinate flip for away team
            team_id = home_id if team_search in home_name else away_id
            is_home = (team_id == home_id)

            # ── Parse SPADL actions ──────────────────────────────────────────
            parser = WhoScoredParser(str(f), competition_id=competition_id,
                                     season_id=season_id, game_id=int(f.stem))
            df_ev = (pd.DataFrame.from_dict(parser.extract_events(), orient="index")
                     .merge(_eventtypesdf, on="type_id", how="left")
                     .reset_index(drop=True))
            actions = convert_to_actions(df_ev, home_team_id=home_id)
            actions = spadl.add_names(actions)
            actions = add_xt(actions, xt_model)
            kane = actions[actions["player_id"] == KANE_ID].copy()
            if kane.empty:
                continue

            matches += 1
            minutes += match_mins

            # Shots (SPADL)
            shots = kane[kane["type_name"].isin(["shot", "freekick_shot", "penalty"])]
            counts["shots_p90"] += len(shots)

            # PA touches (start position inside box)
            pa_mask = (kane["start_x"] > 88.5) & (kane["start_y"].between(13.84, 54.16))
            counts["pa_touches_p90"] += pa_mask.sum()

            # Zone 14 touches
            z14_mask = (kane["start_x"].between(70, 88.5)) & (kane["start_y"].between(24.5, 43.5))
            counts["z14_touches_p90"] += z14_mask.sum()

            # Progressive pass (pass/cross, success, xT > 0.003)
            prog_pass = kane[
                kane["type_name"].isin(["pass", "cross", "freekick_short"]) &
                kane["result_name"].eq("success") &
                (kane["xT_value"] > 0.003)
            ]
            counts["prog_pass_p90"] += len(prog_pass)

            # Progressive carry (dribble, success, xT > 0.002)
            prog_carry = kane[
                kane["type_name"].eq("dribble") &
                kane["result_name"].eq("success") &
                (kane["xT_value"] > 0.002)
            ]
            counts["prog_carry_p90"] += len(prog_carry)

            # Defensive actions (SPADL)
            def_acts = kane[kane["type_name"].isin(["tackle", "interception", "clearance"])]
            counts["def_actions_p90"] += len(def_acts)

            # Passes (for completion %)
            passes = kane[kane["type_name"].isin(["pass", "freekick_short", "cross"])]
            succ   = passes[passes["result_name"].eq("success")]
            pass_total += len(passes)
            pass_succ  += len(succ)

            # Passes total (link-up proxy)
            counts["passes_p90"] += len(passes)

            # ── From raw events ──────────────────────────────────────────────
            for e in kane_raw:
                t = e.get("type", {}).get("displayName", "")

                # Aerials
                if t == "Aerial":
                    counts["aerials_p90"] += 1

                # Fouls drawn (Foul event, Successful outcome = Kane won it)
                if t == "Foul" and e.get("outcomeType", {}).get("displayName") == "Successful":
                    counts["fouls_drawn_p90"] += 1

                # Shot accuracy tracking from raw events
                if t in ["MissedShots", "SavedShot", "Goal", "ShotOnPost", "BlockedShot"]:
                    shot_total += 1
                    if t in ["SavedShot", "Goal"]:
                        shot_on_tgt += 1

        except Exception:
            continue

    if matches == 0:
        return {}, 0, 0.0

    p90 = minutes / 90.0
    per90_keys = [k for k in BENCH if k not in ("pass_comp_pct", "shot_acc_pct")]
    for k in per90_keys:
        counts[k] /= p90

    counts["pass_comp_pct"] = (pass_succ / pass_total * 100) if pass_total > 5 else 60.0
    counts["shot_acc_pct"]  = (shot_on_tgt / shot_total * 100) if shot_total > 3 else 40.0

    return counts, matches, minutes


# ── Draw a single pizza (Depth of Field dark theme) ─────────────────────────
def draw_pizza(ax, values_pct: list[float], title: str, subtitle: str,
               logo_color: str):
    n     = len(METRICS)
    width = 2 * np.pi / n

    ax.set_facecolor(BG)

    # ── Reference rings ───────────────────────────────────────────────────────
    for r, lw, ls, alpha in [(0.25, 0.6, "--", 0.18), (0.50, 0.6, "--", 0.18),
                              (0.75, 0.6, "--", 0.18), (1.00, 1.1, "-",  0.35)]:
        ax.add_patch(plt.Circle((0, 0), r, fill=False,
                                linestyle=ls, color=TEXT_SEC,
                                linewidth=lw, alpha=alpha, zorder=1))

    # Ring percentage labels — placed at ~38° between first two segments
    ref_angle = np.radians(38)
    for r, lbl in [(0.25, "25"), (0.50, "50"), (0.75, "75")]:
        ax.text(r * np.cos(ref_angle) + 0.01, r * np.sin(ref_angle) + 0.01,
                lbl, color=TEXT_DIM, fontsize=5.5, va="bottom", ha="left",
                zorder=3, fontfamily="Helvetica Neue")

    # ── Segments ──────────────────────────────────────────────────────────────
    for i, (name, color, _) in enumerate(METRICS):
        angle_mid = np.pi / 2 - i * width
        angle_lo  = angle_mid + width / 2
        angle_hi  = angle_mid - width / 2
        pct = values_pct[i]
        r   = pct / 100

        th = np.linspace(angle_hi, angle_lo, 80)

        # Ghost full-radius slice (subtle)
        ax.fill(np.concatenate([[0], np.cos(th), [0]]),
                np.concatenate([[0], np.sin(th), [0]]),
                color=color, alpha=0.10, zorder=2)

        # Filled wedge
        ax.fill(np.concatenate([[0], r * np.cos(th), [0]]),
                np.concatenate([[0], r * np.sin(th), [0]]),
                color=color, alpha=0.92, zorder=3)

        # Segment separator lines (BG colour — makes crisp gaps)
        ax.plot([0, np.cos(angle_lo)], [0, np.sin(angle_lo)],
                color=BG, linewidth=1.1, zorder=4)

        # ── Value label ───────────────────────────────────────────────────────
        if pct >= 18:
            lr = r * 0.60
            ax.text(lr * np.cos(angle_mid), lr * np.sin(angle_mid),
                    str(int(round(pct))),
                    color="white", fontsize=8.5, fontweight="bold",
                    ha="center", va="center", zorder=7,
                    fontfamily="Helvetica Neue")
        else:
            lr = max(r + 0.13, 0.25)
            ax.text(lr * np.cos(angle_mid), lr * np.sin(angle_mid),
                    str(int(round(pct))),
                    color=TEXT_SEC, fontsize=8, fontweight="bold",
                    ha="center", va="center", zorder=7,
                    fontfamily="Helvetica Neue")

        # ── Metric label outside ring (horizontal, radial placement) ────────────
        out_r = 1.19
        lx, ly = out_r * np.cos(angle_mid), out_r * np.sin(angle_mid)
        # Horizontal alignment by quadrant
        cos_a = np.cos(angle_mid)
        if cos_a > 0.2:
            ha = "left"
        elif cos_a < -0.2:
            ha = "right"
        else:
            ha = "center"
        ax.text(lx, ly, name,
                color=TEXT_PRI, fontsize=7.2, fontweight="normal",
                ha=ha, va="center",
                linespacing=1.35, zorder=7,
                fontfamily="Helvetica Neue")

    # ── Category boundary separator lines (prominent) ─────────────────────────
    for b in [0, 2, 5, 8, 11]:
        angle = np.pi / 2 - b * width
        ax.plot([0, 1.07 * np.cos(angle)], [0, 1.07 * np.sin(angle)],
                color=BG, linewidth=2.8, zorder=5)

    # ── Center hub ────────────────────────────────────────────────────────────
    ax.add_patch(plt.Circle((0, 0), 0.075, color=BG,       zorder=8))
    ax.add_patch(plt.Circle((0, 0), 0.055, color=TEXT_SEC, zorder=9))

    # ── Per-pizza title block (above disc) ───────────────────────────────────
    ax.add_patch(plt.Circle((0, 1.64), 0.038, color=logo_color,
                            zorder=10, clip_on=False))
    ax.text(0, 1.54, title,
            color=TEXT_PRI, fontsize=12.5, fontweight="bold",
            ha="center", va="top", zorder=10, fontfamily="Georgia")
    ax.text(0, 1.40, subtitle,
            color=TEXT_DIM, fontsize=8, ha="center", va="top",
            zorder=10, fontstyle="italic", fontfamily="Helvetica Neue")

    # ── Per-chart legend (below disc) ─────────────────────────────────────────
    legend_cats = [
        ("Attacking",   COL_ATT),
        ("Defensive",   COL_DEF),
        ("Possession",  COL_POSS),
        ("Progression", COL_PROG),
    ]
    n_cats = len(legend_cats)
    spacing = 0.62
    x_start = -(n_cats - 1) * spacing / 2
    y_leg = -1.40
    for ci, (lbl, col) in enumerate(legend_cats):
        lx = x_start + ci * spacing
        ax.add_patch(plt.Rectangle((lx - 0.055, y_leg - 0.04), 0.11, 0.08,
                                   color=col, alpha=0.9, zorder=10))
        ax.text(lx, y_leg - 0.10, lbl,
                color=TEXT_SEC, fontsize=7, ha="center", va="top",
                fontfamily="Helvetica Neue", zorder=10)

    ax.set_xlim(-1.72, 1.72)
    ax.set_ylim(-1.65, 1.90)
    ax.set_aspect("equal")
    ax.axis("off")


# ── Pull data ─────────────────────────────────────────────────────────────────
print("Extracting Bayern Kane stats...")
bay_stats, bay_n, bay_mins = extract_stats(
    BAY_CACHE, "GER-Bundesliga", "2526", "Bayern")
print(f"  {bay_n} matches | {bay_mins:.0f} mins")
for k, v in bay_stats.items():
    print(f"    {k}: {v:.2f}")

print("\nExtracting England Kane stats...")
eng_stats, eng_n, eng_mins = extract_stats(
    ENG_CACHE, "INT-WCQ-UEFA", "2025", "England")
print(f"  {eng_n} matches | {eng_mins:.0f} mins")
for k, v in eng_stats.items():
    print(f"    {k}: {v:.2f}")

# Convert to percentiles
bay_pct = [to_pct(bay_stats[m[2]], m[2]) for m in METRICS]
eng_pct = [to_pct(eng_stats[m[2]], m[2]) for m in METRICS]

print("\nBayern percentiles:", [int(p) for p in bay_pct])
print("England percentiles:", [int(p) for p in eng_pct])

# ── Render ────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 14), facecolor=BG)

ax_bay = fig.add_axes([0.02, 0.055, 0.47, 0.840])
ax_eng = fig.add_axes([0.51, 0.055, 0.47, 0.840])
ax_bay.set_facecolor(BG)
ax_eng.set_facecolor(BG)

draw_pizza(ax_bay, bay_pct,
           title="Harry Kane  ·  Bayern Munich",
           subtitle=f"Bundesliga 25/26  ·  {bay_n} matches  ·  {bay_mins:.0f} mins",
           logo_color="#e32221")  # FCB red

draw_pizza(ax_eng, eng_pct,
           title="Harry Kane  ·  England",
           subtitle=f"WCQ 25/26  ·  {eng_n} matches  ·  {eng_mins:.0f} mins",
           logo_color="#c8102e")  # England red

# ── Accent bar at very top ────────────────────────────────────────────────────
fig.add_artist(plt.Line2D([0.0, 1.0], [0.995, 0.995],
                          transform=fig.transFigure,
                          color=ACCENT, linewidth=3.5, zorder=10))

# ── Header ───────────────────────────────────────────────────────────────────
fig.text(0.05, 0.978,
         "Harry Kane in 2025-26",
         color=TEXT_PRI, fontsize=28, fontweight="bold",
         ha="left", va="top", fontfamily="Georgia")

# Inline coloured category labels (no top legend — categories shown per chart)
cats_x = [
    (0.051, "Attacking",   COL_ATT,  True),
    (None,  ", ",           TEXT_SEC, False),
    (None,  "defensive",   COL_DEF,  True),
    (None,  ", ",           TEXT_SEC, False),
    (None,  "possession",  COL_POSS, True),
    (None,  " and ",        TEXT_SEC, False),
    (None,  "progression", COL_PROG, True),
    (None,  " percentiles vs top-5 striker peers", TEXT_SEC, False),
]
# Render inline text manually at figure level
import matplotlib.transforms as mtransforms
renderer = fig.canvas.get_renderer()
x_cursor = 0.051
y_sub = 0.945
for (fx, label, col, bold) in cats_x:
    fw = "bold" if bold else "normal"
    t = fig.text(x_cursor, y_sub, label, color=col, fontsize=11,
                 fontweight=fw, ha="left", va="top",
                 fontfamily="Helvetica Neue")
    fig.canvas.draw()
    bb = t.get_window_extent(renderer=renderer)
    x_cursor += bb.width / fig.get_size_inches()[0] / fig.dpi

fig.text(0.051, 0.915,
         f"Bayern: {bay_n} matches, {bay_mins:.0f} mins  ·  "
         f"England: {eng_n} matches, {eng_mins:.0f} mins  ·  "
         "WhoScored / Opta data",
         color=TEXT_DIM, fontsize=9.5, ha="left", va="top",
         fontstyle="italic", fontfamily="Helvetica Neue")

# ── Horizontal rules ─────────────────────────────────────────────────────────
RULE = "#2a2724"
fig.add_artist(plt.Line2D([0.04, 0.96], [0.900, 0.900],
                          transform=fig.transFigure, color=RULE, linewidth=0.9))
fig.add_artist(plt.Line2D([0.04, 0.96], [0.048, 0.048],
                          transform=fig.transFigure, color=RULE, linewidth=0.9))

# Centre vertical rule
fig.add_artist(plt.Line2D([0.505, 0.505], [0.052, 0.896],
                          transform=fig.transFigure, color=RULE, linewidth=0.9))

# ── Footnote ─────────────────────────────────────────────────────────────────
fig.text(0.051, 0.025,
         "* Percentiles estimated vs top-5 league striker benchmarks.  "
         "Progressive actions: xT-gated (pass >0.003, carry >0.002).  "
         "England: 8 WCQ matches — interpret directionally.",
         color=TEXT_DIM, fontsize=8, ha="left", va="top",
         fontstyle="italic", fontfamily="Helvetica Neue")

# ── DoF branding ─────────────────────────────────────────────────────────────
fig.text(0.952, 0.024,
         "Depth of Field",
         color=TEXT_SEC, fontsize=11, fontweight="bold",
         ha="right", va="top", fontfamily="Georgia")
# Accent underline beneath brand
fig.add_artist(plt.Line2D([0.748, 0.955], [0.020, 0.020],
                          transform=fig.transFigure,
                          color=ACCENT, linewidth=1.8))

out_path = OUT / "pub_kane_pizza_comparison.png"
fig.savefig(out_path, dpi=200, facecolor=fig.get_facecolor(),
            bbox_inches="tight", pad_inches=0.20)
plt.close()
print(f"\nSaved → {out_path}")
