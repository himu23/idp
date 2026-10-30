## 6. Mahanadi delta: flood atlas and the link to river flow

### 6.1 The atlas

The production model of §4.8 (mean of the radar-only TerraMind-B and U-Net, retrained on 20 m input as in Appendix B, threshold 0.45) was run on
**590 Sentinel-1 passes** (133 in February–March, 457 in June–November,
2017–2026; tracks ascending 85: 184; descending 48: 211; descending 121: 195; platforms S1A 521, S1B 41, S1D 28).
A pass is all slices of one satellite overpass; together they give a water map of the delta every 2–6 days in the
monsoon. The river bed (main channels and sand bars, 178 km²) and each year's
dry-season water are "normal water"; only water outside them counts as flood. A 3 km band along each pass's data
edge is removed: a first version showed a diagonal stripe of false floods along one track's swath edge.

![Flow at Naraj and flooded land on every pass](../results/atlas_figures/atlas_timeseries.png)

![Flood frequency 2017–2026](../results/atlas_figures/atlas_frequency_map.png)

- Land flooded on at least one pass: 1,137 km²; in at least 20 % of monsoon passes:
  26 km².
- The largest flood seen on a near-complete pass was on 2018-09-08 (278 km² of flooded land).
- The flooded fraction of each pass follows the Naraj flow. Spearman ρ by predictor:
  same-day flow 0.758, previous-day flow 0.760, 3-day peak 0.765, 5-day peak 0.764, 7-day peak 0.760; the 3-day peak is used
  (the five are practically tied: floodplains drain slowly, so any recent peak works).

### 6.2 Independent check with Sentinel-2

For 60 radar passes of June–November a Sentinel-2 image was taken within one day with enough clear
sky (most of them at the end of the monsoon). On the pixels that are clear in the optical image, radar water agrees with
optical water (MNDWI > 0) with IoU **0.56**; taking the optical map as reference, the radar map has
precision 0.75 and recall 0.69. For water outside the normal-water mask — the flood
part — agreement drops to IoU 0.20 (precision 0.63, recall 0.22): the
radar misses much of the shallow water that the optical image sees among crops and on water-logged fields, where the crop
canopy dominates the radar echo. MNDWI has errors of its own (0.65 on the Sen1Floods11 official test, and wet soil
reads as water), so neither map is truth; but the low flood-part recall says the radar atlas under-states shallow
field flooding and is most reliable for open water. The field points (§8.3) are the next check.

### 6.3 Trigger discharge: which flow floods which land

![Trigger discharge](../results/atlas_figures/atlas_trigger_map.png)

Every pixel gets the Naraj flow above which it is flooded (§3.5). The map reads directly as "at this forecast
flow, this land goes under". The river-driven score separates land that floods with the river from land that is wet
in the monsoon whatever the river does: 749 km² has AUC ≥ 0.75, i.e. it floods mainly at
high river flow, including fields far from the channels that flood when high river stages block their drainage.

![River-driven flooding](../results/atlas_figures/atlas_river_driven.png)

### 6.4 Does it predict years it has not seen?

For each year the trigger map was fitted on the other years and the year's passes were predicted from their discharge
alone.

| Year | Passes | Largest flood on a pass (km²) | IoU, discharge model | IoU, climatology |
|---|---|---|---|---|
| 2017 | 39 | 81 | 0.17 | 0.14 |
| 2018 | 57 | 278 | 0.13 | 0.06 |
| 2019 | 63 | 129 | 0.18 | 0.09 |
| 2020 | 46 | 377 | 0.14 | 0.06 |
| 2021 | 46 | 411 | 0.10 | 0.07 |
| 2022 | 43 | 280 | 0.28 | 0.08 |
| 2023 | 41 | 87 | 0.25 | 0.16 |
| 2024 | 43 | 61 | 0.21 | 0.16 |
| 2025 | 45 | 114 | 0.20 | 0.10 |
| 2026 | 34 | 246 | 0.16 | 0.05 |

Over all 457 monsoon passes the discharge model reaches IoU 0.17 (precision
0.55, recall 0.20) against 0.08 for
climatology. **On the 66 high-flow passes (Naraj ≥ 9,682 m³/s, the top 10 % of monsoon
days), the ones that matter for warnings, it reaches 0.20 against 0.04**
(recall 0.25 vs 0.04): climatology misses the extra land that only
floods in big years. Predicted and observed flooded area correlate with r = 0.39.

