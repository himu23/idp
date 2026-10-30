# Prithvi Flood-IN — final-phase plan (29 Oct → 9 Nov 2026)

## 1. What the evaluators will look for

From the IDP coordinator's review on 14 Oct (`audio transcribe/meets/Idp 14-10-transcript.txt`):

1. **A real, sanctioned project with stakeholders** — not a classroom exercise. She suggested joining
   Prof. Basudev Biswal's long-running **Mahanadi basin** work and connecting one fine-tuned foundation model to it.
2. **A site visit with substance** — "what did you do at the site, what did you take from the site, how did you
   continue". A team last year lost marks because they "went to the river, floated and came back".
3. **Interdisciplinary** — a real river project also has geotechnical, structural and transportation sides;
   last year's L&T team split traffic / geotechnical / structural between members.
4. **Refine the problem statement** from what the site and the stakeholders tell us.

The industry side (ClimMaTech, Siddik, Dr. Vivek Gupta) asked for the five-plus foundation-model comparison and a
fusion model; that is done (section 3) and becomes the *model-selection* part of the story, not the whole story.

## 2. Refined problem statement (draft — update after the visit)

> ClimMaTech's early-warning system measures and forecasts river level and flow at points — radar gauges on
> bridges and dam spillways — and alerts villages through sirens and the Aagah app. What an operator cannot see
> is the consequence of a forecast: **which land, villages, roads, bridges and embankments go under water at a
> given river flow.** For the Mahanadi delta below Naraj, the most flood-exposed reach of the Mahanadi basin, we
> (1) select a satellite water-mapping model by benchmarking six geospatial foundation models against CNN/U-Net
> on an unseen Indian flood, (2) run it on every Sentinel-1 radar pass over the delta from 2017 to 2026 to build
> a flood atlas, (3) link the atlas to river discharge at Naraj so that a discharge forecast becomes an
> inundation map, (4) translate inundation into engineering impacts — people, roads and bridges, river banks —
> and (5) use them to plan where sirens and river sensors should go, checked and calibrated with measurements
> and interviews from the field visit.

Who it serves: ClimMaTech (product: a "flood-extent layer" for River View / Rakshak Control Centre that it does
not have today — its site lists only point sensors, sirens and the app); Odisha WRD / CWC (embankment and road
priorities); district administrations (villages to warn per forecast).

## 3. Status of the work (what exists in this folder)

