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
R20N = J(AN, "radar20m_r20.json")
# the atlas was built with the radar pair retrained on 20 m input when its threshold is that pair's validation threshold
ADOPTED = bool(R20N) and abs(AS.get("threshold", 0) - R20N.get("threshold", -1)) < 1e-9
PROD = R20N if ADOPTED else R20
CMPA = J(os.path.dirname(AT), "archive_atlas_10m", "compare.json")  # the atlas built with the 10 m-trained pair, for comparison
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

def top_floods(drv, k=2, gap_days=10):
    """The k largest floods on radar that are separate events (more than gap_days apart), largest first."""
    d = drv.assign(when=pd.to_datetime(drv.date)).sort_values("flood_km2", ascending=False)
    picked = []
    for _, r_ in d.iterrows():
        if all(abs((r_['when'] - p_['when']).days) > gap_days for p_ in picked):
            picked.append(r_)
        if len(picked) == k:
            break
    return picked


def fold_word(x):
    k_ = round(x)
    return {2: "two-fold", 3: "three-fold", 4: "four-fold", 5: "five-fold", 6: "six-fold"}.get(k_, f"{k_}-fold")



# ------------------------------------------------------------------ 00 front matter
FC = J(ROOT, "results", "forecast", "forecast_summary.json")
RISK = J(IM, "risk_economics.json")
RISK_ROW = (f"| Risk and economics (cross-cutting) | What do floods cost, and what is protection worth? | Depth–damage curve, paddy at the support price, 29 years of daily flows through the flow–impact table | ₹{RISK['expected_annual_damage_rs_crore']['total_rs_crore']:.0f} crore of damage a year; raising the critical links repays {RISK['road_raising']['benefit_cost_ratio']:.0f} times | Losses in the interviews | Himanshu, Prabhat |\n") if RISK else ""
LIVE = J(ROOT, "live", "out", "mahanadi", "status.json")
LIVECFG = J(ROOT, "live", "basins", "mahanadi.json")
_rp = sorted(glob.glob(os.path.join(ROOT, "live", "out", "replay_*", "mahanadi", "status.json")))
REPLAY = J(_rp[-1]) if _rp else {}
BASKEYS = sorted(d for d in os.listdir(os.path.join(ROOT, "results", "basins"))
                 if os.path.isdir(os.path.join(ROOT, "results", "basins", d))) if os.path.isdir(os.path.join(ROOT, "results", "basins")) else []
BAS = {k: dict(AS=J(ROOT, "results", "basins", k, "atlas", "atlas_summary.json"),
               EX=J(ROOT, "results", "basins", k, "impact", "exposure_summary.json"),
               S2=J(ROOT, "results", "basins", k, "impact", "s2_crosscheck.json"),
               CFG=J(ROOT, "live", "basins", f"{k}.json")) for k in BASKEYS}
BAS = {k: v for k, v in BAS.items() if v["AS"]}
_LF = J(AT, "learned", "learned_summary.json") or {"pixel_iou": {"heavy_rain_passes": {"learned": {"iou": 0}, "trigger": {"iou": 0}}}}
ABS_NEW = ""
if FC:
    _k = FC["skill"]
    ABS_NEW += (f" A gradient-boosted model forecasts the Naraj flow one to three days ahead from the upstream flows and the"
                f" catchment rain (Nash-Sutcliffe efficiency {_k['lead_1d']['boosted']['nse']:.2f}, {_k['lead_2d']['boosted']['nse']:.2f}"
                f" and {_k['lead_3d']['boosted']['nse']:.2f} on monsoons it never saw, against {_k['lead_1d']['persistence']['nse']:.2f},"
                f" {_k['lead_2d']['persistence']['nse']:.2f} and {_k['lead_3d']['persistence']['nse']:.2f} for persistence), and a live feed"
                f" turns each day's GloFAS ensemble into an impact-based warning with a CAP alert.")
if BAS:
    ABS_NEW += (" The same pipeline mapped the " + " and the ".join(v["CFG"].get("name", k) for k, v in BAS.items())
                + " from every Sentinel-1 pass since 2017.")
