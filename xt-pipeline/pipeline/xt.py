"""xT computation using socceraction's published 12x16 grid."""
from __future__ import annotations
import pandas as pd
from socceraction.xthreat import ExpectedThreat, load_model
from socceraction.spadl import add_names as spadl_add_names

# Karun Singh's published xT grid (12 cols x 8 rows) hosted by socceraction.
DEFAULT_XT_URL = (
    "https://karun.in/blog/data/open_xt_12x8_v1.json"
)


def load_xt() -> ExpectedThreat:
    return load_model(DEFAULT_XT_URL)


def add_xt(actions: pd.DataFrame, xt: ExpectedThreat) -> pd.DataFrame:
    """Add per-action xT delta to a SPADL frame.

    Only successful moving actions (pass, dribble, cross) get a positive value;
    others get 0.
    """
    df = actions.copy()
    if "type_name" not in df.columns:
        df = spadl_add_names(df)
    coord_ok = df[["start_x", "start_y", "end_x", "end_y"]].notna().all(axis=1)
    moving = (
        df["type_name"].isin(["pass", "dribble", "cross"])
        & df["result_name"].eq("success")
        & coord_ok
    )
    df["xT_value"] = 0.0
    if moving.any():
        df.loc[moving, "xT_value"] = xt.rate(df.loc[moving])
    return df
