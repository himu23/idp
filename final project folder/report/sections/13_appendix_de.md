## Appendix D. Reproducing every result

Everything runs from the scripts in this folder; the lab server holds the data (`/home1/vineet/floodfm`) and the
laptop builds the documents. Each stage writes files that the next one reads.

| Stage | Scripts | Writes |
|---|---|---|
| Benchmark data | `scripts/build_cache.py`, `server/get_data.sh` | Sen1Floods11 cache (446 chips) |
| Benchmark training | `floodfm/train.py` through `scripts/jobqueue.py server/jobs_main.txt` | 92 runs, each with `results.json` and predictions |
| Benchmark analysis | `scripts/analyze.py`, `scripts/make_tables.py`, `scripts/eval_no_training.py` | tables, figures, thresholds, fusion |
| Training audit | `scripts/audit_training.py` | `results/analysis/audit_training.json` (Appendix A) |
| 20 m retraining | `floodfm/train.py --s1_res 20` (`server/jobs_r20.txt`, `server/run_r20_seeds.sh`), `scripts/test_resolution.py --json`, `scripts/summarise_r20_seeds.py` | `results/analysis/radar20m*.json` (Appendix B) |
| Context layers | `mahanadi/fetch_context.py`, `fetch_osm_pbf.py` | discharge, rain, OpenStreetMap, population, land cover, DEM, soils, storm tracks |
| Radar archive | `mahanadi/atlas_pull.py` | 590 Sentinel-1 passes at 20 m |
| Water maps | `mahanadi/atlas_infer.py` through `server/run_r20_candidate.sh` (the 20 m-trained pair) | 1,180 probability maps |
| Atlas, trigger map, validation, design floods | `mahanadi/atlas_build.py` | `results/atlas/` |
| Learned flood model | `mahanadi/learned_flood_model.py` | `results/atlas/learned/` |
| Impacts and siting | `mahanadi/impact_exposure.py`, `impact_transport.py`, `impact_siting.py`, `impact_geotech.py`, `impact_depth.py`, `impact_structures.py`, `impact_ground.py`, `ocean_cyclones.py`, `cm_plan.py`, `watershed_share.py`, `travel_time.py` | `results/impact/` |
| Independent check | `mahanadi/s2_crosscheck.py` | `results/impact/s2_crosscheck.json` |
| Bulletins and CAP alerts | `mahanadi/forecast_to_impact.py` | `results/impact/bulletins/` |
| Field check points, figures, viewer | `mahanadi/make_checkpoints.py`, `make_atlas_figures.py`, `make_discipline_figures.py`, `make_dashboard.py` | `fieldkit/checkpoints/`, `results/atlas_figures/`, `dashboard/index.html` |
| Whole chain on the server | `mahanadi/run_atlas_pipeline.sh`, `run_disciplines.sh` (`SKIP_BUILD=1 SKIP_S2=1` re-runs only the impacts) | all of the above |
| First atlas against the rebuilt one | `scripts/compare_atlases.py` | `results/archive_atlas_10m/compare.json` (Appendix B) |
| Flow–impact tables | `mahanadi/impact_curve.py` | `results/impact/impact_curve.csv`, `settlement_thresholds.csv`, `road_cut_flows.csv`, `facility_thresholds.csv` |
| Naraj flow forecast | `mahanadi/forecast_model.py` | `results/forecast/` (§6.7) |
| Risk and economics | `mahanadi/risk_economics.py` (after `impact_depth.py`) | `results/impact/risk_economics.json`, `damage_by_scenario.csv`, `alert_days_per_year.csv` (§7.9, C.9) |
| Other basins | `mahanadi/basins.py`, `server/run_basins_pull.sh`, `run_basins_context.sh`, `run_basin_atlas.sh` | `results/basins/<basin>/` (§6.8) |
| Live warnings | `live/make_basin_config.py`, `live/run_live.py` (`server/run_live.sh` daily) | `live/out/` (§9.7) |
| Documents | `report/write_sections.py`, `build_report.py`, `build_slides.py`, `build_website.py`, `build_handouts.py` | this report, the slides, the website, the summary and team guide |

The exact commands are in `README.md`. Every number in this report is read from these files when the report is built,
so a re-run updates the text, the tables, the slides and the website together.

## Appendix E. Glossary

| Term | Meaning in this report |
|---|---|
| Sentinel-1 | European radar satellites; the radar sees the ground through cloud, and calm water looks dark because it reflects the signal away |
| Sentinel-2 | European optical satellites (like a camera with extra colours); blocked by cloud |
| VV, VH | The two radar polarisations Sentinel-1 records |
| RTC, γ⁰, σ⁰ | Radiometric terrain correction, and two conventions for radar brightness; the atlas converts γ⁰ to σ⁰ to match the training data |
| Sen1Floods11 | A public set of 446 hand-labelled flood images from 11 floods, used to train and test the models |
| Foundation model | A large network pre-trained on millions of unlabelled satellite images, then fine-tuned for a task (Prithvi, TerraMind, DOFA, Clay, Satlas, DeCUR) |
| Fine-tuned, frozen | Fine-tuned: every weight is trained further; frozen: the pre-trained encoder is kept and only the decoder learns |
| U-Net, CNN | Small convolutional networks trained from scratch, the baselines |
| Fusion | Combining the predictions of several models (mean, weighted or a learned layer) |
| Leave-India-out | Training without any Indian image and testing on the Assam 2016 flood, so the test flood is unseen |
| IoU | Intersection over union: overlap between predicted and true water divided by their union (1 = perfect) |
| mIoU | Mean of the IoU for water and for dry land, the metric of the foundation-model papers |
| Precision, recall | Of the pixels called water, the share that is water; of the true water, the share that was found |
| POD, FAR, CSI | For villages: probability of detection, false-alarm ratio, critical success index (hits over hits + misses + false alarms) |
| ROC AUC | How well a map ranks flooded land above dry land (0.5 = chance, 1 = perfect) |
| GloFAS | Global Flood Awareness System; modelled daily river flow, used here at Naraj, Tikarpara and below Hirakud |
| ERA5 | A global weather reanalysis; daily rain over the delta |
| Trigger discharge | For each 20 m pixel, the Naraj flow above which it is usually flooded |
| Flood climatology, frequency | How often a pixel was flooded on past passes |
| Analog map | The flood seen on past passes with a similar flow (and rain) |
| Leave-one-year-out | Each year is predicted by a model fitted on the other years only |
| Return period, Gumbel | A T-year flood is exceeded on average once in T years; the Gumbel distribution is fitted to yearly maxima to estimate it |
| Lakh cusec | 100,000 cubic feet per second, about 2,832 m³/s; the unit of Odisha flood bulletins |
| HFL | High flood level |
| Scour | Erosion of the river bed around bridge piers and abutments during a flood |
| IRC:78, IRC:5 | Indian Roads Congress codes for bridge foundations (scour) and bridge design (clearance) |
| Bearing capacity | The load a soil can carry under a footing; it drops when the soil is saturated |
| Rapid drawdown | A river falling faster than its bank drains, the condition in which banks most often slide |
| IBTrACS | International record of tropical cyclone tracks |
| CAP | Common Alerting Protocol, the standard format for warnings that the Rakshak Control Centre accepts |
| PINN | Physics-informed neural network; here trained to satisfy the Saint-Venant equations of river flow |