if RISK:
    ABS_NEW += (f" Flood damage to houses and paddy comes to about ₹{RISK['expected_annual_damage_rs_crore']['total_rs_crore']:.0f} crore a"
                f" year (a lower bound), and raising ten critical roads repays its cost {RISK['road_raising']['benefit_cost_ratio']:.0f} times"
                f" in hospital access alone.")

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
(IoU {PROD['calibrated_test_iou']:.3f} on 20 m radar{", trained on 20 m input" if ADOPTED else ""}). Applied to {AS['n_passes']} Sentinel-1 passes from
{AS['years'][0]} to {AS['years'][-1]}, it gives a flood atlas of the delta. Linking the atlas to GloFAS discharge at
Naraj, each 20 m pixel receives the flow at which it starts to flood, so a discharge forecast becomes a flood map;
on years held out from fitting, this map beats flood climatology at high flows (IoU {HF['model']['iou']:.2f} vs
{HF['climatology']['iou']:.2f}). For the 25-year flood ({n(RP[25])} m³/s) about {n(T25['people'])} people live on
flooded land, {T25['road km (all)']:.0f} km of road is under water and {n(TR25['hospital: people cut off'])} people in
{int(TR25['hospital: settlements cut off'])} settlements lose road access to any hospital. A learned model that adds local
rain and each pixel's flood history to the river flow maps held-out heavy-rain passes better still (IoU
{_LF['pixel_iou']['heavy_rain_passes']['learned']['iou']:.2f} against {_LF['pixel_iou']['heavy_rain_passes']['trigger']['iou']:.2f}).{ABS_NEW} The same scenarios are carried
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
    a0, a1, t0 = HR["analog_flow"]["iou"], HR["analog_flow_rain"]["iou"], HR["model"]["iou"]
    rain_sent = (f"adding rain to the analogs leaves their IoU at {a1:.2f}" if abs(a1 - a0) < 0.005 else
                 f"adding rain to the analogs {'raises' if a1 > a0 else 'lowers'} their IoU from {a0:.2f} to {a1:.2f}")
    rain_sent += (", about the trigger map's level" if abs(a1 - t0) < 0.005 else
                  f", only {a1 - t0:.2f} above the trigger map" if a1 > t0 else f", still below the trigger map's {t0:.2f}")
    _tops = top_floods(C(IM, "flood_drivers.csv"))
    _qmax = AS["largest_observed_predictor_m3s"]
    _moderate = all(t_.naraj_m3s < 0.7 * _qmax for t_ in _tops)
    top_txt = " and ".join(
        f"{t_['when'].day} {t_['when']:%B %Y} ({t_.flood_km2:.0f} km², Naraj flow {n(t_.naraj_m3s)} m³/s, {t_.rain_mm:.0f} mm of ERA5 rain in the "
        f"week before{', with a Bay of Bengal depression' if isinstance(t_.system, str) and t_.system else ''})" for t_ in _tops)
    cmp_txt = f"""
**The river is not the only driver.** The largest flood extents in the record came with {"moderate " if _moderate else ""}Naraj
flows (the largest flow seen is {n(_qmax)} m³/s): {top_txt}. A map driven by Naraj flow
alone cannot predict those. The same held-out test was therefore repeated with
analog maps: for each pass of the held-out year, the 7 training passes most similar in flow (or in flow and
{PRAIN.get(AS.get('rain_predictor', ''), 'local rain')}) are looked up, and land flooded on at least half of them is predicted
flooded.

| Method | IoU, all passes | IoU, high flow (≥ {n(HF['q90_threshold_m3s'])} m³/s) | IoU, heavy rain (≥ {HR['r90_threshold_mm']:.0f} mm in {PRAIN.get(AS.get('rain_predictor', ''), '7 days').replace(' rain', '').replace('-day', ' days')}) | Settlements, high flow: POD / FAR | Settlements, heavy rain: POD / FAR |
|---|---|---|---|---|---|
{chr(10).join(rows_m)}

On the heavy-rain passes the best method is the {SHORT[best_hr[0]]} (IoU {HR[best_hr[0]]['iou']:.2f}), and
{rain_sent}:
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

The production model of §4.8 (mean of the radar-only TerraMind-B and U-Net{", retrained on 20 m input as in Appendix B" if ADOPTED else ""}, threshold {AS.get('threshold', 0.3):.2f}) was run on
**{AS['n_passes']} Sentinel-1 passes** ({AS['n_dry']} in February–March, {AS['n_monsoon']} in June–November,
{AS['years'][0]}–{AS['years'][-1]}; tracks {trk}; platforms {', '.join(f'{k} {v}' for k, v in plat.items())}).
A pass is all slices of one satellite overpass; together they give a water map of the delta every 2–6 days in the
monsoon. The river bed (main channels and sand bars, {AS.get('river_bed_km2', 0):.0f} km²) and each year's
dry-season water are "normal water"; only water outside them counts as flood. A 3 km band along each pass's data
edge is removed: a first version showed a diagonal stripe of false floods along one track's swath edge.

![Flow at Naraj and flooded land on every pass]({F}/atlas_timeseries.png)

![Flood frequency 2017–2026]({F}/atlas_frequency_map.png)

- Land flooded on at least one pass: {n(AS['flooded_ever_km2'])} km²; in at least 20 % of monsoon passes:
  {AS['flooded_20pct_km2']:.0f} km².
- The largest flood seen on a near-complete pass was on {obs_date} ({EX.loc[OBS, 'flood_km2']:.0f} km² of flooded land).
- The flooded fraction of each pass follows the Naraj flow. Spearman ρ by predictor:
  {', '.join(f"{PNAME[k]} {v:.3f}" for k, v in AS['predictor_spearman'].items())}; the {PNAME[AS['predictor']]} is used
  {('(the five are practically tied: floodplains drain slowly, so any recent peak works)'
    if max(AS['predictor_spearman'].values()) - min(AS['predictor_spearman'].values()) < 0.01 else
    '(floodplains drain slowly, so the map follows the recent peak more than the flow of the day)') if 'max' in AS['predictor'] else ''}.

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

Gumbel fit to {AS['gumbel']['n_years']} GloFAS annual maxima at Naraj (1997–2025):

| Return period (years) | Naraj flow (m³/s) | (lakh cusec) | Flooded land (km²) |
|---|---|---|---|
{rp_rows}

The largest flow in the radar record is {n(AS['largest_observed_predictor_m3s'])} m³/s; above it the map cannot grow
further and is a lower bound{(' (' + ', '.join(f'{T}-yr' for T in lb) + ')') if lb else ''}.

Day-to-day changes of flow below Hirakud correlate best with those at Naraj
{lagtxt(TT['hirakud_below']['best_lag_days'])} (r = {TT['hirakud_below']['corr_by_lag_days'][str(TT['hirakud_below']['best_lag_days'])]:.2f}),
and those at Tikarpara {lagtxt(TT['tikarpara']['best_lag_days'])} (r = {TT['tikarpara']['corr_by_lag_days'][str(TT['tikarpara']['best_lag_days'])]:.2f}),
in June–October 1997–2025 (daily data resolve only whole days). A release seen by a spillway sensor at Hirakud
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
- **The flow forecast is scored against GloFAS itself** (§6.7): its skill against measured Naraj flows is unknown
  until CWC records or upstream gauges arrive, and GloFAS's own forecast skill at Naraj has not been verified here.
"""
LRN = J(AT, "learned", "learned_summary.json")
LRU = J(os.path.dirname(AT), "archive_atlas_10m", "learned_unconstrained_summary.json")  # first run, on the earlier atlas
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
    _lr_fold = fold_word(sc_.get('T5 heavy rain', {}).get('flood_km2', 0) / max(sc_.get('T5 dry week', {}).get('flood_km2', 1), 1))
    _an_fold = fold_word(_b[RH]['flooded_land_km2'] / max(_b[20]['flooded_land_km2'], 1)) if all(_b.values()) else ""
    an_cmp = ("" if not _an_fold else ", the same as in the analog maps of §6.4" if _an_fold == _lr_fold else
              f" (the analog maps of §6.4 give {_an_fold}: {_b[20]['flooded_land_km2']:.0f} against {_b[RH]['flooded_land_km2']:.0f} km²)")
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
{"a first run without these constraints (on the earlier atlas of Appendix B) scored " + format(LRU['pixel_iou']['all_passes']['learned']['iou'], '.3f') + " IoU but gave less flooded land for heavy than for typical rain at the 25-year flow (" + format(LRU['scenarios_all_years_model']['T25 heavy rain']['flood_km2'], '.0f') + " against " + format(LRU['scenarios_all_years_model']['T25 typical rain']['flood_km2'], '.0f') + " km²), which a warning map must never do." if LRU else ""}
The inputs it leans on most (drop in held-out ranking AUC when each is shuffled):
{"; ".join(f"{FEAT_NAMES.get(k, k)} {v:.3f}" for k, v in imp)}. Fitted on all years, it floods
{sc_.get('T5 dry week', {}).get('flood_km2', 0):.0f} km² at the 5-year flow in a dry week,
{sc_.get('T5 typical rain', {}).get('flood_km2', 0):.0f} km² with typical rain and {sc_.get('T5 heavy rain', {}).get('flood_km2', 0):.0f} km²
with heavy rain ({LRN.get('scenario_note', '')}), a roughly {fold_word(sc_.get('T5 heavy rain', {}).get('flood_km2', 0) / max(sc_.get('T5 dry week', {}).get('flood_km2', 1), 1))}
effect of rain between a dry and a heavy-rain week{an_cmp}.
For a warning system this is the model that takes both of
ClimMaTech's inputs, the river forecast and a rain-gauge or forecast rain total, and returns one map.

