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
```

### 9.2 Forecast-to-bulletin tool

`python mahanadi/forecast_to_impact.py --q <flow>` (or `--lakh-cusec`, and `--rain <mm>` for the flow-and-rain
analogs) runs in seconds. Output for the 5-year flow (23,940 m³/s; the 25-year and rain bulletins are in
`results/impact/bulletins/`):

```
MAHANADI DELTA - EXPECTED FLOODING FOR A NARAJ FLOW OF 23,940 m3/s (8.5 lakh cusec), lead time 24 h
(flow = highest daily flow over 5 days at Naraj, the measure the atlas is fitted on; method: trigger-discharge map, river flow only)
Expected flooded land: 203 km2
People living on that land: 22,545
Settlements with at least 10 % of people on flooded land: 20
  - near Patkura (9.7 km): about 321 people (46% of 704) at 20.3133 N, 86.3615 E
  - near Biridi (1.4 km): about 309 people (54% of 574) at 20.3319 N, 86.0429 E
  - near Bhattasagar Square (7.0 km): about 234 people (15% of 1,613) at 20.6301 N, 86.1248 E
  - near Patkura (2.7 km): about 152 people (24% of 647) at 20.4002 N, 86.3823 E
  - near Patkura (1.5 km): about 78 people (28% of 281) at 20.3855 N, 86.3917 E
  - near Dhuria (8.6 km): about 76 people (14% of 529) at 20.4610 N, 86.3444 E
  - near Choudwar (4.0 km): about 75 people (11% of 694) at 20.5588 N, 85.8918 E
  - near Patkura (14.6 km): about 71 people (16% of 440) at 20.2606 N, 86.4338 E
  - near Patkura (9.3 km): about 65 people (25% of 269) at 20.3113 N, 86.3760 E
  - near Patkura (10.8 km): about 62 people (25% of 247) at 20.3116 N, 86.3447 E
  - near Patkura (9.1 km): about 59 people (23% of 253) at 20.3116 N, 86.4309 E
  - near Nemalo (1.2 km): about 58 people (14% of 414) at 20.4409 N, 86.1674 E
  - near Gobindpur (2.2 km): about 48 people (15% of 326) at 20.3460 N, 86.0320 E
  - near Patkura (14.9 km): about 47 people (13% of 352) at 20.2562 N, 86.4195 E
  - near Bhattasagar Square (5.9 km): about 44 people (11% of 417) at 20.6256 N, 86.1147 E
Main roads under water: 10.9 km
Source: Sentinel-1 flood atlas 2017-2026 + GloFAS discharge (IIT Bombay IDP prototype). Not an official warning.
```

The interactive viewer (`dashboard/index.html`, one file, works offline) shows each design flood with flooded land,
roads cut, the settlements list (click to zoom), siren and sensor sites and the bank-inspection cells.

### 9.3 Siren sites

Greedy maximal coverage of the 27,371 people living on land flooded in the 25-year flood or in at
least 10 % of monsoon passes. With 40 sirens the share covered is 34%, 49%
and 62% for an audible range of 1.0, 1.5 and 2.0 km. At 1.5 km: 10 sirens cover 26%,
20 cover 37%. Exposed people are spread thinly over many
small settlements, so the first sirens give most of the benefit; the rest is better reached by phone alerts (Aagah)
than by more sirens.

| Rank | Settlement | Location | New people covered | Cumulative share |
|---|---|---|---|---|
| 1 | Fakirabad | 20.5029 N, 86.4186 E | 1,561 | 6% |
| 2 | near Patkura (8.5 km) | 20.3190 N, 86.3756 E | 1,067 | 10% |
| 3 | near Patkura (1.5 km) | 20.3872 N, 86.4195 E | 696 | 12% |
| 4 | near Gobindpur (1.1 km) | 20.3312 N, 86.0318 E | 602 | 14% |
| 5 | near Balachandrapur (1.4 km) | 20.6305 N, 86.2469 E | 565 | 16% |
| 6 | near Patkura (2.4 km) | 20.4047 N, 86.3886 E | 565 | 18% |
| 7 | near Bhattasagar Square (7.0 km) | 20.6301 N, 86.1248 E | 522 | 20% |
| 8 | near Fakirabad (6.7 km) | 20.4514 N, 86.3849 E | 486 | 22% |
| 9 | near Balachandrapur (3.8 km) | 20.6377 N, 86.2729 E | 481 | 24% |
| 10 | near Patkura (5.9 km) | 20.3416 N, 86.3819 E | 469 | 26% |
| 11 | near Patkura (8.6 km) | 20.3448 N, 86.3385 E | 393 | 27% |
| 12 | Badambadi | 20.4658 N, 85.8797 E | 378 | 28% |
| 13 | near Patkura (2.2 km) | 20.4084 N, 86.4129 E | 366 | 30% |
| 14 | near Patkura (3.9 km) | 20.3910 N, 86.4426 E | 364 | 31% |
| 15 | near Patkura (14.9 km) | 20.2598 N, 86.4417 E | 279 | 32% |

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

1. **Season 0 (now)**: hand the trigger map, bulletin tool and viewer to ClimMaTech; refit with CWC/WRD observed flows.
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
| River View (platform layer: "a live map-based view of river levels and flood risk") | No flood-extent layer behind the map | Flood frequency, trigger flow and impact layers for the Mahanadi delta | 590 passes; held-out IoU 0.23 vs 0.07 at high flows |
| AI forecasting, 30 min to 48 h ahead | A forecast level is not a list of villages | Forecast-to-bulletin tool: map, settlements to warn, roads under water | 25-year flow: 216 km², 25,163 people, 24 settlements |
| Research group, satellite reconstructions | Flood width measured by hand at 36 cross-sections; optical pass 75–79 % cloud, only radar pass two days early | Benchmarked radar model that maps every Sentinel-1 pass automatically, through cloud | 92 audited runs (Appendix A); ~5 s per pass |
| Solution pages, network design | Layouts drawn as illustrations | Data-backed siting of sirens and river gauges with coordinates | 40 sirens reach 49% of exposed people at 1.5 km; 6 sensor bridges |
| Pravaah discharge | Needs a surveyed cross-section and a surface-to-mean velocity factor | Field protocols B and C measure both, plus Manning's n | §8.4; scripts in `fieldkit/analysis/` |
| Varshaq rain gauge | Rain not linked to flooded land | Rain-aware flood maps (analogs, learned model §6.6) | 5-year flow: 25 km² dry week vs 105 km² heavy rain |
| Flood-warning solution and Aagah app ("time to evacuate populations, reroute traffic, and secure critical infrastructure") | Which people, which roads | Settlements to warn, roads that close, villages that lose their hospital, in every bulletin | 32 settlements lose hospital access (25-year flood) |
| Rakshak Control Centre ("draw an area, pick districts, or upload your own boundaries"; accepts CAP) | Alert areas drawn by hand | Every forecast also writes a CAP 1.2 alert with one area per settlement to warn | `bulletin_<flow>.cap.xml`; 24 areas for the 25-year flow |
| Dam and reservoir solution | Level at the dam, not the water spread | The same radar model can map reservoir area on every pass (next step: Hirakud) | — |
| Installation and O&M | Timing against floods and storms | Work window and schedule from 42 years of flows and storm tracks | December–April; 78 crew-days |
