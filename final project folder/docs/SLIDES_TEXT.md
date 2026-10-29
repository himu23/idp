# Prithvi Flood-IN: slide text and speaker notes

Every slide of `report/Prithvi_Flood-IN_Final.pptx`: what it shows, who presents it and what to say (about a minute per slide; the same notes are in the deck's speaker notes).

## Slide 1. Prithvi Flood-IN

*Presenter: Nikhil*

**On the slide**

- From a river-flow forecast to who goes under water:
- a satellite foundation model for the Mahanadi delta
- Nikhil Upadhyay (lead) · Prakhar Gupta · Prabhat Kumar · Vineet Jangir · Himanshu Shete
- Guide: Prof. Basudev Biswal (IIT Bombay) · Industry: Dr. Vivek Gupta, Siddik Barbhuiya (ClimMaTech)
- CE Integrated Design Project · final review · November 2026

**What to say**

Introduce the team and the question in one line: when the Mahanadi rises, what floods, and who must be warned? Say that the work joins satellite AI with the department's seven specializations, for a real delta and a real industry partner.

## Slide 2. The problem in the field

*Presenter: Nikhil*

**On the slide**

- ClimMaTech forecasts the river at a point; nobody sees what that flow floods
- ClimMaTech: radar gauges on bridges and spillways, sirens, Aagah app; forecasts 30 min – 48 h ahead.
- Every product is a point: the level or flow at one gauge.
- Missing: which land, villages, roads, bridges and embankments go under water at that flow.
- Mahanadi delta below Naraj: 3,038 km² study box, 4.1 million people, floods in 2018, 2020, 2022…
- Prof. Biswal's Mahanadi basin work, Odisha WRD and CWC (Naraj gauge, barrages) all meet here.
- Refined problem statement
- For the Mahanadi delta, turn a river-flow forecast at Naraj into a map of what floods and whom it affects, using a satellite foundation model chosen by a fair benchmark, and use that map to plan where warnings and sensors should go, checked and calibrated at the site.

**What to say**

ClimMaTech measures and forecasts the river at points: radar gauges, sirens, an app. A forecast says how much water reaches Naraj, not which villages go under. Our refined problem statement fills that gap for the Mahanadi delta: 4.1 million people in 3,038 km².

## Slide 3. Who needs what

*Presenter: Nikhil*

**On the slide**

- The project is built around the people who would use it

| Stakeholder | Needs from us | We need from them |
|---|---|---|
| ClimMaTech (CTO Dr. Vivek Gupta; Siddik) | Flood-extent layer + village list per forecast; siren and sensor sites | Siren range, data formats, site-survey practice |
| Prof. Biswal's Mahanadi basin project | Inundation and impacts for the delta | Site access, introductions |
| Odisha WRD, CWC Mahanadi division | Which banks and roads fail at which flow | Naraj discharge, embankment inventory, breach history |
| OSDMA, Cuttack / Kendrapara / Jagatsinghpur | Villages to warn, roads that close | Evacuation records, shelters |
| Villages and farmers | Earlier, local warning | What flooded, when, how deep |

**What to say**

Walk through the stakeholders: ClimMaTech needs a flood-extent layer and site plans; the guide's Mahanadi project needs inundation and impacts; the Water Resources Department needs to know which banks and roads fail; the district needs villages to warn. Each row is something we deliver.

## Slide 4. One flood, seven specializations

*Presenter: Himanshu*

**On the slide**

- Each specialization asks its own question of the same flood scenarios

| Specialization | Question | Headline (25-year flood) | Field check |
|---|---|---|---|
| Remote sensing | Which model maps floods through cloud? | 590 radar passes mapped; U-Net beats FMs on unseen flood | 40 random points |
| Water resources | Which flow floods which land; where does it come from? | Trigger map 0.23 vs 0.07 climatology; ~48% of a flood peak from Hirakud | Discharge, Manning's n |
| Transportation | Who loses the road to a hospital? | 36,941 people cut off | Road closures |
| Structural | Where do walls crack; how deep must piers go? | 3,626 people where depth >= 1 m | HFL marks, foundations |
| Geotechnical | Which banks fail; which dry houses sit on soaked ground? | 415,549 people in the 200 m advisory zone | Soil samples, wells |
| Ocean | What do Bay of Bengal storms add? | 11 of 20 largest floods followed a storm | Surge, tidal drainage |
| Construction tech & mgmt | When to build, what it costs? | Work window Dec–Apr; 17,442 m³ to raise 8 critical links | Site sheets |

**What to say**

One set of flood scenarios, one question per specialization. Read the headline column quickly and say the details follow. Mention that water resources includes the watershed above the delta, where about half of a flood peak comes from below Hirakud dam.

## Slide 5. Model selection: a fair benchmark

*Presenter: Vineet*

**On the slide**

- Sen1Floods11 v1.1 · 446 hand-labelled chips · 13 optical bands + radar VV/VH · 11 flood events
- 8 trainable models, one recipe: same decoder, CE + Dice, D4 augmentation, AdamW + cosine, 40 epochs
- Foundation models: Prithvi-EO-2.0-300M, TerraMind-B, DOFA-B, Clay-v1-B, Satlas Swin-B, DeCUR ResNet-50
- Baselines: simple CNN, U-Net; Otsu, NDWI, published Prithvi checkpoint
- 3 seeds each, frozen vs fine-tuned, fusion, radar vs optical, label efficiency: 92 runs

| Protocol | Train | Test |
|---|---|---|
| Official | 252 chips, 10 events (incl. India) | 90 chips, same events |
| Leave-India-out | 212 chips, 9 events, no India | all 68 Assam chips (unseen flood) |

**What to say**

Same data, same recipe, same decoder for every model: six foundation models, a CNN and a U-Net, three seeds each. The key design choice is leave-India-out: the test is an Indian flood no model saw. 92 runs in total.

## Slide 6. Unseen Indian flood: U-Net beats every foundation model

*Presenter: Vineet*

**On the slide**

- Assam 2016, never in training · U-Net 0.770 ± 0.006 · best FM Prithvi-EO-2.0-300M 0.747 ± 0.006 · top-3 fusion 0.776 ± 0.003
- Every model loses 0.07–0.14 IoU when the flood is unseen (U-Net 0.840 → 0.770)
- Fine-tuning helps every FM on the unseen flood (+0.003 to +0.048)
- Fusing FMs alone does not beat the best FM; U-Net + CNN + best FM does
- 21 labelled chips: U-Net 0.736 ≈ FMs with 212
- Water is spectrally simple; ~250 chips suffice for a 7.8 M-parameter U-Net

**What to say**

The surprise: a small U-Net (0.770) beat every foundation model (best 0.747). Water is spectrally simple and a few hundred labels are enough. Fusing the top three gives 0.776.

## Slide 7. Monsoon reality: radar only

*Presenter: Vineet*

**On the slide**

- Optical is better when the sky is clear; on flood dates the delta was 61–95 % cloud
- TerraMind is the only FM that takes radar alone natively
- Production model of the atlas = TerraMind-B + U-Net, radar only
- 20 m input costs ~0.02 IoU, cuts the download 4×

| Radar-only model (official test) | IoU |
|---|---|
| U-Net, 10 m | 0.649 |
| TerraMind-B, 10 m | 0.654 |
| Fusion (mean), 10 m | 0.664 |
| Fusion, 20 m input (atlas) | 0.640 |
| Fusion, 20 m, threshold 0.30 (val.) | 0.646 |

**What to say**

Optical is better under clear sky, but the delta was 61–95 % cloud on flood dates. So the production model is radar-only: TerraMind, which takes radar natively, fused with a U-Net.

## Slide 8. Checked, not assumed: the training audit

*Presenter: Himanshu*

**On the slide**

- scripts/audit_training.py re-checks all 92 runs from their stored outputs
- Published values: TerraMind paper (arXiv:2504.11171, PANGAEA protocol); ours are within one point
- The delta's radar looks like the training radar: dry-land VV median -8.7 dB vs -9.7 dB; water 8-11 dB lower in both

| Check | Result |
|---|---|
| Runs made with the queued arguments | 92 of 92 |
| Chips in two splits | none |
| India chips in leave-India-out training | none |
| Model selection on validation only | every run |
| Test IoU recomputed = stored | every run |
| Seed spread (sd of test IoU) | at most 0.017 |
| Problems found | 0 |

| TerraMind-B on Sen1Floods11 | Ours, mIoU | Paper |
|---|---|---|
| Radar + optical | 89.7 | 90.62 |
| Radar only | 79.8 | 80.39 |

**What to say**

We re-checked all 92 runs from their saved outputs: right settings, no chip in two splits, no Indian chip in training, selection on validation only, every score recomputed. Our TerraMind matches the published paper within a point (89.7 against 90.62).

## Slide 9. Mahanadi flood atlas 2017–2026

*Presenter: Prakhar*

**On the slide**

- 590 Sentinel-1 passes (457 monsoon, 133 dry season) · 3 tracks · Sentinel-1A/B/D · 20 m
- Flooded land follows the Naraj flow (Spearman ρ = 0.76, predictor: 5-day peak flow); river bed (178 km²) and normal water excluded; a 3 km swath-edge band removed per pass

**What to say**

Every Sentinel-1 pass since 2017: 590 passes, mapped in about 5 seconds each. Flood means water outside the river bed and the dry-season water. 905 km² flooded at least once.

## Slide 10. From a flow forecast to a flood map

*Presenter: Nikhil*

**On the slide**

- Each 20 m pixel gets the Naraj flow at which it starts to flood
- Years never seen in fitting, high flows (≥ 9,682 m³/s): IoU 0.23 vs 0.07 for climatology
- Per settlement (≥ 10 % of people flooded), high flows: POD 17%, FAR 65% (climatology POD 3%)
- Design floods (Gumbel): 2-yr 17,897, 25-yr 32,997 m³/s
- Same 5-yr flow: 25 km² flooded in a dry week, 105 km² with 171 mm of rain — read the rain forecast too
- Where it floods is predictable from the past (AUC 0.93); how much floods on a day only partly
- Hirakud → Naraj ≈ 1 day

**What to say**

Each pixel gets the Naraj flow at which it starts to flood. Tested on years it never saw: IoU 0.23 against 0.07 for climatology at high flows. Past floods rank flood-prone land very well (AUC 0.91); how much floods on a given day is harder.

## Slide 11. A learned flow + rain + history model

*Presenter: Nikhil*

**On the slide**

- Gradient boosting per pixel and pass; each year predicted from the other years
- Inputs: flow and 7-day rain of the pass, month, radar track; per pixel the training years' trigger flow, flood frequency (all, high flow, heavy rain), height above and distance to the river bed
- Leans most on: flood frequency, Naraj flow, 7-day rain, month
- 5-year flow: 44 km² in a dry week, 172 km² with heavy rain: one model for the river forecast plus a rain gauge

| Held-out passes, IoU | Learned | Trigger map | Climatology |
|---|---|---|---|
| All monsoon (457) | 0.24 | 0.23 | 0.14 |
| High flow (85) | 0.24 | 0.23 | 0.07 |
| Heavy rain (46) | 0.22 | 0.17 | 0.05 |
| Villages, high flow: POD / FAR | 21% / 71% | 17% / 65% | 3% / 23% |
| Ranking AUC, all passes | 0.95 | 0.79 | 0.93 |

**What to say**

A gradient-boosted model adds 7-day rain and each pixel's flood history to the flow. It is better on heavy-rain passes (0.22 against 0.17) and ranks land best (AUC 0.95), and it catches more flooded villages at the cost of more false alarms. Its maps never show less flooding for more rain.

## Slide 12. What floods: people, farmland, roads, hospitals

*Presenter: Himanshu*

**On the slide**

- Per design flood; land outside the river bed and normal water
- People: GHSL 2020; roads, bridges, hospitals, schools: OpenStreetMap
- Flows above the largest in the 2017–2026 radar record give lower-bound maps
- Mapped building footprints are incomplete here (~120 k for 4.1 M people), so people, not buildings, are counted

| Scenario | Naraj flow (m³/s) | Flooded land (km²) | People | Cropland (km²) | Road km | Health fac. | Cut off from hospital |
|---|---|---|---|---|---|---|---|
| 2-yr | 17,897 | 38 | 6,086 | 16 | 3 | 5 | 0 |
| 5-yr | 23,940 | 203 | 22,545 | 152 | 30 | 5 | 36,941 |
| 10-yr | 27,941 | 216 | 25,163 | 164 | 32 | 6 | 36,941 |
| 25-yr | 32,997 | 216 | 25,163 | 164 | 32 | 6 | 36,941 |
| 100-yr | 40,470 | 216 | 25,163 | 164 | 32 | 6 | 36,941 |
| largest seen 2018 | — | 275 | 28,826 | 232 | 23 | 6 | 15,784 |

**What to say**

For each design flood: people on flooded land, farmland, roads, hospitals, bridges. In the 25-year flood 25,163 people live on 216 km² of flooded land. Floods above the largest seen since 2017 are lower bounds.

## Slide 13. Transportation: who is cut off from a hospital

*Presenter: Himanshu*

**On the slide**

- Road graph of 6,383 km; a road is cut when ≥ 20 m is under water
- 25-year flood: 36,941 people in 32 settlements lose road access to any hospital or clinic
- 24,345 more reach one only by a detour (median +9.1 min)
- 40,836 people can reach no dry school (relief camp); 12,023 extra person-hours of travel a day
- Critical links = flooded roads that carry most people's hospital route (circled)
- Field: confirm closures with locals and PWD at the 10 critical links

**What to say**

The road network becomes a graph; flooded sections are cut. 36,941 people lose road access to every hospital in the 25-year flood, and everyday trips grow by about 12,023 person-hours a day. The critical links are listed with coordinates.

## Slide 14. Geotechnical: which river banks to inspect first

*Presenter: Prabhat*

**On the slide**

- 1 km cells along the main channels
- Priority = water behind the bank (frequency, years) + erodibility + people within 2 km
- SoilGrids is too coarse to separate banks (all clay loam here) → field samples decide
- Lab plan: wet sieve + Atterberg (IS 2720) → IS 1498 class, Kenney–Lau stability, piping flag
- Top cell: 20.429 N, 85.909 E, water behind the bank in 4% of passes, 10 years

**What to say**

Bank cells ranked by how often water stands behind the bank, the soil and the people nearby. Twenty inspection sites, at least 3 km apart, are on the field GPS file; the lab tests on their soil samples decide the ranking.

## Slide 15. Structural: walls crack at about a metre, piers must go deep

*Presenter: Himanshu*

**On the slide**

- Flood depth from the flood-edge elevation; IRC:78 Lacey scour
- Hydrostatic moment > out-of-plane capacity: a 230 mm brick wall cracks at 0.8-1.0 m of water
- 3,626 people live where the 25-yr flood is >= 1 m deep
- Pier scour 7-24 m below HFL at a quarter of the 100-yr flow (branch split asked from WRD)

**What to say**

Flood depth from the elevation at the flood edge. A 230 mm brick wall cracks at about a metre of water; 3,626 people live where the 25-year flood is that deep. Pier scour reaches 7–24 m below the high flood level; the flow split between branches is the missing input.

## Slide 16. Geotechnical: dry houses on soaked ground

*Presenter: Prabhat*

**On the slide**

- Within 200 m of flood water on silty clay: bearing capacity drops, then the clay settles
- 415,549 people in the advisory zone of the 25-yr flood; 310 settlements advised to check foundations
- Footing on silty sand: bearing capacity -55 % with water at the surface
- Soaked clay: -37 %; drawdown settlement 20 to 39 mm
- Field: well levels at 0-500 m from the flood edge fix the 200 m

**What to say**

Floodwater raises the groundwater under houses that stay dry: 415,549 people within 200 m of the 25-year flood on silty clay. Soaking cuts bearing capacity by about 55 %, and the clay settles when the water drops. Well levels at the site fix the 200 m.

## Slide 17. Ocean: Bay of Bengal storms and the largest floods

*Presenter: Nikhil*

**On the slide**

- IBTrACS tracks matched to the radar atlas
- 37 storms and depressions within 300 km since 2016 · of the 20 largest floods: 18 high river, 14 heavy rain, 11 after a storm
- Surge and high tide hold back the drainage of the lower delta: a Paradip tide record is the next dataset

**What to say**

37 storms and depressions came within 300 km since 2016; 11 of the 20 largest floods followed one. The largest floods were rain-driven, not river-driven: read the rain forecast with the river forecast.

## Slide 18. Construction management: when to build, what it costs

*Presenter: Prabhat*

**On the slide**

- 42 years of flows and storm tracks; earthwork take-off for the critical links
- Work window: Dec–Apr (no flood days, few storms)
- Raising 8 critical links above the 25-yr flood + 0.6 m: 17,442 m³, about Rs 0.6 crore (assumed Rs 350/m³)
- Links 6 and 9 would need 4.9 and 3.9 m: a bridge or vented causeway, depth checked on site
- Each link carries the hospital route of 4,638–10,351 people
- Deployment: 40 sirens cover 49% of exposed people at 1.5 km, 6 river sensors, 78 crew-days

**What to say**

Build in December–April, the months with no flood days and few storms. Raising 8 critical roads takes about 17,442 m³ of earthwork; two more need a bridge or vented causeway. The schedule fits approvals, procurement and installation inside the window.

## Slide 19. Deployment plan for a ClimMaTech-type system

*Presenter: Prabhat*

**On the slide**

- Sirens where exposed people live; one river sensor per distributary
- Exposed people (25-yr flood or ≥ 10 % frequency): 27,371
- 40 sirens cover 34% / 49% / 62% at 1.0 / 1.5 / 2.0 km audible range
- River sensors on 6 bridges: Devi River, Kathajodi, Birupa, Luna, Mahanadi, Biropa
- Approach roads checked dry in the 25-year flood (reachable during floods)
- Field: mobile signal, mounting, access → final list

**What to say**

Sirens where exposed people live: 40 sirens reach 49% at 1.5 km, phones reach the rest. One radar gauge per distributary, on the bridge nearest Naraj whose approaches stay dry, measures how the flood splits.

## Slide 20. Implementation: forecast → bulletin in seconds

*Presenter: Himanshu*

**On the slide**

- mahanadi/forecast_to_impact.py · interactive viewer dashboard/index.html
- MAHANADI DELTA - EXPECTED FLOODING FOR A NARAJ FLOW OF 23,940 m3/s (8.5 lakh cusec), lead time 24 h
- (flow = highest daily flow over 5 days at Naraj, the measure the atlas is fitted on; method: trigger-discharge map, river flow only)
- Expected flooded land: 203 km2
- People living on that land: 22,545
- Settlements with at least 10 % of people on flooded land: 20
- - near Patkura (9.7 km): about 321 people (46% of 704) at 20.3133 N, 86.3615 E
- - near Biridi (1.4 km): about 309 people (54% of 574) at 20.3319 N, 86.0429 E
- - near Bhattasagar Square (7.0 km): about 234 people (15% of 1,613) at 20.6301 N, 86.1248 E
- - near Patkura (2.7 km): about 152 people (24% of 647) at 20.4002 N, 86.3823 E
- - near Patkura (1.5 km): about 78 people (28% of 281) at 20.3855 N, 86.3917 E
- - near Dhuria (8.6 km): about 76 people (14% of 529) at 20.4610 N, 86.3444 E
- Input: forecast flow at Naraj (m³/s or lakh cusec), e.g. from ClimMaTech or CWC
- Output: flood GeoTIFF, settlements GeoJSON (for Rakshak Control Centre / Aagah), text bulletin
- Viewer: pick a design flood → flooded land, cut roads, villages, sirens, sensors
- Fills the map layer ('River View') that ClimMaTech's architecture lists for flood risk

**What to say**

A forecast flow goes in; a flood map, the settlements to warn and the roads under water come out in seconds, plus a CAP alert the Rakshak Control Centre can take (24 alert areas for the 25-year flow). The map viewer shows every scenario.

## Slide 21. What ClimMaTech's system lacks, and what we add

*Presenter: Himanshu*

**On the slide**

- From all 50 pages of climmatech.com; every row has a number behind it

| Their service | Gap | What we add (evidence) |
|---|---|---|
| River View map layer | No flood extent behind it | Flood frequency, trigger flow and impact layers (590 passes; IoU 0.23 vs 0.07) |
| AI forecast, 30 min-48 h | A level is not a list of villages | Forecast-to-bulletin: 25-yr flow -> 216 km², 25,163 people, 24 settlements |
| Research group reconstructions | Width by hand; optical 75-79 % cloud | Benchmarked radar model maps every Sentinel-1 pass through cloud, ~5 s per pass |
| Solution pages | Illustrative site layouts | Data-backed siting: 40 sirens reach 49% of exposed people; 6 sensor bridges |
| Pravaah discharge | Needs section + velocity factor | Field protocols B and C measure both, plus Manning's n |
| Varshaq rain gauge | Rain not linked to flooded land | Rain-aware maps: analogs and the learned flow + rain model |
| Rakshak Control Centre | Alert areas drawn by hand | CAP 1.2 alert per forecast, one area per settlement to warn |

**What to say**

We read every page of their site. Each row is one of their services, the gap and what we add, with the number behind it: the flood-extent layer for River View, bulletins and CAP alerts, a real network of sites, a field method for discharge, rain-aware maps.

## Slide 22. Field visit: measure what the models cannot know

*Presenter: Nikhil*

**On the slide**

- Every measurement has a script and changes a number in the report
- GPS check points (GPX / KML), printed dossier, protocols, safety rules: fieldkit/

| At the site | Feeds | What it can change |
|---|---|---|
| 40 random ground-truth points, flood marks, villagers' years | field_validate_map.py | Atlas accuracy (POD / FAR / CSI) for ClimMaTech |
| Cross-section + floats + slope at a bridge | discharge_velocity_area.py | GloFAS check; Manning's n for the PINN (now 0.015 assumed) |
| Bridge deck, HFL marks, scour, closures | bridge_clearance.py | IRC:5 clearance; critical-link ranking |
| Bank inspection + soil samples → IITB lab | soil_gradation.py | Bank inspection ranking (replaces SoilGrids) |
| Siren / sensor site sheets | sensor_site_assessment.csv | Final deployment list |
| Interviews: WRD, CWC, ClimMaTech, villages | interviews.csv | Problem statement; 'which flow floods which village' |

**What to say**

The visit measures what the models cannot know: accuracy at 40 random points, discharge and roughness at a bridge, bridge and bank inspections with soil samples, well levels, sensor sites and interviews. Every measurement has a script and changes a number in the report.

## Slide 23. Checks of our own numbers

*Presenter: Prakhar*

**On the slide**

- Independent sensor in the delta; physics track
- Sentinel-2 within ±1 day, clear pixels: 60 pairs
- Radar atlas vs optical water, all water: IoU 0.49 (precision 0.60, recall 0.73)
- Outside normal water, Jun–Nov: IoU 0.18 over 60 pairs
- PINN (Saint-Venant): 6 published cases reproduced (0.0 % deviation); case 3 retrained 2.7 % better than the paper; L-BFGS-B stage adds nothing
- Field Manning's n will replace the assumed 0.015

**What to say**

Sentinel-2 within a day of 60 radar passes: IoU 0.49 on all water, lower on the flood part, so the radar misses shallow water among crops. The mentor's PINN for the Saint-Venant equations was reproduced exactly and retrained.

## Slide 24. Team and contributions

*Presenter: Nikhil*

**On the slide**

- Five students, seven specializations; each presents the part they built

| Member | Specializations | What they built |
|---|---|---|
| Nikhil Upadhyay (lead) | Water resources, Ocean | Flow-to-flood model, design floods, travel time, Saint-Venant PINN, storm drivers; organises the visit |
| Vineet Jangir | Remote sensing | Benchmark of six foundation models (92 runs), fusion, the 20 m radar model |
| Prakhar Gupta | Remote sensing | Flood atlas from 590 Sentinel-1 passes, Sentinel-2 check, map viewer |
| Himanshu Shete | Transportation, Structural | Hospital access, critical links, flood depth, walls, bridge scour; integration of the impact chain, forecast-to-bulletin tool, website, report and slides |
| Prabhat Kumar | Geotechnical, Construction mgmt | Bank screening, ground saturation, foundations; work windows, earthwork, siren and sensor plan |

**What to say**

Who built what: each member presents the part they own and can answer for the whole chain.

## Slide 25. What we conclude

*Presenter: Nikhil*

**On the slide**

- Model choice: on an unseen Indian flood U-Net (0.770 ± 0.006) beats every foundation model; the FM's value here is that one network takes radar alone when monsoon cloud removes the optical image.
- The delta's flood atlas from 590 radar passes turns a Naraj flow forecast into a map; on held-out years it beats flood climatology at high flows (0.23 vs 0.07).
- In a 25-year flood about 25,163 people live on flooded land and 36,941 lose road access to a hospital; the critical links and banks to inspect are listed with coordinates.
- Deployment: siren and sensor sites, and a forecast-to-bulletin tool, ready for ClimMaTech's platform.
- Next: the field visit closes the loop — accuracy at random points, measured discharge and roughness, soil classes.

**What to say**

Five points: U-Net beats the foundation models on an unseen flood; radar maps the monsoon; a forecast flow becomes a flood map that beats climatology; the impacts reach every specialization; and the field visit is designed to change these numbers where they are wrong. Thank the guide and the mentors.
