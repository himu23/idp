## Appendix C. Engineering details of the seven specializations

Formulas, parameters and full tables behind the short summaries of chapter 7 (C.1–C.7 follow 7.1–7.7; C.8 is the watershed analysis of 7.8).

Population: GHSL 2020 (4,102,130 people in the box, 3,839,001 of them in
1,082 settlements). Roads, bridges, railways, hospitals and schools: OpenStreetMap
(6,383 km of road, 691 bridge segments, 386 hospitals and
clinics, 103 schools). All areas exclude the river bed and normal water.

### C.1 Exposure

| Scenario | Flooded land (km²) | People on flooded land | Settlements ≥ 10 % flooded | Cropland (km²) | Road under water, km (main roads) | Rail (km) | Bridges with flooded approach | Health facilities | Schools |
|---|---|---|---|---|---|---|---|---|---|
| 2-year | 50 | 7,837 | 4 | 24 | 6 (1) | 0.0 | 46 | 4 | 0 |
| 5-year | 218 | 25,384 | 24 | 165 | 34 (11) | 0.3 | 71 | 6 | 0 |
| 10-year | 240 | 30,427 | 32 | 182 | 39 (14) | 0.3 | 79 | 7 | 0 |
| 25-year | 240 | 30,427 | 32 | 182 | 39 (14) | 0.3 | 79 | 7 | 0 |
| 50-year | 240 | 30,427 | 32 | 182 | 39 (14) | 0.3 | 79 | 7 | 0 |
| 100-year | 240 | 30,427 | 32 | 182 | 39 (14) | 0.3 | 79 | 7 | 0 |
| flooded in ≥ 10 % of passes | 54 | 11,801 | 3 | 27 | 20 (7) | 0.1 | 62 | 7 | 2 |
| largest seen (2018-09-08) | 278 | 39,367 | 38 | 231 | 35 (11) | 0.4 | 97 | 8 | 2 |

Most flooded land is cropland; the people exposed live in villages on slightly higher ground at the edge of the
flooded fields, which is why a settlement-level list (viewer, bulletin tool) is more useful to a district officer
than a total. Mapped building footprints are incomplete here (Microsoft: 120,647 footprints for
4.1 million people), so people, not buildings, are counted.

### C.2 Transportation systems

![25-year flood: roads cut and critical links](../results/atlas_figures/impact_T25_map.png)

| Scenario | Road cut (km) | Settlements cut off from any hospital/clinic | People cut off | People reaching one only by a detour ≥ 5 min | Median detour (min) | People cut off from any town |
|---|---|---|---|---|---|---|
| 2-year | 8 | 0 | 0 | 802 | 7.5 | 0 |
| 5-year | 48 | 39 | 51,155 | 20,287 | 8.3 | 63,788 |
| 10-year | 54 | 41 | 52,423 | 20,605 | 7.6 | 65,056 |
| 25-year | 54 | 41 | 52,423 | 20,605 | 7.6 | 65,056 |
| 50-year | 54 | 41 | 52,423 | 20,605 | 7.6 | 65,056 |
| 100-year | 54 | 41 | 52,423 | 20,605 | 7.6 | 65,056 |
| flooded in ≥ 10 % of passes | 25 | 1 | 521 | 802 | 7.5 | 521 |
| largest seen (2018-09-08) | 49 | 43 | 49,742 | 32,621 | 11.7 | 95,950 |

Graph: 147,729 nodes, 156,647 edges, 6,383 km; 364 hospital/clinic
nodes and 6 towns; settlements farther than 500 m from the main network are not routed.

- **Evacuation**: schools serve as relief camps. In the 25-year flood 101 of the
  mapped schools stay dry and 65,056 people can reach none of them by
  road. OpenStreetMap maps only about a hundred schools here (every village has one), so travel times to shelters
  need the official OSDMA shelter list; the cut-off count is the robust part.
- **Everyday travel**: with an assumed 0.2 trips per person per day to the nearest town, the detours of the 25-year
  flood add about 10,077 person-hours of travel a day — the cost that does not appear in damage figures.
- **Critical links** (flooded sections carrying the most people's dry-weather route to the nearest hospital; raising
  or protecting these keeps the most people connected; earthwork in C.7):

