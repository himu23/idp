# Live flood warnings

Turns today's river-flow forecast into an impact-based flood warning for each basin: the warning level, the
villages to warn with the day each is expected to flood, the villages that lose road access to every hospital, the
roads that close, a CAP 1.2 alert and an Atom feed of the alerts.

```bash
pip install requests pandas numpy                  # enough for the warnings
pip install scikit-learn pystac-client             # optional: upstream-gauge forecast, latest radar pass
python live/run_live.py                            # every basin in live/basins/
python live/run_live.py --basin mahanadi --horizon 10
python live/run_live.py --basin mahanadi --replay 2022-08-14   # a past morning, with the flows that came
```

Output in `live/out/`: `index.html` (status board), `feed.atom` (index of the alerts), and per basin `status.json`,
`forecast.csv` (30 days: median, 10–90 % band, level and the share of runs at each level), `bulletin.txt` and
`alert.cap.xml` (from "Be aware" upwards; status "Exercise", because this is a student prototype and not an official
warning), `outlook.png` (the 30-day flow band against the level flows). A replay writes the same files to
`live/out/replay_<date>/`: the recorded GloFAS flows replace the forecast (a perfect forecast), the upstream-gauge model
is run as it would have been that morning, and the radar passes of the following days are checked against the flooded
land the bulletin expected.

## How it works

1. **Forecast.** The GloFAS v4 ensemble (control + 50 members, 30 days) at the basin's gauge, through the Open-Meteo
   flood API, becomes per member and day the flow measure the atlas was fitted on (Mahanadi: the highest daily flow at
   Naraj over the last 3 days).
2. **Impact.** `data/<basin>/impact_curve.csv` (made once by `mahanadi/impact_curve.py` from the trigger map) gives the
   flooded land, people on it, villages with 10 % of their people on flooded land and people cut off from every
   hospital at that flow; `settlement_thresholds.csv`, `road_cut_flows.csv` and `facility_thresholds.csv` give the flow
   at which each village, road and health facility is hit.
3. **Level** (`levels.py`), set by impact: Be aware (5,000 people on flooded land or 3 villages), Be prepared (10,000
   people or a village cut off from every hospital), Act now (25,000 people or 20,000 cut off). Villages, hospital
   cut-offs, roads and health facilities count beyond the **ordinary monsoon**: what is already wet or cut at the flow
   exceeded on a quarter of monsoon days (`baseline_m3s` in the basin file) belongs to the season, not to a flood.

   | Basin | Gauge | Ordinary monsoon | Be aware | Be prepared | Act now |
   |---|---|---|---|---|---|
   | Mahanadi delta | Naraj | 6,682 | 12,250 | 18,500 | 21,250 |
   | Brahmani–Baitarani delta | Jenapur | 1,737 | 3,500 | 3,500 | 4,250 |
   | Brahmaputra at Majuli | Neamatighat | 17,988 | 21,500 | 22,750 | 29,000 |

   (m³/s of the flow measure each atlas was fitted on: the highest daily flow over the last 3 days at Naraj and
   Neamatighat, the same day's flow at Jenapur.)
4. **Context.** Official alerts of the state (NDMA SACHET), CWC stations above warning level (one national list per
   run, shared by every basin), ECMWF rain, the latest Sentinel-1 pass, and on the Mahanadi a 1–3 day forecast from the
   upstream gauges (`mahanadi/forecast_model.py`).

## Plugins

Each source is one function in `sources.py`, decorated with `@plugin("name")`; a source that is down is reported as
unavailable and never stops the bulletin.

| Plugin | Source | Login |
|---|---|---|
| glofas | GloFAS v4 via the Open-Meteo flood API (ensemble, upstream gauges) | none |
| rain | ECMWF IFS 0.25° via the Open-Meteo forecast API | none |
| sachet | NDMA SACHET CAP feed of the state (IMD, CWC, SDMA alerts) | none |
| cwc | CWC flood-forecasting portal: stations above warning level (Indian networks) | none |
| sentinel1 | Microsoft Planetary Computer catalogue: latest Sentinel-1 pass | none |

To add a basin: add it to `mahanadi/basins.py`, run the atlas pipeline (`server/run_basin_atlas.sh <basin>`), pull its
results into `results/basins/<basin>/`, then `python live/make_basin_config.py <basin>`.

## Running it every day

On the lab server: `server/run_live.sh` (the cron line is in the script; the server clock is US Pacific time). Anywhere else: Windows Task Scheduler or cron calling
`python live/run_live.py`; each run takes about 15 seconds per basin.
