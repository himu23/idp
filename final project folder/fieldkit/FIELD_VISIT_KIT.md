# Field visit kit: Mahanadi delta (Naraj – Cuttack – Kendrapara)

**Purpose of the visit.** We do not go to "see the river". We go to **measure and ask** the things the satellite
model cannot know, and every item below ends up as a number or a decision in the report:

| What we collect at site | Why the model needs it | Script that uses it | Where it appears |
|---|---|---|---|
| 40 ground-truth points (flood marks, people's memory of flooded years) | Only independent check of the flood atlas in the delta | `analysis/field_validate_map.py` | Report §8.3, accuracy table (POD / FAR / CSI) |
| River cross-section + float timings at 1–2 bridges | Discharge on the day, to compare with GloFAS / CWC and with the radar sensor (if one is installed) | `analysis/discharge_velocity_area.py` | §8.4 hydrometry |
| Water-surface slope over 200–500 m | Manning's *n* back-calculated (the PINN currently assumes n = 0.015) | same script | §5 (PINN) and §8.4 |
| Cowan's *n* observation sheet | Second, independent estimate of *n* | `analysis/manning_cowan.py` | §8.4 |
| Bridge sheet (deck-to-water, HFL mark, scour, debris) | Clearance above HFL vs IRC:5; which bridges are vulnerable | `analysis/bridge_clearance.py` | §7.3 structures |
| Embankment sheet + 4–6 soil samples | Bank-failure screening uses SoilGrids at 250 m; lab tests replace it | `analysis/soil_gradation.py` (after sieve + Atterberg in the IITB geotech lab), `analysis/embankment_stability.py` (rapid drawdown) | §7.4 geotechnical |
| Water level in 8–12 village wells at increasing distance from the flood edge | Fixes the 200 m "ground-saturation" advisory distance for houses that stay dry | `templates/well_levels.csv`, `analysis/foundation_checks.py` | §7.5 geotechnical (ground) |
| Flood-mark heights (from protocol A) | Checks the DEM-based flood depth used for wall and road-raising estimates | `analysis/field_validate_map.py` output vs `depth_T25.tif` | §7.3 structures, §7.7 construction |
| Road-closure answers at the critical links | Confirms or corrects the network model's cut-off roads | entered in `templates/ground_truth_points.csv` notes, checked against `critical_links.csv` | §7.2 transport |
| Sensor / siren site sheet | Feasibility of the proposed deployment (mounting, mobile signal, access in flood) | `templates/sensor_site_assessment.csv` | §9 deployment plan |
| Interviews (engineers, operators, village heads) | The constraints that change the problem statement | `templates/interviews.csv` | §1.1 problem statement, §10 discussion |

Everything is recorded in the CSV templates in `templates/` (print one copy of each, fill on paper, type in the
same evening). Photos: one photo log row per photo (`photo_log.csv`), every photo with GPS on.

---

## 1. Before leaving (owner: Nikhil, with everyone)

1. **Fix the site and the hosts.** Ask Prof. Basudev Biswal which part of his Mahanadi basin work we can join
   (Hirakud releases, Naraj/Mundali barrage, delta embankments) and whom to meet: Odisha Water Resources
   Department (Mahanadi South / North Division, Cuttack), CWC Mahanadi Division (Naraj and Tikarpara gauges),
   OSDMA or the district emergency office, and ClimMaTech (Dr. Vivek Gupta, Siddik) for the sensor side.
   Carry a letter from the department; most sites (barrage, gauge station, embankment crest) need permission.
2. **Send data requests now** (they take days):
   - CWC / WRD: daily discharge and water level at Naraj and Mundali for June–October 2017–2025, danger and
     highest flood levels at Naraj, rating curve if shareable.
   - WRD: embankment inventory of the delta (names, chainage, breach history 2008–2025).
   - OSDMA / district: list of villages evacuated in the 2020 and 2022 floods, cyclone-shelter locations.
   - NDEM / NRSC: flood inundation layers for Aug 2020, Aug 2022 (to validate the atlas).
3. **Load the check points.** `checkpoints/checkpoints.gpx` into a phone GPS app (OsmAnd, Locus, GPX Viewer)
   and `checkpoints/checkpoints.kml` into Google Earth / My Maps. Print `checkpoints/checkpoints.csv` and the
   dossier maps (`report/figures/dossier_*.png`).
4. **Equipment** (cheap, mostly borrowable from the department):
   - phones with GPS + compass apps (one per pair), power banks;
   - 30 m or 50 m measuring tape, 50 m of rope marked every 1 m, a 3 m levelling staff or marked bamboo pole;
   - laser distance meter (deck-to-water), clinometer app or Abney level (bank slopes);
   - stopwatch, 6–8 floats (oranges or half-filled bottles), two ranging rods or flags;
   - 10 zip-lock sample bags (2 kg each), marker, trowel/auger, field notebook, clipboard;
   - life jackets (borrow), gloves, gum boots, first-aid kit, drinking water.
5. **Safety rules (non-negotiable).** Work in pairs. Nobody wades in water above the knee or in visibly
   moving water; the cross-section is measured **from a bridge** (depth by weighted rope/staff from the deck)
   or at a ghat in the shallow margin only. No work on embankments during rain or in the dark. Tell the host
   engineer where each pair is going. Follow every instruction of barrage and gauge staff.

## 2. Day plan (adapt to permissions)

| Day | Morning | Afternoon | Evening |
|---|---|---|---|
| 1 | Meet WRD / CWC engineers at Cuttack; interviews A and B; see the Naraj gauge and the Mundali/Naraj barrage | Hydrometry at a road bridge near Naraj (protocol B, C, D) | Type data; run `discharge_velocity_area.py` |
| 2 | Ground-truth points GT01–GT20 (Cuttack–Salepur side) with well levels (H); interviews D in villages | Embankment inspection + soil samples at GB sites (protocol E) | Type data; check points on the map |
| 3 | Ground-truth points GT21–GT40 (Kendrapara side); critical road links RL; flooded facilities HF | Sensor / siren site assessments SR, RS (protocol F); ClimMaTech discussion (C) | Run `field_validate_map.py`; list open questions |
| after | IITB geotech lab: sieve + hydrometer + Atterberg for the samples (protocol E, lab part) | | `soil_gradation.py`; update report §7.4 |

Evening data runs: each owner types their own sheets; Himanshu runs the analysis scripts, checks the points on the
map and carries the numbers into the report, slides and website.

## 3. Protocols

### A. Ground-truth points and flood marks (owner: Vineet + Prakhar)
1. Navigate to the GT point (any spot within ~50 m is fine; record the actual GPS position and accuracy).
2. Record land cover (paddy, other crop, fallow, homestead, orchard, road, water).
3. Ask two residents independently: *"In which years did water come here? How deep (knee / waist /
   above head)? For how many days?"* Write the years exactly as said; note uncertainty ("2020 for sure, maybe
   2022"). Use `none` only when the person is sure the spot did not flood in 2017–2025.