| Rank | Road | Class | People routed | Flooded length (km) | Location |
|---|---|---|---|---|---|
| 1 | (unnamed) | secondary | 10,930 | 0.83 | 20.2661 N, 86.3614 E |
| 2 | (unnamed) | unclassified | 10,351 | 1.68 | 20.3826 N, 86.1631 E |
| 3 | (unnamed) | unclassified | 9,421 | 0.34 | 20.2716 N, 86.0251 E |
| 4 | (unnamed) | unclassified | 7,657 | 0.14 | 20.3995 N, 86.2551 E |
| 5 | (unnamed) | tertiary | 7,582 | 0.42 | 20.4527 N, 86.3781 E |
| 6 | (unnamed) | tertiary | 7,045 | 0.14 | 20.3455 N, 86.3792 E |
| 7 | (unnamed) | unclassified | 6,210 | 0.34 | 20.4651 N, 86.3551 E |
| 8 | (unnamed) | residential | 6,171 | 0.03 | 20.2845 N, 86.4417 E |
| 9 | (unnamed) | tertiary | 4,863 | 0.16 | 20.3869 N, 86.4210 E |
| 10 | (unnamed) | unclassified | 4,638 | 0.05 | 20.5250 N, 86.0275 E |

### C.3 Structural

![Estimated flood depth and settlements where walls are at risk](../results/atlas_figures/depth_T25_map.png)

- **Flood depth** (`impact_depth.py`): the water surface of each flood patch is the median elevation of its edge,
  depth = surface − ground (Copernicus GLO-30, ~2 m vertical error: a screening estimate, checked against the flood
  marks of the field points). 25-year flood: median depth 0.0 m,
  90th percentile 1.1 m.
- **Masonry walls**: water on one side of an unreinforced brick wall gives a base moment γ_w d³/6 per metre; the wall
  cracks when this exceeds f_t t²/6. With flexural tension f_t = 0.1–0.2 MPa the critical depth is
  0.81–1.03 m for a 230 mm wall and
  0.51–0.65 m for a 115 mm wall (self-weight
  ignored, conservative). **4,080 people** live where the 25-year flood is 1 m deep
  or more (5,867 at 0.6 m or more); mud walls weaken with soaking at any depth.
  The settlements are listed in `results/impact/wall_risk_settlements.csv`.
- **Bridge scour** (IRC:78, Lacey): d_sm = 1.34 (D_b²/K_sf)^(1/3), D_b = Q / linear waterway, K_sf = 1.76 √d_m
  (d_m = 0.3 mm until the field sieve gives the bed size); maximum scour 2.0 d_sm at piers, 1.27 d_sm at abutments,
  below HFL. The share of the Naraj flow each branch carries is not known here (asked from WRD). For the 100-year flow
  (+10 %) the maximum pier scour is 7–24 m
  below HFL if the branch carries a quarter of it and 11–38 m
  if it carries half. Minor distributaries carry far less than half, so their upper values are not credible; the
  short waterways of the minor-branch bridges drive the large numbers. With half of the flow through each branch:

| River | Bridge | Linear waterway (m) | Q (m³/s) | D_b (m³/s/m) | d_sm (m) | Pier scour below HFL (m) | Abutment scour (m) |
|---|---|---|---|---|---|---|---|
| Devi River | Netaji Subhash Chandra Bose Setu | 2823 | 22,258 | 7.9 | 5.4 | 10.7 | 6.8 |
| Kathajodi | NH16 | 869 | 22,258 | 25.6 | 11.8 | 23.6 | 15.0 |
| Birupa | NH16;NH55 | 543 | 22,258 | 41.0 | 16.1 | 32.3 | 20.5 |
| Luna | (unnamed) | 776 | 22,258 | 28.7 | 12.7 | 25.4 | 16.1 |
| Mahanadi | (unnamed) | 458 | 22,258 | 48.5 | 18.1 | 36.1 | 22.9 |
| Biropa | (unnamed) | 424 | 22,258 | 52.5 | 19.0 | 38.0 | 24.1 |
| – | (unnamed) | 2240 | 22,258 | 9.9 | 6.3 | 12.5 | 8.0 |
| – | (unnamed) | 1935 | 22,258 | 11.5 | 6.9 | 13.8 | 8.8 |
| – | NH16;NH55 | 2253 | 22,258 | 9.9 | 6.2 | 12.5 | 7.9 |
| – | NH16;NH55 | 2260 | 22,258 | 9.8 | 6.2 | 12.5 | 7.9 |
| Mahanadi | Utkal Gourab Madhusudan Bridge | 2580 | 22,258 | 8.6 | 5.7 | 11.4 | 7.2 |

  –: river not matched in OpenStreetMap; these are the parallel road crossings of the Mahanadi just north of Cuttack
  (20.48 N, 85.91 E). Shares of 25 % and 75 % are in
  `bridge_scour.csv`. Pier foundations must reach well below these depths; the PWD
  foundation levels collected at the site close the check.