Pixel IoU is a hard score here: the observed map is itself a radar map with ~0.65 IoU, and floodplain flooding is
patchy. A warning is issued per village, so the same held-out test was scored per settlement (1,082
settlements; flagged when at least 10 % of the people are on flooded land). **On high-flow passes the trigger map
flagged 21% of the settlements that were actually flooded (POD), with 62% false alarms (FAR),
CSI 0.16; climatology: POD 2%, FAR 40%, CSI 0.02.** Over all monsoon
passes: POD 19%, FAR 57%, CSI 0.15.

**Where versus how much.** Ranking the pixels of each held-out pass, the flood frequency of the other years reaches
ROC AUC 0.91 (high flows 0.90), the trigger map
0.72 and the flow-and-rain analogs 0.77. *Where* the delta floods is
very predictable from its past; *how much* of it floods on a given day is only partly predictable from river flow.
Both layers are kept: the frequency map says where to prepare, the trigger map says at which flow to act.

**The river is not the only driver.** The largest flood extents in the record came with moderate Naraj
flows (the largest flow seen is 28,378 m³/s): 14 September 2021 (411 km², Naraj flow 11,614 m³/s, 231 mm of ERA5 rain in the week before, with a Bay of Bengal depression) and 26 August 2020 (377 km², Naraj flow 14,487 m³/s, 187 mm of ERA5 rain in the week before). A map driven by Naraj flow
alone cannot predict those. The same held-out test was therefore repeated with
analog maps: for each pass of the held-out year, the 7 training passes most similar in flow (or in flow and
7-day rain) are looked up, and land flooded on at least half of them is predicted
flooded.

| Method | IoU, all passes | IoU, high flow (≥ 9,682 m³/s) | IoU, heavy rain (≥ 135 mm in 7 days) | Settlements, high flow: POD / FAR | Settlements, heavy rain: POD / FAR |
|---|---|---|---|---|---|
| Trigger map (flow only) | 0.17 | 0.20 | 0.15 | 21% / 62% | 14% / 63% |
| Analogs on flow | 0.16 | 0.18 | 0.13 | 14% / 58% | 8% / 46% |
| Analogs on flow + local rain | 0.17 | 0.19 | 0.16 | 12% / 67% | 10% / 65% |
| Flood climatology | 0.08 | 0.04 | 0.03 | 2% / 40% | 1% / 50% |

On the heavy-rain passes the best method is the flow-and-rain analogs (IoU 0.16), and
adding rain to the analogs raises their IoU from 0.13 to 0.16, only 0.01 above the trigger map:
at the scale of single passes rain is hard to use because the observed maps are noisy. The effect of rain is clear
when the same method is asked about the same river flow. With the same analog method and the 5-year flow (23,940 m³/s), a dry week (20 mm of rain) gives 27 km² of flooded land with 5,232 people on it; a week with 171 mm (the monsoon 95th percentile) gives 93 km² and 13,540 people.
For warnings this means the river forecast has to be read together with the rainfall forecast, which the ClimMaTech
app already carries.


![Leave-one-year-out test](../results/atlas_figures/atlas_loyo.png)

### 6.5 Design floods and travel time

Gumbel fit to 29 GloFAS annual maxima at Naraj (1997–2025):

| Return period (years) | Naraj flow (m³/s) | (lakh cusec) | Flooded land (km²) |
|---|---|---|---|
| 2 | 17,897 | 6.3 | 50 |
| 5 | 23,940 | 8.5 | 218 |
| 10 | 27,941 | 9.9 | 240 |
| 25 | 32,997 | 11.7 | 240 (lower bound) |
| 50 | 36,747 | 13.0 | 240 (lower bound) |
| 100 | 40,470 | 14.3 | 240 (lower bound) |

The largest flow in the radar record is 28,378 m³/s; above it the map cannot grow
further and is a lower bound (25-yr, 50-yr, 100-yr).

Day-to-day changes of flow below Hirakud correlate best with those at Naraj
1 day later (r = 0.47),
and those at Tikarpara on the same day (r = 0.93),
in June–October 1997–2025 (daily data resolve only whole days). A release seen by a spillway sensor at Hirakud
therefore gives about a day of lead time for the delta, on top of the hydrological forecast.

### 6.6 A learned flow + rain + history model

