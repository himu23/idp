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
(IoU 0.646 on 20 m radar). Applied to 590 Sentinel-1 passes from
2017 to 2026, it gives a flood atlas of the delta. Linking the atlas to GloFAS discharge at
Naraj, each 20 m pixel receives the flow at which it starts to flood, so a discharge forecast becomes a flood map;
on years held out from fitting, this map beats flood climatology at high flows (IoU 0.23 vs
0.07). For the 25-year flood (32,997 m³/s) about 25,163 people live on
flooded land, 32 km of road is under water and 36,941 people in
32 settlements lose road access to any hospital. A learned model that adds local
rain and each pixel's flood history to the river flow maps held-out heavy-rain passes better still (IoU
0.22 against 0.17). The same scenarios are carried
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
| Nikhil Upadhyay (lead) | Water resources, Ocean | Flow-to-flood model, rain analogs, design floods and travel time, Saint-Venant PINN; storm drivers; field-visit organisation and WRD/CWC contacts | §5, §6.3–6.5, §7.6 | Discharge, slope, Manning's n (B, C); WRD/CWC interviews |
| Vineet Jangir | Remote sensing | Benchmark of six foundation models against CNN and U-Net (92 runs), fusion, radar model for 20 m input | §4, §6.1 | Ground-truth points (A) |
| Prakhar Gupta | Remote sensing | Flood atlas from all Sentinel-1 passes, Sentinel-2 cross-check, map viewer | §6.1–6.2 | Ground-truth points, GPS and photo log (A) |
| Himanshu Shete | Transportation systems, Structural | Road-network model (hospital and shelter access, travel delay, critical links), flood depth, wall and IRC:78 scour checks; integration of the impact chain, forecast-to-bulletin tool, project website, report and slides | §7.1–7.3, §9.1–9.2 | Bridge inspections, foundation levels, road closures (D); evening data runs |
| Prabhat Kumar | Geotechnical, Construction technology and management | Bank screening, ground-saturation advisory, foundation and drawdown checks; work windows, earthwork, deployment quantities and schedule; siren and sensor siting | §7.4–7.5, §7.7, §9.3–9.4 | Bank inspection, soil samples and lab tests, well levels, site sheets (E, F, H) |

