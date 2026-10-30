## 9. Implementation for ClimMaTech: what a deployment would use

### 9.1 Where it fits

ClimMaTech's system observes (radar gauges), predicts (level and flow 30 min to 48 h ahead) and warns (sirens,
Aagah app, control centre). This project adds the step between "predict" and "warn": **forecast flow at Naraj →
flooded land → settlements, roads and facilities affected**, from the trigger-discharge map of §6.3 and the impact
layers of §7.

```
ClimMaTech / CWC forecast of Naraj flow ──► forecast_to_impact.py ──► flood map (GeoTIFF)
   (m³/s or lakh cusec, lead time)            trigger map + impacts    settlements to warn (GeoJSON) ──► Rakshak Control Centre, Aagah
                                                                       roads under water, bulletin text ──► district / OSDMA
Sentinel-1 pass (every 2-6 days) ──► atlas_infer.py ──► observed flood map ──► refit trigger map each season
GloFAS ensemble + ECMWF rain + SACHET/CWC alerts ──► live/run_live.py (daily) ──► impact-based level, villages with dates,
                                                                                  CAP alert + Atom feed ──► Rakshak Control Centre
```

### 9.2 Forecast-to-bulletin tool

`python mahanadi/forecast_to_impact.py --q <flow>` (or `--lakh-cusec`, and `--rain <mm>` for the flow-and-rain
analogs) runs in seconds. Output for the 5-year flow (23,940 m³/s; the 25-year and rain bulletins are in
`results/impact/bulletins/`):

```
MAHANADI DELTA - EXPECTED FLOODING FOR A NARAJ FLOW OF 23,940 m3/s (8.5 lakh cusec), lead time 24 h
(flow = highest daily flow over 3 days at Naraj, the measure the atlas is fitted on; method: trigger-discharge map, river flow only)
Expected flooded land: 218 km2
People living on that land: 25,384
Settlements with at least 10 % of people on flooded land: 24
  - near Biridi (1.4 km): about 403 people (70% of 574) at 20.3319 N, 86.0429 E
  - near Patkura (9.7 km): about 341 people (48% of 704) at 20.3133 N, 86.3615 E
  - near Bhattasagar Square (7.0 km): about 263 people (16% of 1,613) at 20.6301 N, 86.1248 E
  - near Choudwar (4.0 km): about 143 people (21% of 694) at 20.5588 N, 85.8918 E
  - near Patkura (2.7 km): about 129 people (20% of 647) at 20.4002 N, 86.3823 E
  - near Patkura (1.5 km): about 90 people (32% of 281) at 20.3855 N, 86.3917 E
  - near Fakirabad (7.2 km): about 89 people (13% of 706) at 20.4445 N, 86.4497 E
  - near Dhuria (8.6 km): about 76 people (14% of 529) at 20.4610 N, 86.3444 E
  - near Patkura (9.3 km): about 75 people (28% of 269) at 20.3113 N, 86.3760 E
  - near Patkura (9.1 km): about 74 people (30% of 253) at 20.3116 N, 86.4309 E
  - near Gobindpur (2.6 km): about 72 people (28% of 260) at 20.3515 N, 86.0166 E
  - near Biridi (7.9 km): about 69 people (14% of 481) at 20.2658 N, 86.0652 E
  - near Bhattasagar Square (5.9 km): about 69 people (17% of 417) at 20.6256 N, 86.1147 E
  - near Patkura (10.8 km): about 67 people (27% of 247) at 20.3116 N, 86.3447 E
  - near Nemalo (1.2 km): about 65 people (16% of 414) at 20.4409 N, 86.1674 E
Main roads under water: 11.4 km; named sections: Right Puri Main Canal Road 0.8 km
Source: Sentinel-1 flood atlas 2017-2026 + GloFAS discharge (IIT Bombay IDP prototype). Not an official warning.
```

The interactive viewer (`dashboard/index.html`, one file, works offline) shows each design flood with flooded land,
roads cut, the settlements list (click to zoom), siren and sensor sites and the bank-inspection cells.

### 9.3 Siren sites

