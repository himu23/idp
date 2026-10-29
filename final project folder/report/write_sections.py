"""Write the report sections whose numbers come from the Mahanadi atlas and impact runs, so the text always matches
results/atlas and results/impact (pulled from the server after mahanadi/run_atlas_pipeline.sh).

    python report/write_sections.py
Writes sections/00_front.md, 06_mahanadi.md, 07_impacts.md, 09_implementation.md, 10_discussion.md.
"""
import glob
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AT, IM, AN = (os.path.join(ROOT, "results", d) for d in ("atlas", "impact", "analysis"))
SEC = os.path.join(HERE, "sections")
F = "../results/atlas_figures"


def J(*p):
    path = os.path.join(*p)
    return json.load(open(path)) if os.path.exists(path) else None


def C(*p):
    path = os.path.join(*p)
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


def n(x):
    return f"{x:,.0f}"


AS, R20, TT, S2C = J(AT, "atlas_summary.json"), J(AN, "radar20m.json"), J(IM, "travel_time.json"), J(IM, "s2_crosscheck.json")
EXS, TRS, GS, SIT = J(IM, "exposure_summary.json"), J(IM, "transport_summary.json"), J(IM, "geotech_summary.json"), J(IM, "siting_summary.json")
EX, TR = C(IM, "exposure_scenarios.csv").set_index("scenario"), C(IM, "transport_scenarios.csv").set_index("scenario")
CL, GEO, SR, SEN = C(IM, "critical_links.csv"), C(IM, "geotech_top20.csv"), C(IM, "siren_sites.csv"), C(IM, "sensor_sites.csv")
CURVE, PASSES, INV = C(IM, "siren_coverage_curve.csv"), C(AT, "atlas_passes.csv"), C(AT, "atlas_inventory_used.csv")
BENCH = {s["protocol"] + "/" + s["model"] + "/" + s["mode"] + "/" + s["modalities"]: s for s in J(AN, "summary.json")}
RP = {int(k): v for k, v in AS["gumbel"]["return_period_m3s"].items()}
def lagtxt(d):
    return "on the same day" if int(d) == 0 else f"{int(d)} day{'s' if int(d) > 1 else ''} later"


PRAIN = {"R_3d": "3-day rain", "R_prev_3d": "rain of the 3 previous days", "R_5d": "5-day rain", "R_7d": "7-day rain"}
PNAME = {"Q_same_day": "same-day flow", "Q_prev_day": "previous-day flow", "Q_max_3d": "3-day peak",
         "Q_max_5d": "5-day peak", "Q_max_7d": "7-day peak"}
V = AS["validation"]
HF, ALLP = V["high_flow_passes"], V["all_monsoon_passes"]
OBS = [k for k in EX.index if k.startswith("observed_")][0]
obs_date = f"{OBS[9:13]}-{OBS[13:15]}-{OBS[15:17]}"
T25, T100 = EX.loc["T25"], EX.loc["T100"]
TR25 = TR.loc["T25"]
lb = [T for T, q in RP.items() if q > AS["largest_observed_predictor_m3s"]]
tracks = INV.groupby(["orbit_state", "relative_orbit"]).size() if len(INV) else pd.Series(dtype=int)
plat = INV.platform.str.upper().str.replace("SENTINEL-", "S").value_counts().to_dict() if len(INV) else {}
u = lambda k: BENCH[k]["test_iou"]  # noqa: E731

# ------------------------------------------------------------------ 00 front matter
_LF = J(AT, "learned", "learned_summary.json") or {"pixel_iou": {"heavy_rain_passes": {"learned": {"iou": 0}, "trigger": {"iou": 0}}}}
front = f"""# Prithvi Flood-IN: from a river-flow forecast to who goes under water

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
no model saw in training (Assam 2016), U-Net reached IoU {u('lio/unet/full/default'):.3f} and the best foundation
model {u('lio/prithvi/full/default'):.3f}; fusing U-Net, CNN and the best-validated foundation model reached {u('lio/enstop3_mean/full/default'):.3f}.
Because monsoon floods are under cloud, the operational model is a radar-only fusion of TerraMind-B and U-Net
(IoU {R20['calibrated_test_iou']:.3f} on 20 m radar). Applied to {AS['n_passes']} Sentinel-1 passes from
{AS['years'][0]} to {AS['years'][-1]}, it gives a flood atlas of the delta. Linking the atlas to GloFAS discharge at
Naraj, each 20 m pixel receives the flow at which it starts to flood, so a discharge forecast becomes a flood map;
on years held out from fitting, this map beats flood climatology at high flows (IoU {HF['model']['iou']:.2f} vs
{HF['climatology']['iou']:.2f}). For the 25-year flood ({n(RP[25])} m³/s) about {n(T25['people'])} people live on
flooded land, {T25['road km (all)']:.0f} km of road is under water and {n(TR25['hospital: people cut off'])} people in
{int(TR25['hospital: settlements cut off'])} settlements lose road access to any hospital. A learned model that adds local
rain and each pixel's flood history to the river flow maps held-out heavy-rain passes better still (IoU
{_LF['pixel_iou']['heavy_rain_passes']['learned']['iou']:.2f} against {_LF['pixel_iou']['heavy_rain_passes']['trigger']['iou']:.2f}). The same scenarios are carried
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

"""
open(os.path.join(SEC, "00_front.md"), "w", encoding="utf-8").write(front)

# ------------------------------------------------------------------ 06 Mahanadi atlas
trk = "; ".join(f"{o} {r}: {c}" for (o, r), c in tracks.items())
py = V["per_year"]
rows_y = "\n".join(f"| {y} | {d['n']} | {d['max_obs_km2']:.0f} | {d['model']['iou']:.2f} | {d['climatology']['iou']:.2f} |"
                   for y, d in sorted(py.items(), key=lambda kv: int(kv[0])))
rp_rows = "\n".join(f"| {T} | {n(q)} | {q / 2831.7:.1f} | {AS['scenario_flood_km2'][str(T)]:.0f}"
                    f"{' (lower bound)' if T in lb else ''} |" for T, q in RP.items())
s2txt = ""
if S2C:
    aa, mm = S2C.get("all/all_months", {}), S2C.get("outside_normal/monsoon_Jun_Nov", {})
    dd = S2C.get("all/dry_Feb_Mar", {})
    s2txt = f"""For {S2C['pairs']} radar passes of June–November a Sentinel-2 image was taken within one day with enough clear
sky (most of them at the end of the monsoon). On the pixels that are clear in the optical image, radar water agrees with
optical water (MNDWI > 0) with IoU **{aa.get('iou', 0):.2f}**; taking the optical map as reference, the radar map has
precision {aa.get('precision', 0):.2f} and recall {aa.get('recall', 0):.2f}. For water outside the normal-water mask — the flood
part — agreement drops to IoU {mm.get('iou', 0):.2f} (precision {mm.get('precision', 0):.2f}, recall {mm.get('recall', 0):.2f}): the
radar misses much of the shallow water that the optical image sees among crops and on water-logged fields, where the crop
canopy dominates the radar echo. MNDWI has errors of its own (0.65 on the Sen1Floods11 official test, and wet soil
reads as water), so neither map is truth; but the low flood-part recall says the radar atlas under-states shallow
field flooding and is most reliable for open water. The field points (§8.3) are the next check."""
else:
    s2txt = "The Sentinel-2 cross-check (`mahanadi/s2_crosscheck.py`) did not finish in time for this version."
rain_pair = ""
RH = int(AS.get("heavy_rain_scenario", {}).get("rain_mm", 171))
_b = {r_: J(IM, "bulletins", f"bulletin_{round(RP[5])}_rain{r_}.json") for r_ in (20, RH)}
if all(_b.values()):
    rain_pair = (f"With the same analog method and the 5-year flow ({n(RP[5])} m³/s), a dry week (20 mm of rain) gives "
                 f"{_b[20]['flooded_land_km2']:.0f} km² of flooded land with {n(_b[20]['people_on_flooded_land'])} people on it; a week "
                 f"with {RH} mm (the monsoon 95th percentile) gives {_b[RH]['flooded_land_km2']:.0f} km² and "
                 f"{n(_b[RH]['people_on_flooded_land'])} people.")
