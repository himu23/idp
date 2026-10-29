## 1. Introduction

### 1.1 The problem in the field

ClimMaTech, the project's industry partner (IIT Mandi), builds flood early-warning systems: non-contact radar
gauges on bridges and dam spillways (Pravaah, Tarang), edge-AI camera nodes (Doordrishti), solar sirens
(Rakshak), a control-room web application and the Aagah mobile app. Their architecture lists a "River View"
layer, a map-based view of river levels and flood risk. Every product measures or forecasts the river **at a
point**: the level and flow at a gauge, 30 minutes to 48 hours ahead. None of them shows what that flow means on
the ground: which land, villages, roads, bridges and embankments go under water. Their own case study of the
26 August 2026 Nepal–China flood compares a 1-D Saint-Venant model with flood widths measured on Sentinel-2
images, which is exactly the link between satellite water maps and hydraulics that this project builds.

The Mahanadi delta below Naraj (Cuttack, Kendrapara, Jagatsinghpur; about 4.1 million people in our 3,038 km²
study box) is the most flood-exposed reach of the Mahanadi basin, where Prof. Basudev Biswal's long-running basin work,
the Hirakud–Naraj flood operations of the Odisha Water Resources Department and the Central Water Commission's
gauges all meet. The IDP review of 14 October asked us to connect one fine-tuned foundation model to such a
real project, to go to the site with a purpose, and to bring in the other civil-engineering disciplines that a
river project involves.

**Refined problem statement.** *For the Mahanadi delta, turn a river-flow forecast at Naraj into a map of what
floods and whom it affects, using a satellite foundation model selected by a fair benchmark, and use that map to
plan where warnings and sensors should go.* Concretely we

1. select a satellite water-mapping model by benchmarking six geospatial foundation models against CNN and U-Net
   baselines, including on a flood in India that the models never saw (§4);
2. run it on every Sentinel-1 radar pass over the delta from 2017 to 2026 (monsoon and dry season) to build a
   flood atlas, and check it against Sentinel-2 images taken within a day (§6);
3. link the atlas to river discharge at Naraj, so that a discharge forecast becomes an inundation map, and test
   that link on years it was not fitted on (§6);
4. translate inundation into engineering impacts: people and buildings, roads and bridges (transportation and
   structures), river banks (geotechnical) (§7);
5. plan siren and river-sensor sites for a ClimMaTech-type deployment (§9); and
6. check and calibrate all of this with measurements and interviews at the site (§8).

### 1.2 Stakeholders

| Stakeholder | Role in the problem | What they need from this work | What we need from them |
|---|---|---|---|
| ClimMaTech (Dr. Vivek Gupta, CTO; Siddik Barbhuiya, lead hydrologist) | Industry partner; sensors, sirens, forecasts | A flood-extent layer and village list per forecast; sensor and siren siting | Product constraints (siren range, data formats), site-survey practice |
| Prof. Basudev Biswal's Mahanadi basin project (IIT Bombay) | The sanctioned real project | Inundation maps and impacts for the delta | Site access, introductions to engineers |
| Odisha Water Resources Dept., CWC Mahanadi division | Embankments, Naraj/Mundali barrages, gauges | Which banks and roads fail at which flow | Observed discharge, embankment inventory, breach history |
| OSDMA, district administrations (Cuttack, Kendrapara, Jagatsinghpur) | Warnings, evacuation, shelters | Villages to warn per forecast; cut-off roads | Evacuation records, shelter list |
| Villages and farmers in the delta | Flooded every few years | Earlier, local warnings | What actually flooded, when and how deep |

### 1.3 Where the project stood at mid-term

At mid-term (5 October 2026) the team had fine-tuned the published Prithvi-EO-2.0 Sen1Floods11
checkpoint on 3,584 Indian chips built from NDEM flood maps. Test IoU on 16 unseen Indian events
rose from 0.337 to 0.375. The review of that work (mid-term meeting) raised five problems that this
second half addresses directly:

1. **The absolute scores were far below the benchmark** (IoU ≈ 0.68–0.71 for Sen1Floods11 models),
   which pointed to problems in how the Indian chips and masks were built rather than in the model.