Greedy maximal coverage of the 32,388 people living on land flooded in the 25-year flood or in at
least 10 % of monsoon passes. With 40 sirens the share covered is 32%, 48%
and 62% for an audible range of 1.0, 1.5 and 2.0 km. At 1.5 km: 10 sirens cover 24%,
20 cover 35%. Exposed people are spread thinly over many
small settlements, so the first sirens give most of the benefit; the rest is better reached by phone alerts (Aagah)
than by more sirens.

| Rank | Settlement | Location | New people covered | Cumulative share |
|---|---|---|---|---|
| 1 | Fakirabad | 20.5029 N, 86.4186 E | 1,794 | 6% |
| 2 | near Patkura (8.5 km) | 20.3190 N, 86.3756 E | 1,160 | 9% |
| 3 | near Gobindpur (1.1 km) | 20.3312 N, 86.0318 E | 787 | 12% |
| 4 | near Patkura (1.5 km) | 20.3872 N, 86.4195 E | 760 | 14% |
| 5 | near Bhattasagar Square (7.0 km) | 20.6301 N, 86.1248 E | 669 | 16% |
| 6 | near Balachandrapur (1.4 km) | 20.6305 N, 86.2469 E | 555 | 18% |
| 7 | near Patkura (2.4 km) | 20.4047 N, 86.3886 E | 554 | 19% |
| 8 | near Balachandrapur (3.8 km) | 20.6377 N, 86.2729 E | 505 | 21% |
| 9 | near Fakirabad (6.7 km) | 20.4514 N, 86.3849 E | 497 | 22% |
| 10 | near Patkura (5.9 km) | 20.3416 N, 86.3819 E | 493 | 24% |
| 11 | Jagatpur | 20.4950 N, 85.9355 E | 487 | 26% |
| 12 | near Balachandrapur (2.3 km) | 20.6314 N, 86.2243 E | 456 | 27% |
| 13 | near Patkura (8.6 km) | 20.3448 N, 86.3385 E | 392 | 28% |
| 14 | near Patkura (2.2 km) | 20.4084 N, 86.4129 E | 387 | 29% |
| 15 | near Patkura (3.9 km) | 20.3910 N, 86.4426 E | 367 | 30% |

### 9.4 River-sensor bridges

One non-contact radar gauge (level and surface velocity) at the head of each main distributary measures how the
flood splits between the branches, which the Naraj forecast alone cannot tell:

| River | Bridge | Road class | Length (m) | km from Naraj | Approaches dry in 25-yr flood | Location |
|---|---|---|---|---|---|---|
| Devi River | Netaji Subhash Chandra Bose Setu | primary | 2823 | 8 | yes | 20.4546 N, 85.8481 E |
| Kathajodi | NH16 | trunk | 869 | 13 | yes | 20.4405 N, 85.8901 E |
| Birupa | NH16;NH55 | trunk | 543 | 17 | yes | 20.5133 N, 85.9320 E |
| Luna | (unnamed) | unclassified | 776 | 31 | no | 20.4650 N, 86.0743 E |
| Mahanadi | (unnamed) | unclassified | 458 | 52 | yes | 20.3668 N, 86.2642 E |
| Biropa | (unnamed) | unclassified | 424 | 60 | no | 20.6261 N, 86.3224 E |

Pravaah needs a surveyed cross-section and a surface-to-mean velocity factor to give discharge (ClimMaTech
documentation); the field protocol B–C measures exactly these at one bridge (§8.4).

### 9.5 Rolling it out

1. **Season 0 (now)**: hand the trigger map, bulletin tool, live feed and viewer to ClimMaTech; run the live feed every
   morning; refit with CWC/WRD observed flows.
2. **Before the next monsoon**: field-verified siren and sensor sites (§8.7); first sensors at the heads of the
   Mahanadi and Kathajodi branches.
3. **During the monsoon**: map every new Sentinel-1 pass (6 s per pass on the lab GPU, ~2 min to download) and compare
   with the bulletin of that day; add the season to the atlas.
4. **Each year**: refit the trigger map, update design floods, re-rank links and banks.

### 9.6 Gaps in the partner's services and what this project adds

All 50 public pages of climmatech.com were downloaded on 29 October 2026; the product, solution, platform, fact-sheet
and case-study pages were read in full and the blog was searched. The partner measures and forecasts the river at points and warns through sirens and an app; its
research group reconstructs past floods from satellite, seismic and gauge data by hand. The table lists each service, the
gap found and what this project adds, with the number behind it.