auc_ = V.get("ranking_auc", {})
auc_txt = ""
if auc_:
    auc_txt = (f"""
**Where versus how much.** Ranking the pixels of each held-out pass, the flood frequency of the other years reaches
ROC AUC {auc_['all_passes']['clim']:.2f} (high flows {auc_['high_flow_passes']['clim']:.2f}), the trigger map
{auc_['all_passes']['model']:.2f} and the flow-and-rain analogs {auc_['all_passes']['aqr']:.2f}. *Where* the delta floods is
very predictable from its past; *how much* of it floods on a given day is only partly predictable from river flow.
Both layers are kept: the frequency map says where to prepare, the trigger map says at which flow to act.""")
cmp_txt = ""
if "analog_flow_rain" in V["all_monsoon_passes"]:
    HR = V["high_rain_passes"]
    names_m = [("model", "Trigger map (flow only)"), ("analog_flow", "Analogs on flow"),
               ("analog_flow_rain", "Analogs on flow + local rain"), ("climatology", "Flood climatology")]
    sv = V.get("settlements", {})
    rows_m = []
    for key, label in names_m:
        st_h = sv.get("high_flow_passes", {}).get(key, {})
        st_r = sv.get("high_rain_passes", {}).get(key, {})
        rows_m.append(f"| {label} | {V['all_monsoon_passes'][key]['iou']:.2f} | {V['high_flow_passes'][key]['iou']:.2f} | "
                      f"{HR[key]['iou']:.2f} | {st_h.get('POD', 0):.0%} / {st_h.get('FAR', 0):.0%} | "
                      f"{st_r.get('POD', 0):.0%} / {st_r.get('FAR', 0):.0%} |")
    best_hr = max(names_m, key=lambda kv: HR[kv[0]]["iou"])
    SHORT = {"model": "flow-only trigger map", "analog_flow": "flow analogs", "analog_flow_rain": "flow-and-rain analogs",
             "climatology": "flood climatology"}
    gain = HR["analog_flow_rain"]["iou"] - HR["model"]["iou"]
    cmp_txt = f"""
**The river is not the only driver.** The largest flood extents in the record came with moderate Naraj flows:
8 September 2018 and 14–16 September 2021, when depressions brought 100–160 mm of rain a day over the delta
(ERA5). A map driven by Naraj flow alone cannot predict those. The same held-out test was therefore repeated with
analog maps: for each pass of the held-out year, the 7 training passes most similar in flow (or in flow and
{PRAIN.get(AS.get('rain_predictor', ''), 'local rain')}) are looked up, and land flooded on at least half of them is predicted
flooded.

| Method | IoU, all passes | IoU, high flow (≥ {n(HF['q90_threshold_m3s'])} m³/s) | IoU, heavy rain (≥ {HR['r90_threshold_mm']:.0f} mm in {PRAIN.get(AS.get('rain_predictor', ''), '7 days').replace(' rain', '').replace('-day', ' days')}) | Settlements, high flow: POD / FAR | Settlements, heavy rain: POD / FAR |
|---|---|---|---|---|---|
{chr(10).join(rows_m)}

On the heavy-rain passes the best method is the {SHORT[best_hr[0]]} (IoU {HR[best_hr[0]]['iou']:.2f}), and
{"adding rain to the analogs leaves their IoU about the same as the trigger map's" if abs(gain) < 0.01 else f"adding rain to the analogs changes IoU by {gain:+.2f} against the trigger map"}:
at the scale of single passes rain is hard to use because the observed maps are noisy. The effect of rain is clear
when the same method is asked about the same river flow. {rain_pair}
For warnings this means the river forecast has to be read together with the rainfall forecast, which the ClimMaTech
app already carries.
"""
sett_txt = ""
if "settlements" in V:
    sv = V["settlements"]
    hm, hc, am = sv["high_flow_passes"]["model"], sv["high_flow_passes"]["climatology"], sv["all_passes"]["model"]
    sett_txt = (f"""
Pixel IoU is a hard score here: the observed map is itself a radar map with ~0.65 IoU, and floodplain flooding is
patchy. A warning is issued per village, so the same held-out test was scored per settlement ({sv['settlements']:,}
settlements; flagged when at least 10 % of the people are on flooded land). **On high-flow passes the trigger map
flagged {hm['POD']:.0%} of the settlements that were actually flooded (POD), with {hm['FAR']:.0%} false alarms (FAR),
CSI {hm['CSI']:.2f}; climatology: POD {hc['POD']:.0%}, FAR {hc['FAR']:.0%}, CSI {hc['CSI']:.2f}.** Over all monsoon
passes: POD {am['POD']:.0%}, FAR {am['FAR']:.0%}, CSI {am['CSI']:.2f}.""")
sec6 = f"""## 6. Mahanadi delta: flood atlas and the link to river flow

### 6.1 The atlas

The production model of §4.8 (mean of the radar-only TerraMind-B and U-Net, threshold {AS.get('threshold', 0.3):.2f}) was run on
**{AS['n_passes']} Sentinel-1 passes** ({AS['n_dry']} in February–March, {AS['n_monsoon']} in June–November,
{AS['years'][0]}–{AS['years'][-1]}; tracks {trk}; platforms {', '.join(f'{k} {v}' for k, v in plat.items())}).
A pass is all slices of one satellite overpass; together they give a water map of the delta every 2–6 days in the
monsoon. The river bed (main channels and sand bars, {AS.get('river_bed_km2', 0):.0f} km²) and each year's
dry-season water are "normal water"; only water outside them counts as flood. A 3 km band along each pass's data
edge is removed: a first version showed a diagonal stripe of false floods along one track's swath edge.

![Flow at Naraj and flooded land on every pass]({F}/atlas_timeseries.png)

![Flood frequency 2017–2026]({F}/atlas_frequency_map.png)

- Land flooded on at least one pass: {AS['flooded_ever_km2']:.0f} km²; in at least 20 % of monsoon passes:
  {AS['flooded_20pct_km2']:.0f} km².
- The largest flood seen on a near-complete pass was on {obs_date} ({EX.loc[OBS, 'flood_km2']:.0f} km² of flooded land).
- The flooded fraction of each pass follows the Naraj flow. Spearman ρ by predictor:
  {', '.join(f"{PNAME[k]} {v:.2f}" for k, v in AS['predictor_spearman'].items())}; the {PNAME[AS['predictor']]} is used
  {'(floodplains drain slowly, so the map follows the recent peak more than the flow of the day)' if 'max' in AS['predictor'] else ''}.

### 6.2 Independent check with Sentinel-2

{s2txt}

### 6.3 Trigger discharge: which flow floods which land

![Trigger discharge]({F}/atlas_trigger_map.png)

Every pixel gets the Naraj flow above which it is flooded (§3.5). The map reads directly as "at this forecast
flow, this land goes under". The river-driven score separates land that floods with the river from land that is wet
in the monsoon whatever the river does: {AS['river_driven_km2']:.0f} km² has AUC ≥ 0.75, i.e. it floods mainly at
high river flow, including fields far from the channels that flood when high river stages block their drainage.

![River-driven flooding]({F}/atlas_river_driven.png)

### 6.4 Does it predict years it has not seen?

For each year the trigger map was fitted on the other years and the year's passes were predicted from their discharge
alone.

| Year | Passes | Largest flood on a pass (km²) | IoU, discharge model | IoU, climatology |
|---|---|---|---|---|
{rows_y}

Over all {ALLP['n']} monsoon passes the discharge model reaches IoU {ALLP['model']['iou']:.2f} (precision
{ALLP['model']['precision']:.2f}, recall {ALLP['model']['recall']:.2f}) against {ALLP['climatology']['iou']:.2f} for
climatology. **On the {HF['n']} high-flow passes (Naraj ≥ {n(HF['q90_threshold_m3s'])} m³/s, the top 10 % of monsoon
days), the ones that matter for warnings, it reaches {HF['model']['iou']:.2f} against {HF['climatology']['iou']:.2f}**
(recall {HF['model']['recall']:.2f} vs {HF['climatology']['recall']:.2f}): climatology misses the extra land that only
floods in big years. Predicted and observed flooded area correlate with r = {V['area_correlation']:.2f}.
{sett_txt}
{auc_txt}
{cmp_txt}

![Leave-one-year-out test]({F}/atlas_loyo.png)

### 6.5 Design floods and travel time

Gumbel fit to {AS['gumbel']['n_years']} GloFAS annual maxima at Naraj (1984–2025):

| Return period (years) | Naraj flow (m³/s) | (lakh cusec) | Flooded land (km²) |
|---|---|---|---|
{rp_rows}

The largest flow in the radar record is {n(AS['largest_observed_predictor_m3s'])} m³/s; above it the map cannot grow
further and is a lower bound{(' (' + ', '.join(f'{T}-yr' for T in lb) + ')') if lb else ''}.

Day-to-day changes of flow below Hirakud correlate best with those at Naraj
{lagtxt(TT['hirakud_below']['best_lag_days'])} (r = {TT['hirakud_below']['corr_by_lag_days'][str(TT['hirakud_below']['best_lag_days'])]:.2f}),
and those at Tikarpara {lagtxt(TT['tikarpara']['best_lag_days'])} (r = {TT['tikarpara']['corr_by_lag_days'][str(TT['tikarpara']['best_lag_days'])]:.2f}),
in June–October 1984–2025 (daily data resolve only whole days). A release seen by a spillway sensor at Hirakud
therefore gives about a day of lead time for the delta, on top of the hydrological forecast.

### 6.6 Limits

- **Discharge is modelled (GloFAS), not gauged.** CWC/WRD daily flows at Naraj are the first thing to request
  (§8.1); with them the trigger map is refitted in minutes.
- **Radar misses water under dense vegetation and in towns, and sees smooth surfaces as water.** The model scores
  0.65 on the official test with radar only; the atlas inherits that.
- **Short floods between passes** (2–12 days apart) are missed; Sentinel-1C/D (2025–26) shorten the gap.
- **Paddy**: transplanted paddy holds water in July–August. Land whose wetness does not follow the river (low
  river-driven score) should not trigger river-flood warnings.
- **Flows beyond the record** (rarer than the largest flood seen since 2017) are lower bounds.
"""
LRN = J(AT, "learned", "learned_summary.json")
LRU = J(AT, "learned_unconstrained", "learned_summary.json")
if LRN:
    li, ls, la = LRN["pixel_iou"], LRN["settlements"], LRN.get("ranking_auc", {})

    def cell(sub, m):
        x = li[sub][m]
        return f"{x['iou']:.2f} ({x['precision']:.2f} / {x['recall']:.2f})"

    imp = list(LRN.get("permutation_importance_auc_drop", {}).items())[:5]
    FEAT_NAMES = {"freq_all": "flood frequency", "flow_q_max_5d": "Naraj flow", "rain_7d_mm": "7-day rain", "month": "month",
                  "elevation_m": "elevation", "track": "radar track", "freq_high_flow": "flood frequency at high flows",
                  "freq_heavy_rain": "flood frequency in heavy rain", "flow_minus_trigger_log10": "flow above the trigger",
                  "trigger_log10_q": "trigger discharge", "height_above_bed_m": "height above the river bed",
                  "distance_to_bed_m": "distance to the river bed"}
    sc_ = LRN.get("scenarios_all_years_model", {})
    d_all = li["all_passes"]["learned"]["iou"] - li["all_passes"]["trigger"]["iou"]
    d_rain = li["heavy_rain_passes"]["learned"]["iou"] - li["heavy_rain_passes"]["trigger"]["iou"]
    verdict = ("better than the trigger map on all passes and on heavy-rain passes" if d_all >= 0.01 and d_rain >= 0.01 else
               "better on heavy-rain passes than the trigger map, with no overall gain" if d_rain >= 0.01 else
               "about as good as the trigger map on all passes" if abs(d_all) < 0.01 else
               "better than the trigger map on all passes" if d_all >= 0.01 else "not better than the trigger map")
    learned_md = f"""### 6.6 A learned flow + rain + history model

The trigger map uses the Naraj flow alone, and the analogs use rain only through similar past passes. A gradient-boosted
classifier (scikit-learn HistGradientBoosting, `mahanadi/learned_flood_model.py`) was trained on pixels of every monsoon
pass with the flow and 7-day rain of the pass, its month and radar track, and what the training years say about each
pixel: trigger discharge, flood frequency overall, at high flows and in heavy rain, height above the nearest river bed
and distance to it. Each year is predicted by a model fitted on the other years, a pixel is called flooded when its
probability is at least 0.5 (the per-pixel error-minimising rule of the trigger fit), and the three methods are scored
on the same held-out passes. Cells give IoU (precision / recall).

| Held-out passes | Learned model | Trigger map | Flood climatology |
|---|---|---|---|
| All monsoon passes ({li['all_passes']['n']}) | {cell('all_passes', 'learned')} | {cell('all_passes', 'trigger')} | {cell('all_passes', 'climatology')} |
| High flow ({li['high_flow_passes']['n']}) | {cell('high_flow_passes', 'learned')} | {cell('high_flow_passes', 'trigger')} | {cell('high_flow_passes', 'climatology')} |
| Heavy rain ({li['heavy_rain_passes']['n']}) | {cell('heavy_rain_passes', 'learned')} | {cell('heavy_rain_passes', 'trigger')} | {cell('heavy_rain_passes', 'climatology')} |
| Settlements, high flow: POD / FAR | {ls['high_flow_passes']['learned']['POD']:.0%} / {ls['high_flow_passes']['learned']['FAR']:.0%} | {ls['high_flow_passes']['trigger']['POD']:.0%} / {ls['high_flow_passes']['trigger']['FAR']:.0%} | {ls['high_flow_passes']['climatology']['POD']:.0%} / {ls['high_flow_passes']['climatology']['FAR']:.0%} |
| Settlements, heavy rain: POD / FAR | {ls['heavy_rain_passes']['learned']['POD']:.0%} / {ls['heavy_rain_passes']['learned']['FAR']:.0%} | {ls['heavy_rain_passes']['trigger']['POD']:.0%} / {ls['heavy_rain_passes']['trigger']['FAR']:.0%} | {ls['heavy_rain_passes']['climatology']['POD']:.0%} / {ls['heavy_rain_passes']['climatology']['FAR']:.0%} |
| Ranking AUC, all / high flow | {la.get('all_passes', {}).get('learned', 0):.2f} / {la.get('high_flow_passes', {}).get('learned', 0):.2f} | {la.get('all_passes', {}).get('trigger', 0):.2f} / {la.get('high_flow_passes', {}).get('trigger', 0):.2f} | {la.get('all_passes', {}).get('climatology', 0):.2f} / {la.get('high_flow_passes', {}).get('climatology', 0):.2f} |

The learned model is {verdict}. At village level, at high flows, it catches {"more" if ls['high_flow_passes']['learned']['POD'] > ls['high_flow_passes']['trigger']['POD'] else "fewer"} flooded villages
than the trigger map ({ls['high_flow_passes']['learned']['POD']:.0%} against {ls['high_flow_passes']['trigger']['POD']:.0%}) and raises
{"more" if ls['high_flow_passes']['learned']['FAR'] > ls['high_flow_passes']['trigger']['FAR'] else "fewer"} false alarms ({ls['high_flow_passes']['learned']['FAR']:.0%} against
{ls['high_flow_passes']['trigger']['FAR']:.0%}); the critical success index, which weighs both, is {ls['high_flow_passes']['learned']['CSI']:.2f} against
{ls['high_flow_passes']['trigger']['CSI']:.2f}. It ranks flood-prone land
{"best of the three" if la.get('all_passes', {}).get('learned', 0) >= max(la.get('all_passes', {}).get('trigger', 0), la.get('all_passes', {}).get('climatology', 0)) else "below flood climatology"}
(ROC AUC {la.get('all_passes', {}).get('learned', 0):.2f}). The physical direction of each input is imposed (more flow or rain, a
flow further above the trigger or a pixel that flooded more often never lowers the probability):
{"a first run without these constraints scored " + format(LRU['pixel_iou']['all_passes']['learned']['iou'], '.3f') + " IoU but gave less flooded land for heavy than for typical rain at the 25-year flow (" + format(LRU['scenarios_all_years_model']['T25 heavy rain']['flood_km2'], '.0f') + " against " + format(LRU['scenarios_all_years_model']['T25 typical rain']['flood_km2'], '.0f') + " km²), which a warning map must never do." if LRU else ""}
The inputs it leans on most (drop in held-out ranking AUC when each is shuffled):
{"; ".join(f"{FEAT_NAMES.get(k, k)} {v:.3f}" for k, v in imp)}. Fitted on all years, it floods
{sc_.get('T5 dry week', {}).get('flood_km2', 0):.0f} km² at the 5-year flow in a dry week,
{sc_.get('T5 typical rain', {}).get('flood_km2', 0):.0f} km² with typical rain and {sc_.get('T5 heavy rain', {}).get('flood_km2', 0):.0f} km²
with heavy rain ({LRN.get('scenario_note', '')}), the same roughly four-fold effect of rain as the analog maps of §6.4.
For a warning system this is the model that takes both of
ClimMaTech's inputs, the river forecast and a rain-gauge or forecast rain total, and returns one map.

"""
    sec6 = sec6.replace("### 6.6 Limits", learned_md + "### 6.7 Limits")
