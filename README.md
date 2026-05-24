# xT pipeline — Bayern 25-26 + England WCQ

```
WhoScored (soccerdata)  →  pandas / SPADL (socceraction)  →  xT (Karun Singh 12×8 grid)  →  mplsoccer
```

## Why not SofaScore
SofaScore exposes shotmaps + xG but **not pass-level event coordinates**, which xT requires.
WhoScored carries Opta event data with start/end x,y per action — that's what feeds xT.

## Run
```bash
cd ~/Desktop/xt-pipeline
.venv/bin/python demo.py        # 2-match Bayern proof-of-pipeline
.venv/bin/python run_all.py     # full Bayern Bundesliga 25-26 season
```

Outputs land in `out/`. Per-match plot = xT heatmap (start-zone density)
overlaid with arrows for top-N xT-positive actions. Player bar chart = total
xT per player.

## England WCQ
WhoScored's WCQ tournament isn't in soccerdata's default league dict.
See the docstring at the top of `run_all.py` for the 3-step extension:
look up tournamentId on WhoScored, add a custom entry to
`~/soccerdata/config/league_dict.json`, re-run.

## Caveats
- WhoScored scraping is against their ToS. Risk is yours.
- soccerdata 1.8.8 sometimes saves the Chrome-wrapped page (`<html><body>{json}</body></html>`)
  to the JSON cache. We monkey-patched `whoscored.py::_validate_page` to strip the wrapper.
- Negative xT totals are possible and correct — backward successful passes have negative ΔxT.
- xT model: 12×8 grid from Karun Singh, loaded at runtime from karun.in.
  Treat per-action xT as the value-add of moving the ball, not a goal probability.

## Files
- `pipeline/scrape.py` — soccerdata wrapper + cache cleaner
- `pipeline/xt.py` — SPADL → xT
- `pipeline/plot.py` — mplsoccer plots
- `demo.py` — 2-match demo
- `run_all.py` — full season + WCQ extension stub
