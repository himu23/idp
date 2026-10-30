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
| Water resources | Which flow floods which land? | GloFAS + ERA5, trigger discharge, held-out years, Gumbel | High-flow IoU 0.20 vs 0.04 climatology; 25-yr flow 32,997 m³/s | Discharge, Manning's n | Nikhil |
| Transportation systems | Who loses the road to a hospital or shelter? | OSM road graph, flooded edges cut, Dijkstra | 52,423 people cut off from any hospital; 10,077 extra person-hours of travel a day | Road closures at critical links | Himanshu |
| Structural | Where do walls crack; how deep must piers go? | DEM flood depth, wall moment check, IRC:78 Lacey scour | 4,080 people where depth ≥ 1 m; pier scour 7–24 m below HFL (100-yr, a quarter of the flow) | Deck clearance, HFL marks, foundation levels | Himanshu |
| Geotechnical | Which banks fail; which dry houses sit on soaked ground? | Bank screening; 200 m saturation advisory; bearing / settlement checks | 441,605 people in the advisory zone; bearing loss 55 % when soaked | Soil samples, well levels, slopes | Prabhat |
| Ocean | What do Bay of Bengal storms add? | IBTrACS tracks vs atlas; flood drivers | 37 systems within 300 km since 2016; 11 of the 20 largest floods followed one | Interviews on surge and tidal drainage | Nikhil |
| Construction technology & management | When to build, what it costs, in what order | Flood/storm climatology, earthwork take-off, BoQ, schedule | Work window December–April; 27,603 m³ to raise 10 critical links, all by embankment (largest raise 2.1 m) | Site sheets for sensors/sirens | Prabhat |
| Risk and economics (cross-cutting) | What do floods cost, and what is protection worth? | Depth–damage curve, paddy at the support price, 29 years of daily flows through the flow–impact table | ₹17 crore of damage a year; raising the critical links repays 17 times | Losses in the interviews | Himanshu, Prabhat |

### 7.1 Exposure: who and what is on flooded land

**Why it matters.** A warning has to say who is at risk, not how many square kilometres flood. **What we did.** Each
scenario was overlaid with population (GHSL), settlements, farmland (WorldCover), roads, railways, bridges, hospitals
and schools (OpenStreetMap). **What we found.** The 25-year flood covers 240 km² of land with
30,427 people on it, 32 settlements with at least 10 % of their people on flooded land,
182 km² of cropland and 39 km of road. Most flooded land is farmland; the people
exposed live in villages at its edges, which is why the viewer and the bulletin list settlements, not totals.

### 7.2 Transportation systems

![25-year flood: roads cut and critical links](../results/atlas_figures/impact_T25_map.png)

**Why it matters.** A flooded road is a lost hospital trip, a blocked evacuation and a long detour to market.
**What we did.** The OpenStreetMap road network became a graph; flooded sections were cut and shortest paths to
hospitals, towns and dry schools compared with dry weather. **What we found.** In the 25-year flood
52,423 people in 41 settlements lose road access to
any hospital, 20,605 more reach one only by a detour, and everyday trips grow
by about 10,077 person-hours a day. Ten critical links carry most of the cut-off routes (C.2). **At the site:** road
closures at those links.

### 7.3 Structural

![Estimated flood depth](../results/atlas_figures/depth_T25_map.png)

**Why it matters.** Standing water pushes over brick walls, and scour undermines bridge piers. **What we did.** Flood
depth from the ground elevation at the flood edge; a bending check of unreinforced brick walls; IRC:78 scour at
11 major bridges. **What we found.** A 230 mm brick wall cracks at about
0.8–1.0 m of water, and
4,080 people live where the 25-year flood is a metre deep or more. Pier scour reaches
7–24 m below the high flood
level if a branch carries a quarter of the 100-year flow; how the flow splits between branches is the missing input.
**At the site:** flood marks, deck clearance and foundation levels.

### 7.4 Geotechnical: river banks

**Why it matters.** Embankment breaches cause the worst local floods. **What we did.** 664 one-kilometre
bank cells were ranked by how often water stands behind the bank, in how many years, how erodible the soil is and how
many people live nearby. **What we found.** Twenty inspection sites at least 3 km apart (map and list in C.4);
SoilGrids at 250 m cannot tell one bank from another, so the field samples and lab tests decide. **At the site:** bank
inspection, slopes and soil samples.