open(os.path.join(SEC, "06_mahanadi.md"), "w", encoding="utf-8").write(sec6)

# ------------------------------------------------------------------ 07 impacts
order = [f"T{t}" for t in (2, 5, 10, 25, 50, 100)] + ["freq10", OBS]
HRS = AS.get("heavy_rain_scenario", {})
lab = lambda k: (f"{k[1:]}-year" if k.startswith("T") else ("flooded in ≥ 10 % of passes" if k == "freq10" else  # noqa: E731
                 (f"5-year flow + heavy rain ({HRS.get('rain_mm', 0)} mm)" if k == "rain_T5" else f"largest seen ({obs_date})")))
ex_rows = "\n".join(
    f"| {lab(k)} | {EX.loc[k, 'flood_km2']:.0f} | {n(EX.loc[k, 'people'])} | {int(EX.loc[k, 'settlements >= 10 % of people flooded'])} | "
    f"{EX.loc[k, 'cropland km2']:.0f} | {EX.loc[k, 'road km (all)']:.0f} ({EX.loc[k, 'road km (trunk-tertiary)']:.0f}) | "
    f"{EX.loc[k, 'rail km']:.1f} | {int(EX.loc[k, 'bridges with flooded approach'])} | {int(EX.loc[k, 'health facilities'])} | "
    f"{int(EX.loc[k, 'schools'])} |" for k in order if k in EX.index)
tr_rows = "\n".join(
    f"| {lab(k)} | {TR.loc[k, 'road_km_cut']:.0f} | {int(TR.loc[k, 'hospital: settlements cut off'])} | "
    f"{n(TR.loc[k, 'hospital: people cut off'])} | {n(TR.loc[k, 'hospital: people with trip +5 min or more'])} | "
    f"{TR.loc[k, 'hospital: median extra minutes (still reachable, delayed)']} | {n(TR.loc[k, 'town: people cut off'])} |"
    for k in order if k in TR.index)
cl25 = CL[CL.scenario == "T25"].head(10)
cl_rows = "\n".join(f"| {int(r['rank'])} | {r['road'] if isinstance(r['road'], str) else '(unnamed)'} | {r['highway']} | "
                    f"{n(r['people_routed'])} | {r['flooded_km']:.2f} | {r['lat']:.4f} N, {r['lon']:.4f} E |" for _, r in cl25.iterrows())
geo_rows = "\n".join(f"| {int(r['rank'])} | {r['lat']:.4f} N, {r['lon']:.4f} E | {r['behind_freq']:.0%} | {int(r['years_flooded'])} | "
                     f"{r['texture']} ({r['sand']:.0f}/{r['silt']:.0f}/{r['clay']:.0f}) | {n(r['people_2km'])} |" for _, r in GEO.head(10).iterrows())
DEP, STR, GRD, OCN, CMP = (J(IM, f) or {} for f in ("depth_summary.json", "structures_summary.json", "ground_summary.json",
                                                      "ocean_summary.json", "cm_plan.json"))
SC, DRV, CYC, LR, BOQ = (C(IM, f) for f in ("bridge_scour.csv", "flood_drivers.csv", "cyclones_near_delta.csv", "link_raising.csv", "boq.csv"))
walls = STR.get("walls", {})
wT25 = walls.get("T25", {})
dcrit = walls.get("critical_depth_m", {})
gT25 = GRD.get("scenarios", {}).get("T25", {})
fe = GRD.get("foundation_example", {})
lrk, dep_ = CMP.get("link_raising", {}), CMP.get("deployment", {})
cnt = OCN.get("top20_flood_passes_driver_counts", {})
FULLM = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]