| Block | Discipline | Status | Where |
|---|---|---|---|
| Benchmark: 6 FMs + CNN + U-Net, 2 protocols, 3 seeds, frozen vs fine-tuned, fusion, radar vs optical, label efficiency | AI / remote sensing | **done** (92 training runs) | `results/analysis`, report §4 |
| PINN (Saint-Venant) reproduction + case 3 retrain, L-BFGS finding | hydraulics | **done** | `pinn/`, report §5 |
| Mahanadi flood atlas 2017–2026 (all 590 Sentinel-1 passes, radar FM) | remote sensing + hydrology | **done** | `mahanadi/atlas_*.py`, report §6 |
| Naraj flow forecast 1–3 days ahead from upstream flows and catchment rain (efficiency 0.99 / 0.94 / 0.89 on unseen monsoons, against 0.96 / 0.88 / 0.79 for persistence) | water resources | **done** | `mahanadi/forecast_model.py`, report §6.7 |
| Live warning feed for all three basins: GloFAS ensemble + ECMWF rain + NDMA SACHET + CWC + latest Sentinel-1 pass → impact-based levels counted beyond the ordinary monsoon, villages with dates, CAP alert, Atom feed; plugins per source; replay of the August 2022 flood | deployment | **done** (run of 31 Oct: no flood impact on any basin) | `live/`, report §9.7, website "Live" |
| Flood risk in rupees: house and paddy damage, expected annual damage, hospital-access person-days, benefit–cost of road raising, Hirakud what-if | structural, transportation, construction management | **done** | `mahanadi/risk_economics.py`, report §7.9, C.9 |
| Two more basins (Brahmani–Baitarani: 394 passes, 2,277 km² flooded at least once; Brahmaputra at Majuli: 346 passes, 2,145 km²) through the same pipeline, both in the live feed | remote sensing + hydrology | **done** | `mahanadi/basins.py`, `server/run_basin*.sh`, `results/basins/`, report §6.8 |
| Radar pair retrained on the atlas's 20 m input (3 seeds, +0.022 IoU on every seed); atlas rebuilt with it after it agreed better with Sentinel-2 (IoU 0.56 against 0.49) | remote sensing | **done** (atlas, impacts and learned model all on the rebuilt atlas; the first atlas archived) | `server/run_r20_*.sh`, `scripts/compare_atlases.py`, `results/archive_atlas_10m/`, report Appendix B |
| Discharge → inundation model (GloFAS at Naraj, per-pixel trigger flow, leave-one-year-out test, return periods) | hydrology | **done** | `mahanadi/atlas_build.py`, report §6 |
| Independent check with Sentinel-2 on the same days | remote sensing | **done** (60 pairs) | `mahanadi/s2_crosscheck.py`, report §6 |
| Exposure: people, roads, bridges, rail, health facilities, schools, farmland | all | **done** | `mahanadi/impact_exposure.py`, report §7.1 |
| Hospital and shelter access, everyday travel delay, critical links | Transportation Systems | **done** | `mahanadi/impact_transport.py`, §7.2 |
| Flood depth, masonry-wall screening, IRC:78 bridge scour, IRC:5 clearance (field) | Structural | **done** | `impact_depth.py`, `impact_structures.py`, §7.3 |
| River-bank screening; ground saturation under dry houses; foundation and rapid-drawdown checks | Geotechnical | **done** | `impact_geotech.py`, `impact_ground.py`, `fieldkit/analysis/*`, §7.4–7.5 |
| Bay of Bengal storms vs the 20 largest floods (IBTrACS) | Ocean | **done** | `ocean_cyclones.py`, §7.6 |
| Work windows, earthwork for raising critical links, deployment quantities, schedule, risks | Construction Technology & Management | **done** | `cm_plan.py`, §7.7 |
| Siren and river-sensor siting; forecast-to-bulletin tool (river flow ± rain) | deployment | **done** | `impact_siting.py`, `forecast_to_impact.py`, §9 |
| Training audit: all 92 runs re-checked (splits, selection, recomputed scores), published TerraMind numbers reproduced, atlas radar vs training radar | AI / remote sensing | **done** (0 problems) | `scripts/audit_training.py`, report Appendix A |
| Learned flow + rain + history flood model (gradient boosting, leave-one-year-out against the trigger map) | water resources + AI | **done** | `mahanadi/learned_flood_model.py`, report §6.6 |
| CAP 1.2 alert export for the Rakshak Control Centre (one area per settlement to warn) | deployment | **done** | `forecast_to_impact.py` → `bulletin_<flow>.cap.xml` |
| Gap analysis of ClimMaTech's services (all 50 pages of climmatech.com) with data-backed contributions | all | **done** | report §9.6, website "For ClimMaTech", slide |
| Project website in the partner's interface style (Inter, pill navigation, tile grids) with a scenario explorer and the map viewer | presentation | **done** | `website/` (published as a private link) |
| Field-visit kit: protocols, interview guides, data sheets, GPS check points, analysis scripts | all | **done** | `fieldkit/` |
| Interactive map / dashboard for ClimMaTech and the presentation | implementation | **done** | `dashboard/` |
| Final report (.md/.docx) and slides (.pptx) | — | **done**; field results (§8) added after the visit | `report/` |
| Executive summary, slide text with speaker notes, team guide from the basics | all | **done** | `docs/` |

## 4. Who does what (suggested split — the department's seven specializations, like the L&T team's split)