"""
    sec6 = sec6.replace("### 6.6 Limits", learned_md + "### 6.7 Limits")
_n6 = 7 if "### 6.7 Limits" in sec6 else 6
extra6 = ""
if FC:
    _k = FC["skill"]
    _row = lambda L, m: _k[f"lead_{L}d"][m]  # noqa: E731
    fc_rows = "\n".join(
        f"| {L} day{'s' if L > 1 else ''} | {_row(L, 'persistence')['nse']:.3f} | {_row(L, 'linear_routing')['nse']:.3f} | "
        f"{_row(L, 'boosted')['nse']:.3f} ({_row(L, 'boosted')['kge']:.2f}) | {_row(L, 'boosted_with_rain_forecast')['nse']:.3f} | "
        f"{_row(L, 'persistence')['two_year_flood']['pod']:.0%} / {_row(L, 'persistence')['two_year_flood']['far']:.0%} | "
        f"{_row(L, 'boosted')['two_year_flood']['pod']:.0%} / {_row(L, 'boosted')['two_year_flood']['far']:.0%} | "
        f"{_row(L, 'boosted_with_rain_forecast')['two_year_flood']['pod']:.0%} / {_row(L, 'boosted_with_rain_forecast')['two_year_flood']['far']:.0%} |"
        for L in (1, 2, 3))
    extra6 += f"""### 6.{_n6} Forecasting the flow at Naraj

A flood map is only as early as the flow forecast behind it. The trigger map turns a Naraj flow into a map; this
section asks how far ahead that flow can be known from what is measured upstream today. Water reaches Naraj from the
Hirakud reach and the Tel and Ong tributaries in about a day (§6.5), so the flows at Naraj, Tikarpara and below Hirakud
on the issue day and the two days before, their last-day changes, ERA5 rain over the catchment between Hirakud and Naraj
(eight points; the day, the day before, 3- and 7-day sums) and the season predict the change in the Naraj flow one,
two and three days ahead. One gradient-boosted model per lead time (scikit-learn HistGradientBoosting,
`mahanadi/forecast_model.py`) was trained on {FC['train_years'][0]}–{FC['train_years'][1]} and tested on the June–November
days of {FC['test_years'][0]}–{FC['test_years'][1]}, which it never saw. Baselines: persistence (the flow stays as it is)
and linear routing (log-flows at the three gauges). A second variant adds the rain of the coming days as if it were
forecast perfectly, the most a rain forecast can add.

| Lead | Persistence | Linear routing | Model (KGE) | Model + rain forecast | 2-year flood, persistence: caught / false | Model | Model + rain forecast |
|---|---|---|---|---|---|---|---|
{fc_rows}

Cells give Nash–Sutcliffe efficiency of the daily flow (1 = perfect), and for the {n(FC['thresholds_m3s']['two_year_flood'])} m³/s
two-year flow the share of exceedance days caught and the share of forecast exceedances that were false. The model keeps
its skill where persistence fades: three days ahead its efficiency is {_row(3, 'boosted')['nse']:.2f} against
{_row(3, 'persistence')['nse']:.2f}, and one day ahead it catches the two-year flood as often as persistence with
{_row(1, 'boosted')['two_year_flood']['far']:.0%} instead of {_row(1, 'persistence')['two_year_flood']['far']:.0%} false alarms.
A rain forecast adds little to the efficiency but most where it matters: two and three days ahead it raises the
two-year floods caught from {_row(2, 'boosted')['two_year_flood']['pod']:.0%} to {_row(2, 'boosted_with_rain_forecast')['two_year_flood']['pod']:.0%}
and from {_row(3, 'boosted')['two_year_flood']['pod']:.0%} to {_row(3, 'boosted_with_rain_forecast')['two_year_flood']['pod']:.0%}.
The flows are GloFAS reanalysis, the series the atlas is fitted on; with CWC records or Pravaah-type gauges upstream the
same code trains on measured flows, and the forecast runs in the live feed of §9.7 next to the GloFAS ensemble.

![Two test monsoons: the Naraj flow and the forecasts made one and three days earlier](../results/forecast/forecast_naraj.png)

"""
    _n6 += 1
if BAS:
    b_rows = []
    for k_, v_ in [("mahanadi", dict(AS=AS, EX=EXS, S2=S2C, CFG=LIVECFG))] + list(BAS.items()):
        a_, hf_ = v_["AS"], v_["AS"]["validation"]["high_flow_passes"]
        t25_ = (v_["EX"] or {}).get("scenarios", {}).get("T25", {})
        s2_ = (v_["S2"] or {}).get("all/all_months", {})
        v_["CFG"] = v_["CFG"] or {}
        b_rows.append(f"| {v_['CFG'].get('name', k_)} | {v_['CFG'].get('river', '')} at {v_['CFG'].get('gauge_name', '')} | "
                      f"{a_['n_passes']} | {n(a_['flooded_ever_km2'])} | {n(a_['gumbel']['return_period_m3s']['25'])} | "
                      f"{n(t25_.get('flood_km2', 0))} | {n(t25_.get('people', 0))} | {hf_['model']['iou']:.2f} vs {hf_['climatology']['iou']:.2f} | "
                      + (f"{s2_['iou']:.2f} |" if s2_ else "– |"))
    _bt = []
    for k_, v_ in BAS.items():
        a_, sc_ = v_["AS"], (v_["EX"] or {}).get("scenarios", {})
        ob_ = next((k for k in sc_ if k.startswith("observed_")), None)
        lf_ = (v_["CFG"] or {}).get("level_flows_m3s", {})
        _bt.append(f"**{(v_['CFG'] or {}).get('name', k_)}.** {a_['n_passes']} usable passes; {n(a_['flooded_ever_km2'])} km² flooded at least once"
                   + (f"; the largest flood seen, on {ob_[9:13]}-{ob_[13:15]}-{ob_[15:17]}, covered {n(sc_[ob_]['flood_km2'])} km² with "
                      f"{n(sc_[ob_]['people'])} people on it" if ob_ else "")
                   + f". The 25-year flow ({n(a_['gumbel']['return_period_m3s']['25'])} m³/s) maps {n(sc_.get('T25', {}).get('flood_km2', 0))} km²"
                   f" with {n(sc_.get('T25', {}).get('people', 0))} people, a lower bound because the largest flow on a pass was "
                   f"{n(a_['largest_observed_predictor_m3s'])} m³/s"
                   + (f"; warnings start at {n(lf_.get('1'))}, {n(lf_.get('2'))} and {n(lf_.get('3'))} m³/s" if lf_ else "") + ".")
    _bas_txt = "\n\n".join(_bt)
    extra6 += f"""### 6.{_n6} The same pipeline on two more basins

