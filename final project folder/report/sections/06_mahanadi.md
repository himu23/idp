## 6. Mahanadi delta: flood atlas and the link to river flow

### 6.1 The atlas

The production model of §4.8 (mean of the radar-only TerraMind-B and U-Net, threshold 0.30) was run on
**590 Sentinel-1 passes** (133 in February–March, 457 in June–November,
2017–2026; tracks ascending 85: 184; descending 48: 211; descending 121: 195; platforms S1A 521, S1B 41, S1D 28).
A pass is all slices of one satellite overpass; together they give a water map of the delta every 2–6 days in the
monsoon. The river bed (main channels and sand bars, 178 km²) and each year's
dry-season water are "normal water"; only water outside them counts as flood. A 3 km band along each pass's data
edge is removed: a first version showed a diagonal stripe of false floods along one track's swath edge.

![Flow at Naraj and flooded land on every pass](../results/atlas_figures/atlas_timeseries.png)

![Flood frequency 2017–2026](../results/atlas_figures/atlas_frequency_map.png)

- Land flooded on at least one pass: 905 km²; in at least 20 % of monsoon passes:
  27 km².
- The largest flood seen on a near-complete pass was on 2018-09-08 (275 km² of flooded land).
- The flooded fraction of each pass follows the Naraj flow. Spearman ρ by predictor:
  same-day flow 0.75, previous-day flow 0.76, 3-day peak 0.76, 5-day peak 0.76, 7-day peak 0.75; the 5-day peak is used
  (floodplains drain slowly, so the map follows the recent peak more than the flow of the day).

### 6.2 Independent check with Sentinel-2

For 60 radar passes of June–November a Sentinel-2 image was taken within one day with enough clear
sky (most of them at the end of the monsoon). On the pixels that are clear in the optical image, radar water agrees with
optical water (MNDWI > 0) with IoU **0.49**; taking the optical map as reference, the radar map has
precision 0.60 and recall 0.73. For water outside the normal-water mask — the flood
part — agreement drops to IoU 0.18 (precision 0.51, recall 0.22): the
radar misses much of the shallow water that the optical image sees among crops and on water-logged fields, where the crop
canopy dominates the radar echo. MNDWI has errors of its own (0.65 on the Sen1Floods11 official test, and wet soil
reads as water), so neither map is truth; but the low flood-part recall says the radar atlas under-states shallow
field flooding and is most reliable for open water. The field points (§8.3) are the next check.

### 6.3 Trigger discharge: which flow floods which land

![Trigger discharge](../results/atlas_figures/atlas_trigger_map.png)

Every pixel gets the Naraj flow above which it is flooded (§3.5). The map reads directly as "at this forecast
flow, this land goes under". The river-driven score separates land that floods with the river from land that is wet
in the monsoon whatever the river does: 662 km² has AUC ≥ 0.75, i.e. it floods mainly at
high river flow, including fields far from the channels that flood when high river stages block their drainage.

![River-driven flooding](../results/atlas_figures/atlas_river_driven.png)

### 6.4 Does it predict years it has not seen?

For each year the trigger map was fitted on the other years and the year's passes were predicted from their discharge
alone.

| Year | Passes | Largest flood on a pass (km²) | IoU, discharge model | IoU, climatology |
|---|---|---|---|---|
| 2017 | 39 | 53 | 0.21 | 0.19 |
| 2018 | 57 | 276 | 0.17 | 0.11 |
| 2019 | 63 | 78 | 0.26 | 0.16 |
| 2020 | 46 | 204 | 0.20 | 0.10 |
| 2021 | 46 | 267 | 0.16 | 0.12 |
| 2022 | 43 | 218 | 0.32 | 0.13 |
| 2023 | 41 | 50 | 0.30 | 0.24 |
| 2024 | 43 | 39 | 0.26 | 0.24 |
| 2025 | 45 | 72 | 0.26 | 0.18 |
| 2026 | 34 | 154 | 0.20 | 0.09 |

Over all 457 monsoon passes the discharge model reaches IoU 0.23 (precision
0.57, recall 0.27) against 0.14 for
climatology. **On the 85 high-flow passes (Naraj ≥ 9,682 m³/s, the top 10 % of monsoon
days), the ones that matter for warnings, it reaches 0.23 against 0.07**
(recall 0.29 vs 0.07): climatology misses the extra land that only
floods in big years. Predicted and observed flooded area correlate with r = 0.45.

Pixel IoU is a hard score here: the observed map is itself a radar map with ~0.65 IoU, and floodplain flooding is
patchy. A warning is issued per village, so the same held-out test was scored per settlement (1,082
settlements; flagged when at least 10 % of the people are on flooded land). **On high-flow passes the trigger map
flagged 17% of the settlements that were actually flooded (POD), with 65% false alarms (FAR),
CSI 0.13; climatology: POD 3%, FAR 23%, CSI 0.03.** Over all monsoon
passes: POD 18%, FAR 57%, CSI 0.14.

**Where versus how much.** Ranking the pixels of each held-out pass, the flood frequency of the other years reaches
ROC AUC 0.93 (high flows 0.91), the trigger map
0.79 and the flow-and-rain analogs 0.80. *Where* the delta floods is
very predictable from its past; *how much* of it floods on a given day is only partly predictable from river flow.
Both layers are kept: the frequency map says where to prepare, the trigger map says at which flow to act.