4. Look for flood marks (silt line on walls, trees, poles). Measure height above ground with the tape and
   photograph it with the tape in view.
5. One row per point in `ground_truth_points.csv`.

*Why these points:* they were drawn at random within four atlas classes (never / rarely / sometimes / often
flooded) near roads and villages, so the comparison is fair to the model and not only where it is right.

### B. River cross-section from a bridge (owner: Nikhil)
1. Choose a straight reach with a road bridge (RS points are candidates). Note the bridge name and GPS.
2. Mark stations across the water surface every 5–10 m (every 2 m near the banks) from the left water edge.
3. At each station lower a weighted rope or the staff from the parapet to the bed; depth = rope length to
   bed − rope length to water surface. Record `station_m`, `depth_m`; depth 0 at both water edges.
4. Note bed material (sand, silt, gravel) where the weight comes up with sample.

### C. Surface velocity by floats (owner: Nikhil)
1. Mark a reach of known length upstream of the bridge along the bank (20–50 m, with ranging rods).
2. Release a float well upstream of the first mark; start the stopwatch when it passes the first line, stop at
   the second. At least 3 trials at each of 3–5 positions across the channel (record the station of each).
3. Enter `float_velocity.csv`. The script converts surface to depth-mean velocity with k = 0.85 and reports the
   range for k = 0.80–0.90.
