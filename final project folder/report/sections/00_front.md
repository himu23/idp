# Prithvi Flood-IN: from a river-flow forecast to who goes under water

**Satellite foundation models, a flood atlas and engineering impacts for the Mahanadi delta**

CE Integrated Design Project, Department of Civil Engineering, IIT Bombay, 2026

Team: Nikhil Upadhyay (lead), Prakhar Gupta, Prabhat Kumar, Vineet Jangir, Himanshu Shete
Faculty guide: Prof. Basudev Biswal (IIT Bombay) · Industry partner: ClimMaTech Pvt. Ltd., IIT Mandi (Dr. Vivek Gupta, CTO; Siddik Barbhuiya, lead hydrologist)

## Abstract

Flood early-warning systems in India, including those of our industry partner ClimMaTech, measure and forecast the
river at points (gauges on bridges and spillways), but do not show what a forecast flow floods. We address this for
the Mahanadi delta below Naraj (3,038 km², 4.1 million people). First, we select a satellite water-mapping model
with a controlled benchmark of six geospatial foundation models (Prithvi-EO-2.0, TerraMind, DOFA, Clay, Satlas,
DeCUR) against CNN and U-Net baselines on Sen1Floods11 (92 training runs, three seeds). On a flood in India that
no model saw in training (Assam 2016), U-Net reached IoU 0.770 and the best foundation
model 0.747; fusing U-Net, CNN and the best-validated foundation model reached 0.776.
Because monsoon floods are under cloud, the operational model is a radar-only fusion of TerraMind-B and U-Net
(IoU 0.681 on 20 m radar, trained on 20 m input). Applied to 590 Sentinel-1 passes from
2017 to 2026, it gives a flood atlas of the delta. Linking the atlas to GloFAS discharge at
Naraj, each 20 m pixel receives the flow at which it starts to flood, so a discharge forecast becomes a flood map;
on years held out from fitting, this map beats flood climatology at high flows (IoU 0.20 vs
0.04). For the 25-year flood (32,997 m³/s) about 30,427 people live on
flooded land, 39 km of road is under water and 52,423 people in
41 settlements lose road access to any hospital. A learned model that adds local
rain and each pixel's flood history to the river flow maps held-out heavy-rain passes better still (IoU
0.22 against 0.15). A gradient-boosted model forecasts the Naraj flow one to three days ahead from the upstream flows and the catchment rain (Nash-Sutcliffe efficiency 0.99, 0.94 and 0.89 on monsoons it never saw, against 0.96, 0.88 and 0.79 for persistence), and a live feed turns each day's GloFAS ensemble into an impact-based warning with a CAP alert. The same pipeline mapped the Brahmani–Baitarani delta and the Brahmaputra at Majuli from every Sentinel-1 pass since 2017. Flood damage to houses and paddy comes to about ₹17 crore a year (a lower bound), and raising ten critical roads repays its cost 17 times in hospital access alone. The same scenarios are carried
through seven civil-engineering specializations: hospital and shelter access and travel delay (transportation), wall
failure depth and IRC:78 bridge scour (structural), river banks to inspect and ground saturation under houses that
stay dry (geotechnical), Bay of Bengal storms as a flood driver (ocean), work windows, earthwork for raising critical
links and a deployment schedule (construction management), and the watershed above the delta, where about half of a
flood peak comes from below Hirakud dam (water resources). An audit of all 92 training runs found no problems and
reproduces the published TerraMind scores within a point. We provide a forecast-to-bulletin tool with CAP alerts, a map
viewer and project website, and a field protocol that measures what the models cannot know (accuracy at random
points, discharge and roughness, bridge clearance, bank soils, well levels).

**Keywords:** flood mapping, Sentinel-1, geospatial foundation models, TerraMind, Prithvi, U-Net, Mahanadi, impact-based
flood warning, road network, river-bank screening

## Team and contributions

| Member | Specializations | What they built | Report | At the site |
|---|---|---|---|---|
| Nikhil Upadhyay (lead) | Water resources, Ocean | Flow-to-flood model, rain analogs, learned flow + rain model, Naraj flow forecast model, design floods and travel time, the watershed analysis, Saint-Venant PINN; storm drivers; field-visit organisation and WRD/CWC contacts | §5, §6.3–6.6, §7.6, §7.8 | Discharge, slope, Manning's n (B, C); WRD/CWC interviews |
| Vineet Jangir | Remote sensing | Benchmark of six foundation models against CNN and U-Net (92 runs), fusion, radar models retrained on 20 m input | §4, §6.1, Appendix B | Ground-truth points (A) |
| Prakhar Gupta | Remote sensing | Flood atlas from all Sentinel-1 passes, Sentinel-2 cross-check, atlases of the two other basins, map viewer | §6.1–6.2, §6.8 | Ground-truth points, GPS and photo log (A) |
| Himanshu Shete | Transportation systems, Structural | Road-network model (hospital and shelter access, travel delay, critical links), flood depth, wall and IRC:78 scour checks; integration of the impact chain, forecast-to-bulletin tool with CAP alerts, live warning feed with data plugins, flood-risk economics, training audit, gap analysis against the partner's services, project website, report and slides | §7.1–7.3, §7.9, §9.1–9.2, §9.6–9.7, Appendix A | Bridge inspections, foundation levels, road closures (D); evening data runs |
| Prabhat Kumar | Geotechnical, Construction technology and management | Bank screening, ground-saturation advisory, foundation and drawdown checks; work windows, earthwork, deployment quantities and schedule; siren and sensor siting | §7.4–7.5, §7.7, §9.3–9.4 | Bank inspection, soil samples and lab tests, well levels, site sheets (E, F, H) |