**The river is not the only driver.** The largest flood extents in the record came with moderate Naraj flows:
8 September 2018 and 14–16 September 2021, when depressions brought 100–160 mm of rain a day over the delta
(ERA5). A map driven by Naraj flow alone cannot predict those. The same held-out test was therefore repeated with
analog maps: for each pass of the held-out year, the 7 training passes most similar in flow (or in flow and
7-day rain) are looked up, and land flooded on at least half of them is predicted
flooded.

| Method | IoU, all passes | IoU, high flow (≥ 9,682 m³/s) | IoU, heavy rain (≥ 135 mm in 7 days) | Settlements, high flow: POD / FAR | Settlements, heavy rain: POD / FAR |
|---|---|---|---|---|---|
| Trigger map (flow only) | 0.23 | 0.23 | 0.17 | 17% / 65% | 14% / 70% |
| Analogs on flow | 0.21 | 0.20 | 0.16 | 9% / 68% | 6% / 56% |
| Analogs on flow + local rain | 0.21 | 0.20 | 0.17 | 5% / 78% | 2% / 84% |
| Flood climatology | 0.14 | 0.07 | 0.05 | 3% / 23% | 2% / 17% |

On the heavy-rain passes the best method is the flow-only trigger map (IoU 0.17), and
adding rain to the analogs leaves their IoU about the same as the trigger map's:
at the scale of single passes rain is hard to use because the observed maps are noisy. The effect of rain is clear
when the same method is asked about the same river flow. With the same analog method and the 5-year flow (23,940 m³/s), a dry week (20 mm of rain) gives 25 km² of flooded land with 5,021 people on it; a week with 171 mm (the monsoon 95th percentile) gives 105 km² and 11,802 people.
For warnings this means the river forecast has to be read together with the rainfall forecast, which the ClimMaTech
app already carries.


![Leave-one-year-out test](../results/atlas_figures/atlas_loyo.png)

### 6.5 Design floods and travel time

Gumbel fit to 42 GloFAS annual maxima at Naraj (1984–2025):

| Return period (years) | Naraj flow (m³/s) | (lakh cusec) | Flooded land (km²) |
|---|---|---|---|
| 2 | 17,897 | 6.3 | 38 |
| 5 | 23,940 | 8.5 | 203 |
| 10 | 27,941 | 9.9 | 216 |
| 25 | 32,997 | 11.7 | 216 (lower bound) |
| 50 | 36,747 | 13.0 | 216 (lower bound) |
| 100 | 40,470 | 14.3 | 216 (lower bound) |

The largest flow in the radar record is 28,378 m³/s; above it the map cannot grow
further and is a lower bound (25-yr, 50-yr, 100-yr).

Day-to-day changes of flow below Hirakud correlate best with those at Naraj
1 day later (r = 0.47),
and those at Tikarpara on the same day (r = 0.93),
in June–October 1984–2025 (daily data resolve only whole days). A release seen by a spillway sensor at Hirakud
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
| All monsoon passes (457) | 0.24 (0.51 / 0.32) | 0.23 (0.57 / 0.27) | 0.14 (0.64 / 0.15) |
| High flow (85) | 0.24 (0.43 / 0.35) | 0.23 (0.51 / 0.29) | 0.07 (0.82 / 0.07) |
| Heavy rain (46) | 0.22 (0.40 / 0.33) | 0.17 (0.49 / 0.21) | 0.05 (0.75 / 0.05) |
| Settlements, high flow: POD / FAR | 21% / 71% | 17% / 65% | 3% / 23% |
| Settlements, heavy rain: POD / FAR | 18% / 76% | 14% / 70% | 2% / 17% |
| Ranking AUC, all / high flow | 0.95 / 0.93 | 0.79 / 0.76 | 0.93 / 0.91 |

The learned model is better than the trigger map on all passes and on heavy-rain passes. At village level, at high flows, it catches more flooded villages
than the trigger map (21% against 17%) and raises
more false alarms (71% against
65%); the critical success index, which weighs both, is 0.14 against
0.13. It ranks flood-prone land
best of the three
(ROC AUC 0.95). The physical direction of each input is imposed (more flow or rain, a
flow further above the trigger or a pixel that flooded more often never lowers the probability):
a first run without these constraints scored 0.233 IoU but gave less flooded land for heavy than for typical rain at the 25-year flow (108 against 121 km²), which a warning map must never do.
The inputs it leans on most (drop in held-out ranking AUC when each is shuffled):
flood frequency 0.163; Naraj flow 0.030; 7-day rain 0.022; month 0.008; elevation 0.008. Fitted on all years, it floods
44 km² at the 5-year flow in a dry week,
64 km² with typical rain and 172 km²
with heavy rain (August, averaged over the three radar tracks; typical rain = median 7-day rain of the monsoon passes (58 mm); heavy rain = monsoon 95th percentile (171 mm)), the same roughly four-fold effect of rain as the analog maps of §6.4.
For a warning system this is the model that takes both of
ClimMaTech's inputs, the river forecast and a rain-gauge or forecast rain total, and returns one map.

### 6.7 Limits

- **Discharge is modelled (GloFAS), not gauged.** CWC/WRD daily flows at Naraj are the first thing to request
  (§8.1); with them the trigger map is refitted in minutes.
- **Radar misses water under dense vegetation and in towns, and sees smooth surfaces as water.** The model scores
  0.65 on the official test with radar only; the atlas inherits that.
- **Short floods between passes** (2–12 days apart) are missed; Sentinel-1C/D (2025–26) shorten the gap.
- **Paddy**: transplanted paddy holds water in July–August. Land whose wetness does not follow the river (low
  river-driven score) should not trigger river-flood warnings.
- **Flows beyond the record** (rarer than the largest flood seen since 2017) are lower bounds.