2. **There was no from-scratch baseline**, so the value of the foundation model was not isolated.
3. **Only optical data were used**, although monsoon floods happen under cloud.
4. **One training run per model**, so run-to-run noise was unknown. (The mentor notebook itself
   shows ±0.02 IoU for the same U-Net, same data, same seed.)
5. The mentors' new plan (7 October): every team member takes one foundation model, all models are
   trained on a common dataset, compared zero-shot and fine-tuned, and then fused into one model.

The NDEM-based Indian dataset lives on a team member's Google Drive and was not available on the lab
server used for this phase. All new experiments therefore use **Sen1Floods11**, the dataset of the
mentor notebook, with two protocols designed to answer the Indian question honestly (Section 2.2).

### 1.4 Objectives of this phase

| No. | Objective | Discipline | Answered in |
|---|---|---|---|
| F1 | Compare six foundation-model families against from-scratch and no-training baselines under one identical recipe | AI / remote sensing | §4.1 |
| F2 | Measure performance on a flood event the models have **never seen** in India | AI / remote sensing | §4.2 |
| F3 | Separate what pre-training gives for free (frozen encoder) from what fine-tuning adds | AI / remote sensing | §4.3 |
| F4 | Fuse the models ("fuse layer") and test whether the fusion beats the best single model | AI / remote sensing | §4.4 |
| F5 | Decide whether radar, optical or both are needed (monsoon cloud) | remote sensing | §4.5 |
| F6 | Calibrate thresholds; errors by event and by permanent vs flood water; label efficiency | AI / remote sensing | §4.6–4.7 |
| F7 | PINN track: verify, reproduce, complete the residual exercise, retrain | hydraulics | §5 |
| F8 | Flood atlas of the Mahanadi delta 2017–2026 with an independent optical check | remote sensing, hydrology | §6.1–6.2 |
| F9 | Discharge-to-inundation model at Naraj, tested on held-out years; design floods | hydrology | §6.3–6.5 |
| F10 | Exposure; hospital and shelter access, everyday travel delay and critical links | transportation systems | §7.1–7.2 |
| F11 | Flood depth, masonry-wall screening, bridge scour (IRC:78) and clearance (IRC:5) | structural | §7.3 |
| F12 | River-bank screening; ground saturation under houses that stay dry; foundation and slope checks | geotechnical | §7.4–7.5 |
| F13 | Bay of Bengal storms as a flood driver | ocean | §7.6 |
| F14 | Work windows, earthwork for raising critical links, deployment quantities and schedule | construction technology & management | §7.7 |
| F15 | Field visit: measure, ask, and feed the results back into the models | all | §8 |
| F16 | Siren and river-sensor siting; forecast-to-bulletin tool; integration with the ClimMaTech platform | construction planning | §9 |

## 2. Data

### 2.1 Sen1Floods11 (hand-labelled subset, v1.1)

446 chips of 512 × 512 pixels (~5 km × 5 km at 10 m) from 11 flood events. Each chip has
Sentinel-2 L1C (13 bands, top-of-atmosphere reflectance × 10⁴), Sentinel-1 GRD (VV, VH, σ⁰ in dB),
a hand label (1 water, 0 dry, −1 unknown), and the JRC permanent-water layer. The archive downloaded
on the lab server matches the published checksum (SHA-256 `d836b0c9…640a4f`).

The labels mark **all surface water during the flood**, including normal rivers and lakes
(96.4 % of JRC permanent-water pixels are labelled water). Section 4.6 therefore also scores every
model on non-permanent water only, which is closer to "flood".

Our audit of the cache (`results/audit.json`):

| Event | Chips | Water share of labelled pixels | Unknown share | Permanent share of water |
|---|---|---|---|---|
| India (Assam, 12 Aug 2016) | 68 | 12.4 % | 16.0 % | 19.5 % |
| USA | 69 | 4.6 % | 2.4 % | 33.0 % |
| Paraguay | 67 | 8.4 % | 5.0 % | 33.5 % |
| Ghana | 53 | 6.3 % | 33.8 % | 12.6 % |
| Sri Lanka | 42 | 11.8 % | 9.5 % | 69.2 % |
| Mekong | 30 | 24.1 % | 9.3 % | 28.6 % |
| Spain | 30 | 13.2 % | 1.7 % | 39.5 % |
| Pakistan | 28 | 7.5 % | 26.7 % | 18.9 % |
| Somalia | 26 | 6.5 % | 21.1 % | 0.0 % |
| Nigeria | 18 | 23.5 % | 14.3 % | 8.4 % |
| Bolivia (held-out) | 15 | 15.9 % | 27.1 % | 6.6 % |