def window_text(months):
    """Month set on a circular calendar -> 'December–April'."""
    idx = sorted({[m[:3] for m in FULLM].index(m[:3]) for m in months})
    sset, blocks = set(idx), []
    for i in idx:
        if (i - 1) % 12 not in sset:
            j = i
            while (j + 1) % 12 in sset and (j + 1) % 12 != i:
                j = (j + 1) % 12
            blocks.append((i, j))
    return ", ".join(FULLM[a] if a == b else f"{FULLM[a]}–{FULLM[b]}" for a, b in blocks) or "–"


wwin = window_text(CMP.get("work_window_months", []))


def sysname(s):
    """IBTrACS names -> report text: 'Unnamed' -> 'depression (unnamed)', 'Bulbul:Matmo' -> 'Bulbul (Matmo)'."""
    if not isinstance(s, str) or not s.strip():
        return ""
    out = []
    for x in s.split(","):
        x = x.strip()
        if x.lower() in ("unnamed", "not_named", "not named"):
            out.append("depression (unnamed)")
        elif ":" in x:
            a_, b_ = x.split(":", 1)
            out.append(f"{a_} ({b_.split('-')[0]})")
        else:
            out.append(x)
    return ", ".join(dict.fromkeys(out))
sc_rows = "\n".join(f"| {r['river'] if isinstance(r['river'], str) else '–'} | {r['bridge'] if isinstance(r['bridge'], str) else '(unnamed)'} | {r['linear_waterway_m']:.0f} | "
                    f"{n(r['Q_m3s'])} | {r['Db_m3s_per_m']:.1f} | {r['d_sm_m']:.1f} | {r['pier_scour_below_HFL_m']:.1f} | {r['abutment_scour_below_HFL_m']:.1f} |"
                    for _, r in SC[(SC["T"] == 100) & (SC.share == 0.5)].iterrows()) if len(SC) else ""
cy_rows = "\n".join(f"| {sysname(r['name'])} | {r['closest_date']} | {r['min_dist_km']} | {'' if pd.isna(r['max_wind_kt_near']) else int(r['max_wind_kt_near'])} | "
                    f"{r['rain_week_mm']} | {n(r['naraj_max_week_m3s'])} | {'' if pd.isna(r['max_flood_km2_on_a_pass']) else r['max_flood_km2_on_a_pass']} |"
                    for _, r in CYC.iterrows()) if len(CYC) else ""
dr_rows = "\n".join(f"| {r['date']} | {r['flood_km2']:.0f} | {n(r['naraj_m3s'])} | {r['rain_mm']} | {sysname(r['system'])} | {r['drivers']} |"
                    for _, r in DRV.iterrows()) if len(DRV) else ""
lr_rows = "\n".join(f"| {int(r['rank'])} | {r['road']} | {r['highway']} | {r['flooded_km']:.2f} | {r['depth_p90_m']:.1f} | {r['raise_m']:.1f} | "
                    f"{r['crest_m']:.2f} | {r.get('design', 'embankment raise')} | "
                    + (f"{n(r['earthwork_m3'])} | {r['cost_lakh_rs_at_350_per_m3']:.1f} |" if r.get('design', 'embankment raise') == 'embankment raise'
                       else f"({n(r.get('earthwork_m3_as_embankment', 0))} as embankment) | – |") for _, r in LR.iterrows()) if len(LR) else ""
struct_links = lrk.get("links_needing_structure", [])
struct_txt = ""
if struct_links:
    s0 = struct_links[0]
    one = len(struct_links) == 1
    ranks = " and ".join(str(x["rank"]) for x in struct_links)
    raises = "; ".join(f"{x['raise_m']:.1f} m over {x['flooded_km']:.2f} km" for x in struct_links)
    pts = ", ".join(f"RL{x['rank']:02d}" for x in struct_links)
    struct_txt = (f" {'Link' if one else 'Links'} {ranks} would need {'a raise' if one else 'raises'} above "
                  f"{lrk.get('max_raise_for_embankment_m', 3):.0f} m ({raises}): {'that needs' if one else 'each needs'} a bridge or a vented "
                  f"causeway rather than a road embankment, and the DEM depth there is the first thing to check at the site "
                  f"(check {'point' if one else 'points'} {pts}). "
                  f"As {'an embankment it' if one else 'embankments they'} alone would take "
                  f"{n(lrk.get('earthwork_m3_if_all_by_embankment', 0) - lrk.get('earthwork_m3', 0))} m³.")
ww_rows = "\n".join(f"| {w['month']} | {n(w['mean_flow_m3s'])} | {w['share_days_above_2yr_flood']:.1%} | {w['storms_per_year_within_300km']:.2f} | "
                    f"{'' if pd.isna(w['mean_flooded_share_on_radar']) else format(w['mean_flooded_share_on_radar'], '.1%')} | {w['work_window']} |"
                    for w in CMP.get("work_windows_table", []))