| Member | Specializations they present | Report | At the site |
|---|---|---|---|
| Vineet | Remote Sensing (model benchmark, radar foundation model in production, radar models retrained at 20 m) | §4, §6.1, App. B | Ground-truth points with Prakhar (A) |
| Prakhar | Remote Sensing (flood atlas, Sentinel-2 check, atlases of the Brahmani–Baitarani and Brahmaputra basins, map viewer) | §6.1–6.2, §6.8 | Ground-truth points, GPS/photo log (A) |
| Nikhil | Water Resources (flow-to-flood model, rain, learned flow + rain model, Naraj flow forecast 1–3 days ahead, design floods, watershed, PINN) and Ocean (storm drivers); organises the visit | §5, §6.3–6.7, §7.6, §7.8 | Discharge, slope, Manning's n (B, C); WRD/CWC interviews |
| Himanshu | Transportation Systems and Structural (cut-offs, shelters, critical links; flood depth, walls, scour, clearance); integration of the impact chain, forecast-to-bulletin tool with CAP alerts, live warning feed with its data plugins and the August 2022 replay, flood-risk economics, training audit, partner gap analysis, project website, report and slides | §7.1–7.3, §7.9, §9.1–9.2, §9.6–9.7, App. A | Bridge inspections, foundation levels, road closures (D); runs the field scripts each evening and updates the numbers |
| Prabhat | Geotechnical and Construction Technology & Management (banks, ground saturation, foundations; work windows, earthwork, siren and sensor plan) | §7.4–7.5, §7.7, §9.3–9.4 | Bank inspection, soil samples + lab, well levels, site sheets (E, F, H) |

Each member should be able to answer for the whole chain, but present the part they own.

## 5. Timeline

| Date | Task | Owner |
|---|---|---|
| 29 Oct | Read this plan and `fieldkit/FIELD_VISIT_KIT.md`; confirm visit site, dates and hosts with Prof. Basudev Biswal and ClimMaTech; send the data requests (kit §1.2) | Nikhil (all) |
| 29–30 Oct | Each owner reads their report section and the code behind it; prepare questions for the hosts | all |
| 31 Oct – 3 Nov | Field visit (3 days, kit §2) | all |
| 3–5 Nov | Type data; run the seven field scripts; soil tests in the geotech lab; write §8 "field results and what changed" | owners (scripts: Himanshu) |
| 5–6 Nov | Update problem statement (§2), impacts and deployment plan with field findings; rebuild report, slides and website | all (rebuild: Himanshu) |
| 7 Nov | Dry run of the presentation with the mentors; fix | all |
| 7–9 Nov | Run `python live/run_live.py` the morning of the presentation so the live outlook on the slides and website is that day's | Himanshu |
| 8 Nov | Submit report + slides; abstract for HYDRO/journal ready | — |
| 9 Nov | Deadline (PROJECT_SCOPE.md) | — |

## 6. What to say when asked "what did you do at the site and what changed because of it?"

Prepare one slide per item, each with a photo, the measured number and the change it caused:
- atlas accuracy at 40 random field points (POD / FAR / CSI) — tells ClimMaTech how far to trust the map;
- discharge measured at the bridge vs. GloFAS / CWC — calibrates the flow used to trigger maps;
- Manning's n measured vs. 0.015 assumed in the PINN — re-run the Saint-Venant case with the measured value;
- bridge clearance vs. IRC:5 and road closures confirmed or corrected — re-ranks critical links;
- soil class and piping susceptibility of the bank samples — re-ranks the inspection list;
- siren / sensor sites confirmed or dropped (mobile signal, access in flood, mounting) — final deployment plan;
- the engineers' answer to "which flow at Naraj floods which villages?" vs. our trigger-discharge map and the levels of
  the live warning (12,250 / 18,500 / 21,250 m³/s);
- the house and paddy losses people report for 2020 and 2022 vs. the damage estimate (§7.9);
- whether villagers and the district would act on the live bulletin that names them with a date.

## 7. Risks and fallbacks

- **Visit cannot happen in the Mahanadi delta.** Run the same protocols at the nearest reachable river site with
  a gauge or a ClimMaTech installation (e.g. their Mandi deployments); the hydrometry, bridge and soil
  protocols do not depend on the place. A new area is one entry in `mahanadi/basins.py` (box, gauge, season);
  `server/run_basin_atlas.sh` then builds its atlas and `mahanadi/make_checkpoints.py` its check points.
- **No permission for gauge/barrage areas.** Use a public road bridge for hydrometry and interviews by phone.
- **No lab slot.** Field texture by feel + SoilGrids remain; state it as a limitation.
- **Observed discharge not shared in time.** GloFAS (modelled) stays the discharge source; state it.