- **Clearance and facilities**: 79 bridge segments have flood water within 60 m
  of an end; deck clearance above HFL is checked against IRC:5 at the site (§8.5). 7
  hospitals/clinics and 0 schools have flood water within 60 m; 0.3 km of railway is
  under water.

![Bridge scour screening](../results/atlas_figures/bridge_scour.png)

### C.4 Geotechnical: river banks

![River-bank inspection priority](../results/atlas_figures/geotech_map.png)

664 one-kilometre cells contain river bank. SoilGrids gives clay loam (454), clay (166), silty clay loam (36), silty clay (8)
— too coarse to tell one bank from another, which is why the field samples matter. OpenStreetMap maps only
12 embankment segments (1.8 km), so the screening works from the river-bed
outline (the WRD embankment inventory is requested in §8.1). The field list is the 20 highest cells at least 3 km apart:

| Rank | Location | Water behind the bank (share of passes) | Years with water behind the bank | Texture (sand/silt/clay %) | People within 2 km |
|---|---|---|---|---|---|
| 1 | 20.5110 N, 85.9180 E | 4% | 10 | clay loam (29/38/32) | 53,829 |
| 2 | 20.4920 N, 85.8320 E | 3% | 10 | clay loam (30/37/33) | 93,127 |
| 3 | 20.4290 N, 85.9090 E | 6% | 10 | clay loam (29/37/34) | 68,934 |
| 4 | 20.4290 N, 85.8710 E | 7% | 10 | clay loam (29/36/34) | 22,047 |
| 5 | 20.3140 N, 86.3690 E | 8% | 10 | clay loam (22/44/34) | 18,481 |
| 6 | 20.3210 N, 85.8810 E | 2% | 10 | clay loam (37/30/33) | 24,225 |
| 7 | 20.2940 N, 85.8910 E | 2% | 9 | clay loam (36/30/34) | 13,872 |
| 8 | 20.2570 N, 85.8810 E | 1% | 8 | clay loam (34/34/32) | 14,397 |
| 9 | 20.3140 N, 86.3980 E | 1% | 8 | clay loam (21/44/34) | 23,281 |
| 10 | 20.3140 N, 86.3220 E | 7% | 10 | clay loam (23/40/37) | 14,275 |

Laboratory plan: wet sieving (IS 2720 Part 4), liquid / plastic limits (IS 2720 Part 5), IS 1498 class, Kenney–Lau
internal stability and a piping flag (`soil_gradation.py`); bank slopes measured at the site give the factor of
safety dry, under seepage and after rapid drawdown (`embankment_stability.py`), when the river falls faster than the
bank drains and the factor of safety roughly halves.

### C.5 Geotechnical: ground saturation under houses that stay dry

![Ground-saturation advisory](../results/atlas_figures/ground_advisory_map.png)

Floodwater raises the water table under the land around it. Houses that stay dry but stand on that soaked ground
lose bearing capacity while it is wet and settle when the water table falls back. The advisory zone is dry land within
200 m of flood water on fine-grained soil (silt + clay ≥ 50 %, 94% of the box).

| Scenario | Advisory zone (km²) | People in the zone | People on flooded land | Settlements with ≥ 25 % of people in the zone |
|---|---|---|---|---|
| 5-year | 464 | 407,037 | 25,384 | 305 |
| 25-year | 489 | 441,605 | 30,427 | 329 |
| 100-year | 489 | 441,605 | 30,427 | 329 |
| flooded in ≥ 10 % of passes | 366 | 291,194 | 11,801 | 177 |