Nothing in the method is specific to the Mahanadi. A basin is a box, a GloFAS cell on the main river (checked by its
mean flow), the months of the dry season and of the flood season (`mahanadi/basins.py`). The Brahmani–Baitarani delta
next door (Jajpur, Kendrapara and Bhadrak districts) and the Brahmaputra around Majuli in Assam, the region of the
benchmark's unseen Indian flood, went through the same chain: every Sentinel-1 pass since 2017 at 20 m, the production
radar pair at threshold 0.45, the trigger map with its held-out-year test, Gumbel design floods, exposure, the
flow-impact tables of §9.7 and the Sentinel-2 check (`server/run_basins_pull.sh`, `run_basins_context.sh`,
`run_basin_atlas.sh`).

| Basin | Gauge | Passes | Flooded at least once (km²) | 25-year flow (m³/s) | Flooded land, 25-year (km²) | People on it | Held-out high flows: trigger vs climatology (IoU) | Sentinel-2 agreement (IoU) |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(b_rows)}

{_bas_txt}

The Brahmani–Baitarani delta is fed by two rivers and the trigger map is fitted on the Brahmani alone, so floods that
the Baitarani drives are predicted less well; the Brahmaputra floodplain is braided and its char islands move between
years. Both basins run in the live feed under the same impact-based rule, counted beyond what an ordinary monsoon
already floods (§9.7).