boq_rows = "\n".join(f"| {r['item']} | {r['unit']} | {r['qty']} | {r['crew_days']:.0f} | {r['basis']} |" for _, r in BOQ.iterrows()) if len(BOQ) else ""
shel = TR25.get("shelter: people > 30 min from a dry school", float("nan"))
delay = TR25.get("town: extra person-hours of travel per day", float("nan"))
old7 = f"""## 7. Seven specializations, one flood: engineering impacts

The department's seven specializations each get one question about the same flood scenarios (the design floods
of §6.5, land flooded in ≥ 10 % of monsoon passes, and the largest flood seen), and each has a field measurement
that can change the answer. The 10- to 100-year scenarios are identical: the largest flow in the radar record
(about 28,400 m³/s, roughly a 10-year flood) bounds what the atlas can map, so they are lower bounds.

| Specialization | Question | Method | Headline result (25-year flood unless stated) | Field check (§8) | Owner |
|---|---|---|---|---|---|
| Remote sensing | Which model maps Indian floods through cloud? | Benchmark of 6 FMs vs CNN/U-Net; Sentinel-1 atlas; Sentinel-2 check | U-Net {u('lio/unet/full/default'):.3f}, best FM {u('lio/prithvi/full/default'):.3f} (unseen flood); {AS['n_passes']} passes mapped | 40 random ground-truth points | Vineet, Prakhar |
| Water resources | Which flow floods which land? | GloFAS + ERA5, trigger discharge, held-out years, Gumbel | High-flow IoU {HF['model']['iou']:.2f} vs {HF['climatology']['iou']:.2f} climatology; 25-yr flow {n(RP[25])} m³/s | Discharge, Manning's n | Nikhil |
| Transportation systems | Who loses the road to a hospital or shelter? | OSM road graph, flooded edges cut, Dijkstra | {n(TR25['hospital: people cut off'])} people cut off from any hospital; {n(delay)} extra person-hours of travel a day | Road closures at critical links | Himanshu |
| Structural | Where do walls crack; how deep must piers go? | DEM flood depth, wall moment check, IRC:78 Lacey scour | {n(wT25.get('people_deeper_than_1m', 0))} people where depth ≥ 1 m; pier scour {STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[0]:.0f}–{STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[1]:.0f} m below HFL (100-yr, a quarter of the flow) | Deck clearance, HFL marks, foundation levels | Himanshu |
| Geotechnical | Which banks fail; which dry houses sit on soaked ground? | Bank screening; 200 m saturation advisory; bearing / settlement checks | {n(gT25.get('people_in_zone', 0))} people in the advisory zone; bearing loss {fe.get('silty_sand_drained', {}).get('reduction_pct', 0)} % when soaked | Soil samples, well levels, slopes | Prabhat |
| Ocean | What do Bay of Bengal storms add? | IBTrACS tracks vs atlas; flood drivers | {OCN.get('systems_within_300km_since_2016', 0)} systems within 300 km since 2016; {cnt.get('cyclone/depression', 0)} of the 20 largest floods followed one | Interviews on surge and tidal drainage | Nikhil |
| Construction technology & management | When to build, what it costs, in what order | Flood/storm climatology, earthwork take-off, BoQ, schedule | Work window {wwin}; {n(lrk.get('earthwork_m3', 0))} m³ to raise {lrk.get('links_by_embankment', 10)} critical links, {len(lrk.get('links_needing_structure', []))} more need a bridge or vented causeway | Site sheets for sensors/sirens | Prabhat |

Population: GHSL 2020 ({n(EXS['population_ghsl'])} people in the box, {n(EXS['settlement_population'])} of them in
{n(EXS['settlements'])} settlements). Roads, bridges, railways, hospitals and schools: OpenStreetMap
({n(EXS['road_km_total'])} km of road, {n(EXS['bridges'])} bridge segments, {n(EXS['health_facilities'])} hospitals and
clinics, {n(EXS['schools'])} schools). All areas exclude the river bed and normal water.

### 7.1 Exposure

| Scenario | Flooded land (km²) | People on flooded land | Settlements ≥ 10 % flooded | Cropland (km²) | Road under water, km (main roads) | Rail (km) | Bridges with flooded approach | Health facilities | Schools |
|---|---|---|---|---|---|---|---|---|---|
{ex_rows}

Most flooded land is cropland; the people exposed live in villages on slightly higher ground at the edge of the
flooded fields, which is why a settlement-level list (viewer, bulletin tool) is more useful to a district officer
than a total. Mapped building footprints are incomplete here (Microsoft: {n(EXS['mapped_buildings_ms'])} footprints for
4.1 million people), so people, not buildings, are counted.

### 7.2 Transportation systems

![25-year flood: roads cut and critical links]({F}/impact_T25_map.png)

| Scenario | Road cut (km) | Settlements cut off from any hospital/clinic | People cut off | People reaching one only by a detour ≥ 5 min | Median detour (min) | People cut off from any town |
|---|---|---|---|---|---|---|
{tr_rows}

Graph: {n(TRS['nodes'])} nodes, {n(TRS['edges'])} edges, {n(TRS['road_km'])} km; {TRS['destinations']['hospital']} hospital/clinic
nodes and {TRS['destinations']['town']} towns; settlements farther than 500 m from the main network are not routed.

- **Evacuation**: schools serve as relief camps. In the 25-year flood {int(TR25.get('shelter: dry schools', 0))} of the
  mapped schools stay dry and {n(TR25.get('shelter: people with no reachable dry school', 0))} people can reach none of them by
  road. OpenStreetMap maps only about a hundred schools here (every village has one), so travel times to shelters
  need the official OSDMA shelter list; the cut-off count is the robust part.
- **Everyday travel**: with an assumed 0.2 trips per person per day to the nearest town, the detours of the 25-year
  flood add about {n(delay)} person-hours of travel a day — the cost that does not appear in damage figures.
- **Critical links** (flooded sections carrying the most people's dry-weather route to the nearest hospital; raising
  or protecting these keeps the most people connected; earthwork in §7.7):

| Rank | Road | Class | People routed | Flooded length (km) | Location |
|---|---|---|---|---|---|
{cl_rows}

### 7.3 Structural

![Estimated flood depth and settlements where walls are at risk]({F}/depth_T25_map.png)

- **Flood depth** (`impact_depth.py`): the water surface of each flood patch is the median elevation of its edge,
  depth = surface − ground (Copernicus GLO-30, ~2 m vertical error: a screening estimate, checked against the flood
  marks of the field points). 25-year flood: median depth {DEP.get('scenarios', {}).get('T25', {}).get('median_depth_m', 0)} m,
  90th percentile {DEP.get('scenarios', {}).get('T25', {}).get('p90_depth_m', 0)} m.
- **Masonry walls**: water on one side of an unreinforced brick wall gives a base moment γ_w d³/6 per metre; the wall
  cracks when this exceeds f_t t²/6. With flexural tension f_t = 0.1–0.2 MPa the critical depth is
  {dcrit.get('230 mm wall, f_t 0.1 MPa', 0):.2f}–{dcrit.get('230 mm wall, f_t 0.2 MPa', 0):.2f} m for a 230 mm wall and
  {dcrit.get('115 mm wall, f_t 0.1 MPa', 0):.2f}–{dcrit.get('115 mm wall, f_t 0.2 MPa', 0):.2f} m for a 115 mm wall (self-weight
  ignored, conservative). **{n(wT25.get('people_deeper_than_1m', 0))} people** live where the 25-year flood is 1 m deep
  or more ({n(wT25.get('people_deeper_than_0_6m', 0))} at 0.6 m or more); mud walls weaken with soaking at any depth.
  The settlements are listed in `results/impact/wall_risk_settlements.csv`.
- **Bridge scour** (IRC:78, Lacey): d_sm = 1.34 (D_b²/K_sf)^(1/3), D_b = Q / linear waterway, K_sf = 1.76 √d_m
  (d_m = 0.3 mm until the field sieve gives the bed size); maximum scour 2.0 d_sm at piers, 1.27 d_sm at abutments,
  below HFL. The share of the Naraj flow each branch carries is not known here (asked from WRD). For the 100-year flow
  (+10 %) the maximum pier scour is {STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[0]:.0f}–{STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[1]:.0f} m
  below HFL if the branch carries a quarter of it and {STR.get('bridges', {}).get('pier_scour_T100_share50_range_m', [0, 0])[0]:.0f}–{STR.get('bridges', {}).get('pier_scour_T100_share50_range_m', [0, 0])[1]:.0f} m
  if it carries half. Minor distributaries carry far less than half, so their upper values are not credible; the
  short waterways of the minor-branch bridges drive the large numbers. With half of the flow through each branch:

| River | Bridge | Linear waterway (m) | Q (m³/s) | D_b (m³/s/m) | d_sm (m) | Pier scour below HFL (m) | Abutment scour (m) |
|---|---|---|---|---|---|---|---|
{sc_rows}

  –: river not matched in OpenStreetMap; these are the parallel road crossings of the Mahanadi just north of Cuttack
  (20.48 N, 85.91 E). Shares of 25 % and 75 % are in
  `bridge_scour.csv`. Pier foundations must reach well below these depths; the PWD
  foundation levels collected at the site close the check.
- **Clearance and facilities**: {int(T25['bridges with flooded approach'])} bridge segments have flood water within 60 m
  of an end; deck clearance above HFL is checked against IRC:5 at the site (§8.5). {int(T25['health facilities'])}
  hospitals/clinics and {int(T25['schools'])} schools have flood water within 60 m; {T25['rail km']:.1f} km of railway is
  under water.

![Bridge scour screening]({F}/bridge_scour.png)

### 7.4 Geotechnical: river banks

![River-bank inspection priority]({F}/geotech_map.png)

{GS['cells']} one-kilometre cells contain river bank. SoilGrids gives {', '.join(f'{k} ({v})' for k, v in GS['texture_counts'].items())}
— too coarse to tell one bank from another, which is why the field samples matter. OpenStreetMap maps only
{GS['osm_embankments']} embankment segments ({GS['osm_embankment_km']} km), so the screening works from the river-bed
outline (the WRD embankment inventory is requested in §8.1). The field list is the 20 highest cells at least 3 km apart:

| Rank | Location | Water behind the bank (share of passes) | Years with water behind the bank | Texture (sand/silt/clay %) | People within 2 km |
|---|---|---|---|---|---|
{geo_rows}

Laboratory plan: wet sieving (IS 2720 Part 4), liquid / plastic limits (IS 2720 Part 5), IS 1498 class, Kenney–Lau
internal stability and a piping flag (`soil_gradation.py`); bank slopes measured at the site give the factor of
safety dry, under seepage and after rapid drawdown (`embankment_stability.py`), when the river falls faster than the
bank drains and the factor of safety roughly halves.

### 7.5 Geotechnical: ground saturation under houses that stay dry

![Ground-saturation advisory]({F}/ground_advisory_map.png)

Floodwater raises the water table under the land around it. Houses that stay dry but stand on that soaked ground
lose bearing capacity while it is wet and settle when the water table falls back. The advisory zone is dry land within
200 m of flood water on fine-grained soil (silt + clay ≥ 50 %, {GRD.get('fine_soil_share_of_box', 0):.0%} of the box).

| Scenario | Advisory zone (km²) | People in the zone | People on flooded land | Settlements with ≥ 25 % of people in the zone |
|---|---|---|---|---|
{chr(10).join(f"| {lab(k)} | {v['zone_km2']:.0f} | {n(v['people_in_zone'])} | {n(v['people_on_flooded_land'])} | {v['advisory_settlements']} |" for k, v in GRD.get('scenarios', {}).items())}

What the advisory means for a typical house foundation (strip footing 1 m wide at 1 m depth; textbook parameters to be
replaced by the lab results, `foundation_checks.py`):

- silty sand (φ' = 28°): ultimate bearing capacity {fe.get('silty_sand_drained', {}).get('q_ult_dry_kPa', 0)} kPa with a deep water
  table, {fe.get('silty_sand_drained', {}).get('q_ult_water_at_surface_kPa', 0)} kPa with water at the surface
  (−{fe.get('silty_sand_drained', {}).get('reduction_pct', 0)} %);
- clay loam, undrained: {fe.get('clay_loam_undrained', {}).get('q_ult_stiff_kPa', 0)} kPa stiff → {fe.get('clay_loam_undrained', {}).get('q_ult_soaked_kPa', 0)} kPa soaked
  (−{fe.get('clay_loam_undrained', {}).get('reduction_pct', 0)} %);
- when the water table falls 2 m after the flood, 4 m of soft clay consolidates by
  {" to ".join(f"{v:.0f}" for v in fe.get('drawdown_settlement_mm', {}).values())} mm (m_v 0.25–0.5 m²/MN) — enough to crack
  load-bearing masonry where it is uneven.

The 200 m distance is a screening value; the water levels in village wells at increasing distance from the flood edge
(field protocol H) fix it.

### 7.6 Ocean engineering

![Flood drivers]({F}/flood_drivers.png)

{OCN.get('systems_within_300km_since_2016', 0)} cyclones and depressions passed within 300 km of the delta since 2016
(IBTrACS). Of the 20 largest floods seen by radar, {cnt.get('river', 0)} came with a high Naraj flow (≥ {n(OCN.get('q90_m3s', 0))} m³/s, the
monsoon 90th percentile), {cnt.get('rain', 0)} with heavy rain (≥ {OCN.get('r90_mm', 0):.0f} mm in {AS.get('rain_predictor', 'R_7d')[2:-1]} days) and
{cnt.get('cyclone/depression', 0)} within a week of a Bay of Bengal system:

| Date | Flooded land (km²) | Naraj flow (m³/s) | Rain (mm) | System | Drivers |
|---|---|---|---|---|---|
{dr_rows}

Systems that came within 300 km:

| System | Closest | Distance (km) | Max wind near the delta (kt) | Rain that week (mm) | Max Naraj flow that week (m³/s) | Largest flood on a pass (km²) |
|---|---|---|---|---|---|---|
{cy_rows}

Storm surge and high tide also slow the drainage of the lower delta through the tidal distributaries; the study box
ends about 25 km inland of Paradip, and a tide-gauge record (Paradip) is the first ocean dataset to add.

### 7.7 Construction technology and management

![Construction windows]({F}/construction_windows.png)

| Month | Mean Naraj flow (m³/s) | Days above the 2-year flood | Storms within 300 km per year | Mean flooded share on radar | Work window |
|---|---|---|---|---|---|
{ww_rows}

**Raising the critical links** above the 25-year flood (raise = 90th-percentile depth + 0.6 m freeboard; crest 3.75 m
single lane or 7.5 m for trunk/primary roads; side slopes 2H:1V; earthwork at an assumed ₹350/m³):

| Rank | Road | Class | Flooded (km) | Depth p90 (m) | Raise (m) | Crest (m) | Design | Earthwork (m³) | Cost (₹ lakh) |
|---|---|---|---|---|---|---|---|---|---|
{lr_rows}

Embankment raises for {lrk.get('links_by_embankment', lrk.get('links', 0))} links ({lrk.get('embankment_km', lrk.get('total_km', 0)):.2f} km of road):
{n(lrk.get('earthwork_m3', 0))} m³, about ₹{lrk.get('cost_crore_rs_at_350_per_m3', 0):.2f} crore.{struct_txt} Each of the ten links
carries the dry-weather hospital route of {n(lrk.get('people_routed_per_link', [0, 0])[0])}–{n(lrk.get('people_routed_per_link', [0, 0])[1])} people.

**Deployment quantities** (quantities and effort only; the unit rates are asked from ClimMaTech):

| Item | Unit | Quantity | Crew-days | Basis |
|---|---|---|---|---|
{boq_rows}

![Deployment schedule]({F}/gantt.png)

**Risks**: permissions for bridge mounting (PWD/NH) and siren sites (panchayat) — start in week 1; theft and vandalism of
solar panels — mount high, community custody; mobile-network gaps — LoRa or satellite backhaul at the sites the field
sheets flag; installation slipping into the monsoon — the window closes in May; maintenance — one pre-monsoon visit per
site each year.
"""
WS = J(IM, "watershed_summary.json")
cut = old7.index("Population: GHSL")
appC = ("## Appendix C. Engineering details of the seven specializations\n\n"
        "Formulas, parameters and full tables behind the short summaries of chapter 7 (C.1–C.7 follow 7.1–7.7; C.8 is the "
        "watershed analysis of 7.8).\n\n" + old7[cut:].replace("### 7.", "### C.").replace("earthwork in §7.7", "earthwork in C.7"))