Missing measurements: 2.2 % of radar pixels are NaN and 2.1 % of optical pixels are 0.

### 2.2 Two evaluation protocols

| Protocol | Train | Validation | Test | What it measures |
|---|---|---|---|---|
| **Official** | 252 chips (10 events incl. 40 India) | 89 | 90 (all 10 events) | Comparable with published numbers; test events were also seen in training |
| **Leave-India-out (LIO)** | 212 chips (9 events, no India) | 75 (no India) | **all 68 India chips** | A flood the model has never seen, in India: Assam / Brahmaputra, Aug 2016 |

Both protocols also report the official **Bolivia** hold-out (15 chips, an event never in any training set).
The LIO protocol follows the caution in our data kit: the official split puts the single Indian event
in train, validation and test, so its "India score" is not an unseen-event score.

### 2.3 Mahanadi delta: satellite archive and context layers (no flood labels)

The study box is the central delta around Cuttack–Kendrapara (85.80–86.45 °E, 20.25–20.65 °N, 3,038 km²; one
UTM 45N grid at 10 m for single events and 20 m for the atlas). All sources are open and need no login.

| Layer | Source | Use |
|---|---|---|
| Sentinel-1 RTC γ⁰ (VV, VH), every pass in Feb–Mar and Jun–Nov, 2017 – Oct 2026, three tracks (descending 48 and 121, ascending 85), Sentinel-1A/B/D | Microsoft Planetary Computer, `sentinel-1-rtc` | flood atlas (§6) |
| Sentinel-2 L2A (B03, B11, scene classification) within ±1 day of a radar pass | Planetary Computer, `sentinel-2-l2a` | independent optical check (§6.2) |
| JRC Global Surface Water occurrence 1984–2021 | Planetary Computer, `jrc-gsw` | normal rivers and lakes |
| River discharge, daily, Naraj / Tikarpara / below Hirakud, 1984–2026 | GloFAS v4 reanalysis via the Open-Meteo flood API | discharge-to-inundation model, design floods |
| Rainfall, daily, mean of 6 points over the delta, 2016–2026 | ERA5 via the Open-Meteo archive API | second flood driver (§6.4) |
| Population 2020 (3″ grid) | JRC GHSL GHS-POP R2023A | people exposed, settlements |
| Building footprints | Microsoft Global ML Building Footprints (incomplete here: ~120 k) | mapped buildings exposed |
| Land cover 2021 | ESA WorldCover (Planetary Computer) | farmland, built-up |
| Elevation | Copernicus GLO-30 DEM (Planetary Computer) | context |
| Soil sand / silt / clay, 0–30 cm | ISRIC SoilGrids 2.0 (250 m) | bank screening (§7.4) |
| Roads (with node ids), railways, waterways | OpenStreetMap via Overpass | network analysis, bridges |
| Places, hospitals and clinics, schools, embankments, shelters | OpenStreetMap, Geofabrik eastern-India extract (the Overpass servers were overloaded) | destinations, names |

| Cyclone and depression tracks, North Indian Ocean, 1980–2025 | IBTrACS v4 (NOAA NCEI) | storm drivers (§7.6), work windows (§7.7) |
| Basin areas: Hirakud catchment about 83,400 km², whole Mahanadi basin about 141,600 km² | published figures (sources differ by about 2 %) | watershed view (§7.8) |

Optical images on the large flood dates were 61–95 % cloud over the box, so the atlas uses radar only.

### 2.4 Software, compute and data volume