| Their service | Gap | What this project adds | Evidence |
|---|---|---|---|
| River View (platform layer: "a live map-based view of river levels and flood risk") | No flood-extent layer behind the map | Flood frequency, trigger flow and impact layers for the Mahanadi delta | 590 passes; held-out IoU 0.20 vs 0.04 at high flows |
| AI forecasting, 30 min to 48 h ahead | A forecast level is not a list of villages | Forecast-to-bulletin tool and a daily live feed with impact-based levels; a 1–3 day Naraj forecast from upstream flows (§6.7, §9.7) | 25-year flow: 240 km², 30,427 people, 32 settlements; forecast efficiency 0.99 / 0.94 / 0.89 at 1 / 2 / 3 days |
| Research group, satellite reconstructions | Flood width measured by hand at 36 cross-sections; optical pass 75–79 % cloud, only radar pass two days early | Benchmarked radar model that maps every Sentinel-1 pass automatically, through cloud | 92 audited runs (Appendix A); ~5 s per pass |
| Solution pages, network design | Layouts drawn as illustrations | Data-backed siting of sirens and river gauges with coordinates | 40 sirens reach 48% of exposed people at 1.5 km; 6 sensor bridges |
| Pravaah discharge | Needs a surveyed cross-section and a surface-to-mean velocity factor | Field protocols B and C measure both, plus Manning's n | §8.4; scripts in `fieldkit/analysis/` |
| Varshaq rain gauge | Rain not linked to flooded land | Rain-aware flood maps (analogs, learned model §6.6) | 5-year flow: 27 km² dry week vs 93 km² heavy rain |
| Flood-warning solution and Aagah app ("time to evacuate populations, reroute traffic, and secure critical infrastructure") | Which people, which roads | Settlements to warn, roads that close, villages that lose their hospital, in every bulletin | 41 settlements lose hospital access (25-year flood) |
| Rakshak Control Centre ("draw an area, pick districts, or upload your own boundaries"; accepts CAP) | Alert areas drawn by hand | Every forecast also writes a CAP 1.2 alert with one area per settlement to warn, listed in an Atom feed the centre can subscribe to | `bulletin_<flow>.cap.xml`; 32 areas for the 25-year flow |
| Dam and reservoir solution | Level at the dam, not the water spread | The same radar model can map reservoir area on every pass (next step: Hirakud) | — |
| Installation and O&M | Timing against floods and storms | Work window and schedule from 29 years of flows and 46 years of storm tracks | December–April; 78 crew-days |

### 9.7 The live warning service

The bulletin tool of §9.2 needs someone to type a flow. The live service (`live/`) reads the forecasts itself, every
time it runs, from sources that need no login, each a plugin that fails soft (`live/sources.py`):

| Plugin | Source | What it gives |
|---|---|---|
| glofas | GloFAS v4 through the Open-Meteo flood API | the Naraj flow 30 days ahead: control run and 50 ensemble members; the upstream gauges |
| rain | ECMWF IFS 0.25° through the Open-Meteo forecast API | daily rain over the delta and over the catchment, 16 days ahead |
| sachet | NDMA SACHET CAP feed of the state | official IMD, CWC and SDMA alerts, matched to the basin's districts |
| cwc | CWC flood-forecasting portal | stations now above warning level (answers from Indian networks) |
| sentinel1 | Planetary Computer catalogue | the latest radar pass over the basin, to map the flood actually there |

