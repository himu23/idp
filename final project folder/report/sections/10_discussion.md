## 10. Discussion, limitations and conclusions

### 10.1 What the benchmark means for practice

Foundation models did not beat a U-Net on Sen1Floods11, also not on an unseen Indian flood nor with few labels.
The pre-trained features are good (frozen encoders reach 0.62–0.83), but water is a spectrally easy target and a
few hundred labelled chips are enough for a small network. Their value in this project is different: TerraMind takes
radar alone as a native input, which is what remains during a monsoon flood. Fusion helped only when its members
made different errors (U-Net + CNN + the best foundation model).

### 10.2 What the Mahanadi work adds

The atlas turns a free, global archive into a local hazard layer: which land floods, how often, and at which river
flow. The trigger-discharge map is the piece a point-forecast system lacks, and it was tested the way it would be
used: predicting a year it had not seen, from discharge alone. The impact analyses put the map into civil-engineering
terms — hospitals cut off, critical links, banks to inspect, siren and sensor sites — with coordinates that can be
checked in the field. The flow forecast and the live feed turn the map into a daily service that names villages and
dates, and the risk estimate puts the hazard in rupees and person-days, the terms in which protection is funded.

### 10.3 Limitations

- One Indian test event (Assam 2016) in the benchmark; the NDEM-based Indian chips of the mid-term were not on
  the lab server.
- No surveyed flood maps for the Mahanadi; the atlas is checked against Sentinel-2 and, after the visit, against
  random field points.
- Modelled discharge (GloFAS) and modelled population (GHSL); OpenStreetMap is incomplete in villages.
- Radar-only water maps: about 0.65 IoU on the benchmark; urban and vegetated flooding are under-detected.
- The road model treats any 20 m of water as a closure and ignores depth; the bank screening uses 250 m soil data.
- Pass-level prediction is modest (pixel IoU ~0.2, settlement POD well below half): floodplain flooding is patchy, the
  observed maps are themselves radar maps, and local rain and storms — not only the Naraj flow — drive the largest
  floods. Past flood frequency ranks where land floods best (ROC AUC 0.90–0.91);
  the trigger map adds at which flow it floods (AUC 0.72), so the two are used together.
- Flood depth comes from a 30 m surface model (~2 m vertical error); wall screening, scour and foundation numbers
  use typical parameters (masonry tension, bed size, soil strength) and an unknown flow split between distributaries,
  all of which the field visit and the lab replace.
- The money figures use a continental depth–damage curve, the public housing grant as the value of a house, an
  assumed 4.4 people per household and a simple paddy-loss rule; they are lower bounds to be checked against the
  losses people report (§8.7).
- The live warning levels are proposed thresholds; GloFAS's own forecast skill at Naraj and the flow forecast of §6.7
  have not been checked against measured flows.

### 10.4 Conclusions

1. On a flood it had never seen, a U-Net (0.770) mapped water better than six geospatial
   foundation models (best 0.747); a three-model fusion was best
   (0.776).
2. A radar-only fusion of TerraMind and U-Net maps the Mahanadi delta through monsoon cloud; 590 passes
   from 2017 to 2026 form the atlas.
3. A per-pixel trigger discharge turns a Naraj flow forecast into a flood map and beats climatology on held-out years
   at high flows (0.20 vs 0.04).
4. In a 25-year flood about 30,427 people live on flooded land and 52,423 lose
   road access to a hospital; the links, banks, siren sites and sensor bridges to act on are listed.
5. Local rain and Bay of Bengal storms, not only the river, drive the largest floods of the delta; a warning has to
   read the river forecast together with the rainfall forecast. A learned model that adds rain and each pixel's flood
   history to the flow maps held-out heavy-rain passes better than the trigger map
   (0.22 vs 0.15).
6. The same scenarios give each specialization its answer: who loses the road to a hospital or shelter
   (transportation), where walls crack and how deep scour reaches (structural), which banks to inspect and which dry
   houses sit on soaked ground (geotechnical), how storms add to floods (ocean), when and at what earthwork the
   critical links can be raised (construction management), and where a flood peak comes from: about half from
   Hirakud dam and half from the tributaries below it (water resources).
7. Every one of the 92 training runs was re-checked from its saved outputs and the published TerraMind scores were
   reproduced within a point, so the benchmark can be relied on.
8. The Naraj flow can be forecast one to three days ahead from today's upstream flows and catchment rain (efficiency 0.89 three days ahead against 0.79 for persistence), and a live feed turns each day's GloFAS ensemble into an impact-based warning, a CAP alert and a list of villages and roads with dates.
9. The pipeline is not specific to the Mahanadi: the Brahmani–Baitarani delta and the Brahmaputra at Majuli were mapped from every radar pass since 2017 with the same models and joined the live feed.
10. Flood damage to houses and paddy is at least ₹17 crore a year; raising the ten critical roads repays its cost about 17 times in hospital access alone, so it is the first protection measure to fund.
10. The field visit is designed to measure what these numbers depend on and to change them where they are wrong.
### 10.5 Next steps, by specialization

| Specialization | Next step | Why |
|---|---|---|
| Remote sensing | Add SWOT water-surface elevations (2023–) and NISAR L-band (2025–) | Depth from measured water levels instead of a surface model; flooding under crops and trees |
| Water resources | Refit with observed CWC/WRD flows; calibrate a 2-D HEC-RAS model of the delta against the atlas | A physics-based inundation model that can go beyond the floods seen since 2017 |
| Transportation | Evacuation routing and shelter capacity from the live cut-off dates (§9.7); school and market (mandi) access | Who to move first, and where to |
| Structural | Local depth–damage curves for kutcha and pucca houses from the field survey, replacing the continental JRC curve of §7.9 | A damage estimate fitted to the delta's houses |
| Geotechnical | 2-D seepage analysis of the top-ranked embankments with lab permeability; bank-line migration from Landsat 1990– | Piping and erosion risk with numbers, not ranks |
| Ocean | Paradip tide-gauge and surge hindcasts; sea-level-rise scenarios for drainage of the lower delta | Compound river–rain–surge flooding |
| Construction technology & management | Life-cycle cost and O&M plan of the sensor network; procurement through GeM; contract packaging for road raising | From a plan to a project ClimMaTech and WRD can execute |

The common first step for all of them is the field visit (§8) and the observed Naraj flows.

### 10.6 Abstract for HYDRO 2026 / journal submission

*Turning river-flow forecasts into flood maps with Sentinel-1 and geospatial foundation models: the Mahanadi delta.*
We benchmark six geospatial foundation models against CNN and U-Net baselines on Sen1Floods11 with a leave-India-out
protocol (U-Net 0.770, best foundation model 0.747, fusion
0.776 IoU on an unseen Indian flood), build a radar-only flood atlas of the
Mahanadi delta from 590 Sentinel-1 passes (2017–2026), and link it to river
discharge at Naraj through a per-pixel trigger discharge. On held-out years the resulting flow-to-flood maps reach IoU
0.20 at high flows against 0.04 for flood climatology. Combined with road
networks and population, they identify the people cut off from hospitals, critical road links and river banks for
inspection, giving point-forecast early-warning systems the spatial impact layer they lack. A gradient-boosted model forecasts the Naraj flow one to three days ahead (Nash–Sutcliffe efficiency 0.99–0.89 on unseen monsoons), and a live feed turns each day's GloFAS ensemble into impact-based warnings published as CAP alerts.