| Item | What was used |
|---|---|
| Deep learning | PyTorch with TerraTorch (IBM) for the foundation-model backbones; a common decoder and training loop in `floodfm/` |
| Geospatial | rasterio, GDAL, pyproj, geopandas, pyogrio, scipy (Dijkstra on the road graph, image morphology), pystac-client for the Planetary Computer catalogue |
| Statistics and learning on tables | scikit-learn (logistic-regression fusion layer, gradient-boosted flood model, ROC AUC), pandas, numpy |
| Maps and documents | matplotlib, Leaflet 1.9.4 (map viewer), pandoc / python-docx / python-pptx (report and slides) |
| Compute | IIT Bombay lab server: 2 GPUs, 32 CPU cores, 62 GB memory; the benchmark cache sat in RAM because the data disks are slow |
| Data volume | Sen1Floods11 hand-labelled set 446 chips; Mahanadi radar archive 590 passes at 20 m (about 11 GB); atlas probability maps about 1.7 GB |
| Run times | one benchmark run 10–40 minutes; one radar pass mapped in about 5 s on one GPU; atlas build about 26 minutes; impact chain about 5 minutes; learned flood model about 27 minutes on 28 cores |

## 3. Methods

### 3.1 One pipeline for every model

All models read chips through the same code (`floodfm/`), so differences in scores come from the
models:

- **Inputs**: 13 Sentinel-2 bands + VV, VH. Prithvi uses the six HLS bands it was pre-trained on
  (B02, B03, B04, B8A, B11, B12); Satlas and DeCUR are optical-only by design; TerraMind, DOFA and Clay
  receive optical and radar.
- **Normalisation**: each band is standardised with the model's own pre-training statistics where
  they are published (TerraMind, Prithvi), otherwise with statistics of the training split. Missing
  pixels are replaced by the band mean before standardising, so they become exactly 0. (The mentor
  notebook filled missing VH with the VV mean, which becomes 1.31 after standardising.)
- **Training recipe** (identical for all): full 512 × 512 chips; random rotations/flips (D4);
  loss = cross-entropy + soft Dice on the water class with unknown pixels ignored; AdamW with 2-epoch
  warm-up and cosine decay; 40 epochs; batch 8; bf16. Learning rates: 10⁻³ for from-scratch models;
  5 × 10⁻⁵ for pre-trained encoders and 3 × 10⁻⁴ for the new decoder.
- **Model selection**: the epoch with the best validation water IoU. Test chips are used once, after
  training.
- **Seeds**: every fine-tuned model is trained with seeds 0, 1, 2 under both protocols; tables give
  mean ± standard deviation.
- **Metric**: water IoU (TP / (TP + FP + FN)) over labelled pixels, pooled over all test chips;
  also F1, precision, recall, mean per-chip IoU and per-event IoU.

### 3.2 Models

| Group | Model | Parameters | Pre-training | Inputs used |
|---|---|---|---|---|
| No training | Otsu threshold on VH | 0 | — | S1 VH |
| No training | NDWI > 0, MNDWI > 0 | 0 | — | S2 green/NIR, green/SWIR1 |
| No training | Prithvi-EO-2.0-300M-TL-Sen1Floods11 (published) | 324 M | HLS MAE + Sen1Floods11 fine-tune by IBM/NASA | 6 S2 bands |
| From scratch | Simple CNN (3 conv) | 0.02 M | none | 15 bands |
| From scratch | U-Net (4 levels, 32 base channels) | 7.8 M | none | 15 bands |
| Foundation | Prithvi-EO-2.0-300M (ViT-L) | 324 M | masked autoencoder on global HLS | 6 S2 bands |
| Foundation | TerraMind-v1-base (ViT-B) | 103 M | multimodal generative, S1+S2+DEM+LULC… | 13 S2 + 2 S1 |
| Foundation | DOFA-base (ViT-B) | 128 M | wavelength-conditioned MAE, optical + SAR | 13 S2 + 2 S1 |
| Foundation | Clay-v1-base (ViT-B) | 108 M | wavelength-aware MAE, multi-sensor | 13 S2 + 2 S1 |
| Foundation | Satlas Swin-v2-B | 93 M | SatlasPretrain, Sentinel-2 multispectral | 13 S2 |
| Foundation | SSL4EO-S12 DeCUR ResNet-50 | 35 M | contrastive (DeCUR), Sentinel-2 | 13 S2 |

The four ViT encoders feed four of their layers through a learned feature pyramid into the same
UNet-style decoder (channels 512-256-128-64); the hierarchical encoders (Swin, ResNet) feed their four
stages into the same decoder type. Every model outputs two logits per pixel.