4. **Slope (for Manning's n):** mark the water edge at two points 200–500 m apart along the bank; level the
   water surface difference with the staff and a line level / auto-level if available, or read two staff
   gauges at the same time. Enter `water_surface_slope.csv`. Without a level instrument, skip; Cowan's method
   (sheet `manning_cowan.csv`, words from the table in `analysis/manning_cowan.py`) still gives *n*.
5. If a ClimMaTech / CWC radar gauge is on the bridge, note its reading at the same time: our float discharge
   vs. the sensor's level and surface velocity is a direct check of the instrument.

### D. Bridge inspection (owner: Himanshu)
1. Deck-to-water distance with the laser meter or tape at mid-span; deck thickness (slab + girder) at the edge.
2. Highest flood level: look for marks on piers or abutments, and ask the bridge/PWD/WRD engineer for the
   design HFL and the highest observed level; record the source.
3. Visual condition: scour around piers (exposed foundation), debris trapped against piers, bearing condition,
   cracks, approach-road settlement or erosion. Photograph each.
4. Ask: *"Was this bridge or its approach closed in 2020 / 2022? For how long? Which detour was used?"* and the
   PWD/NH engineer: *"What is the foundation type and level of the piers?"* — compared with the IRC:78 scour depth of
   `bridge_scour.csv` (§7.3); collect a bed-sand sample under the bridge for the silt factor (sieve, d_m).
5. `bridge_inspection.csv`; `bridge_clearance.py` checks clearance above HFL against IRC:5 (1.5 m for
   Q > 3,000 m³/s).

### E. Embankment inspection and soil sampling (owner: Prabhat)
1. At each GB site, walk 200–300 m of the bank. Record crest width, height above the landward field, river-
   and land-side slopes (clinometer), seepage or sand boils on the land side, cracks, slips, rat holes,
   protection works (stone pitching, geobags) and any breach history the locals give.
2. Take two disturbed samples (~2 kg): one from the embankment body (≥ 0.5 m below the crest surface or from a
   fresh cut) and one from the landward toe at 0.3–0.5 m depth. Label `sample_id`, record GPS, depth,
   location, field texture by feel (gritty / smooth / sticky), colour, moisture.
3. **In the lab (IITB geotechnical lab, with the lab staff):** oven-dry mass; wet sieving on 4.75, 2, 1, 0.6,
   0.425, 0.3, 0.15, 0.075 mm (IS 2720 Part 4); hydrometer for the fines if time allows; liquid and plastic
   limits on the fraction passing 0.425 mm (IS 2720 Part 5).
4. `sieve_analysis.csv`, `atterberg.csv` → `soil_gradation.py` gives the IS 1498 and USCS class, Cu, Cc, PI,
   the Kenney–Lau internal-stability check and a piping-susceptibility flag; these replace the SoilGrids
   texture for the sampled cells in the bank-screening ranking.

### F. Sensor and siren site assessment (owner: Prabhat + Himanshu)
For each SR (siren) and RS (river sensor) point: structure available (school roof, panchayat building, bridge
parapet), mounting height above the water for a radar, clear view of the channel, mobile signal strength
(phone: Settings → About → SIM status, dBm) and operator, hours of direct sun for the solar panel, whether the
site stays reachable in a flood (ask), security/theft risk, whose permission is needed.
`sensor_site_assessment.csv`.

### H. Groundwater in village wells (owner: Prabhat, with Vineet at the GT points)
1. At each WL point (settlements in the ground-saturation advisory list) and at GT points near the flood edge, find
   open wells or hand-pump tube wells at roughly 0–50, 50–100, 100–200 and 200–500 m from the land that floods
   (distance read from the dossier map).
2. Measure the depth from ground level to the water surface with a weighted tape (open wells) or ask for the
   static level (tube wells); photograph the tape.
3. Ask: *"How high did the water in this well come during the last flood, and how long did it stay high? Did
   houses here crack or sink after the flood?"*
4. `well_levels.csv`. Plotted against distance, the levels show how far the soaked zone reaches — the distance
   the ground advisory uses (200 m now, a screening guess).

### G. Interviews (everyone; one person asks, one writes)
Ask for consent to note and quote. One row per interview in `interviews.csv`; key points in the person's words.

## 4. Interview guides

**A. WRD / CWC engineers (flood management):**
1. How is flood information passed from Hirakud and Naraj to the delta today? Who decides warnings, how much
   lead time is there, and what is the bottleneck?
   Show the live outlook (`live/out/index.html`): would its levels (from 12,250, 18,500 and 21,250 m³/s at Naraj)
   and its village list match what you would announce?
2. Which discharge at Naraj (in lakh cusec) starts flooding which areas? Is there a local rule of thumb?
3. Which embankment reaches breach or overtop most often? What causes it (overtopping, seepage/piping, slope
   failure, rat holes)? How are they repaired and inspected?
4. Can we compare our flood atlas with your observed water levels / breach records? What would make such a map
   useful in your control room?
5. What data can be shared (gauge records, embankment inventory)?

**B. Barrage / dam operation (Naraj, Mundali, or Hirakud if reachable):**
1. How are gate operations decided during a flood? How is the flow split between Mahanadi and Kathajodi?
2. Which downstream areas are warned before large releases, how, and how early?

**C. ClimMaTech (Dr. Vivek Gupta, Siddik, or the field engineer):**
1. How are Pravaah / Tarang sites chosen today? What does a site survey check?
2. What would an operator do with a "discharge → inundation" map and a village list per forecast?
3. Which format can the Rakshak Control Centre / Aagah app take (GeoJSON, API, tiles)?
4. Siren audible range of Rakshak in open paddy land? Typical installation cost and time per site?

**D. Village heads, farmers, shopkeepers (at GT points):**
1. Which years did water enter the village / fields? Depth and duration?
2. How did you get the warning, and how early? Which road did you use to leave or to reach a hospital, and
   was it cut?
3. Where do people go (cyclone shelter, school, embankment top)?
4. What would help most: earlier warning, a siren, a phone message, a raised road?
5. In the last big flood (2020 or 2022): what happened to the house (water inside? how deep? walls cracked or
   fell? repair cost in rupees) and to the paddy (how many days under water, how deep, how much of the crop was
   lost)? These check the damage estimate of the report (§7.9): the depth–damage curve and the paddy-loss rule.
6. Would the village act on a warning that names it and says the day the water is expected (show the live
   bulletin on the phone)? Who should receive it first?

## 5. After the visit

1. Type every sheet into the CSVs (same column names). Keep the paper originals and photos (they are evidence
   for the review).
2. Run:
   ```
   python fieldkit/analysis/field_validate_map.py fieldkit/templates/ground_truth_points.csv results/atlas
   python fieldkit/analysis/discharge_velocity_area.py fieldkit/templates/cross_section.csv fieldkit/templates/float_velocity.csv fieldkit/templates/water_surface_slope.csv
   python fieldkit/analysis/manning_cowan.py fieldkit/templates/manning_cowan.csv
   python fieldkit/analysis/bridge_clearance.py fieldkit/templates/bridge_inspection.csv 5000
   python fieldkit/analysis/soil_gradation.py fieldkit/templates/sieve_analysis.csv fieldkit/templates/atterberg.csv
   python fieldkit/analysis/embankment_stability.py fieldkit/templates/embankment_inspection.csv <segment_soils.csv>
   python fieldkit/analysis/foundation_checks.py --phi <lab phi> --c <lab c> --mv <oedometer mv>
   ```
3. Write §8 (field results) of the report with what was found **and what changed because of it**: e.g. a
   corrected Manning's n in the hydraulic model, the atlas accuracy at field points, roads the network model
   missed, bank cells re-ranked by the lab results, siren sites dropped for lack of mobile signal.
4. Update the problem statement (report §1.1 and `PLAN.md` §2) with the constraints heard in the interviews.

The `examples/` folder has made-up sheets that only show the format and test the scripts. They are **not**
field data and must never be reported as such.
