## 7. Seven specializations, one flood

The department's seven specializations each answer one question about the same flood scenarios: the design floods of
§6.5, land flooded in at least 10 % of monsoon passes, and the largest flood seen. This chapter gives, for each one, why
it matters for a flood warning, what was done and what was found, briefly; formulas, parameters and full tables are in
Appendix C. Remote sensing is chapters 4 and 6; water resources is chapter 6 and §7.8, which adds the watershed above
the delta. The 10- to 100-year scenarios are identical because the largest flow in the radar record (about 28,400 m³/s,
roughly a 10-year flood) bounds what the atlas can map, so they are lower bounds.

| Specialization | Question | Method | Headline result (25-year flood unless stated) | Field check (§8) | Owner |
|---|---|---|---|---|---|
| Remote sensing | Which model maps Indian floods through cloud? | Benchmark of 6 FMs vs CNN/U-Net; Sentinel-1 atlas; Sentinel-2 check | U-Net 0.770, best FM 0.747 (unseen flood); 590 passes mapped | 40 random ground-truth points | Vineet, Prakhar |
| Water resources | Which flow floods which land? | GloFAS + ERA5, trigger discharge, held-out years, Gumbel | High-flow IoU 0.23 vs 0.07 climatology; 25-yr flow 32,997 m³/s | Discharge, Manning's n | Nikhil |
| Transportation systems | Who loses the road to a hospital or shelter? | OSM road graph, flooded edges cut, Dijkstra | 36,941 people cut off from any hospital; 12,023 extra person-hours of travel a day | Road closures at critical links | Himanshu |
| Structural | Where do walls crack; how deep must piers go? | DEM flood depth, wall moment check, IRC:78 Lacey scour | 3,626 people where depth ≥ 1 m; pier scour 7–24 m below HFL (100-yr, a quarter of the flow) | Deck clearance, HFL marks, foundation levels | Himanshu |
| Geotechnical | Which banks fail; which dry houses sit on soaked ground? | Bank screening; 200 m saturation advisory; bearing / settlement checks | 415,549 people in the advisory zone; bearing loss 55 % when soaked | Soil samples, well levels, slopes | Prabhat |
| Ocean | What do Bay of Bengal storms add? | IBTrACS tracks vs atlas; flood drivers | 37 systems within 300 km since 2016; 11 of the 20 largest floods followed one | Interviews on surge and tidal drainage | Nikhil |
| Construction technology & management | When to build, what it costs, in what order | Flood/storm climatology, earthwork take-off, BoQ, schedule | Work window December–April; 17,442 m³ to raise 8 critical links, 2 more need a bridge or vented causeway | Site sheets for sensors/sirens | Prabhat |

### 7.1 Exposure: who and what is on flooded land

**Why it matters.** A warning has to say who is at risk, not how many square kilometres flood. **What we did.** Each
scenario was overlaid with population (GHSL), settlements, farmland (WorldCover), roads, railways, bridges, hospitals
and schools (OpenStreetMap). **What we found.** The 25-year flood covers 216 km² of land with
25,163 people on it, 24 settlements with at least 10 % of their people on flooded land,
164 km² of cropland and 32 km of road. Most flooded land is farmland; the people
exposed live in villages at its edges, which is why the viewer and the bulletin list settlements, not totals.

### 7.2 Transportation systems

![25-year flood: roads cut and critical links](../results/atlas_figures/impact_T25_map.png)

**Why it matters.** A flooded road is a lost hospital trip, a blocked evacuation and a long detour to market.
**What we did.** The OpenStreetMap road network became a graph; flooded sections were cut and shortest paths to
hospitals, towns and dry schools compared with dry weather. **What we found.** In the 25-year flood
36,941 people in 32 settlements lose road access to
any hospital, 24,345 more reach one only by a detour, and everyday trips grow
by about 12,023 person-hours a day. Ten critical links carry most of the cut-off routes (C.2). **At the site:** road
closures at those links.

### 7.3 Structural

