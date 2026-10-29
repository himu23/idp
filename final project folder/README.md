# Final project folder — Prithvi Flood-IN (CE IDP, IIT Bombay × ClimMaTech)

Everything produced after the mid-term lives here. New to the project? Read **`docs/TEAM_GUIDE.docx`** first. Then **`PLAN.md`** (what the evaluators look for, who
does what until 9 Nov) and **`fieldkit/FIELD_VISIT_KIT.md`** (the visit). The final report is
`report/FINAL_REPORT.docx` (+ `.md`), the slides `report/Prithvi_Flood-IN_Final.pptx`, the interactive map viewer
`dashboard/index.html` (one file, opens in any browser), the project website `website/index.html` (also published as
a private link).

## What was done

| Track | What | Where |
|---|---|---|
| Model selection | CNN, U-Net and 6 geospatial foundation models (Prithvi-EO-2.0, TerraMind, DOFA, Clay, Satlas, DeCUR), frozen and fine-tuned, 3 seeds, 2 protocols incl. an unseen Indian flood; fusion; radar vs optical; label efficiency (92 runs) | `floodfm/`, `scripts/`, `results/analysis` |
| Radar model for the monsoon | Radar-only TerraMind-B + U-Net fusion, tested on 20 m input (`scripts/test_resolution.py`) | `results/analysis/radar20m.json` |
| Mahanadi flood atlas | Every Sentinel-1 pass over the delta (Feb–Mar, Jun–Nov, 2017–Oct 2026) → water, flood frequency, river bed, swath-edge cleaning | `mahanadi/atlas_pull.py`, `atlas_infer.py`, `atlas_build.py`, `results/atlas` |
| Flow → inundation | GloFAS discharge at Naraj, per-pixel trigger discharge, leave-one-year-out test (pixels and settlements), Gumbel design floods, travel time | `mahanadi/atlas_build.py`, `travel_time.py` |
| Independent check | Sentinel-2 MNDWI within ±1 day of radar passes | `mahanadi/s2_crosscheck.py` |
| Impacts, seven specializations | Transportation (hospital/shelter access, travel delay, critical links); Structural (DEM depth, masonry walls, IRC:78 scour); Geotechnical (bank screening, ground saturation under dry houses); Ocean (IBTrACS storms vs floods); Construction management (work windows, link-raising earthwork, BoQ, schedule) | `mahanadi/impact_*.py`, `ocean_cyclones.py`, `cm_plan.py`, `results/impact` |
| Deployment | Siren maximal coverage, river-sensor bridges, forecast-to-bulletin tool, map viewer | `mahanadi/impact_siting.py`, `forecast_to_impact.py`, `make_dashboard.py`, `dashboard/` |
| Field visit | Protocols, interview guides, data sheets, analysis scripts, GPS check points (GPX/KML), printable dossier | `fieldkit/` |
| PINN (Saint-Venant) | Environment verified, 6 cases reproduced, residuals completed, case 3 retrained | `pinn/` |
| Website | Project site in the partner's interface style (Inter, pill navigation, tile grids), with a scenario explorer drawn from the atlas and the map viewer as a second page | `report/build_website.py`, `website/` |
| Training audit | Every run re-checked from its stored outputs; published TerraMind scores reproduced within a point | `scripts/audit_training.py`, `results/analysis/audit_training.json` |
| Learned flood model | Flow + rain + pixel history, gradient boosting, leave-one-year-out against the trigger map | `mahanadi/learned_flood_model.py`, `results/atlas/learned/` |
| Partner gap analysis | What climmatech.com offers, what is missing, what this project adds with evidence; CAP alerts | report §9.6, website, `results/impact/bulletins/*.cap.xml` |
| Admin | Revised IDP proposal (draft), draft emails to the guide, CWC/WRD and ClimMaTech | `admin/` |

## Folder map

```
PLAN.md             final-phase plan: grading criteria, refined problem statement, roles, timeline, risks
floodfm/            shared package: data layer, model zoo (TerraTorch), trainer, metrics
scripts/            build_cache, probe_models, eval_no_training, analyze, make_tables, jobqueue, test_resolution
server/             setup scripts, job list, bg.sh (detached jobs)
mahanadi/           atlas_pull / atlas_infer / atlas_build, impact_exposure / transport / siting / geotech / depth /
                    structures / ground, ocean_cyclones, cm_plan, forecast_to_impact, travel_time, s2_crosscheck,
                    make_checkpoints, make_atlas_figures, make_discipline_figures, make_dashboard (+ template),
                    run_atlas_pipeline.sh, run_disciplines.sh; older event pilot (infer.py)
results/analysis    benchmark tables and figures      results/atlas    atlas rasters (20 m GeoTIFF) and tables
results/impact      impact tables, GeoJSON, bulletins  results/atlas_figures   maps, charts, dossier.pdf
fieldkit/           FIELD_VISIT_KIT.md/.docx, Field_data_sheets.docx, templates/ (CSV sheets), analysis/ (7 scripts),
                    examples/ (made-up, EXAMPLE),
                    checkpoints/ (GPX, KML, CSV)
dashboard/          index.html map viewer
website/            index.html (project site), viewer.html (map viewer), img/ (built by report/build_website.py)
docs/               EXECUTIVE_SUMMARY, SLIDES_TEXT (slide text + speaker notes), TEAM_GUIDE (the project from the
                    basics), each .md and .docx (built by report/build_handouts.py)
report/             sections/, write_sections.py, build_report.py, build_slides.py, slides_content.py, build_website.py,
                    outputs
pinn/               PINN exercise, logs, figures, PINN_RESULTS.md
admin/              IDP_Proposal_revised_DRAFT.docx, emails.md (drafts to the guide, CWC/WRD, ClimMaTech)
```