"""
    _n6 += 1
sec6 = sec6.replace("### 6.7 Limits" if "### 6.7 Limits" in sec6 else "### 6.6 Limits", extra6 + f"### 6.{_n6} Limits")
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
mr_emb = lrk.get("max_raise_for_embankment_m", 3)
max_raise = float(LR["raise_m"].max()) if len(LR) and "raise_m" in LR else 0.0
struct_short = (f"{len(struct_links)} more need a bridge or vented causeway" if struct_links
                else f"all by embankment (largest raise {max_raise:.1f} m)")
struct_long = (f"{len(struct_links)} more would need raises above {mr_emb:.0f} m, that is a bridge or a vented causeway"
               if struct_links else
               f"none needs more than {max_raise:.1f} m, so all are road embankments and none needs a bridge or a vented causeway")
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
| Construction technology & management | When to build, what it costs, in what order | Flood/storm climatology, earthwork take-off, BoQ, schedule | Work window {wwin}; {n(lrk.get('earthwork_m3', 0))} m³ to raise {lrk.get('links_by_embankment', 10)} critical links, {struct_short} | Site sheets for sensors/sirens | Prabhat |
{RISK_ROW}
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

Daily GloFAS v4 flows just below Hirakud dam and at Naraj, {WS['years']} complete years between 1997 and 2025
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
at an assumed ₹350/m³); {struct_long}. Installing {CMP.get('deployment', {}).get('sirens', 40)} sirens and {CMP.get('deployment', {}).get('sensor_sites', 6)} river gauges takes about
{CMP.get('deployment', {}).get('crew_days', 0):.0f} crew-days. **At the site:** access, mounting and signal at the proposed sites.
"""
if WS:
    sec7 += f"""
### 7.8 Water resources and the watershed

**Why it matters.** The delta's floods are set upstream, by releases from Hirakud dam and by rain on the uncontrolled
tributaries below it, so a warning for the delta is a warning about the whole watershed. **What we did.** GloFAS
flows below Hirakud, at Tikarpara and at Naraj (1997–2025) were compared at the annual flood peak and over the monsoon
(C.8), next to the travel times and design floods of §6.5. **What we found.** Hirakud controls about 59 % of the basin
(83,400 of about 141,600 km²) and passes {WS['jul_sep_share']:.0%} of the July–September flow at Naraj, but only a median
{WS['median_share_hirakud_of_naraj_peak']:.0%} of the annual flood peak ({WS['years']} years): the other half comes from the
roughly 58,000 km² below the dam, within about a day. A delta warning therefore needs both the dam's release plan and
gauges on the tributaries below it, and watershed measures in that lower catchment (land cover, soil conservation, small
storages) act on the frequent floods more than on the rare largest ones. **At the site:** discharge and Manning's n at a
road bridge; the WRD's account of gate operations.
"""
if RISK:
    _e, _d, _r, _h = (RISK[k] for k in ("expected_annual_damage_rs_crore", "daily_record", "road_raising", "hirakud_1000_m3s_off_the_peak"))
    _py, _lv = _d["per_year"], _d["mean_days_per_year_at_level"]
    sec7 += f"""
### 7.9 Flood risk in rupees and person-days

**Why it matters.** Protection and warnings compete for money with everything else a district builds, so the hazard
has to be put in rupees and in days of life disrupted. **What we did.** Flood depth (§7.3) times the JRC depth–damage
curve for houses in Asia gives the houses damaged; flooded paddy at Odisha's yield and the support price gives the crop
lost; every day of {_d['years'].replace('-', '–')} at Naraj, run through the flow–impact table, gives what an average year costs (C.9).
**What we found.** Expected flood damage is about ₹{_e['total_rs_crore']:.0f} crore a year (houses ₹{_e['houses_rs_crore']:.1f}
crore, paddy ₹{_e['paddy_rs_crore']:.1f} crore), a lower bound because floods above the largest seen are. An average year
brings {n(_py.get('person_days_on_flooded_land', 0))} person-days on flooded land and {n(_py.get('person_days_without_hospital_access', 0))}
person-days without road access to any hospital. Raising the ten critical links (§7.7) cuts the latter to
{n(_py.get('person_days_without_hospital_access_links_raised', 0))}; valued only at the rural wage, that repays the earthwork
{_r['benefit_cost_ratio']:.0f} times. Every 1,000 m³/s that Hirakud keeps off a 5-year peak keeps about {n(_h['T5']['people_saved'])}
people dry. The impact-based warning levels of §9.7 would have reached "Be prepared" on {_lv.get('days_level_2_or_more', 0):.1f}
days a year on average, so warnings stay rare. **At the site:** the farmers' and householders' losses in the interviews.
"""
    dmg_rows = "\n".join(f"| {r['T']}-year | {n(r['flow_m3s'])} | {n(r['people_on_flooded_land'])} | {n(r['house_equivalents_damaged'])} | "
                         f"{r['houses_rs_crore']:.2f} | {n(r['paddy_flooded_ha'])} | {n(r['paddy_lost_ha'])} | {r['paddy_rs_crore']:.2f} | "
                         f"{r['total_rs_crore']:.2f} |" for r in RISK["damage_by_flood"])
    appC += f"""
### C.9 Risk and economics

**Houses.** For each design flood, the people on flooded land in each 0.1 m depth step (impact_depth.py, now also for
the 2- and 10-year floods) times the JRC depth–damage fraction for residential buildings in Asia (Huizinga et al. 2017:
0.33 at 0.5 m, 0.49 at 1 m, 0.72 at 2 m, 1.0 at 6 m) gives damage in house-equivalents at one household per
{RISK['parameters']['people_per_household']} people (an assumption of the order of the Census for rural Odisha), priced at
the PMAY-G rural housing assistance of ₹1.20 lakh a house: the public cost of rebuilding, a lower bound of the loss.
**Paddy.** Flooded cropland (ESA WorldCover) at Odisha's rice yield of 2,081 kg/ha (RBI, 2023-24) and the 2025-26 MSP of
₹2,369 a quintal (₹{n(RISK['parameters']['paddy_rs_per_ha'])} a hectare); the crop is lost where the water is 0.5 m deep or more and
{RISK['parameters']['shallow_crop_loss']:.0%} is lost where it is shallower. **Expected annual damage** is the area under the
damage–probability curve from the 2- to the 100-year flood (trapezoid rule) plus the 100-year damage for the rarer tail.

| Flood | Naraj flow (m³/s) | People on flooded land | Houses (damage-equivalent) | Houses (₹ crore) | Paddy flooded (ha) | Paddy lost (ha) | Paddy (₹ crore) | Total (₹ crore) |
|---|---|---|---|---|---|---|---|---|
{dmg_rows}

The 10- to 100-year rows are equal because the radar record has not seen a larger flood (§6.5): the expected annual
damage, ₹{_e['total_rs_crore']:.1f} crore, is a lower bound. **The daily record.** Each day of {_d['years'].replace('-', '–')} at Naraj, as the
3-day peak flow the atlas uses, was looked up in the flow–impact table (`impact_curve.csv`): on average a year brings
{n(_py.get('person_days_on_flooded_land', 0))} person-days on flooded land and {n(_py.get('person_days_without_hospital_access', 0))}
person-days without road access to any hospital ({n(_py.get('person_days_without_hospital_access_links_raised', 0))} with the ten
critical links raised, i.e. never cut). The warning levels of §9.7 would have stood at "Be aware" or above on
{_lv.get('days_level_1_or_more', 0):.1f} days a year, "Be prepared" or above on {_lv.get('days_level_2_or_more', 0):.1f} and
"Act now" on {_lv.get('days_level_3_or_more', 0):.1f}, with "Act now" in {_d['years_with_any_level_3']} of the years.
**Road raising.** The earthwork of C.7 (₹{_r['cost_rs_crore']:.2f} crore) annualised over {_r['life_years']} years at
{_r['discount_rate']:.0%} costs ₹{_r['annual_cost_rs_lakh']:.1f} lakh a year; the {n(_r['person_days_saved_per_year'])} person-days of
hospital access it saves, valued at the Odisha MGNREGA wage of ₹254 a day (2024-25), are worth ₹{_r['annual_benefit_rs_lakh']:.0f}
lakh: a benefit–cost ratio of {_r['benefit_cost_ratio']:.0f} that leaves out health outcomes and travel delays.
**Hirakud.** Taking 1,000 m³/s off the peak keeps about {n(_h['T2']['people_saved'])}, {n(_h['T5']['people_saved'])} and
{n(_h['T10']['people_saved'])} people dry in a 2-, 5- and 10-year flood. **Warnings.** Twenty-four hours of warning cuts flood
damage by about 30 % (Global Commission on Adaptation, 2019), about ₹{RISK['warning_saving_rs_crore_per_year']:.0f} crore a year here.
"""
open(os.path.join(SEC, "07_impacts.md"), "w", encoding="utf-8").write(sec7)
open(os.path.join(SEC, "12_appendix_c.md"), "w", encoding="utf-8").write(appC)

# ------------------------------------------------------------------ 09 implementation
FC_EVID = (f"; forecast efficiency {FC['skill']['lead_1d']['boosted']['nse']:.2f} / {FC['skill']['lead_2d']['boosted']['nse']:.2f} / "
           f"{FC['skill']['lead_3d']['boosted']['nse']:.2f} at 1 / 2 / 3 days") if FC else ""
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
GloFAS ensemble + ECMWF rain + SACHET/CWC alerts ──► live/run_live.py (daily) ──► impact-based level, villages with dates,
                                                                                  CAP alert + Atom feed ──► Rakshak Control Centre
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