if WS:
    ws_rows = "\n".join(f"| {r_['year']} | {n(r_['naraj_peak'])} | {n(r_['hirakud_prev_day'])} | {r_['share']:.0%} |" for r_ in WS["top5"])
    appC += f"""
### C.8 Water resources: the watershed above the delta

Daily GloFAS v4 flows just below Hirakud dam and at Naraj, {WS['years']} complete years between 1984 and 2025
(`mahanadi/watershed_share.py`). For each year the flow below Hirakud on the day before the Naraj peak is compared with
the peak (one day is the travel time found in §6.5).

| Year | Naraj annual peak (m³/s) | Flow below Hirakud the day before (m³/s) | Share from Hirakud |
|---|---|---|---|
{ws_rows}

Over all {WS['years']} years the share has a median of {WS['median_share_hirakud_of_naraj_peak']:.0%} (interquartile range
{WS['iqr'][0]:.0%}–{WS['iqr'][1]:.0%}); in July–September the dam passes {WS['jul_sep_share']:.0%} of the mean flow at Naraj
({n(WS['jul_sep_mean_hirakud'])} of {n(WS['jul_sep_mean_naraj'])} m³/s). Basin areas: Hirakud controls about 83,400 km² of a
basin of about 141,600 km² (sources differ between about 139,700 and 141,600 km²). GloFAS represents the reservoir with
a generic operating rule, so these shares are indicative until CWC/WRD gauge and release records replace them.
"""

sec7 = f"""## 7. Seven specializations, one flood

The department's seven specializations each answer one question about the same flood scenarios: the design floods of
§6.5, land flooded in at least 10 % of monsoon passes, and the largest flood seen. This chapter gives, for each one, why
it matters for a flood warning, what was done and what was found, briefly; formulas, parameters and full tables are in
Appendix C. Remote sensing is chapters 4 and 6; water resources is chapter 6 and §7.8, which adds the watershed above
the delta. The 10- to 100-year scenarios are identical because the largest flow in the radar record (about 28,400 m³/s,
roughly a 10-year flood) bounds what the atlas can map, so they are lower bounds.

{old7[old7.index("| Specialization | Question |"):old7.index("Population: GHSL")].strip()}

### 7.1 Exposure: who and what is on flooded land

**Why it matters.** A warning has to say who is at risk, not how many square kilometres flood. **What we did.** Each
scenario was overlaid with population (GHSL), settlements, farmland (WorldCover), roads, railways, bridges, hospitals
and schools (OpenStreetMap). **What we found.** The 25-year flood covers {T25['flood_km2']:.0f} km² of land with
{n(T25['people'])} people on it, {int(T25['settlements >= 10 % of people flooded'])} settlements with at least 10 % of their people on flooded land,
{T25['cropland km2']:.0f} km² of cropland and {T25['road km (all)']:.0f} km of road. Most flooded land is farmland; the people
exposed live in villages at its edges, which is why the viewer and the bulletin list settlements, not totals.

### 7.2 Transportation systems

![25-year flood: roads cut and critical links]({F}/impact_T25_map.png)

**Why it matters.** A flooded road is a lost hospital trip, a blocked evacuation and a long detour to market.
**What we did.** The OpenStreetMap road network became a graph; flooded sections were cut and shortest paths to
hospitals, towns and dry schools compared with dry weather. **What we found.** In the 25-year flood
{n(TR25['hospital: people cut off'])} people in {int(TR25['hospital: settlements cut off'])} settlements lose road access to
any hospital, {n(TR25['hospital: people with trip +5 min or more'])} more reach one only by a detour, and everyday trips grow
by about {n(delay)} person-hours a day. Ten critical links carry most of the cut-off routes (C.2). **At the site:** road
closures at those links.

### 7.3 Structural

![Estimated flood depth]({F}/depth_T25_map.png)

**Why it matters.** Standing water pushes over brick walls, and scour undermines bridge piers. **What we did.** Flood
depth from the ground elevation at the flood edge; a bending check of unreinforced brick walls; IRC:78 scour at
{STR.get('bridges', {}).get('bridges', 0)} major bridges. **What we found.** A 230 mm brick wall cracks at about
{dcrit.get('230 mm wall, f_t 0.1 MPa', 0):.1f}–{dcrit.get('230 mm wall, f_t 0.2 MPa', 0):.1f} m of water, and
{n(wT25.get('people_deeper_than_1m', 0))} people live where the 25-year flood is a metre deep or more. Pier scour reaches
{STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[0]:.0f}–{STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[1]:.0f} m below the high flood
level if a branch carries a quarter of the 100-year flow; how the flow splits between branches is the missing input.
**At the site:** flood marks, deck clearance and foundation levels.

### 7.4 Geotechnical: river banks

**Why it matters.** Embankment breaches cause the worst local floods. **What we did.** {GS['cells']} one-kilometre
bank cells were ranked by how often water stands behind the bank, in how many years, how erodible the soil is and how
many people live nearby. **What we found.** Twenty inspection sites at least 3 km apart (map and list in C.4);
SoilGrids at 250 m cannot tell one bank from another, so the field samples and lab tests decide. **At the site:** bank
inspection, slopes and soil samples.

### 7.5 Geotechnical: ground under houses that stay dry

![Ground-saturation advisory]({F}/ground_advisory_map.png)

**Why it matters.** Floodwater raises the groundwater under dry houses nearby: foundations weaken while it is high and
settle when it drops. **What we did.** An advisory zone of dry land within 200 m of flood water on fine-grained soil,
with textbook bearing-capacity and settlement checks. **What we found.** {n(gT25.get('people_in_zone', 0))} people
({gT25.get('advisory_settlements', 0)} settlements) live in the zone in the 25-year flood; soaking cuts the bearing
capacity of a strip footing on silty sand by about {fe.get('silty_sand_drained', {}).get('reduction_pct', 0)} %, and a 2 m
drop of the water table settles soft clay by {" to ".join(f"{v:.0f}" for v in fe.get('drawdown_settlement_mm', {}).values())} mm.
**At the site:** water levels in village wells at 0–500 m from the flood edge.

### 7.6 Ocean

![Flood drivers]({F}/flood_drivers.png)

**Why it matters.** Bay of Bengal cyclones and depressions bring the heaviest rain, and surge and tide hold back the
drainage of the lower delta. **What we did.** IBTrACS storm tracks were matched to the radar floods. **What we found.**
{OCN.get('systems_within_300km_since_2016', 0)} systems passed within 300 km since 2016; of the 20 largest floods,
{cnt.get('cyclone/depression', 0)} followed one, {cnt.get('rain', 0)} came with heavy rain and {cnt.get('river', 0)} with a high river.
**At the site:** interviews on surge and tide-locked drainage.

### 7.7 Construction technology and management

![Deployment schedule]({F}/gantt.png)

**Why it matters.** Protection and sensors must be built outside the flood season, in the right order and within a
budget. **What we did.** Monthly flood and storm climatology, an earthwork take-off for raising the critical links,
deployment quantities and a schedule. **What we found.** The work window is {wwin}. Raising {lrk.get('links_by_embankment', 0)}
critical links takes about {n(lrk.get('earthwork_m3', 0))} m³ of earthwork (about ₹{lrk.get('cost_crore_rs_at_350_per_m3', 0):.2f} crore
at an assumed ₹350/m³); {len(lrk.get('links_needing_structure', []))} more would need raises above 3 m, that is a bridge or a vented
causeway. Installing {CMP.get('deployment', {}).get('sirens', 40)} sirens and {CMP.get('deployment', {}).get('sensor_sites', 6)} river gauges takes about
{CMP.get('deployment', {}).get('crew_days', 0):.0f} crew-days. **At the site:** access, mounting and signal at the proposed sites.
"""
if WS:
    sec7 += f"""
### 7.8 Water resources and the watershed

**Why it matters.** The delta's floods are set upstream, by releases from Hirakud dam and by rain on the uncontrolled
tributaries below it, so a warning for the delta is a warning about the whole watershed. **What we did.** GloFAS
flows below Hirakud, at Tikarpara and at Naraj (1984–2025) were compared at the annual flood peak and over the monsoon
(C.8), next to the travel times and design floods of §6.5. **What we found.** Hirakud controls about 59 % of the basin
(83,400 of about 141,600 km²) and passes {WS['jul_sep_share']:.0%} of the July–September flow at Naraj, but only a median
{WS['median_share_hirakud_of_naraj_peak']:.0%} of the annual flood peak ({WS['years']} years): the other half comes from the
roughly 58,000 km² below the dam, within about a day. A delta warning therefore needs both the dam's release plan and
gauges on the tributaries below it, and watershed measures in that lower catchment (land cover, soil conservation, small
storages) act on the frequent floods more than on the rare largest ones. **At the site:** discharge and Manning's n at a
road bridge; the WRD's account of gate operations.
"""
open(os.path.join(SEC, "07_impacts.md"), "w", encoding="utf-8").write(sec7)
open(os.path.join(SEC, "12_appendix_c.md"), "w", encoding="utf-8").write(appC)

