"""mplsoccer plotting for xT."""
from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mplsoccer import Pitch


def plot_xt_actions(
    actions: pd.DataFrame,
    title: str,
    out_path: str,
    top_n: int = 30,
) -> None:
    """Arrows for the top-N xT-positive actions, plus a heatmap of xT density."""
    pos = actions[actions["xT_value"] > 0].nlargest(top_n, "xT_value")
    pitch = Pitch(pitch_type="custom", pitch_length=105, pitch_width=68,
                  line_color="white", pitch_color="#22312b")
    fig, ax = pitch.draw(figsize=(11, 7))
    fig.set_facecolor("#22312b")

    # Heatmap: bin xT_value by start location across all positive actions
    all_pos = actions[actions["xT_value"] > 0]
    if len(all_pos):
        bin_stat = pitch.bin_statistic(
            all_pos["start_x"], all_pos["start_y"],
            values=all_pos["xT_value"], statistic="sum", bins=(12, 8),
        )
        pitch.heatmap(bin_stat, ax=ax, cmap="hot", edgecolors="#22312b", alpha=0.55)

    # Top arrows
    if len(pos):
        pitch.arrows(
            pos["start_x"], pos["start_y"], pos["end_x"], pos["end_y"],
            ax=ax, width=2.5, headwidth=4, headlength=4,
            color="#39ff14", alpha=0.9,
        )

    ax.set_title(title, color="white", fontsize=14, pad=12)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_player_xt_bar(actions: pd.DataFrame, title: str, out_path: str, top_n: int = 15):
    by_player = (
        actions[actions["xT_value"] > 0]
        .groupby("player_name")["xT_value"]
        .sum()
        .sort_values(ascending=True)
        .tail(top_n)
    )
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.set_facecolor("#22312b")
    ax.set_facecolor("#22312b")
    ax.barh(by_player.index, by_player.values, color="#39ff14")
    ax.set_title(title, color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("white")
    ax.set_xlabel("Total xT", color="white")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
