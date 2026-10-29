## 8. Field visit: what we measure, whom we ask, and what it changes

The 14 October review was explicit: the committee will ask what we did at the site, what we took from it and how
it changed the work. The visit is therefore designed around **the gaps the models cannot close by themselves**.
The full protocols, equipment and safety rules are in `fieldkit/FIELD_VISIT_KIT.md`; the data sheets are the CSV
files in `fieldkit/templates/`; every sheet has an analysis script in `fieldkit/analysis/`, tested on made-up
example sheets (`fieldkit/examples/`, marked EXAMPLE, never reported as results).

> **Status (29 Oct 2026):** visit being arranged with Prof. Basudev Biswal (Mahanadi basin project) and ClimMaTech.
> Sections 8.3–8.7 are filled in from the field sheets after the visit; until then they state the method only.

### 8.1 Where and with whom

Planned area: the Mahanadi delta between Naraj (delta head, CWC gauge, Naraj and Mundali barrages) and
Kendrapara. Hosts and interviews: Odisha Water Resources Department (Mahanadi divisions, Cuttack), CWC Mahanadi
division, the district emergency office, ClimMaTech, and residents at the check points. Data requested before
the visit: daily discharge at Naraj/Mundali 2017–2025, embankment inventory and breach history, villages
evacuated in 2020 and 2022, NDEM flood layers for August 2020 and 2022.

### 8.2 Check points carried to the field

`fieldkit/checkpoints/checkpoints.gpx` (phone GPS) and `.kml` (Google Earth), generated from the atlas and
impact results by `mahanadi/make_checkpoints.py`:

| Code | Number | What | Chosen how |
|---|---|---|---|
| GT | 40 | Ground-truth points | Random, 10 in each atlas class (never / < 10 % / 10–30 % / ≥ 30 % of passes flooded), within 150 m of a road and 1 km of a settlement, ≥ 2 km apart |
| SR | 15 | Siren sites | Top of the greedy coverage list (§9) |
| RS | per river | River-sensor bridges | One per main distributary (§9) |
| GB | 12 | Bank inspection and soil sampling | Top of the geotechnical screening (§7.4) |
| RL | 10 | Critical road links | Flooded links carrying most people's hospital route (§7.2) |
| HF | ≤ 10 | Health facilities flooded in the 25-year flood | §7.1 |
| WL | 8 | Well water levels | Settlements in the ground-saturation advisory list (§7.5) |

Random ground-truth points matter: checking the map only where it is easy to reach, or only where it shows
water, would overstate its accuracy.

### 8.3 Atlas accuracy at the ground-truth points  *(to be filled after the visit)*

Method: `fieldkit/analysis/field_validate_map.py`. Each (point, year) pair with a local answer is one test:
hit, miss, false alarm or correct negative, with a 60 m window for GPS error. Report POD, FAR and CSI, the
flood-mark heights, and the cases where people and the atlas disagree, with the likely reason (short floods
between radar passes, flooded paddy, water under tree cover, memory of the wrong year).

*What it changes:* the accuracy statement that goes with the map to ClimMaTech; if misses cluster in short
floods, the atlas needs the denser 6-day revisit of Sentinel-1C/D; if false alarms cluster on paddy, the
river-driven mask (§6.4) must be applied before warnings. The flood-mark heights are compared with the DEM-based
depth (§7.3): the wall screening and the road-raising earthwork (§7.7) scale with that depth.

### 8.4 Discharge and roughness at a bridge  *(to be filled after the visit)*

Method: cross-section from the bridge and float timings, velocity-area method (ISO 748 mid-section,
surface-to-mean factor 0.85 with 0.80–0.90 as the range), water-surface slope over 200–500 m;
`discharge_velocity_area.py` and `manning_cowan.py`.

*What it changes:* (1) measured flow vs GloFAS for that day, a first check of the modelled discharge that drives
§6; (2) Manning's n from slope and discharge and from Cowan's method vs the n = 0.015 that the PINN assumes
(§5): the Saint-Venant case is re-run with the measured n; (3) if a ClimMaTech or CWC radar gauge is on the
bridge, our float discharge against its level and surface-velocity reading.

### 8.5 Bridges and roads  *(to be filled after the visit)*

Method: deck-to-water, deck thickness, high-flood-level marks, scour and debris, closure history;
`bridge_clearance.py` checks the clearance above HFL against IRC:5 (1.5 m for Q > 3,000 m³/s). At the critical
links: was the road closed in 2020/2022, for how long, which detour was used.

*What it changes:* confirmed closures validate the network model; a road the model calls safe but locals
report cut (or the reverse) re-ranks the critical links of §7.2; bridges with insufficient clearance or scour
are added to the structural list.

### 8.6 River banks and soils  *(to be filled after the visit)*

Method: bank geometry, seepage and boils, cracks, burrows, breach history; two samples per GB site; in the
IITB geotechnical laboratory wet sieving (IS 2720 Part 4) and liquid/plastic limits (IS 2720 Part 5);
`soil_gradation.py` gives the IS 1498 and USCS class, Cu, Cc, PI, the Kenney–Lau internal-stability check and a
piping-susceptibility flag.

*What it changes:* measured classes replace the SoilGrids texture in the bank-screening ranking (§7.4); cells
with non-plastic silty sand and recurrent water behind the bank move to the top of the inspection list.

### 8.7 Sensor and siren sites, and the interviews  *(to be filled after the visit)*

Method: structure, mounting height, view of the channel, mobile signal (dBm), sun hours, access in a flood,
security, permissions; interview notes in `interviews.csv`.

*What it changes:* sites without signal or without flood-time access are dropped from the deployment plan (§9);
the engineers' rule of thumb for "which flow at Naraj floods which villages" is compared with the trigger-
discharge map (§6.3); the constraints heard in the interviews are written into the problem statement (§1.1).

### 8.8 Groundwater beside the flood  *(to be filled after the visit)*

Method: water levels in 8–12 village wells at roughly 0–50, 50–100, 100–200 and 200–500 m from land that floods,
with the residents' account of how high the wells rose in the last flood and whether houses cracked or settled after
it (protocol H, `templates/well_levels.csv`).

*What it changes:* the 200 m distance of the ground-saturation advisory (§7.5) is replaced by the distance at which
the wells stop responding to the flood; reported cracking after floods tests the drawdown-settlement explanation.