## Re-running (lab server `vineet@10.119.2.98`, everything under `/home1/vineet/floodfm`)

```bash
# benchmark
bash code/server/setup_env.sh && bash code/server/get_data.sh
env/bin/python code/scripts/build_cache.py code data/sen1floods11_v1.1 data/cache && cp -r data/cache /dev/shm/floodfm_cache
env/bin/python code/scripts/eval_no_training.py code
env/bin/python code/scripts/jobqueue.py code/server/jobs_main.txt 0,1,1
env/bin/python code/scripts/analyze.py code
env/bin/python code/scripts/test_resolution.py code runs/official_unet_s1_full_s0 runs/official_terramind_s1_full_s0
env/bin/python code/scripts/audit_training.py code          # re-checks every run, writes runs/_analysis/audit_training.json
# Mahanadi atlas and impacts
env/bin/python code/mahanadi/fetch_context.py --out data/mahanadi_context        # + fetch_osm_pbf.py if Overpass is down
env/bin/python code/mahanadi/atlas_pull.py --out data/mahanadi_atlas20 --res 20 --months 2,3,6,7,8,9,10,11
env/bin/python code/mahanadi/atlas_infer.py code data/mahanadi_atlas20 --out runs/_atlas/prob \
    --runs runs/official_terramind_s1_full_s0 runs/official_unet_s1_full_s0
bash code/mahanadi/run_atlas_pipeline.sh final && bash code/mahanadi/run_disciplines.sh final
# after a change to an impact script only (skips the 26-min atlas build and the 18-min Sentinel-2 check):
SKIP_BUILD=1 SKIP_S2=1 bash code/mahanadi/run_atlas_pipeline.sh final && bash code/mahanadi/run_disciplines.sh final
ATLAS_DIR=runs/_atlas/build_final env/bin/python code/mahanadi/learned_flood_model.py --context data/mahanadi_context \n    --out runs/_atlas/learned_final                              # learned flow + rain model, ~35 min on 24 cores
# radar pair retrained on 20 m input (server/jobs_r20.txt; report Appendix B): better on the atlas input. To swap it in:
env/bin/python code/mahanadi/atlas_infer.py code data/mahanadi_atlas20 --out runs/_atlas/prob_r20     --runs runs/official_terramind_s1_full_s0_r20 runs/official_unet_s1_full_s0_r20
# then in run_atlas_pipeline.sh use --prob runs/_atlas/prob_r20 and --thr 0.45 (chosen on validation), re-run both
# pipeline scripts and the learned model, pull results/ and rebuild the report, slides and website
# on this laptop: pull, then rebuild text, report and slides
python scripts/make_tables.py results/analysis report/sections/02_tables.md
python report/write_sections.py && python report/build_report.py && python report/build_slides.py && python report/build_website.py && python report/build_handouts.py
```

A bulletin for any forecast: `python mahanadi/forecast_to_impact.py --lakh-cusec 9` (with `ATLAS_DIR` and `IMPACT_DIR`
pointing at the build and impact folders).

## Engineering notes worth keeping

- The mentor notebook filled missing VH radar with the VV mean (normalised value 1.31 instead of 0). Here every
  invalid pixel is filled with its own band mean before standardising, so it becomes exactly 0.
- On the shared server, memory-mapped reads and CPU-side rotation starved the GPUs; chips are read with `os.pread`
  and normalisation and augmentation run on the GPU (epoch ~30 s → ~13 s).
- The published Prithvi Sen1Floods11 checkpoint was trained on the official split (40 of the 68 India chips in
  training, 14 in validation), so its India score is not an unseen-event score.
- Planetary Computer from the lab server: default GDAL settings read a 10 m band window in ~54 s; with
  `GDAL_NUM_THREADS`, 2 MB chunks and multi-range requests ~3 s; HTTP time-outs and a low-speed abort are needed
  because single connections stall. The 20 m COG overview is the exact 2 × 2 power average.
- River bed: dry-season sand bars are not water in February–March, so without a river-bed mask the bed going under
  every monsoon counted as "flood" (two thirds of the 2-year flood area in a first run).
- Swath edges: one track's data edge produced a 3 km-wide stripe of false floods; a 3 km edge buffer per pass
  removes it.