**Frozen vs fine-tuned.** "Zero-shot" in the strict sense is impossible for Prithvi, DOFA, Clay,
Satlas and DeCUR: they are encoders and output features, not water masks. We therefore report two
modes: **frozen encoder** (only the decoder is trained — what the pre-trained features already know)
and **full fine-tune**. The published Prithvi flood checkpoint is the one true zero-shot model.

### 3.3 Fusion ("fuse layer")

Fusion combines models of the same seed and is fitted on **validation** predictions only. Three member
sets are used: the six fine-tuned foundation models; all eight trained models (the six plus CNN and U-Net); and
the three models with the best validation IoU ("top-3"). Variants:

- **Mean**: equal-weight average of the water probabilities.
- **Validation-weighted**: average weighted by each member's validation IoU.
- **Learned layer**: logistic regression on the members' logits (equivalent to a learned 1 × 1
  convolution over the stacked predictions), fitted on 400,000 validation pixels.

Merging the weights of different architectures into one network is not possible (their layers do not
correspond), so fusion is done at the prediction level, as discussed in the 7 October team call.

### 3.4 Threshold calibration and error analysis

The decision threshold on water probability is swept from 0.10 to 0.90 on the validation set; the best
threshold is then applied once to the test set. For the LIO protocol, validation contains no Indian
chips, so this is an honest test of whether a threshold transfers to a new region.

### 3.5 Flood atlas and discharge-to-inundation model (Mahanadi delta)

Code: `mahanadi/atlas_pull.py`, `atlas_infer.py`, `atlas_build.py`, `s2_crosscheck.py`.

1. **Every radar pass.** All Sentinel-1 RTC passes over the box in February–March (dry season) and June–November
   (monsoon) of 2017–2026, all slices of a pass mosaicked, on one 20 m grid. The 20 m data are the COG overviews,
   which are exact 2 × 2 averages of the 10 m power (checked against a full-resolution read); they cut the
   download four-fold, which mattered because the lab server's connection to the archive ran at 4–8 MB/s.
2. **Production model.** The mean water probability of the two radar-only models of §4 (TerraMind-B and U-Net,
   official split), each run at 10 m on the up-sampled pass with overlapping 512 × 512 windows, averaged back to
   20 m. Fed with 20 m data this way, the pair scores 0.640 on the official Sen1Floods11 test at threshold 0.5,
   and 0.646 at threshold 0.30, the threshold chosen on the validation set (`scripts/test_resolution.py`;
   native 10 m: 0.664). RTC γ⁰ is shifted to σ⁰ by −0.97 dB. A pair retrained directly on 20 m input scores 0.681
   and is ready for the next atlas run (Appendix B).
3. **Normal water** of each year = water in at least half of that year's February–March passes, or JRC
   occurrence ≥ 50 %. **Flood** on a monsoon pass = water and not normal water of that year. Flood frequency =
   flooded passes / valid passes per pixel.
4. **Discharge.** GloFAS v4 daily discharge at Naraj (Open-Meteo). The predictor (same-day flow, previous-day
   flow, or the peak of the last 3, 5 or 7 days) is chosen by its Spearman correlation with the flooded fraction
   of each pass, because floodplains drain slowly and the map follows the recent peak.
5. **Trigger discharge per pixel.** For each 20 m pixel, the threshold θ that best separates its wet and dry
   monsoon observations under the rule "flooded when the predictor ≥ θ" (ties go to the lower θ, i.e. earlier
   warning). A forecast flow Q then gives the map {θ ≤ Q}. A per-pixel AUC of discharge between wet and dry
   observations separates **river-driven** flooding (AUC near 1) from water that comes regardless of river flow
   (AUC near 0.5: rain water-logging, paddy).
6. **Test on unseen years.** For each year, the maps are fitted on the other years and the held-out year's passes
   are predicted, then compared with the observed flood map, per pixel (IoU, precision, recall) and per settlement
   (flagged when ≥ 10 % of its people are on flooded land; probability of detection POD, false-alarm ratio FAR,
   critical success index CSI). Methods: the trigger map (flow only); **analog maps** — land flooded on at least
   half of the 7 training passes most similar in flow, or in flow and local rain (ERA5 daily rain over the delta,
   window chosen like the flow predictor); and flood climatology (flooded when the pixel's frequency in the other
   years ≥ 50 %).