The trigger map uses the Naraj flow alone, and the analogs use rain only through similar past passes. A gradient-boosted
classifier (scikit-learn HistGradientBoosting, `mahanadi/learned_flood_model.py`) was trained on pixels of every monsoon
pass with the flow and 7-day rain of the pass, its month and radar track, and what the training years say about each
pixel: trigger discharge, flood frequency overall, at high flows and in heavy rain, height above the nearest river bed
and distance to it. Each year is predicted by a model fitted on the other years, a pixel is called flooded when its
probability is at least 0.5 (the per-pixel error-minimising rule of the trigger fit), and the three methods are scored
on the same held-out passes. Cells give IoU (precision / recall).

| Held-out passes | Learned model | Trigger map | Flood climatology |
|---|---|---|---|
| All monsoon passes (457) | 0.20 (0.45 / 0.27) | 0.17 (0.55 / 0.20) | 0.08 (0.61 / 0.09) |
| High flow (66) | 0.24 (0.40 / 0.37) | 0.20 (0.50 / 0.25) | 0.04 (0.86 / 0.04) |
| Heavy rain (46) | 0.22 (0.36 / 0.35) | 0.15 (0.50 / 0.18) | 0.03 (0.78 / 0.03) |
| Settlements, high flow: POD / FAR | 28% / 71% | 21% / 62% | 2% / 40% |
| Settlements, heavy rain: POD / FAR | 23% / 74% | 14% / 63% | 1% / 50% |
| Ranking AUC, all / high flow | 0.95 / 0.92 | 0.72 / 0.72 | 0.91 / 0.90 |

The learned model is better than the trigger map on all passes and on heavy-rain passes. At village level, at high flows, it catches more flooded villages
than the trigger map (28% against 21%) and raises
more false alarms (71% against
62%); the critical success index, which weighs both, is 0.17 against
0.16. It ranks flood-prone land
best of the three
(ROC AUC 0.95). The physical direction of each input is imposed (more flow or rain, a
flow further above the trigger or a pixel that flooded more often never lowers the probability):
a first run without these constraints (on the earlier atlas of Appendix B) scored 0.233 IoU but gave less flooded land for heavy than for typical rain at the 25-year flow (108 against 121 km²), which a warning map must never do.
The inputs it leans on most (drop in held-out ranking AUC when each is shuffled):
flood frequency 0.138; Naraj flow 0.036; 7-day rain 0.032; month 0.016; radar track 0.014. Fitted on all years, it floods
30 km² at the 5-year flow in a dry week,
44 km² with typical rain and 142 km²
with heavy rain (August, averaged over the three radar tracks; typical rain = median 7-day rain of the monsoon passes (58 mm); heavy rain = monsoon 95th percentile (171 mm)), a roughly five-fold
effect of rain between a dry and a heavy-rain week (the analog maps of §6.4 give three-fold: 27 against 93 km²).
For a warning system this is the model that takes both of
ClimMaTech's inputs, the river forecast and a rain-gauge or forecast rain total, and returns one map.

### 6.7 Forecasting the flow at Naraj

A flood map is only as early as the flow forecast behind it. The trigger map turns a Naraj flow into a map; this
section asks how far ahead that flow can be known from what is measured upstream today. Water reaches Naraj from the
Hirakud reach and the Tel and Ong tributaries in about a day (§6.5), so the flows at Naraj, Tikarpara and below Hirakud
on the issue day and the two days before, their last-day changes, ERA5 rain over the catchment between Hirakud and Naraj
(eight points; the day, the day before, 3- and 7-day sums) and the season predict the change in the Naraj flow one,
two and three days ahead. One gradient-boosted model per lead time (scikit-learn HistGradientBoosting,
`mahanadi/forecast_model.py`) was trained on 1997–2015 and tested on the June–November
days of 2016–2026, which it never saw. Baselines: persistence (the flow stays as it is)
and linear routing (log-flows at the three gauges). A second variant adds the rain of the coming days as if it were
forecast perfectly, the most a rain forecast can add.

| Lead | Persistence | Linear routing | Model (KGE) | Model + rain forecast | 2-year flood, persistence: caught / false | Model | Model + rain forecast |
|---|---|---|---|---|---|---|---|
| 1 day | 0.963 | 0.980 | 0.987 (0.99) | 0.988 | 77% / 23% | 77% / 0% | 77% / 5% |
| 2 days | 0.882 | 0.882 | 0.941 (0.97) | 0.948 | 58% / 42% | 62% / 33% | 73% / 32% |
| 3 days | 0.788 | 0.747 | 0.885 (0.94) | 0.892 | 42% / 58% | 50% / 50% | 58% / 38% |