What the advisory means for a typical house foundation (strip footing 1 m wide at 1 m depth; textbook parameters to be
replaced by the lab results, `foundation_checks.py`):

- silty sand (φ' = 28°): ultimate bearing capacity 415 kPa with a deep water
  table, 189 kPa with water at the surface
  (−55 %);
- clay loam, undrained: 275 kPa stiff → 172 kPa soaked
  (−37 %);
- when the water table falls 2 m after the flood, 4 m of soft clay consolidates by
  20 to 39 mm (m_v 0.25–0.5 m²/MN) — enough to crack
  load-bearing masonry where it is uneven.

The 200 m distance is a screening value; the water levels in village wells at increasing distance from the flood edge
(field protocol H) fix it.

### C.6 Ocean engineering

![Flood drivers](../results/atlas_figures/flood_drivers.png)

37 cyclones and depressions passed within 300 km of the delta since 2016
(IBTrACS). Of the 20 largest floods seen by radar, 15 came with a high Naraj flow (≥ 9,682 m³/s, the
monsoon 90th percentile), 13 with heavy rain (≥ 135 mm in 7 days) and
11 within a week of a Bay of Bengal system:

| Date | Flooded land (km²) | Naraj flow (m³/s) | Rain (mm) | System | Drivers |
|---|---|---|---|---|---|
| 2021-09-14 | 411 | 11,614 | 231 | depression (unnamed) | river + rain + cyclone/depression |
| 2020-08-26 | 377 | 14,487 | 187 |  | river + rain |
| 2022-08-16 | 280 | 24,603 | 177 | depression (unnamed) | river + rain + cyclone/depression |
| 2018-09-06 | 222 | 13,867 | 186 | depression (unnamed) | river + rain + cyclone/depression |
| 2018-09-12 | 212 | 13,645 | 117 | depression (unnamed) | river + cyclone/depression |
| 2026-07-26 | 246 | 5,283 | 259 |  | rain |
| 2018-09-08 | 278 | 15,030 | 159 | depression (unnamed) | river + rain + cyclone/depression |
| 2021-09-16 | 271 | 15,380 | 242 | depression (unnamed) | river + rain + cyclone/depression |
| 2026-08-14 | 174 | 9,682 | 187 |  | river + rain |
| 2021-09-19 | 195 | 12,617 | 175 | depression (unnamed) | river + rain + cyclone/depression |
| 2026-10-01 | 153 | 19,497 | 56 |  | river |
| 2018-10-14 | 205 | 6,901 | 145 | Titli | rain + cyclone/depression |
| 2020-09-07 | 136 | 10,279 | 42 |  | river |
| 2026-08-02 | 132 | 14,893 | 155 |  | river + rain |
| 2019-08-14 | 129 | 8,709 | 74 | depression (unnamed) | cyclone/depression |
| 2019-09-13 | 118 | 18,577 | 59 |  | river |
| 2025-07-31 | 114 | 16,217 | 85 | depression (unnamed) | river + cyclone/depression |
| 2025-07-07 | 88 | 3,854 | 125 |  | none above the 90th percentiles |
| 2023-09-16 | 87 | 7,533 | 156 |  | rain |
| 2018-07-25 | 109 | 12,444 | 271 | depression (unnamed) | river + rain + cyclone/depression |

Systems that came within 300 km:

| System | Closest | Distance (km) | Max wind near the delta (kt) | Rain that week (mm) | Max Naraj flow that week (m³/s) | Largest flood on a pass (km²) |
|---|---|---|---|---|---|---|
| Roanu | 2016-05-20 | 132 | 45 | 102 | 69 |  |
| depression (unnamed) | 2016-08-17 | 259 | 25 | 47 | 10,398 |  |
| depression (unnamed) | 2016-11-05 | 236 | 25 | 79 | 1,212 |  |
| depression (unnamed) | 2017-07-18 | 99 | 25 | 89 | 6,838 | 54.5 |
| depression (unnamed) | 2017-10-19 | 64 | 25 | 152 | 2,611 | 18.2 |
| depression (unnamed) | 2017-11-17 | 107 | 25 | 104 | 2,957 | 4.1 |
| depression (unnamed) | 2017-12-09 | 170 | 30 | 98 | 1,171 |  |
| depression (unnamed) | 2018-07-21 | 192 | 30 | 249 | 12,444 | 109.3 |
| depression (unnamed) | 2018-08-07 | 123 | 25 | 212 | 11,040 | 58.1 |
| depression (unnamed) | 2018-08-15 | 52 | 25 | 103 | 13,365 | 49.8 |
| depression (unnamed) | 2018-09-06 | 155 | 30 | 164 | 15,030 | 278.4 |
| Daye | 2018-09-20 | 178 | 35 | 88 | 5,382 | 54.2 |
| Titli | 2018-10-12 | 82 | 80 | 78 | 6,901 | 204.9 |
| Fani | 2019-05-03 | 28 | 115 | 180 | 1,168 |  |
| depression (unnamed) | 2019-08-07 | 140 | 30 | 133 | 11,428 | 129.2 |
| Bulbul (Matmo) | 2019-11-09 | 154 | 75 | 43 | 1,844 | 14.5 |
| Amphan | 2020-05-20 | 180 | 100 | 112 | 377 |  |
| depression (unnamed) | 2020-10-22 | 147 | 25 | 58 | 3,040 | 23.6 |
| Yaas | 2021-05-26 | 134 | 75 | 149 | 385 |  |
| depression (unnamed) | 2021-09-13 | 64 | 30 | 227 | 15,380 | 411.3 |
| Gulab (Shaheen) | 2021-09-26 | 217 | 45 | 52 | 6,682 | 96.1 |
| Jawad | 2021-12-05 | 105 | 30 | 158 | 1,527 |  |
| depression (unnamed) | 2022-08-09 | 67 | 25 | 193 | 24,603 | 280.4 |
| depression (unnamed) | 2022-08-14 | 184 | 25 | 171 | 28,378 | 280.4 |
| depression (unnamed) | 2022-08-19 | 215 | 30 | 136 | 26,914 | 67.4 |
| depression (unnamed) | 2022-09-11 | 182 | 25 | 74 | 6,294 | 14.0 |
| Hamoon | 2023-10-23 | 254 | 50 | 3 | 2,088 | 9.6 |
| Midhili | 2023-11-16 | 247 | 35 | 25 | 1,261 | 4.7 |
| depression (unnamed) | 2024-07-20 | 112 | 25 | 50 | 4,852 | 16.8 |
| depression (unnamed) | 2024-09-09 | 52 | 30 | 52 | 19,098 | 26.8 |
| depression (unnamed) | 2024-09-15 | 288 | 30 | 77 | 17,946 | 18.6 |
| Dana | 2024-10-26 | 88 | 60 | 70 | 1,874 | 13.3 |
| depression (unnamed) | 2025-05-29 | 230 | 30 | 70 | 558 | 7.1 |
| depression (unnamed) | 2025-07-25 | 273 | 25 | 86 | 16,217 | 113.5 |
| depression (unnamed) | 2025-08-19 | 188 | 20 | 100 | 7,655 | 28.3 |
| depression (unnamed) | 2025-09-26 | 128 | 25 | 68 | 9,682 | 52.1 |
| depression (unnamed) | 2025-10-02 | 181 | 30 | 120 | 11,454 | 15.4 |

Storm surge and high tide also slow the drainage of the lower delta through the tidal distributaries; the study box
ends about 25 km inland of Paradip, and a tide-gauge record (Paradip) is the first ocean dataset to add.

### C.7 Construction technology and management

![Construction windows](../results/atlas_figures/construction_windows.png)

| Month | Mean Naraj flow (m³/s) | Days above the 2-year flood | Storms within 300 km per year | Mean flooded share on radar | Work window |
|---|---|---|---|---|---|
| Jan | 569 | 0.0% | 0.00 |  | yes |
| Feb | 398 | 0.0% | 0.00 |  | yes |
| Mar | 269 | 0.0% | 0.00 |  | yes |
| Apr | 278 | 0.0% | 0.02 |  | yes |
| May | 231 | 0.0% | 0.20 |  | no |
| Jun | 291 | 0.0% | 0.35 | 0.2% | no |
| Jul | 3,274 | 1.2% | 0.37 | 1.3% | no |
| Aug | 8,355 | 2.9% | 0.74 | 1.9% | no |
| Sep | 7,465 | 2.6% | 0.59 | 2.2% | no |
| Oct | 2,882 | 0.0% | 0.50 | 0.9% | no |
| Nov | 1,210 | 0.0% | 0.22 | 0.3% | no |
| Dec | 965 | 0.0% | 0.07 |  | yes |

**Raising the critical links** above the 25-year flood (raise = 90th-percentile depth + 0.6 m freeboard; crest 3.75 m
single lane or 7.5 m for trunk/primary roads; side slopes 2H:1V; earthwork at an assumed ₹350/m³):

| Rank | Road | Class | Flooded (km) | Depth p90 (m) | Raise (m) | Crest (m) | Design | Earthwork (m³) | Cost (₹ lakh) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | (unnamed) | secondary | 0.83 | 0.2 | 0.8 | 3.75 | embankment raise | 3,552 | 12.4 |
| 2 | (unnamed) | unclassified | 1.68 | 0.8 | 1.4 | 3.75 | embankment raise | 15,406 | 53.9 |
| 3 | (unnamed) | unclassified | 0.34 | 0.7 | 1.3 | 3.75 | embankment raise | 2,868 | 10.0 |
| 4 | (unnamed) | unclassified | 0.14 | 0.1 | 0.7 | 3.75 | embankment raise | 468 | 1.6 |
| 5 | (unnamed) | tertiary | 0.42 | 0.0 | 0.6 | 3.75 | embankment raise | 1,247 | 4.4 |
| 6 | (unnamed) | tertiary | 0.14 | 0.9 | 1.5 | 3.75 | embankment raise | 1,404 | 4.9 |
| 7 | (unnamed) | unclassified | 0.34 | 0.0 | 0.6 | 3.75 | embankment raise | 1,010 | 3.5 |
| 8 | (unnamed) | residential | 0.03 | 0.2 | 0.8 | 3.75 | embankment raise | 128 | 0.4 |
| 9 | (unnamed) | tertiary | 0.16 | 0.2 | 0.8 | 3.75 | embankment raise | 685 | 2.4 |
| 10 | (unnamed) | unclassified | 0.05 | 1.5 | 2.1 | 3.75 | embankment raise | 835 | 2.9 |

Embankment raises for 10 links (4.13 km of road):
27,603 m³, about ₹0.97 crore. Each of the ten links
carries the dry-weather hospital route of 4,638–10,930 people.

**Deployment quantities** (quantities and effort only; the unit rates are asked from ClimMaTech):

| Item | Unit | Quantity | Crew-days | Basis |
|---|---|---|---|---|
| Solar siren unit with controller (Rakshak-type), mast and foundation | site | 40 | 40 | 40 sirens cover 48% of the exposed people at a 1.5 km audible range (impact_siting.py) |
| Non-contact radar level + surface-velocity station (Pravaah-type) on bridge, with logger and telemetry | site | 6 | 12 | one per main distributary (impact_siting.py) |
| Cross-section and bed-material survey at each sensor bridge | site | 6 | 6 | needed to turn level + surface velocity into discharge |
| Community training and siren drills | village | 40 | 20 | one session per siren site |

![Deployment schedule](../results/atlas_figures/gantt.png)

**Risks**: permissions for bridge mounting (PWD/NH) and siren sites (panchayat) — start in week 1; theft and vandalism of
solar panels — mount high, community custody; mobile-network gaps — LoRa or satellite backhaul at the sites the field
sheets flag; installation slipping into the monsoon — the window closes in May; maintenance — one pre-monsoon visit per
site each year.

### C.8 Water resources: the watershed above the delta

Daily GloFAS v4 flows just below Hirakud dam and at Naraj, 29 complete years between 1997 and 2025
(`mahanadi/watershed_share.py`). For each year the flow below Hirakud on the day before the Naraj peak is compared with
the peak (one day is the travel time found in §6.5).

| Year | Naraj annual peak (m³/s) | Flow below Hirakud the day before (m³/s) | Share from Hirakud |
|---|---|---|---|
| 2003 | 34,673 | 27,541 | 79% |
| 2001 | 30,619 | 14,824 | 48% |
| 2014 | 28,906 | 13,708 | 47% |
| 2022 | 28,378 | 15,310 | 54% |
| 2011 | 28,118 | 14,060 | 50% |

Over all 29 years the share has a median of 48% (interquartile range
30%–66%); in July–September the dam passes 60% of the mean flow at Naraj
(3,803 of 6,353 m³/s). Basin areas: Hirakud controls about 83,400 km² of a
basin of about 141,600 km² (sources differ between about 139,700 and 141,600 km²). GloFAS represents the reservoir with
a generic operating rule, so these shares are indicative until CWC/WRD gauge and release records replace them.

### C.9 Risk and economics

**Houses.** For each design flood, the people on flooded land in each 0.1 m depth step (impact_depth.py, now also for
the 2- and 10-year floods) times the JRC depth–damage fraction for residential buildings in Asia (Huizinga et al. 2017:
0.33 at 0.5 m, 0.49 at 1 m, 0.72 at 2 m, 1.0 at 6 m) gives damage in house-equivalents at one household per
4.4 people (an assumption of the order of the Census for rural Odisha), priced at
the PMAY-G rural housing assistance of ₹1.20 lakh a house: the public cost of rebuilding, a lower bound of the loss.
**Paddy.** Flooded cropland (ESA WorldCover) at Odisha's rice yield of 2,081 kg/ha (RBI, 2023-24) and the 2025-26 MSP of
₹2,369 a quintal (₹49,299 a hectare); the crop is lost where the water is 0.5 m deep or more and
30% is lost where it is shallower. **Expected annual damage** is the area under the
damage–probability curve from the 2- to the 100-year flood (trapezoid rule) plus the 100-year damage for the rarer tail.

| Flood | Naraj flow (m³/s) | People on flooded land | Houses (damage-equivalent) | Houses (₹ crore) | Paddy flooded (ha) | Paddy lost (ha) | Paddy (₹ crore) | Total (₹ crore) |
|---|---|---|---|---|---|---|---|---|
| 2-year | 17,897 | 7,837 | 245 | 2.93 | 2,419 | 985 | 4.85 | 7.78 |
| 5-year | 23,940 | 25,384 | 812 | 9.74 | 16,539 | 6,579 | 32.44 | 42.18 |
| 10-year | 27,941 | 30,427 | 999 | 11.99 | 18,206 | 7,746 | 38.19 | 50.18 |
| 25-year | 32,997 | 30,427 | 999 | 11.99 | 18,206 | 7,746 | 38.19 | 50.18 |
| 50-year | 36,747 | 30,427 | 999 | 11.99 | 18,206 | 7,746 | 38.19 | 50.18 |
| 100-year | 40,470 | 30,427 | 999 | 11.99 | 18,206 | 7,746 | 38.19 | 50.18 |

The 10- to 100-year rows are equal because the radar record has not seen a larger flood (§6.5): the expected annual
damage, ₹17.1 crore, is a lower bound. **The daily record.** Each day of 1997–2025 (29 years) at Naraj, as the
3-day peak flow the atlas uses, was looked up in the flow–impact table (`impact_curve.csv`): on average a year brings
438,978 person-days on flooded land and 131,511
person-days without road access to any hospital (54,811 with the ten
critical links raised, i.e. never cut). The warning levels of §9.7 would have stood at "Be aware" or above on
12.7 days a year, "Be prepared" or above on 3.8 and
"Act now" on 2.2, with "Act now" in 10 of the years.
**Road raising.** The earthwork of C.7 (₹0.97 crore) annualised over 20 years at
10% costs ₹11.4 lakh a year; the 76,700 person-days of
hospital access it saves, valued at the Odisha MGNREGA wage of ₹254 a day (2024-25), are worth ₹195
lakh: a benefit–cost ratio of 17 that leaves out health outcomes and travel delays.
**Hirakud.** Taking 1,000 m³/s off the peak keeps about 295, 1,535 and
2,965 people dry in a 2-, 5- and 10-year flood. **Warnings.** Twenty-four hours of warning cuts flood
damage by about 30 % (Global Commission on Adaptation, 2019), about ₹5 crore a year here.