![Estimated flood depth](../results/atlas_figures/depth_T25_map.png)

**Why it matters.** Standing water pushes over brick walls, and scour undermines bridge piers. **What we did.** Flood
depth from the ground elevation at the flood edge; a bending check of unreinforced brick walls; IRC:78 scour at
11 major bridges. **What we found.** A 230 mm brick wall cracks at about
0.8–1.0 m of water, and
3,626 people live where the 25-year flood is a metre deep or more. Pier scour reaches
7–24 m below the high flood
level if a branch carries a quarter of the 100-year flow; how the flow splits between branches is the missing input.
**At the site:** flood marks, deck clearance and foundation levels.

### 7.4 Geotechnical: river banks

**Why it matters.** Embankment breaches cause the worst local floods. **What we did.** 663 one-kilometre
bank cells were ranked by how often water stands behind the bank, in how many years, how erodible the soil is and how
many people live nearby. **What we found.** Twenty inspection sites at least 3 km apart (map and list in C.4);
SoilGrids at 250 m cannot tell one bank from another, so the field samples and lab tests decide. **At the site:** bank
inspection, slopes and soil samples.

### 7.5 Geotechnical: ground under houses that stay dry

![Ground-saturation advisory](../results/atlas_figures/ground_advisory_map.png)

**Why it matters.** Floodwater raises the groundwater under dry houses nearby: foundations weaken while it is high and
settle when it drops. **What we did.** An advisory zone of dry land within 200 m of flood water on fine-grained soil,
with textbook bearing-capacity and settlement checks. **What we found.** 415,549 people
(310 settlements) live in the zone in the 25-year flood; soaking cuts the bearing
capacity of a strip footing on silty sand by about 55 %, and a 2 m
drop of the water table settles soft clay by 20 to 39 mm.
**At the site:** water levels in village wells at 0–500 m from the flood edge.

### 7.6 Ocean

![Flood drivers](../results/atlas_figures/flood_drivers.png)

**Why it matters.** Bay of Bengal cyclones and depressions bring the heaviest rain, and surge and tide hold back the
drainage of the lower delta. **What we did.** IBTrACS storm tracks were matched to the radar floods. **What we found.**
37 systems passed within 300 km since 2016; of the 20 largest floods,
11 followed one, 14 came with heavy rain and 18 with a high river.
**At the site:** interviews on surge and tide-locked drainage.

### 7.7 Construction technology and management

![Deployment schedule](../results/atlas_figures/gantt.png)

**Why it matters.** Protection and sensors must be built outside the flood season, in the right order and within a
budget. **What we did.** Monthly flood and storm climatology, an earthwork take-off for raising the critical links,
deployment quantities and a schedule. **What we found.** The work window is December–April. Raising 8
critical links takes about 17,442 m³ of earthwork (about ₹0.61 crore
at an assumed ₹350/m³); 2 more would need raises above 3 m, that is a bridge or a vented
causeway. Installing 40 sirens and 6 river gauges takes about
78 crew-days. **At the site:** access, mounting and signal at the proposed sites.

### 7.8 Water resources and the watershed

**Why it matters.** The delta's floods are set upstream, by releases from Hirakud dam and by rain on the uncontrolled
tributaries below it, so a warning for the delta is a warning about the whole watershed. **What we did.** GloFAS
flows below Hirakud, at Tikarpara and at Naraj (1984–2025) were compared at the annual flood peak and over the monsoon
(C.8), next to the travel times and design floods of §6.5. **What we found.** Hirakud controls about 59 % of the basin
(83,400 of about 141,600 km²) and passes 60% of the July–September flow at Naraj, but only a median
48% of the annual flood peak (29 years): the other half comes from the
roughly 58,000 km² below the dam, within about a day. A delta warning therefore needs both the dam's release plan and
gauges on the tributaries below it, and watershed measures in that lower catchment (land cover, soil conservation, small
storages) act on the frequent floods more than on the rare largest ones. **At the site:** discharge and Manning's n at a
road bridge; the WRD's account of gate operations.