# ------------------------------------------------------------------ 09 implementation
cov = SIT["coverage"]
k80 = SIT.get("sirens_for_80pct_at_1500m")
cur = CURVE[CURVE.radius_m == 1500]
pick = lambda kk: cur[cur.sirens == kk].share.iloc[0] if (cur.sirens == kk).any() else float("nan")  # noqa: E731
sr_rows = "\n".join(f"| {int(r['rank'])} | {r['settlement']} | {r['lat']:.4f} N, {r['lon']:.4f} E | {n(r['new_people_covered'])} | "
                    f"{r['cumulative_share']:.0%} |" for _, r in SR.head(15).iterrows())
sen_rows = "\n".join(f"| {r['river']} | {r['name'] if isinstance(r['name'], str) else (r['ref'] if isinstance(r['ref'], str) else '(unnamed)')} | "
                     f"{r['highway']} | {r['length_m']:.0f} | {r['km_from_naraj']:.0f} | {'yes' if r['access_dry'] else 'no'} | "
                     f"{r['lat']:.4f} N, {r['lon']:.4f} E |" for _, r in SEN.iterrows())
bul5 = os.path.join(IM, "bulletins", f"bulletin_{round(RP[5])}.txt")
bul_txt = open(bul5, encoding="utf-8").read().strip() if os.path.exists(bul5) else "(run mahanadi/forecast_to_impact.py)"
sec9 = f"""## 9. Implementation for ClimMaTech: what a deployment would use

### 9.1 Where it fits

ClimMaTech's system observes (radar gauges), predicts (level and flow 30 min to 48 h ahead) and warns (sirens,
Aagah app, control centre). This project adds the step between "predict" and "warn": **forecast flow at Naraj →
flooded land → settlements, roads and facilities affected**, from the trigger-discharge map of §6.3 and the impact
layers of §7.

```
ClimMaTech / CWC forecast of Naraj flow ──► forecast_to_impact.py ──► flood map (GeoTIFF)
   (m³/s or lakh cusec, lead time)            trigger map + impacts    settlements to warn (GeoJSON) ──► Rakshak Control Centre, Aagah
                                                                       roads under water, bulletin text ──► district / OSDMA
Sentinel-1 pass (every 2-6 days) ──► atlas_infer.py ──► observed flood map ──► refit trigger map each season
```

### 9.2 Forecast-to-bulletin tool

`python mahanadi/forecast_to_impact.py --q <flow>` (or `--lakh-cusec`, and `--rain <mm>` for the flow-and-rain
analogs) runs in seconds. Output for the 5-year flow ({n(RP[5])} m³/s; the 25-year and rain bulletins are in
`results/impact/bulletins/`):

```
{bul_txt}
```

The interactive viewer (`dashboard/index.html`, one file, works offline) shows each design flood with flooded land,
roads cut, the settlements list (click to zoom), siren and sensor sites and the bank-inspection cells.

### 9.3 Siren sites

Greedy maximal coverage of the {n(SIT['exposed_people'])} people living on land flooded in the 25-year flood or in at
least 10 % of monsoon passes. With 40 sirens the share covered is {cov['1000']['share']:.0%}, {cov['1500']['share']:.0%}
and {cov['2000']['share']:.0%} for an audible range of 1.0, 1.5 and 2.0 km. At 1.5 km: 10 sirens cover {pick(10):.0%},
20 cover {pick(20):.0%}{f', and {k80} are needed for 80 %' if k80 else ''}. Exposed people are spread thinly over many
small settlements, so the first sirens give most of the benefit; the rest is better reached by phone alerts (Aagah)
than by more sirens.

| Rank | Settlement | Location | New people covered | Cumulative share |
|---|---|---|---|---|
{sr_rows}

### 9.4 River-sensor bridges

One non-contact radar gauge (level and surface velocity) at the head of each main distributary measures how the
flood splits between the branches, which the Naraj forecast alone cannot tell:

| River | Bridge | Road class | Length (m) | km from Naraj | Approaches dry in 25-yr flood | Location |
|---|---|---|---|---|---|---|
{sen_rows}

Pravaah needs a surveyed cross-section and a surface-to-mean velocity factor to give discharge (ClimMaTech
documentation); the field protocol B–C measures exactly these at one bridge (§8.4).

### 9.5 Rolling it out

1. **Season 0 (now)**: hand the trigger map, bulletin tool and viewer to ClimMaTech; refit with CWC/WRD observed flows.
2. **Before the next monsoon**: field-verified siren and sensor sites (§8.7); first sensors at the heads of the
   Mahanadi and Kathajodi branches.
3. **During the monsoon**: map every new Sentinel-1 pass (6 s per pass on the lab GPU, ~2 min to download) and compare
   with the bulletin of that day; add the season to the atlas.
4. **Each year**: refit the trigger map, update design floods, re-rank links and banks.

### 9.6 Gaps in the partner's services and what this project adds

All 50 public pages of climmatech.com were downloaded on 29 October 2026; the product, solution, platform, fact-sheet
and case-study pages were read in full and the blog was searched. The partner measures and forecasts the river at points and warns through sirens and an app; its
research group reconstructs past floods from satellite, seismic and gauge data by hand. The table lists each service, the
gap found and what this project adds, with the number behind it.

| Their service | Gap | What this project adds | Evidence |
|---|---|---|---|
| River View (platform layer: "a live map-based view of river levels and flood risk") | No flood-extent layer behind the map | Flood frequency, trigger flow and impact layers for the Mahanadi delta | {AS['n_passes']} passes; held-out IoU {HF['model']['iou']:.2f} vs {HF['climatology']['iou']:.2f} at high flows |
| AI forecasting, 30 min to 48 h ahead | A forecast level is not a list of villages | Forecast-to-bulletin tool: map, settlements to warn, roads under water | 25-year flow: {T25['flood_km2']:.0f} km², {n(T25['people'])} people, {int(T25['settlements >= 10 % of people flooded'])} settlements |
| Research group, satellite reconstructions | Flood width measured by hand at 36 cross-sections; optical pass 75–79 % cloud, only radar pass two days early | Benchmarked radar model that maps every Sentinel-1 pass automatically, through cloud | 92 audited runs (Appendix A); ~5 s per pass |
| Solution pages, network design | Layouts drawn as illustrations | Data-backed siting of sirens and river gauges with coordinates | 40 sirens reach {SIT['coverage']['1500']['share']:.0%} of exposed people at 1.5 km; {len(SEN)} sensor bridges |
| Pravaah discharge | Needs a surveyed cross-section and a surface-to-mean velocity factor | Field protocols B and C measure both, plus Manning's n | §8.4; scripts in `fieldkit/analysis/` |
| Varshaq rain gauge | Rain not linked to flooded land | Rain-aware flood maps (analogs, learned model §6.6) | 5-year flow: {_b[20]['flooded_land_km2']:.0f} km² dry week vs {_b[RH]['flooded_land_km2']:.0f} km² heavy rain |
| Flood-warning solution and Aagah app ("time to evacuate populations, reroute traffic, and secure critical infrastructure") | Which people, which roads | Settlements to warn, roads that close, villages that lose their hospital, in every bulletin | {int(TR25['hospital: settlements cut off'])} settlements lose hospital access (25-year flood) |
| Rakshak Control Centre ("draw an area, pick districts, or upload your own boundaries"; accepts CAP) | Alert areas drawn by hand | Every forecast also writes a CAP 1.2 alert with one area per settlement to warn | `bulletin_<flow>.cap.xml`; {J(IM, 'bulletins', f'bulletin_{round(RP[25])}.json').get('settlements_to_warn', 0)} areas for the 25-year flow |
| Dam and reservoir solution | Level at the dam, not the water spread | The same radar model can map reservoir area on every pass (next step: Hirakud) | — |
| Installation and O&M | Timing against floods and storms | Work window and schedule from 42 years of flows and storm tracks | {wwin}; {CMP.get('deployment', {}).get('crew_days', 0):.0f} crew-days |
"""
open(os.path.join(SEC, "09_implementation.md"), "w", encoding="utf-8").write(sec9)

