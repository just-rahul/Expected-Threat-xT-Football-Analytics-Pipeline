"""One-page season dashboard from the cached actions parquet."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import Pitch

OUT = Path(__file__).parent / "out"
TEAM = "Bayern Munich"
SEASON = "2025-2026"

actions = pd.read_parquet(OUT / f"actions_{TEAM.replace(' ', '_')}_{SEASON}.parquet")
pos = actions[actions["xT_value"] > 0]

fig = plt.figure(figsize=(18, 9), facecolor="#22312b")
gs = fig.add_gridspec(1, 2, width_ratios=[1.4, 1])

# Pitch heatmap + top arrows
ax1 = fig.add_subplot(gs[0, 0])
pitch = Pitch(pitch_type="custom", pitch_length=105, pitch_width=68,
              line_color="white", pitch_color="#22312b")
pitch.draw(ax=ax1)
bin_stat = pitch.bin_statistic(pos["start_x"], pos["start_y"],
                               values=pos["xT_value"], statistic="sum", bins=(12, 8))
pitch.heatmap(bin_stat, ax=ax1, cmap="hot", edgecolors="#22312b", alpha=0.6)
top = pos.nlargest(60, "xT_value")
pitch.arrows(top["start_x"], top["start_y"], top["end_x"], top["end_y"],
             ax=ax1, width=2, headwidth=4, headlength=4, color="#39ff14", alpha=0.85)
ax1.set_title(f"{TEAM} xT — {SEASON}", color="white", fontsize=16, pad=10)

# Player bar
ax2 = fig.add_subplot(gs[0, 1])
ax2.set_facecolor("#22312b")
name_col = "player" if "player" in pos.columns else "player_name"
by_player = pos.groupby(name_col)["xT_value"].sum().sort_values().tail(15)
ax2.barh(by_player.index, by_player.values, color="#39ff14")
ax2.set_title("Total xT by player", color="white", fontsize=14)
ax2.tick_params(colors="white")
for s in ax2.spines.values():
    s.set_color("white")
ax2.set_xlabel("Total xT", color="white")

fig.savefig(OUT / f"season_dashboard_{TEAM.replace(' ', '_')}.png",
            dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print("Saved:", OUT / f"season_dashboard_{TEAM.replace(' ', '_')}.png")