For each of the 51 runs and each day the flow measure the atlas uses (the 3-day peak at Naraj) is looked up in the
flow–impact table that `mahanadi/impact_curve.py` sweeps once from the trigger map: flooded land, people on it, villages
with 10 % of their people on flooded land, people cut off from every hospital, and per village the flow at which that
happens (the sweep reproduces the design-flood numbers of §7 exactly). The warning level is set by impact, as in
impact-based forecasting: "Be aware" from 5,000 people on flooded land or three villages (12,250 m³/s at Naraj),
"Be prepared" from 10,000 people or the first village cut off from every hospital (18,500 m³/s), "Act now" from
25,000 people or 20,000 cut off (21,250 m³/s), each with the share of the 51 runs that reach it. Villages,
hospital cut-offs, roads and health facilities count beyond the ordinary monsoon: what is already wet or cut at the flow
exceeded on a quarter of monsoon days (6,682 m³/s at Naraj) belongs to the season, not to a
flood. A few river-bank hamlets get wet every monsoon, and on the Brahmani a road without a mapped bridge cuts six
villages off at almost any monsoon flow: a road to raise, not a warning. The output
is a bulletin naming each village with the first day it is expected (median run) or possible (wettest runs), the
villages that lose their hospital, the roads that close and the health facilities at risk; a CAP 1.2 alert (status
"Exercise") from "Be aware" upwards; an Atom index of the alerts, the way CAP feeds are published, for the Rakshak
Control Centre to subscribe to; and a status board. A run takes about 15 seconds on a laptop; on the lab server
`server/run_live.sh` is ready to run every morning from one cron line (README).

The run of 2026-10-31 01:58 IST: Naraj 2,923 m³/s, peaking near 3,810 m³/s
on 2026-11-01 (wettest runs 3,836), level "No flood impact"; the upstream-gauge model of §6.7 gave 2026-10-31 2,526, 2026-11-01 3,078, 2026-11-02 2,762 m³/s for the next three days. The state feed carried
10 official alerts, among them: Moderate Rain, Thundershower with wind speed 30-40kmph is very likely to occur at many places over Anugul, Baleshwar, Bhadrak, Cuttack, Dhenkanal, …; Moderate Rain with squally wind 30-40 kmph  is very likely to occur at isolated places over Baleshwar, Bhadrak, Cuttack(Including Cuttack City), ….

Every basin of §6.8 runs in the same feed with its own tables and the same rule (`live/basins/<basin>.json`, written by
`live/make_basin_config.py`). The flows at which each level starts, and the run of 2026-10-31:

| Basin | Gauge (flow measure) | Ordinary monsoon (m³/s) | Be aware from (m³/s) | Be prepared from | Act now from | Flow today | Level today |
|---|---|---|---|---|---|---|---|
| Mahanadi delta | Naraj (3-day peak) | 6,682 | 12,250 | 18,500 | 21,250 | 2,923 | No flood impact |
| Brahmani–Baitarani delta | Jenapur (same-day flow) | 1,737 | 3,500 | 3,500 | 4,250 | 442 | No flood impact |
| Brahmaputra at Majuli | Neamatighat (3-day peak) | 17,988 | 21,500 | 22,750 | 29,000 | 2,971 | No flood impact |

On the Brahmani the first village cut off from every hospital comes at the same flow as the first 5,000 people on
flooded land, so "Be aware" and "Be prepared" start together; on the Brahmaputra "Act now" starts near the 2-year flood
(29,833 m³/s), as
it should on a river island that floods most years.

**Replay of the largest flood of the radar era.** `python live/run_live.py --replay 2022-08-14` runs the
feed as it would have run on the morning of 2022-08-14, with the flows that came as a perfect forecast:
level "Act now" for a Naraj peak of 28,378 m³/s on 2022-08-18, 31 villages named with
the day the water reaches them, and 41 villages that lose road access to every hospital from 2022-08-16.
The upstream-gauge model of §6.7, trained without 2022, forecast 16,254 m³/s for 2022-08-15, 20,554 m³/s for 2022-08-16, 21,327 m³/s for 2022-08-17: lower than the flows that came (a steep rise is the hardest case), but already above the 'Act now' flow three days ahead.
The radar passes of the following days, against the flooded land the bulletin expected at their flow:

| Radar pass | Naraj flow (m³/s) | Box imaged | Flooded land expected (km²) | Seen by radar (km²) |
|---|---|---|---|---|
| 2022-08-16 | 24,603 | 71% | 218 | 280 |
| 2022-08-18 | 28,378 | 100% | 240 | 125 |
| 2022-08-21 | 26,914 | 90% | 228 | 67 |

More land was under water on the first pass, after 177 mm of rain in a week, than at the river crest two days later,
when the rain water had drained: the flow-only map is too small before the crest and too large after it. This is the
case for the rain-aware model of §6.6 in the feed, and for mapping each new radar pass as soon as it arrives.