### 7.5 Geotechnical: ground under houses that stay dry

![Ground-saturation advisory](../results/atlas_figures/ground_advisory_map.png)

**Why it matters.** Floodwater raises the groundwater under dry houses nearby: foundations weaken while it is high and
settle when it drops. **What we did.** An advisory zone of dry land within 200 m of flood water on fine-grained soil,
with textbook bearing-capacity and settlement checks. **What we found.** 441,605 people
(329 settlements) live in the zone in the 25-year flood; soaking cuts the bearing
capacity of a strip footing on silty sand by about 55 %, and a 2 m
drop of the water table settles soft clay by 20 to 39 mm.
**At the site:** water levels in village wells at 0–500 m from the flood edge.

### 7.6 Ocean

![Flood drivers](../results/atlas_figures/flood_drivers.png)

**Why it matters.** Bay of Bengal cyclones and depressions bring the heaviest rain, and surge and tide hold back the
drainage of the lower delta. **What we did.** IBTrACS storm tracks were matched to the radar floods. **What we found.**
37 systems passed within 300 km since 2016; of the 20 largest floods,
11 followed one, 13 came with heavy rain and 15 with a high river.
**At the site:** interviews on surge and tide-locked drainage.

### 7.7 Construction technology and management

![Deployment schedule](../results/atlas_figures/gantt.png)

**Why it matters.** Protection and sensors must be built outside the flood season, in the right order and within a
budget. **What we did.** Monthly flood and storm climatology, an earthwork take-off for raising the critical links,
deployment quantities and a schedule. **What we found.** The work window is December–April. Raising 10
critical links takes about 27,603 m³ of earthwork (about ₹0.97 crore
at an assumed ₹350/m³); none needs more than 2.1 m, so all are road embankments and none needs a bridge or a vented causeway. Installing 40 sirens and 6 river gauges takes about
78 crew-days. **At the site:** access, mounting and signal at the proposed sites.

### 7.8 Water resources and the watershed

**Why it matters.** The delta's floods are set upstream, by releases from Hirakud dam and by rain on the uncontrolled
tributaries below it, so a warning for the delta is a warning about the whole watershed. **What we did.** GloFAS
flows below Hirakud, at Tikarpara and at Naraj (1997–2025) were compared at the annual flood peak and over the monsoon
(C.8), next to the travel times and design floods of §6.5. **What we found.** Hirakud controls about 59 % of the basin
(83,400 of about 141,600 km²) and passes 60% of the July–September flow at Naraj, but only a median
48% of the annual flood peak (29 years): the other half comes from the
roughly 58,000 km² below the dam, within about a day. A delta warning therefore needs both the dam's release plan and
gauges on the tributaries below it, and watershed measures in that lower catchment (land cover, soil conservation, small
storages) act on the frequent floods more than on the rare largest ones. **At the site:** discharge and Manning's n at a
road bridge; the WRD's account of gate operations.

### 7.9 Flood risk in rupees and person-days

**Why it matters.** Protection and warnings compete for money with everything else a district builds, so the hazard
has to be put in rupees and in days of life disrupted. **What we did.** Flood depth (§7.3) times the JRC depth–damage
curve for houses in Asia gives the houses damaged; flooded paddy at Odisha's yield and the support price gives the crop
lost; every day of 1997–2025 (29 years) at Naraj, run through the flow–impact table, gives what an average year costs (C.9).
**What we found.** Expected flood damage is about ₹17 crore a year (houses ₹4.2
crore, paddy ₹12.9 crore), a lower bound because floods above the largest seen are. An average year
brings 438,978 person-days on flooded land and 131,511
person-days without road access to any hospital. Raising the ten critical links (§7.7) cuts the latter to
54,811; valued only at the rural wage, that repays the earthwork
17 times. Every 1,000 m³/s that Hirakud keeps off a 5-year peak keeps about 1,535
people dry. The impact-based warning levels of §9.7 would have reached "Be prepared" on 3.8
days a year on average, so warnings stay rare. **At the site:** the farmers' and householders' losses in the interviews.