1. **Season 0 (now)**: hand the trigger map, bulletin tool, live feed and viewer to ClimMaTech; run the live feed every
   morning; refit with CWC/WRD observed flows.
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
| AI forecasting, 30 min to 48 h ahead | A forecast level is not a list of villages | Forecast-to-bulletin tool and a daily live feed with impact-based levels; a 1–3 day Naraj forecast from upstream flows (§6.7, §9.7) | 25-year flow: {T25['flood_km2']:.0f} km², {n(T25['people'])} people, {int(T25['settlements >= 10 % of people flooded'])} settlements{FC_EVID} |
| Research group, satellite reconstructions | Flood width measured by hand at 36 cross-sections; optical pass 75–79 % cloud, only radar pass two days early | Benchmarked radar model that maps every Sentinel-1 pass automatically, through cloud | 92 audited runs (Appendix A); ~5 s per pass |
| Solution pages, network design | Layouts drawn as illustrations | Data-backed siting of sirens and river gauges with coordinates | 40 sirens reach {SIT['coverage']['1500']['share']:.0%} of exposed people at 1.5 km; {len(SEN)} sensor bridges |
| Pravaah discharge | Needs a surveyed cross-section and a surface-to-mean velocity factor | Field protocols B and C measure both, plus Manning's n | §8.4; scripts in `fieldkit/analysis/` |
| Varshaq rain gauge | Rain not linked to flooded land | Rain-aware flood maps (analogs, learned model §6.6) | 5-year flow: {_b[20]['flooded_land_km2']:.0f} km² dry week vs {_b[RH]['flooded_land_km2']:.0f} km² heavy rain |
| Flood-warning solution and Aagah app ("time to evacuate populations, reroute traffic, and secure critical infrastructure") | Which people, which roads | Settlements to warn, roads that close, villages that lose their hospital, in every bulletin | {int(TR25['hospital: settlements cut off'])} settlements lose hospital access (25-year flood) |
| Rakshak Control Centre ("draw an area, pick districts, or upload your own boundaries"; accepts CAP) | Alert areas drawn by hand | Every forecast also writes a CAP 1.2 alert with one area per settlement to warn, listed in an Atom feed the centre can subscribe to | `bulletin_<flow>.cap.xml`; {J(IM, 'bulletins', f'bulletin_{round(RP[25])}.json').get('settlements_to_warn', 0)} areas for the 25-year flow |
| Dam and reservoir solution | Level at the dam, not the water spread | The same radar model can map reservoir area on every pass (next step: Hirakud) | — |
| Installation and O&M | Timing against floods and storms | Work window and schedule from 29 years of flows and 46 years of storm tracks | {wwin}; {CMP.get('deployment', {}).get('crew_days', 0):.0f} crew-days |
"""
if LIVE and LIVECFG:
    _short = lambda t, k=150: t if len(t) <= k else t[:k].rsplit(" ", 1)[0] + " …"  # noqa: E731
    _lf = LIVECFG["level_flows_m3s"]
    _pk = LIVE["peak"]
    _mf = LIVE.get("model_forecast", {}).get("naraj_m3s", {})
    _off = LIVE.get("official_alerts", [])
    sec9 += f"""
### 9.7 The live warning service

The bulletin tool of §9.2 needs someone to type a flow. The live service (`live/`) reads the forecasts itself, every
time it runs, from sources that need no login, each a plugin that fails soft (`live/sources.py`):

| Plugin | Source | What it gives |
|---|---|---|
| glofas | GloFAS v4 through the Open-Meteo flood API | the Naraj flow 30 days ahead: control run and 50 ensemble members; the upstream gauges |
| rain | ECMWF IFS 0.25° through the Open-Meteo forecast API | daily rain over the delta and over the catchment, 16 days ahead |
| sachet | NDMA SACHET CAP feed of the state | official IMD, CWC and SDMA alerts, matched to the basin's districts |
| cwc | CWC flood-forecasting portal | stations now above warning level (answers from Indian networks) |
| sentinel1 | Planetary Computer catalogue | the latest radar pass over the basin, to map the flood actually there |

For each of the 51 runs and each day the flow measure the atlas uses (the 3-day peak at Naraj) is looked up in the
flow–impact table that `mahanadi/impact_curve.py` sweeps once from the trigger map: flooded land, people on it, villages
with 10 % of their people on flooded land, people cut off from every hospital, and per village the flow at which that
happens (the sweep reproduces the design-flood numbers of §7 exactly). The warning level is set by impact, as in
impact-based forecasting: "Be aware" from 5,000 people on flooded land or three villages ({n(_lf.get('1'))} m³/s at Naraj),
"Be prepared" from 10,000 people or the first village cut off from every hospital ({n(_lf.get('2'))} m³/s), "Act now" from
25,000 people or 20,000 cut off ({n(_lf.get('3'))} m³/s), each with the share of the 51 runs that reach it. Villages,
hospital cut-offs, roads and health facilities count beyond the ordinary monsoon: what is already wet or cut at the flow
exceeded on a quarter of monsoon days ({n(LIVECFG.get('baseline_m3s'))} m³/s at Naraj) belongs to the season, not to a
flood. A few river-bank hamlets get wet every monsoon, and on the Brahmani a road without a mapped bridge cuts six
villages off at almost any monsoon flow: a road to raise, not a warning. The output
is a bulletin naming each village with the first day it is expected (median run) or possible (wettest runs), the
villages that lose their hospital, the roads that close and the health facilities at risk; a CAP 1.2 alert (status
"Exercise") from "Be aware" upwards; an Atom index of the alerts, the way CAP feeds are published, for the Rakshak
Control Centre to subscribe to; and a status board. A run takes about 15 seconds on a laptop; on the lab server
`server/run_live.sh` is ready to run every morning from one cron line (README).

The run of {LIVE['issued'][:16].replace('T', ' ')} IST: Naraj {n(LIVE['today_m3s'])} m³/s, peaking near {n(_pk['median_m3s'])} m³/s
on {_pk['date']} (wettest runs {n(_pk['p90_m3s'])}), level "{LIVE['level_name']}"{"; the upstream-gauge model of §6.7 gave " + ", ".join(f"{d} {n(q)}" for d, q in _mf.items()) + " m³/s for the next three days" if _mf else ""}. The state feed carried
{LIVE.get('official_alerts_total', 0)} official alerts{", among them: " + "; ".join(_short(a.get('headline') or a['title']) for a in _off[:2]) if _off else ""}.
"""
    _lrows = []
    for k_, c_ in [("mahanadi", LIVECFG)] + [(k, v["CFG"]) for k, v in BAS.items()]:
        s_ = J(ROOT, "live", "out", k_, "status.json")
        if not (c_ and s_):
            continue
        l_ = c_["level_flows_m3s"]
        _lrows.append(f"| {c_['name']} | {c_['gauge_name']} ({PNAME.get(c_['predictor'], c_['predictor'])}) | {n(c_['baseline_m3s'])} | {n(l_.get('1'))} | {n(l_.get('2'))} | "
                      f"{n(l_.get('3'))} | {n(s_['today_m3s'])} | {s_['level_name']} |")
    if len(_lrows) > 1:
        sec9 += f"""
Every basin of §6.8 runs in the same feed with its own tables and the same rule (`live/basins/<basin>.json`, written by
`live/make_basin_config.py`). The flows at which each level starts, and the run of {LIVE['issued'][:10]}:

| Basin | Gauge (flow measure) | Ordinary monsoon (m³/s) | Be aware from (m³/s) | Be prepared from | Act now from | Flow today | Level today |
|---|---|---|---|---|---|---|---|
{chr(10).join(_lrows)}