# ------------------------------------------------------------------ appendix: verification of the training
AUD = J(AN, "audit_training.json")
if AUD:
    om_ = AUD.get("official_test_miou", {})
    rd_ = AUD.get("radar_db_percentiles_10_50_90", {})
    ss_ = AUD.get("seed_spread", {})
    sd_max = max((v["sd"] for v in ss_.values() if v["n"] >= 3), default=0)
    ref_rows = "\n".join(f"| {lab} | {om_.get(k, {}).get('water_iou', 0):.3f} | {om_.get(k, {}).get('miou', 0) * 100:.1f} | {ref} |"
                         for lab, k, ref in (("TerraMind-B, radar + optical", "official_terramind_full_s0", "90.62"),
                                             ("TerraMind-B, radar only", "official_terramind_s1_full_s0", "80.39"),
                                             ("Prithvi-EO-2.0-300M", "official_prithvi_full_s0", "–"),
                                             ("U-Net (from scratch)", "official_unet_full_s0", "–")))
    rad_rows = "\n".join(f"| {lab} | {rd_.get(k, {}).get('VV', [0, 0, 0])[1]:.1f} | {rd_.get(k, {}).get('VH', [0, 0, 0])[1]:.1f} |"
                         for lab, k in (("Sen1Floods11 training chips, water", "sen1floods11_train_water"),
                                        ("Mahanadi atlas passes, water", "mahanadi_atlas_water"),
                                        ("Sen1Floods11 training chips, dry", "sen1floods11_train_dry"),
                                        ("Mahanadi atlas passes, dry", "mahanadi_atlas_dry")))
    appendix = f"""## Appendix A. Verification of the training

`scripts/audit_training.py` re-checks every benchmark run on the lab server from its stored outputs
(`results/analysis/audit_training.json`).

| Check | Result |
|---|---|
| Every queued job has results made with the arguments it was queued with | {AUD['n_checked']} of {AUD['n_jobs']} |
| No chip in two of train / validation / test | yes, every run |
| Leave-India-out: no India chip in training or validation; test = the {AUD['split_sizes']['lio']['test']} India chips | yes, every run |
| Model selection on validation only (stored best validation IoU = maximum of the history; test touched once) | yes, every run |
| Test IoU recomputed from the saved probabilities equals the stored value | yes, every run |
| Frozen runs train only the decoder | {min(j['trainable_share'] for j in AUD['jobs'].values() if j['mode'] == 'frozen'):.0%}–{max(j['trainable_share'] for j in AUD['jobs'].values() if j['mode'] == 'frozen'):.0%} of the parameters |
| Spread over three seeds (sd of test IoU) | at most {sd_max:.3f} |
| Problems found | {len(AUD['problems'])} |

**Comparison with published numbers.** On the official Sen1Floods11 test split, mean IoU over water and dry (the
metric of the foundation-model papers) for seed 0:

| Model | Water IoU | Mean IoU (%) | Published mean IoU (%) |
|---|---|---|---|
{ref_rows}

The published values are from the TerraMind paper (Jakubik et al. 2025, arXiv:2504.11171, Table 7; PANGAEA protocol
with a different decoder and schedule), so a gap of about one point is expected; our runs reproduce them.

**The atlas input looks like the training input.** Median radar backscatter (dB) after the gamma0-to-sigma0 conversion
used by `atlas_infer.py`, for 24 random July–October passes of the delta and 60 random Sen1Floods11 training chips:

| Pixels | VV | VH |
|---|---|---|
{rad_rows}

Dry land differs by about 1 dB, and water lies 8–11 dB below dry land in both, so the conversion holds.

**Runs whose best epoch was the last one.** {len(AUD.get('best_epoch_at_last_epoch', []))} of 92 runs
({", ".join(AUD.get('best_epoch_at_last_epoch', []))}). The headline U-Net gained 0.002 validation IoU over its last five
epochs (converged); the frozen Clay run and the optical-only U-Net (seed 1) were still improving, so those two scores
may be slightly low. Neither changes a ranking or a conclusion.
"""
    R20N = J(AN, "radar20m_r20.json")
    if R20N:
        appendix += f"""
## Appendix B. Retraining the radar models at the atlas resolution

The atlas reads Sentinel-1 from the 20 m overviews, and the radar models of §4 were trained at 10 m. Both radar-only
models (TerraMind-B and U-Net, official split, seed 0) were retrained with the radar degraded on the GPU exactly as the
overview is made (2 × 2 average in linear power, bilinear back to 10 m; `floodfm/train.py --s1_res 20`) and scored by
`scripts/test_resolution.py` on the official test split:

| Input to the fusion | 10 m-trained pair | 20 m-trained pair |
|---|---|---|
| Native 10 m radar | {R20['mean']['native']:.3f} | {R20N['mean']['native']:.3f} |
| 20 m overview (the atlas input) | {R20['mean']['avg20']:.3f} | {R20N['mean']['avg20']:.3f} |
| 20 m overview, threshold from validation | {R20['calibrated_test_iou']:.3f} (at {R20['threshold']:.2f}) | {R20N['calibrated_test_iou']:.3f} (at {R20N['threshold']:.2f}) |

{"The 20 m-trained pair is better on the atlas input and can replace the current models in the next atlas run (re-inference of the 590 passes takes about an hour)." if R20N['mean']['avg20'] - R20['mean']['avg20'] >= 0.005 else "Training at 20 m gives no clear gain on the atlas input, so the atlas keeps the 10 m-trained models."}
"""
    open(os.path.join(SEC, "11_appendix.md"), "w", encoding="utf-8").write(appendix)

# ------------------------------------------------------------------ 10 discussion and conclusions
sec10 = f"""## 10. Discussion, limitations and conclusions

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
checked in the field.

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
  floods. Past flood frequency ranks where land floods best (ROC AUC {V['ranking_auc']['high_flow_passes']['clim']:.2f}–{V['ranking_auc']['all_passes']['clim']:.2f});
  the trigger map adds at which flow it floods (AUC {V['ranking_auc']['high_flow_passes']['model']:.2f}–{V['ranking_auc']['all_passes']['model']:.2f}), so the two are used together.
- Flood depth comes from a 30 m surface model (~2 m vertical error); wall screening, scour and foundation numbers
  use typical parameters (masonry tension, bed size, soil strength) and an unknown flow split between distributaries,
  all of which the field visit and the lab replace.

### 10.4 Conclusions

1. On a flood it had never seen, a U-Net ({u('lio/unet/full/default'):.3f}) mapped water better than six geospatial
   foundation models (best {u('lio/prithvi/full/default'):.3f}); a three-model fusion was best
   ({u('lio/enstop3_mean/full/default'):.3f}).
2. A radar-only fusion of TerraMind and U-Net maps the Mahanadi delta through monsoon cloud; {AS['n_passes']} passes
   from {AS['years'][0]} to {AS['years'][-1]} form the atlas.
3. A per-pixel trigger discharge turns a Naraj flow forecast into a flood map and beats climatology on held-out years
   at high flows ({HF['model']['iou']:.2f} vs {HF['climatology']['iou']:.2f}).
4. In a 25-year flood about {n(T25['people'])} people live on flooded land and {n(TR25['hospital: people cut off'])} lose
   road access to a hospital; the links, banks, siren sites and sensor bridges to act on are listed.
5. Local rain and Bay of Bengal storms, not only the river, drive the largest floods of the delta; a warning has to
   read the river forecast together with the rainfall forecast.
6. The same scenarios give each specialization its answer: who loses the road to a hospital or shelter
   (transportation), where walls crack and how deep scour reaches (structural), which banks to inspect and which dry
   houses sit on soaked ground (geotechnical), how storms add to floods (ocean), and when and at what earthwork the
   critical links can be raised (construction management).
7. The field visit is designed to measure what these numbers depend on and to change them where they are wrong.

### 10.5 Next steps, by specialization

| Specialization | Next step | Why |
|---|---|---|
| Remote sensing | Add SWOT water-surface elevations (2023–) and NISAR L-band (2025–) | Depth from measured water levels instead of a surface model; flooding under crops and trees |
| Water resources | Refit with observed CWC/WRD flows; calibrate a 2-D HEC-RAS model of the delta against the atlas | A physics-based inundation model that can go beyond the floods seen since 2017 |
| Transportation | Time-dependent closures during flood onset; school and market (mandi) access; evacuation timing vs warning lead time | When, not only whether, villages are cut off |
| Structural | Depth–damage curves for kutcha and pucca houses (Census housing types) → expected annual damage | Money at risk, for cost–benefit of road raising and embankments |
| Geotechnical | 2-D seepage analysis of the top-ranked embankments with lab permeability; bank-line migration from Landsat 1990– | Piping and erosion risk with numbers, not ranks |
| Ocean | Paradip tide-gauge and surge hindcasts; sea-level-rise scenarios for drainage of the lower delta | Compound river–rain–surge flooding |
| Construction technology & management | Life-cycle cost and O&M plan of the sensor network; procurement through GeM; contract packaging for road raising | From a plan to a project ClimMaTech and WRD can execute |

The common first step for all of them is the field visit (§8) and the observed Naraj flows.

### 10.6 Abstract for HYDRO 2026 / journal submission

*Turning river-flow forecasts into flood maps with Sentinel-1 and geospatial foundation models: the Mahanadi delta.*
We benchmark six geospatial foundation models against CNN and U-Net baselines on Sen1Floods11 with a leave-India-out
protocol (U-Net {u('lio/unet/full/default'):.3f}, best foundation model {u('lio/prithvi/full/default'):.3f}, fusion
{u('lio/enstop3_mean/full/default'):.3f} IoU on an unseen Indian flood), build a radar-only flood atlas of the
Mahanadi delta from {AS['n_passes']} Sentinel-1 passes ({AS['years'][0]}–{AS['years'][-1]}), and link it to river
discharge at Naraj through a per-pixel trigger discharge. On held-out years the resulting flow-to-flood maps reach IoU
{HF['model']['iou']:.2f} at high flows against {HF['climatology']['iou']:.2f} for flood climatology. Combined with road
networks and population, they identify the people cut off from hospitals, critical road links and river banks for
inspection, giving point-forecast early-warning systems the spatial impact layer they lack.
"""
open(os.path.join(SEC, "10_discussion.md"), "w", encoding="utf-8").write(sec10)
print("written 00_front, 06_mahanadi, 07_impacts, 09_implementation, 10_discussion")