Cells give Nash–Sutcliffe efficiency of the daily flow (1 = perfect), and for the 17,897 m³/s
two-year flow the share of exceedance days caught and the share of forecast exceedances that were false. The model keeps
its skill where persistence fades: three days ahead its efficiency is 0.89 against
0.79, and one day ahead it catches the two-year flood as often as persistence with
0% instead of 23% false alarms.
A rain forecast adds little to the efficiency but most where it matters: two and three days ahead it raises the
two-year floods caught from 62% to 73%
and from 50% to 58%.
The flows are GloFAS reanalysis, the series the atlas is fitted on; with CWC records or Pravaah-type gauges upstream the
same code trains on measured flows, and the forecast runs in the live feed of §9.7 next to the GloFAS ensemble.

![Two test monsoons: the Naraj flow and the forecasts made one and three days earlier](../results/forecast/forecast_naraj.png)

### 6.8 The same pipeline on two more basins

Nothing in the method is specific to the Mahanadi. A basin is a box, a GloFAS cell on the main river (checked by its
mean flow), the months of the dry season and of the flood season (`mahanadi/basins.py`). The Brahmani–Baitarani delta
next door (Jajpur, Kendrapara and Bhadrak districts) and the Brahmaputra around Majuli in Assam, the region of the
benchmark's unseen Indian flood, went through the same chain: every Sentinel-1 pass since 2017 at 20 m, the production
radar pair at threshold 0.45, the trigger map with its held-out-year test, Gumbel design floods, exposure, the
flow-impact tables of §9.7 and the Sentinel-2 check (`server/run_basins_pull.sh`, `run_basins_context.sh`,
`run_basin_atlas.sh`).

| Basin | Gauge | Passes | Flooded at least once (km²) | 25-year flow (m³/s) | Flooded land, 25-year (km²) | People on it | Held-out high flows: trigger vs climatology (IoU) | Sentinel-2 agreement (IoU) |
|---|---|---|---|---|---|---|---|---|
| Mahanadi delta | Mahanadi at Naraj | 590 | 1,137 | 32,997 | 240 | 30,427 | 0.20 vs 0.04 | 0.56 |
| Brahmani–Baitarani delta | Brahmani at Jenapur | 394 | 2,277 | 6,959 | 950 | 129,662 | 0.17 vs 0.01 | 0.65 |
| Brahmaputra at Majuli | Brahmaputra at Neamatighat | 346 | 2,145 | 42,202 | 1,120 | 77,655 | 0.31 vs 0.05 | 0.67 |

**Brahmani–Baitarani delta.** 394 usable passes; 2,277 km² flooded at least once; the largest flood seen, on 2026-08-16, covered 1,168 km² with 131,620 people on it. The 25-year flow (6,959 m³/s) maps 950 km² with 129,662 people, a lower bound because the largest flow on a pass was 6,108 m³/s; warnings start at 3,500, 3,500 and 4,250 m³/s.

**Brahmaputra at Majuli.** 346 usable passes; 2,145 km² flooded at least once; the largest flood seen, on 2017-07-09, covered 1,246 km² with 137,306 people on it. The 25-year flow (42,202 m³/s) maps 1,120 km² with 77,655 people, a lower bound because the largest flow on a pass was 35,891 m³/s; warnings start at 21,500, 22,750 and 29,000 m³/s.

The Brahmani–Baitarani delta is fed by two rivers and the trigger map is fitted on the Brahmani alone, so floods that
the Baitarani drives are predicted less well; the Brahmaputra floodplain is braided and its char islands move between
years. Both basins run in the live feed under the same impact-based rule, counted beyond what an ordinary monsoon
already floods (§9.7).

### 6.9 Limits

- **Discharge is modelled (GloFAS), not gauged.** CWC/WRD daily flows at Naraj are the first thing to request
  (§8.1); with them the trigger map is refitted in minutes.
- **Radar misses water under dense vegetation and in towns, and sees smooth surfaces as water.** The model scores
  0.65 on the official test with radar only; the atlas inherits that.
- **Short floods between passes** (2–12 days apart) are missed; Sentinel-1C/D (2025–26) shorten the gap.
- **Paddy**: transplanted paddy holds water in July–August. Land whose wetness does not follow the river (low
  river-driven score) should not trigger river-flood warnings.
- **Flows beyond the record** (rarer than the largest flood seen since 2017) are lower bounds.
- **The flow forecast is scored against GloFAS itself** (§6.7): its skill against measured Naraj flows is unknown
  until CWC records or upstream gauges arrive, and GloFAS's own forecast skill at Naraj has not been verified here.