On the Brahmani the first village cut off from every hospital comes at the same flow as the first 5,000 people on
flooded land, so "Be aware" and "Be prepared" start together; on the Brahmaputra "Act now" starts near the 2-year flood
({n(BAS.get('brahmaputra', {}).get('AS', {}).get('gumbel', {}).get('return_period_m3s', {}).get('2', 0))} m³/s), as
it should on a river island that floods most years.
"""
    if REPLAY:
        _rpk, _rmf = REPLAY["peak"], REPLAY.get("model_forecast", {}).get("naraj_m3s", {})
        _rcut = [w for w in REPLAY.get("hospital_access_lost", []) if w["expected"]]
        _rv = [w for w in REPLAY["villages_to_warn"] if w["expected"]]
        _rrows = "\n".join(f"| {c['date']} | {n(c['flow_m3s'])} | {c['coverage']:.0%} | {n(c['expected_km2'])} | {n(c['observed_km2'])} |"
                            for c in REPLAY.get("radar_check", []))
        sec9 += f"""
**Replay of the largest flood of the radar era.** `python live/run_live.py --replay {REPLAY['issued'][:10]}` runs the
feed as it would have run on the morning of {REPLAY['issued'][:10]}, with the flows that came as a perfect forecast:
level "{REPLAY['level_name']}" for a Naraj peak of {n(_rpk['median_m3s'])} m³/s on {_rpk['date']}, {len(_rv)} villages named with
the day the water reaches them, and {len(_rcut)} villages that lose road access to every hospital{f" from {_rcut[0]['expected']}" if _rcut else ""}.
{"The upstream-gauge model of §6.7, trained without 2022, forecast " + ", ".join(f"{n(q)} m³/s for {d}" for d, q in _rmf.items()) + ": lower than the flows that came (a steep rise is the hardest case), but already above the 'Act now' flow three days ahead." if _rmf else ""}
The radar passes of the following days, against the flooded land the bulletin expected at their flow:

| Radar pass | Naraj flow (m³/s) | Box imaged | Flooded land expected (km²) | Seen by radar (km²) |
|---|---|---|---|---|
{_rrows}

More land was under water on the first pass, after 177 mm of rain in a week, than at the river crest two days later,
when the rain water had drained: the flow-only map is too small before the crest and too large after it. This is the
case for the rain-aware model of §6.6 in the feed, and for mapping each new radar pass as soon as it arrives.
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
    adopt_txt = ""
    if ADOPTED and CMPA:
        o_, w_ = CMPA["old"], CMPA["new"]
        PNAME = {"Q_same_day": "same-day flow", "Q_prev_day": "previous-day flow", "Q_max_3d": "3-day peak flow",
                 "Q_max_5d": "5-day peak flow", "Q_max_7d": "7-day peak flow"}
        _lead_up = (w_['hf_iou'] - w_['hf_clim_iou']) > (o_['hf_iou'] - o_['hf_clim_iou'])
        _vill_up = w_['sett_hf_pod'] > o_['sett_hf_pod'] and w_['sett_hf_far'] < o_['sett_hf_far']
        lead_txt = (" while its lead over climatology and its village-level skill improve" if _lead_up and _vill_up else
                    " while its village-level skill improves" if _vill_up else
                    " while its lead over climatology grows" if _lead_up else "")
        adopt_txt = f"""The 20 m-trained pair is better on the atlas input, so the atlas was rebuilt with it (all 590 passes mapped again,
threshold {R20N['threshold']:.2f}); every Mahanadi result in this report comes from the rebuilt atlas. The independent
Sentinel-2 check decided it:

| Atlas built with | Sentinel-2, all water: IoU (precision / recall) | Sentinel-2, flood water: IoU (precision / recall) | Held-out high flow: trigger map vs climatology (IoU) | Villages at high flow: POD / FAR | Land flooded at least once (km²) |
|---|---|---|---|---|---|
| 10 m-trained pair (threshold {R20['threshold']:.2f}) | {o_['s2_all_iou']:.3f} ({o_['s2_all_precision']:.2f} / {o_['s2_all_recall']:.2f}) | {o_['s2_flood_iou']:.3f} ({o_['s2_flood_precision']:.2f} / {o_['s2_flood_recall']:.2f}) | {o_['hf_iou']:.3f} vs {o_['hf_clim_iou']:.3f} | {o_['sett_hf_pod']:.0%} / {o_['sett_hf_far']:.0%} | {n(o_['ever_km2'])} |
| 20 m-trained pair (threshold {R20N['threshold']:.2f}) | {w_['s2_all_iou']:.3f} ({w_['s2_all_precision']:.2f} / {w_['s2_all_recall']:.2f}) | {w_['s2_flood_iou']:.3f} ({w_['s2_flood_precision']:.2f} / {w_['s2_flood_recall']:.2f}) | {w_['hf_iou']:.3f} vs {w_['hf_clim_iou']:.3f} | {w_['sett_hf_pod']:.0%} / {w_['sett_hf_far']:.0%} | {n(w_['ever_km2'])} |

The Sentinel-2 check is the like-for-like comparison, because the optical reference is the same for both atlases: the
rebuilt atlas agrees better on all water and on flood water, mainly because it reports less false water (higher
precision). The held-out scores are not like for like, because each atlas is scored against its own observed maps.
The rebuilt atlas sees more flooded land, much of it rain-fed (the flooded share of a pass follows the 7-day rain with
rank correlation {w_['rain_spearman']:.2f}, against {o_['rain_spearman']:.2f} before), which the river flow alone predicts
less well, so the trigger map's pixel score falls{lead_txt}. The flow
predictor is chosen by rank correlation and moved from the {PNAME.get(o_.get('predictor', 'Q_max_5d'), 'old peak')} to the
{PNAME.get(AS['predictor'], AS['predictor'])} (rank correlation {AS['predictor_spearman'][AS['predictor']]:.3f} against {AS['predictor_spearman'].get(o_.get('predictor', ''), 0):.3f}, practically a tie), so
{w_['hf_passes']} rather than {o_['hf_passes']} passes count as high flow. The earlier atlas is kept in
`results/archive_atlas_10m/`."""
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

{adopt_txt if ADOPTED else "The 20 m-trained pair is better on the atlas input and can replace the current models in the next atlas run (re-inference of the 590 passes takes about an hour)." if R20N['mean']['avg20'] - R20['mean']['avg20'] >= 0.005 else "Training at 20 m gives no clear gain on the atlas input, so the atlas keeps the 10 m-trained models."}
"""
    SEEDS = J(AN, "radar20m_seeds.json")
    if SEEDS:
        srows = "\n".join(f"| {s_} | {SEEDS['10m'][s_]['avg20']:.3f} | {SEEDS['10m'][s_]['cal']:.3f} | {SEEDS['20m'][s_]['avg20']:.3f} | "
                          f"{SEEDS['20m'][s_]['cal']:.3f} |" for s_ in sorted(SEEDS["10m"]))
        sm = SEEDS["summary"]
        appendix += f"""