7. **Design floods.** Gumbel distribution (method of moments) fitted to GloFAS annual maxima at Naraj
   (1984–2025); maps for 2- to 100-year flows. Above the largest flow in the radar record the map is a lower
   bound.
8. **Independent optical check.** Sentinel-2 L2A within ±1 day of a radar pass, clear pixels only (scene classes
   vegetation, bare, water), water = MNDWI > 0; agreement with the radar atlas on the same pixels.
9. **Learned flow + rain + history model.** A gradient-boosted classifier (scikit-learn HistGradientBoosting) per
   pixel and pass, with the flow and 7-day rain of the pass, its month and radar track, and the pixel's training-year
   trigger flow, flood frequencies, height above and distance to the river bed as inputs; the physical direction of
   each input is imposed. Tested leave-one-year-out against the trigger map and climatology on the same passes (§6.6).

### 3.6 Engineering impact analyses

All on the same 20 m grid and for the same scenarios (2- to 100-year floods, the largest flood seen, land flooded in
at least 10 % of monsoon passes); code in `mahanadi/impact_*.py`, `ocean_cyclones.py`, `cm_plan.py` and
`watershed_share.py`. Each specialization gets one question and one method:

| Specialization | Method in one line |
|---|---|
| Exposure (all) | GHSL population, settlements, WorldCover farmland, OpenStreetMap roads, bridges, hospitals and schools on flooded land |
| Transportation systems | Road graph from OpenStreetMap; flooded sections cut; shortest paths to hospitals, towns and dry schools; critical links |
| Structural | Flood depth from the elevation at the flood edge; bending check of brick walls; IRC:78 (Lacey) scour at major bridges |
| Geotechnical | Bank cells ranked by water behind the bank, soil and people; a 200 m ground-saturation advisory with bearing and settlement checks |
| Ocean | IBTrACS storm tracks matched to the radar floods; each large flood labelled by its drivers |
| Construction technology and management | Monthly flood and storm climatology for work windows; earthwork for raising critical links; deployment quantities and schedule |
| Water resources and the watershed | GloFAS flows below Hirakud, at Tikarpara and at Naraj: travel time, design floods and the share of a flood peak from each part of the basin |
| Siting (deployment) | Sirens by greedy maximal coverage of exposed people at 1.0 / 1.5 / 2.0 km; one river gauge per distributary on the bridge nearest Naraj with dry approaches |

Chapter 7 gives the results briefly; Appendix C has the formulas, parameters and full tables.

### 3.7 Everything that was trained

| Training | Runs | What it answers | Results |
|---|---|---|---|
| Six foundation models fully fine-tuned, 2 protocols × 3 seeds | 36 | Which pre-trained model maps flood water best | §4.1 |
| CNN and U-Net from scratch, 2 protocols × 3 seeds | 12 | Do foundation models beat small task-specific networks | §4.1 |
| Six foundation models with frozen encoders, 2 protocols, seed 0 | 12 | How much the pre-trained features already know | §4.3 |
| U-Net and TerraMind with radar only or optical only, leave-India-out, 3 seeds | 12 | Radar against optical | §4.5 |
| U-Net and TerraMind with radar only, official split, seed 0 | 2 | The models that map the monsoon (the atlas pair) | §4.5, §6.1 |
| Prithvi, TerraMind and U-Net with 10, 25 and 50 % of the labels, 2 seeds | 18 | Do foundation models need fewer labels | §4.7 |
| **Benchmark total** (all re-checked, Appendix A) | **92** | | |
| Fusion layers (logistic regression on validation predictions) | one per seed and protocol | Does combining models help | §4.4 |
| Radar pair retrained on 20 m input | 2 | The input resolution of the atlas | Appendix B |
| Learned flow + rain + history flood model: 10 held-out years and a final model, without and with physical constraints | 22 | Can flow, rain and flood history together map a pass better than flow alone | §6.6 |
| PINN for the Saint-Venant equations, case 3 retrained (Adam + L-BFGS-B, and Adam only) | 2 | Does the mentor's physics-informed network reproduce and transfer | §5 |
| Inference: every Sentinel-1 pass through both radar models | 1,180 maps | The flood atlas | §6.1 |
