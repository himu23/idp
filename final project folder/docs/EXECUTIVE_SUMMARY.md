# Prithvi Flood-IN: executive summary

**What floods when the Mahanadi rises: a satellite flood atlas, flow-to-flood maps and engineering impacts for the
Mahanadi delta.** Integrated Design Project, Department of Civil Engineering, IIT Bombay, 2026. Team: Nikhil
Upadhyay (lead), Vineet Jangir, Prakhar Gupta, Himanshu Shete, Prabhat Kumar. Faculty guide: Prof. Basudev Biswal.
Industry partner: ClimMaTech (IIT Mandi), Dr. Vivek Gupta and Siddik Barbhuiya.

## The problem

Flood warning systems in India, including our partner's radar gauges, sirens and app, measure and forecast the river
at a point. None of them shows what a forecast flow floods: which fields, villages, roads, bridges and river banks go
under, and who must be warned. We built that missing step for the Mahanadi delta below Naraj (3,038 km², about
4.1 million people), which floods every few years.

## What we built

1. **A fair model benchmark.** Six satellite foundation models (Prithvi-EO-2.0, TerraMind, DOFA, Clay, Satlas,
   DeCUR) against a CNN and a U-Net, 92 training runs, tested on an Indian flood none had seen. A U-Net won
   (0.770 water IoU against 0.747 for the best foundation model;
   fusion 0.776). An audit of all 92 runs found no problems and reproduces the published
   TerraMind scores within a point (89.7 against 90.62).
2. **A flood atlas.** Monsoon floods are under cloud, so a radar-only TerraMind + U-Net model mapped all
   590 Sentinel-1 passes over the delta from 2017 to 2026: 905 km² flooded at least once.
3. **Flow-to-flood maps.** Every 20 m pixel gets the Naraj flow at which it starts to flood, so a forecast flow
   becomes a map. On years held out from fitting it beats flood climatology at high flows (IoU
   0.23 against 0.07). A learned model that adds rain and flood history does
   better still on heavy-rain passes (0.22 against 0.17).
4. **Impacts across the department's specializations.** The same flood scenarios answer one question for each of
   transportation, structural, geotechnical, ocean, construction management, water resources (with the watershed
   above the delta) and remote sensing.
5. **Tools for the partner.** A forecast-to-bulletin tool that also writes CAP alerts, an interactive map viewer,
   siren and river-gauge sites, and a project website.
6. **A field-visit kit** that measures what the models cannot know: accuracy at 40 random points, discharge and
   roughness, bridges, bank soils, well levels.

## Key numbers (25-year flood, 32,997 m³/s at Naraj, unless stated)

| What | Number |
|---|---|
| Land flooded / people living on it | 216 km² / 25,163 |
| Settlements with 10 % or more of people on flooded land | 24 |
| People cut off from every hospital (transportation) | 36,941 in 32 settlements |
| Extra travel every day | 12,023 person-hours |
| People where the flood is 1 m deep or more; brick walls crack at (structural) | 3,626; about 0.8–1.0 m |
| Pier scour below high flood level, a quarter of the 100-year flow | 7–24 m |
| People on soaked ground beside the flood; bearing loss (geotechnical) | 415,549; about 55 % |
| Largest floods that followed a Bay of Bengal storm (ocean) | 11 of 20 |
| Work window; earthwork to raise critical roads (construction) | December–April; 17,442 m³ (about ₹0.61 crore) |
| Share of a flood peak from Hirakud dam (watershed) | median 48% |
| Sirens and coverage | 40 sirens reach 49% of exposed people at 1.5 km |

## What it means for ClimMaTech

Their system lists a map-based River View layer, but no flood extent stands behind it; their alert areas are drawn
by hand; their solution pages show illustrative networks. This project adds the flood-extent and impact layers for one
delta, bulletins and CAP alerts for each forecast, a network of sites placed with data, and a field method to turn
their radar gauge readings into discharge.

## Limits and next steps

River flow is modelled (GloFAS), not gauged; pass-level skill is modest because floodplain flooding is patchy; depth
comes from a 30 m elevation model; soil, masonry and bed values are textbook values until the lab tests; the radar
misses shallow water among crops (it finds 22% of the flood water Sentinel-2 sees). Next: the field visit,
CWC/WRD flows, the radar models retrained at 20 m (ready, 0.681 against
0.646), fine-tuning on the delta with Sentinel-2 labels, and the Hirakud reservoir.

**Find everything:** report `report/FINAL_REPORT.docx`, slides `report/Prithvi_Flood-IN_Final.pptx`, website
`website/`, map viewer `dashboard/index.html`, field kit `fieldkit/`, plan `PLAN.md`.