**Three seeds.** Seeds 1 and 2 of both radar models were trained at 10 m and at 20 m (`server/run_r20_seeds.sh`) and each
pair scored the same way; the threshold is chosen on validation for every pair.

| Seed | 10 m-trained pair, 20 m input | same, threshold from validation | 20 m-trained pair, 20 m input | same, threshold from validation |
|---|---|---|---|---|
{srows}
| Mean ± sd | {sm['10m']['avg20_mean']:.3f} ± {sm['10m']['avg20_sd']:.3f} | {sm['10m']['cal_mean']:.3f} ± {sm['10m']['cal_sd']:.3f} | {sm['20m']['avg20_mean']:.3f} ± {sm['20m']['avg20_sd']:.3f} | {sm['20m']['cal_mean']:.3f} ± {sm['20m']['cal_sd']:.3f} |

{"Training at 20 m wins on every seed, by " + format(sm['gain_cal_mean'], '.3f') + " IoU on average with the threshold from validation: the gain is well outside the seed-to-seed spread." if sm['wins_all'] else "The gain is not consistent across seeds (" + format(sm['gain_cal_mean'], '+.3f') + " IoU on average), so it is within the seed-to-seed spread."}
"""
    open(os.path.join(SEC, "11_appendix.md"), "w", encoding="utf-8").write(appendix)

# ------------------------------------------------------------------ 10 discussion and conclusions
CONC_NEW = ""
HYDRO_NEW = (f" A gradient-boosted model forecasts the Naraj flow one to three days ahead (Nash–Sutcliffe efficiency "
             f"{FC['skill']['lead_1d']['boosted']['nse']:.2f}–{FC['skill']['lead_3d']['boosted']['nse']:.2f} on unseen monsoons), and a "
             "live feed turns each day's GloFAS ensemble into impact-based warnings published as CAP alerts.") if FC else ""
_c = 8
_lo, _hi = sorted((V['ranking_auc']['high_flow_passes']['model'], V['ranking_auc']['all_passes']['model']))
_auc_rng = f"{_lo:.2f}" if f"{_lo:.2f}" == f"{_hi:.2f}" else f"{_lo:.2f}–{_hi:.2f}"
if FC:
    CONC_NEW += (f"{_c}. The Naraj flow can be forecast one to three days ahead from today's upstream flows and catchment rain"
                 f" (efficiency {FC['skill']['lead_3d']['boosted']['nse']:.2f} three days ahead against"
                 f" {FC['skill']['lead_3d']['persistence']['nse']:.2f} for persistence), and a live feed turns each day's"
                 " GloFAS ensemble into an impact-based warning, a CAP alert and a list of villages and roads with dates.\n")
    _c += 1
if BAS:
    CONC_NEW += (f"{_c}. The pipeline is not specific to the Mahanadi: the " + " and the ".join(v["CFG"].get("name", k) for k, v in BAS.items())
                 + " were mapped from every radar pass since 2017 with the same models and joined the live feed.\n")
    _c += 1
if RISK:
    CONC_NEW += (f"{_c}. Flood damage to houses and paddy is at least ₹{RISK['expected_annual_damage_rs_crore']['total_rs_crore']:.0f} crore a year;"
                 f" raising the ten critical roads repays its cost about {RISK['road_raising']['benefit_cost_ratio']:.0f} times in"
                 " hospital access alone, so it is the first protection measure to fund.\n")

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
  floods. Past flood frequency ranks where land floods best (ROC AUC {V['ranking_auc']['high_flow_passes']['clim']:.2f}–{V['ranking_auc']['all_passes']['clim']:.2f});
  the trigger map adds at which flow it floods (AUC {_auc_rng}), so the two are used together.
- Flood depth comes from a 30 m surface model (~2 m vertical error); wall screening, scour and foundation numbers
  use typical parameters (masonry tension, bed size, soil strength) and an unknown flow split between distributaries,
  all of which the field visit and the lab replace.
- The money figures use a continental depth–damage curve, the public housing grant as the value of a house, an
  assumed 4.4 people per household and a simple paddy-loss rule; they are lower bounds to be checked against the
  losses people report (§8.7).
- The live warning levels are proposed thresholds; GloFAS's own forecast skill at Naraj and the flow forecast of §6.7
  have not been checked against measured flows.

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
   read the river forecast together with the rainfall forecast. A learned model that adds rain and each pixel's flood
   history to the flow maps held-out heavy-rain passes better than the trigger map
   ({_LF['pixel_iou']['heavy_rain_passes']['learned']['iou']:.2f} vs {_LF['pixel_iou']['heavy_rain_passes']['trigger']['iou']:.2f}).
6. The same scenarios give each specialization its answer: who loses the road to a hospital or shelter
   (transportation), where walls crack and how deep scour reaches (structural), which banks to inspect and which dry
   houses sit on soaked ground (geotechnical), how storms add to floods (ocean), when and at what earthwork the
   critical links can be raised (construction management), and where a flood peak comes from: about half from
   Hirakud dam and half from the tributaries below it (water resources).
7. Every one of the 92 training runs was re-checked from its saved outputs and the published TerraMind scores were
   reproduced within a point, so the benchmark can be relied on.
{CONC_NEW}{_c}. The field visit is designed to measure what these numbers depend on and to change them where they are wrong.
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
protocol (U-Net {u('lio/unet/full/default'):.3f}, best foundation model {u('lio/prithvi/full/default'):.3f}, fusion
{u('lio/enstop3_mean/full/default'):.3f} IoU on an unseen Indian flood), build a radar-only flood atlas of the
Mahanadi delta from {AS['n_passes']} Sentinel-1 passes ({AS['years'][0]}–{AS['years'][-1]}), and link it to river
discharge at Naraj through a per-pixel trigger discharge. On held-out years the resulting flow-to-flood maps reach IoU
{HF['model']['iou']:.2f} at high flows against {HF['climatology']['iou']:.2f} for flood climatology. Combined with road
networks and population, they identify the people cut off from hospitals, critical road links and river banks for
inspection, giving point-forecast early-warning systems the spatial impact layer they lack.{HYDRO_NEW}
"""
open(os.path.join(SEC, "10_discussion.md"), "w", encoding="utf-8").write(sec10)
print("written 00_front, 06_mahanadi, 07_impacts, 09_implementation, 10_discussion")
