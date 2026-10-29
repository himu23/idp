# Slide content for build_slides.py (executed inside it: prs, slide, text, picture, table, get, iou, S, A, ROOT exist).
# Story for the final review: real problem -> model selection (benchmark) -> Mahanadi atlas -> engineering impacts
# (transport, structures, geotechnical) -> deployment for ClimMaTech -> field visit -> conclusions.
import pandas as pd

FIG = os.path.join(A, "figures")
AT, IM, AF = (os.path.join(ROOT, "results", d) for d in ("atlas", "impact", "atlas_figures"))
FMS = ["prithvi", "terramind", "dofa", "clay", "satlas", "decur"]
lab = {s["model"]: s["label"] for s in S}
best_fm_lio = max([get("lio", m) for m in FMS if get("lio", m)], key=lambda s: s["test_iou"])
unet_l = get("lio", "unet")
AS = json.load(open(os.path.join(AT, "atlas_summary.json")))
R20 = json.load(open(os.path.join(A, "radar20m.json")))
EX = pd.read_csv(os.path.join(IM, "exposure_scenarios.csv")).set_index("scenario")
TR = pd.read_csv(os.path.join(IM, "transport_scenarios.csv")).set_index("scenario")
SIT = json.load(open(os.path.join(IM, "siting_summary.json")))
SENS = pd.read_csv(os.path.join(IM, "sensor_sites.csv"))
GEO = pd.read_csv(os.path.join(IM, "geotech_top20.csv"))
TT = json.load(open(os.path.join(IM, "travel_time.json")))
S2C = json.load(open(os.path.join(IM, "s2_crosscheck.json"))) if os.path.exists(os.path.join(IM, "s2_crosscheck.json")) else None
RP = {int(k): v for k, v in AS["gumbel"]["return_period_m3s"].items()}


def JI(f):
    p_ = os.path.join(IM, f)
    return json.load(open(p_)) if os.path.exists(p_) else {}


DEP, STR, GRD, OCN, CMP = (JI(f) for f in ("depth_summary.json", "structures_summary.json", "ground_summary.json",
                                           "ocean_summary.json", "cm_plan.json"))
RH = int(AS.get("heavy_rain_scenario", {}).get("rain_mm", 171))
RB = {r_: JI(os.path.join("bulletins", f"bulletin_{round(RP[5])}_rain{r_}.json")) for r_ in (20, RH)}
_M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_ix = sorted(_M.index(m) for m in CMP.get("work_window_months", []))
_blocks = [(i, next(j for j in range(i, i + 12) if (j + 1) % 12 not in _ix or (j + 1) % 12 == i) % 12) for i in _ix if (i - 1) % 12 not in _ix]
WWIN = ", ".join(_M[a] if a == b else f"{_M[a]}–{_M[b]}" for a, b in _blocks) or "–"
V = AS["validation"]
OBS = [k for k in EX.index if k.startswith("observed_")][0]


def n(x):
    return f"{x:,.0f}"


# 1 title
s = prs.slides.add_slide(BLANK)
text(s, 0.8, 1.6, 11.8, 1.2, ["Prithvi Flood-IN"], size=44, bold_first=True)
text(s, 0.8, 2.7, 11.8, 1.6, ["From a river-flow forecast to who goes under water:",
                              "a satellite foundation model for the Mahanadi delta"], size=24, color=MUTED)
text(s, 0.8, 4.5, 11.8, 1.4, ["Nikhil Upadhyay (lead) · Prakhar Gupta · Prabhat Kumar · Vineet Jangir · Himanshu Shete",
                              "Guide: Prof. Basudev Biswal (IIT Bombay) · Industry: Dr. Vivek Gupta, Siddik Barbhuiya (ClimMaTech)",
                              "CE Integrated Design Project · final review · November 2026"], size=16, color=MUTED)

# 2 the problem in the field
s = slide("The problem in the field", "ClimMaTech forecasts the river at a point; nobody sees what that flow floods")
text(s, 0.6, 1.6, 6.3, 5.2, [
    "ClimMaTech: radar gauges on bridges and spillways, sirens, Aagah app; forecasts 30 min – 48 h ahead.",
    "Every product is a point: the level or flow at one gauge.",
    "Missing: which land, villages, roads, bridges and embankments go under water at that flow.",
    "Mahanadi delta below Naraj: 3,038 km² study box, 4.1 million people, floods in 2018, 2020, 2022…",
    "Prof. Biswal's Mahanadi basin work, Odisha WRD and CWC (Naraj gauge, barrages) all meet here."], size=16, bullet=True)
text(s, 7.2, 1.6, 5.6, 5.2, ["Refined problem statement",
                             "For the Mahanadi delta, turn a river-flow forecast at Naraj into a map of what floods and whom it "
                             "affects, using a satellite foundation model chosen by a fair benchmark, and use that map to plan "
                             "where warnings and sensors should go, checked and calibrated at the site."], size=17, bold_first=True)

# 3 stakeholders
s = slide("Who needs what", "The project is built around the people who would use it")
table(s, 0.6, 1.6, 12.1, [
    ["Stakeholder", "Needs from us", "We need from them"],
    ["ClimMaTech (CTO Dr. Vivek Gupta; Siddik)", "Flood-extent layer + village list per forecast; siren and sensor sites", "Siren range, data formats, site-survey practice"],
    ["Prof. Biswal's Mahanadi basin project", "Inundation and impacts for the delta", "Site access, introductions"],
    ["Odisha WRD, CWC Mahanadi division", "Which banks and roads fail at which flow", "Naraj discharge, embankment inventory, breach history"],
    ["OSDMA, Cuttack / Kendrapara / Jagatsinghpur", "Villages to warn, roads that close", "Evacuation records, shelters"],
    ["Villages and farmers", "Earlier, local warning", "What flooded, when, how deep"]], col_w=[3.8, 4.4, 3.9], size=13)

# 4 seven specializations
tr25_ = TR.loc["T25"] if "T25" in TR.index else TR.iloc[0]
s = slide("One flood, seven specializations", "Each specialization asks its own question of the same flood scenarios")
table(s, 0.5, 1.5, 12.3, [
    ["Specialization", "Question", "Headline (25-year flood)", "Field check"],
    ["Remote sensing", "Which model maps floods through cloud?", f"{AS['n_passes']} radar passes mapped; U-Net beats FMs on unseen flood", "40 random points"],
    ["Water resources", "Which flow floods which land; where does it come from?", f"Trigger map {V['high_flow_passes']['model']['iou']:.2f} vs {V['high_flow_passes']['climatology']['iou']:.2f} climatology; "
     f"~{JI('watershed_summary.json').get('median_share_hirakud_of_naraj_peak', 0.5):.0%} of a flood peak from Hirakud", "Discharge, Manning's n"],
    ["Transportation", "Who loses the road to a hospital?", f"{n(tr25_['hospital: people cut off'])} people cut off", "Road closures"],
    ["Structural", "Where do walls crack; how deep must piers go?", f"{n(STR.get('walls', {}).get('T25', {}).get('people_deeper_than_1m', 0))} people where depth >= 1 m", "HFL marks, foundations"],
    ["Geotechnical", "Which banks fail; which dry houses sit on soaked ground?", f"{n(GRD.get('scenarios', {}).get('T25', {}).get('people_in_zone', 0))} people in the 200 m advisory zone", "Soil samples, wells"],
    ["Ocean", "What do Bay of Bengal storms add?", f"{OCN.get('top20_flood_passes_driver_counts', {}).get('cyclone/depression', 0)} of 20 largest floods followed a storm", "Surge, tidal drainage"],
    ["Construction tech & mgmt", "When to build, what it costs?", f"Work window {WWIN}; {n(CMP.get('link_raising', {}).get('earthwork_m3', 0))} m³ to raise "
     f"{CMP.get('link_raising', {}).get('links_by_embankment', 10)} critical links", "Site sheets"]],
      col_w=[2.3, 3.8, 4.2, 2.0], size=12)

# 5 benchmark set-up
s = slide("Model selection: a fair benchmark", "Sen1Floods11 v1.1 · 446 hand-labelled chips · 13 optical bands + radar VV/VH · 11 flood events")
table(s, 0.6, 1.7, 7.6, [
    ["Protocol", "Train", "Test"],
    ["Official", "252 chips, 10 events (incl. India)", "90 chips, same events"],
    ["Leave-India-out", "212 chips, 9 events, no India", "all 68 Assam chips (unseen flood)"]], col_w=[2.0, 3.0, 2.6], size=13)
text(s, 0.6, 3.5, 7.6, 3.3, ["8 trainable models, one recipe: same decoder, CE + Dice, D4 augmentation, AdamW + cosine, 40 epochs",
                             "Foundation models: Prithvi-EO-2.0-300M, TerraMind-B, DOFA-B, Clay-v1-B, Satlas Swin-B, DeCUR ResNet-50",
                             "Baselines: simple CNN, U-Net; Otsu, NDWI, published Prithvi checkpoint",
                             "3 seeds each, frozen vs fine-tuned, fusion, radar vs optical, label efficiency: 92 runs"],
     size=14, bullet=True)
picture(s, os.path.join(FIG, "bars_official.png"), 8.4, 1.7, w=4.6)

# 6 headline benchmark
s = slide("Unseen Indian flood: U-Net beats every foundation model",
          f"Assam 2016, never in training · U-Net {iou('lio', 'unet')} · best FM {best_fm_lio['label']} "
          f"{iou('lio', best_fm_lio['model'])} · top-3 fusion {iou('lio', 'enstop3_mean')}")
picture(s, os.path.join(FIG, "bars_lio.png"), 0.5, 1.6, h=5.3)
text(s, 8.6, 1.7, 4.4, 5.2, [f"Every model loses 0.07–0.14 IoU when the flood is unseen (U-Net 0.840 → {unet_l['test_iou']:.3f})",
                             "Fine-tuning helps every FM on the unseen flood (+0.003 to +0.048)",
                             "Fusing FMs alone does not beat the best FM; U-Net + CNN + best FM does",
                             "21 labelled chips: U-Net 0.736 ≈ FMs with 212",
                             "Water is spectrally simple; ~250 chips suffice for a 7.8 M-parameter U-Net"], size=14, bullet=True)

# 7 radar vs optical, fusion
s = slide("Monsoon reality: radar only", "Optical is better when the sky is clear; on flood dates the delta was 61–95 % cloud")
picture(s, os.path.join(FIG, "modality_ablation.png"), 0.5, 1.6, w=6.4)
table(s, 7.2, 1.7, 5.7, [["Radar-only model (official test)", "IoU"],
                         ["U-Net, 10 m", f"{R20['unet']['native']:.3f}"],
                         ["TerraMind-B, 10 m", f"{R20['terramind']['native']:.3f}"],
                         ["Fusion (mean), 10 m", f"{R20['mean']['native']:.3f}"],
                         ["Fusion, 20 m input (atlas)", f"{R20['mean']['avg20']:.3f}"],
                         [f"Fusion, 20 m, threshold {R20['threshold']:.2f} (val.)", f"{R20['calibrated_test_iou']:.3f}"]],
      col_w=[4.4, 1.3], size=13)
text(s, 7.2, 4.4, 5.7, 2.4, ["TerraMind is the only FM that takes radar alone natively",
                             "Production model of the atlas = TerraMind-B + U-Net, radar only",
                             "20 m input costs ~0.02 IoU, cuts the download 4×"], size=14, bullet=True)

# 7b training audit
_aud = os.path.join(A, "audit_training.json")
AUDS = json.load(open(_aud)) if os.path.exists(_aud) else {}
if AUDS:
    om_ = AUDS["official_test_miou"]
    rd_ = AUDS["radar_db_percentiles_10_50_90"]
    s = slide("Checked, not assumed: the training audit", "scripts/audit_training.py re-checks all 92 runs from their stored outputs")
    table(s, 0.5, 1.5, 6.6, [
        ["Check", "Result"],
        ["Runs made with the queued arguments", f"{AUDS['n_checked']} of {AUDS['n_jobs']}"],
        ["Chips in two splits", "none"],
        ["India chips in leave-India-out training", "none"],
        ["Model selection on validation only", "every run"],
        ["Test IoU recomputed = stored", "every run"],
        ["Seed spread (sd of test IoU)", f"at most {max(v['sd'] for v in AUDS['seed_spread'].values() if v['n'] >= 3):.3f}"],
        ["Problems found", str(len(AUDS["problems"]))]], col_w=[4.4, 2.2], size=13)
    table(s, 7.4, 1.5, 5.4, [
        ["TerraMind-B on Sen1Floods11", "Ours, mIoU", "Paper"],
        ["Radar + optical", f"{om_['official_terramind_full_s0']['miou'] * 100:.1f}", "90.62"],
        ["Radar only", f"{om_['official_terramind_s1_full_s0']['miou'] * 100:.1f}", "80.39"]], col_w=[2.8, 1.3, 1.3], size=13)
    text(s, 7.4, 3.3, 5.4, 3.0, [
        "Published values: TerraMind paper (arXiv:2504.11171, PANGAEA protocol); ours are within one point",
        f"The delta's radar looks like the training radar: dry-land VV median {rd_['mahanadi_atlas_dry']['VV'][1]:.1f} dB "
        f"vs {rd_['sen1floods11_train_dry']['VV'][1]:.1f} dB; water 8-11 dB lower in both"], size=13, bullet=True)

# 8 atlas
s = slide("Mahanadi flood atlas 2017–2026",
          f"{AS['n_passes']} Sentinel-1 passes ({AS['n_monsoon']} monsoon, {AS['n_dry']} dry season) · 3 tracks · Sentinel-1A/B/D · 20 m")
picture(s, os.path.join(AF, "atlas_timeseries.png"), 0.4, 1.5, w=7.6)
picture(s, os.path.join(AF, "atlas_area_vs_discharge.png"), 8.7, 1.5, w=4.4)
text(s, 0.6, 5.85, 12.1, 1.1, [f"Flooded land follows the Naraj flow (Spearman ρ = {AS['predictor_spearman'][AS['predictor']]:.2f}, "
                              f"predictor: {AS['predictor'].replace('Q_max_', '').replace('d', '-day peak flow') if 'max' in AS['predictor'] else AS['predictor'].replace('_', ' ')}); river bed ({AS.get('river_bed_km2', 0):.0f} km²) and "
                              "normal water excluded; a 3 km swath-edge band removed per pass"], size=14, bullet=True)

# 9 trigger discharge
s = slide("From a flow forecast to a flood map", "Each 20 m pixel gets the Naraj flow at which it starts to flood")
picture(s, os.path.join(AF, "atlas_trigger_map.png"), 0.4, 1.5, w=8.0)
hf = V["high_flow_passes"]
text(s, 8.6, 1.5, 4.5, 3.2, [f"Years never seen in fitting, high flows (≥ {hf['q90_threshold_m3s']:,} m³/s): "
                             f"IoU {hf['model']['iou']:.2f} vs {hf['climatology']['iou']:.2f} for climatology",
                             (f"Per settlement (≥ 10 % of people flooded), high flows: POD {V['settlements']['high_flow_passes']['model']['POD']:.0%}, "
                              f"FAR {V['settlements']['high_flow_passes']['model']['FAR']:.0%} (climatology POD "
                              f"{V['settlements']['high_flow_passes']['climatology']['POD']:.0%})") if "settlements" in V else "",
                             f"Design floods (Gumbel): 2-yr {RP[2]:,.0f}, 25-yr {RP[25]:,.0f} m³/s",
                             (f"Same 5-yr flow: {RB[20]['flooded_land_km2']:.0f} km² flooded in a dry week, "
                              f"{RB[RH]['flooded_land_km2']:.0f} km² with {RH} mm of rain — read the rain forecast too") if all(RB.values()) else "",
                             (f"Where it floods is predictable from the past (AUC {V['ranking_auc']['all_passes']['clim']:.2f}); "
                              f"how much floods on a day only partly") if "ranking_auc" in V else "",
                             f"Hirakud → Naraj ≈ {TT['hirakud_below']['best_lag_days']} day"], size=13, bullet=True)
picture(s, os.path.join(AF, "atlas_loyo.png"), 8.6, 4.6, w=4.5)

# 9b learned flow + rain + history model
_lrn = os.path.join(AT, "learned", "learned_summary.json")
LRNS = json.load(open(_lrn)) if os.path.exists(_lrn) else {}
if LRNS:
    li_, ls_, la_ = LRNS["pixel_iou"], LRNS["settlements"], LRNS.get("ranking_auc", {})
    s = slide("A learned flow + rain + history model", "Gradient boosting per pixel and pass; each year predicted from the other years")
    table(s, 0.5, 1.5, 7.6, [
        ["Held-out passes, IoU", "Learned", "Trigger map", "Climatology"],
        *[[f"{lab_} ({li_[k]['n']})", f"{li_[k]['learned']['iou']:.2f}", f"{li_[k]['trigger']['iou']:.2f}", f"{li_[k]['climatology']['iou']:.2f}"]
          for k, lab_ in (("all_passes", "All monsoon"), ("high_flow_passes", "High flow"), ("heavy_rain_passes", "Heavy rain"))],
        ["Villages, high flow: POD / FAR", f"{ls_['high_flow_passes']['learned']['POD']:.0%} / {ls_['high_flow_passes']['learned']['FAR']:.0%}",
         f"{ls_['high_flow_passes']['trigger']['POD']:.0%} / {ls_['high_flow_passes']['trigger']['FAR']:.0%}",
         f"{ls_['high_flow_passes']['climatology']['POD']:.0%} / {ls_['high_flow_passes']['climatology']['FAR']:.0%}"],
        ["Ranking AUC, all passes", f"{la_.get('all_passes', {}).get('learned', 0):.2f}", f"{la_.get('all_passes', {}).get('trigger', 0):.2f}",
         f"{la_.get('all_passes', {}).get('climatology', 0):.2f}"]], col_w=[3.1, 1.5, 1.5, 1.5], size=13)
    sc_ = LRNS.get("scenarios_all_years_model", {})
    imp_ = list(LRNS.get("permutation_importance_auc_drop", {}).items())[:4]
    text(s, 8.5, 1.5, 4.4, 5.2, [
        "Inputs: flow and 7-day rain of the pass, month, radar track; per pixel the training years' trigger flow, "
        "flood frequency (all, high flow, heavy rain), height above and distance to the river bed",
        "Leans most on: " + ", ".join({"freq_all": "flood frequency", "flow_q_max_5d": "Naraj flow", "rain_7d_mm": "7-day rain",
                                       "month": "month", "elevation_m": "elevation", "track": "radar track"}.get(k, k.replace("_", " "))
                                      for k, _ in imp_),
        f"5-year flow: {sc_.get('T5 dry week', {}).get('flood_km2', 0):.0f} km² in a dry week, "
        f"{sc_.get('T5 heavy rain', {}).get('flood_km2', 0):.0f} km² with heavy rain: one model for the river forecast plus a rain gauge"],
         size=13, bullet=True)

# 10 exposure table
s = slide("What floods: people, farmland, roads, hospitals", "Per design flood; land outside the river bed and normal water")
rows = [["Scenario", "Naraj flow (m³/s)", "Flooded land (km²)", "People", "Cropland (km²)", "Road km", "Health fac.", "Cut off from hospital"]]
for k in [f"T{t}" for t in (2, 5, 10, 25, 100)] + [OBS]:
    if k in EX.index:
        e, t = EX.loc[k], TR.loc[k] if k in TR.index else None
        rows.append([k.replace("T", "") + "-yr" if k.startswith("T") else ("5-yr + heavy rain" if k == "rain_T5" else "largest seen " + k[9:13]),
                     n(RP[int(k[1:])]) if k.startswith("T") else (n(RP[5]) if k == "rain_T5" else "—"), f"{e['flood_km2']:.0f}", n(e["people"]),
                     f"{e['cropland km2']:.0f}", f"{e['road km (all)']:.0f}", int(e["health facilities"]),
                     n(t["hospital: people cut off"]) if t is not None else "—"])
table(s, 0.6, 1.6, 12.1, rows, col_w=[1.7, 1.6, 1.6, 1.4, 1.5, 1.2, 1.3, 1.8], size=13)
text(s, 0.6, 4.6, 12.1, 2.2, ["People: GHSL 2020; roads, bridges, hospitals, schools: OpenStreetMap",
                              "Flows above the largest in the 2017–2026 radar record give lower-bound maps",
                              "Mapped building footprints are incomplete here (~120 k for 4.1 M people), so people, not buildings, are counted"],
     size=14, bullet=True)

# 11 transport
t25 = TR.loc["T25"] if "T25" in TR.index else TR.iloc[0]
s = slide("Transportation: who is cut off from a hospital",
          f"Road graph of {n(json.load(open(os.path.join(IM, 'transport_summary.json')))['road_km'])} km; a road is cut when ≥ 20 m is under water")
picture(s, os.path.join(AF, "impact_T25_map.png"), 0.4, 1.5, w=8.0)
text(s, 8.6, 1.6, 4.4, 5.3, [f"25-year flood: {n(t25['hospital: people cut off'])} people in {int(t25['hospital: settlements cut off'])} "
                             f"settlements lose road access to any hospital or clinic",
                             f"{n(t25['hospital: people with trip +5 min or more'])} more reach one only by a detour "
                             f"(median +{t25['hospital: median extra minutes (still reachable, delayed)']} min)",
                             f"{n(t25.get('shelter: people with no reachable dry school', 0))} people can reach no dry school (relief camp); "
                             f"{n(t25.get('town: extra person-hours of travel per day', 0))} extra person-hours of travel a day",
                             "Critical links = flooded roads that carry most people's hospital route (circled)",
                             "Field: confirm closures with locals and PWD at the 10 critical links"], size=14, bullet=True)

# 12 geotech
s = slide("Geotechnical: which river banks to inspect first", "1 km cells along the main channels")
picture(s, os.path.join(AF, "geotech_map.png"), 0.4, 1.5, w=8.0)
top = GEO.head(5)
text(s, 8.6, 1.6, 4.4, 5.3, ["Priority = water behind the bank (frequency, years) + erodibility + people within 2 km",
                             "SoilGrids is too coarse to separate banks (all clay loam here) → field samples decide",
                             "Lab plan: wet sieve + Atterberg (IS 2720) → IS 1498 class, Kenney–Lau stability, piping flag",
                             "Top cell: " + f"{top.iloc[0]['lat']:.3f} N, {top.iloc[0]['lon']:.3f} E, water behind the bank in "
                             f"{top.iloc[0]['behind_freq']:.0%} of passes, {int(top.iloc[0]['years_flooded'])} years"], size=14, bullet=True)

# 12b structural
w_ = STR.get("walls", {})
s = slide("Structural: walls crack at about a metre, piers must go deep", "Flood depth from the flood-edge elevation; IRC:78 Lacey scour")
picture(s, os.path.join(AF, "depth_T25_map.png"), 0.4, 1.5, w=7.6)
picture(s, os.path.join(AF, "bridge_scour.png"), 8.2, 4.2, w=4.9)
text(s, 8.2, 1.5, 4.9, 2.7, [f"Hydrostatic moment > out-of-plane capacity: a 230 mm brick wall cracks at {w_.get('critical_depth_m', {}).get('230 mm wall, f_t 0.1 MPa', 0):.1f}-"
                             f"{w_.get('critical_depth_m', {}).get('230 mm wall, f_t 0.2 MPa', 0):.1f} m of water",
                             f"{n(w_.get('T25', {}).get('people_deeper_than_1m', 0))} people live where the 25-yr flood is >= 1 m deep",
                             f"Pier scour {STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[0]:.0f}-"
                             f"{STR.get('bridges', {}).get('pier_scour_T100_share25_range_m', [0, 0])[1]:.0f} m below HFL at a quarter of the 100-yr flow "
                             f"(branch split asked from WRD)"],
     size=13, bullet=True)

# 12c ground saturation
fe_ = GRD.get("foundation_example", {})
s = slide("Geotechnical: dry houses on soaked ground", "Within 200 m of flood water on silty clay: bearing capacity drops, then the clay settles")
picture(s, os.path.join(AF, "ground_advisory_map.png"), 0.4, 1.5, w=8.0)
text(s, 8.6, 1.6, 4.4, 5.3, [f"{n(GRD.get('scenarios', {}).get('T25', {}).get('people_in_zone', 0))} people in the advisory zone of the 25-yr flood; "
                             f"{GRD.get('scenarios', {}).get('T25', {}).get('advisory_settlements', 0)} settlements advised to check foundations",
                             f"Footing on silty sand: bearing capacity -{fe_.get('silty_sand_drained', {}).get('reduction_pct', 0)} % with water at the surface",
                             f"Soaked clay: -{fe_.get('clay_loam_undrained', {}).get('reduction_pct', 0)} %; drawdown settlement "
                             + " to ".join(f"{v:.0f}" for v in fe_.get('drawdown_settlement_mm', {}).values()) + " mm",
                             "Field: well levels at 0-500 m from the flood edge fix the 200 m"], size=14, bullet=True)

# 12d ocean
cnt_ = OCN.get("top20_flood_passes_driver_counts", {})
s = slide("Ocean: Bay of Bengal storms and the largest floods", "IBTrACS tracks matched to the radar atlas")
picture(s, os.path.join(AF, "flood_drivers.png"), 1.2, 1.45, h=4.25)
text(s, 0.6, 5.85, 12.1, 1.1, [f"{OCN.get('systems_within_300km_since_2016', 0)} storms and depressions within 300 km since 2016 · of the 20 largest floods: "
                              f"{cnt_.get('river', 0)} high river, {cnt_.get('rain', 0)} heavy rain, {cnt_.get('cyclone/depression', 0)} after a storm",
                              "Surge and high tide hold back the drainage of the lower delta: a Paradip tide record is the next dataset"], size=14, bullet=True)

# 12e construction management
lr_ = CMP.get("link_raising", {})
s = slide("Construction management: when to build, what it costs", "42 years of flows and storm tracks; earthwork take-off for the critical links")
picture(s, os.path.join(AF, "construction_windows.png"), 0.4, 1.5, w=8.2)
picture(s, os.path.join(AF, "gantt.png"), 0.4, 4.3, w=7.6)
text(s, 8.8, 1.6, 4.2, 5.3, [f"Work window: {WWIN} (no flood days, few storms)",
                             f"Raising {lr_.get('links_by_embankment', 10)} critical links above the 25-yr flood + 0.6 m: "
                             f"{n(lr_.get('earthwork_m3', 0))} m³, about Rs {lr_.get('cost_crore_rs_at_350_per_m3', 0):.1f} crore (assumed Rs 350/m³)",
                             *([f"{'Link' if len(lr_['links_needing_structure']) == 1 else 'Links'} "
                                f"{' and '.join(str(x['rank']) for x in lr_['links_needing_structure'])} would need "
                                f"{' and '.join(format(x['raise_m'], '.1f') for x in lr_['links_needing_structure'])} m: "
                                "a bridge or vented causeway, depth checked on site"]
                               if lr_.get("links_needing_structure") else []),
                             f"Each link carries the hospital route of {n(lr_.get('people_routed_per_link', [0, 0])[0])}–"
                             f"{n(lr_.get('people_routed_per_link', [0, 0])[1])} people",
                             f"Deployment: 40 sirens cover {SIT['coverage']['1500']['share']:.0%} of exposed people at 1.5 km, "
                             f"{CMP.get('deployment', {}).get('sensor_sites', '-')} river sensors, {CMP.get('deployment', {}).get('crew_days', 0):.0f} crew-days"],
     size=13, bullet=True)

# 13 deployment
s = slide("Deployment plan for a ClimMaTech-type system", "Sirens where exposed people live; one river sensor per distributary")
picture(s, os.path.join(AF, "siting_map.png"), 0.4, 1.5, w=8.0)
cov = SIT["coverage"]
text(s, 8.6, 1.6, 4.4, 5.3, [f"Exposed people (25-yr flood or ≥ 10 % frequency): {n(SIT['exposed_people'])}",
                             f"40 sirens cover {cov['1000']['share']:.0%} / {cov['1500']['share']:.0%} / {cov['2000']['share']:.0%} "
                             "at 1.0 / 1.5 / 2.0 km audible range",
                             f"River sensors on {len(SENS)} bridges: " + ", ".join(SENS.river.astype(str).tolist()),
                             "Approach roads checked dry in the 25-year flood (reachable during floods)",
                             "Field: mobile signal, mounting, access → final list"], size=14, bullet=True)

# 14 implementation: bulletin
s = slide("Implementation: forecast → bulletin in seconds", "mahanadi/forecast_to_impact.py · interactive viewer dashboard/index.html")
bul = os.path.join(IM, "bulletins")
txt = sorted([f for f in os.listdir(bul) if f.endswith(".txt")]) if os.path.isdir(bul) else []
lines = open(os.path.join(bul, txt[0]), encoding="utf-8").read().splitlines()[:11] if txt else ["(run forecast_to_impact.py)"]
text(s, 0.6, 1.6, 7.4, 5.3, lines, size=11, color=INK)
text(s, 8.3, 1.6, 4.6, 5.3, ["Input: forecast flow at Naraj (m³/s or lakh cusec), e.g. from ClimMaTech or CWC",
                             "Output: flood GeoTIFF, settlements GeoJSON (for Rakshak Control Centre / Aagah), text bulletin",
                             "Viewer: pick a design flood → flooded land, cut roads, villages, sirens, sensors",
                             "Fills the map layer ('River View') that ClimMaTech's architecture lists for flood risk"], size=14, bullet=True)

# 14b what this adds to ClimMaTech
_b25 = JI(os.path.join("bulletins", f"bulletin_{round(RP[25])}.json"))
s = slide("What ClimMaTech's system lacks, and what we add", "From all 50 pages of climmatech.com; every row has a number behind it")
table(s, 0.4, 1.4, 12.5, [
    ["Their service", "Gap", "What we add (evidence)"],
    ["River View map layer", "No flood extent behind it", f"Flood frequency, trigger flow and impact layers ({AS['n_passes']} passes; IoU {V['high_flow_passes']['model']['iou']:.2f} vs {V['high_flow_passes']['climatology']['iou']:.2f})"],
    ["AI forecast, 30 min-48 h", "A level is not a list of villages", f"Forecast-to-bulletin: 25-yr flow -> {EX.loc['T25']['flood_km2']:.0f} km², {n(EX.loc['T25']['people'])} people, {_b25.get('settlements_to_warn', 0)} settlements"],
    ["Research group reconstructions", "Width by hand; optical 75-79 % cloud", "Benchmarked radar model maps every Sentinel-1 pass through cloud, ~5 s per pass"],
    ["Solution pages", "Illustrative site layouts", f"Data-backed siting: 40 sirens reach {SIT['coverage']['1500']['share']:.0%} of exposed people; {len(SENS)} sensor bridges"],
    ["Pravaah discharge", "Needs section + velocity factor", "Field protocols B and C measure both, plus Manning's n"],
    ["Varshaq rain gauge", "Rain not linked to flooded land", "Rain-aware maps: analogs and the learned flow + rain model"],
    ["Rakshak Control Centre", "Alert areas drawn by hand", "CAP 1.2 alert per forecast, one area per settlement to warn"]],
      col_w=[2.9, 3.3, 6.3], size=12)

# 15 field visit
s = slide("Field visit: measure what the models cannot know", "Every measurement has a script and changes a number in the report")
table(s, 0.6, 1.6, 12.1, [
    ["At the site", "Feeds", "What it can change"],
    ["40 random ground-truth points, flood marks, villagers' years", "field_validate_map.py", "Atlas accuracy (POD / FAR / CSI) for ClimMaTech"],
    ["Cross-section + floats + slope at a bridge", "discharge_velocity_area.py", "GloFAS check; Manning's n for the PINN (now 0.015 assumed)"],
    ["Bridge deck, HFL marks, scour, closures", "bridge_clearance.py", "IRC:5 clearance; critical-link ranking"],
    ["Bank inspection + soil samples → IITB lab", "soil_gradation.py", "Bank inspection ranking (replaces SoilGrids)"],
    ["Siren / sensor site sheets", "sensor_site_assessment.csv", "Final deployment list"],
    ["Interviews: WRD, CWC, ClimMaTech, villages", "interviews.csv", "Problem statement; 'which flow floods which village'"]],
      col_w=[4.6, 2.9, 4.6], size=13)
text(s, 0.6, 5.6, 12.1, 1.2, ["GPS check points (GPX / KML), printed dossier, protocols, safety rules: fieldkit/"], size=14, bullet=True)

# 16 S2 check + PINN
s = slide("Checks of our own numbers", "Independent sensor in the delta; physics track")
lines = []
if S2C:
    a_ = S2C.get("all/all_months", {})
    m_ = S2C.get("outside_normal/monsoon_Jun_Nov", {})
    lines = [f"Sentinel-2 within ±1 day, clear pixels: {S2C['pairs']} pairs",
             f"Radar atlas vs optical water, all water: IoU {a_.get('iou', 0):.2f} (precision {a_.get('precision', 0):.2f}, recall {a_.get('recall', 0):.2f})",
             f"Outside normal water, Jun–Nov: IoU {m_.get('iou', 0):.2f} over {m_.get('pairs', 0)} pairs"]
text(s, 0.6, 1.6, 6.0, 5.2, (lines or ["Sentinel-2 cross-check: see report §6.2"]) +
     ["PINN (Saint-Venant): 6 published cases reproduced (0.0 % deviation); case 3 retrained 2.7 % better than the paper; "
      "L-BFGS-B stage adds nothing", "Field Manning's n will replace the assumed 0.015"], size=14, bullet=True)
picture(s, os.path.join(ROOT, "pinn", "results", "figures", "case3_trained_profiles.png"), 6.9, 1.7, w=6.0)

# 16b team and contributions
s = slide("Team and contributions", "Five students, seven specializations; each presents the part they built")
table(s, 0.5, 1.5, 12.3, [
    ["Member", "Specializations", "What they built"],
    ["Nikhil Upadhyay (lead)", "Water resources, Ocean", "Flow-to-flood model, design floods, travel time, Saint-Venant PINN, storm drivers; organises the visit"],
    ["Vineet Jangir", "Remote sensing", "Benchmark of six foundation models (92 runs), fusion, the 20 m radar model"],
    ["Prakhar Gupta", "Remote sensing", f"Flood atlas from {AS['n_passes']} Sentinel-1 passes, Sentinel-2 check, map viewer"],
    ["Himanshu Shete", "Transportation, Structural", "Hospital access, critical links, flood depth, walls, bridge scour; integration of the impact chain, "
                                                      "forecast-to-bulletin tool, website, report and slides"],
    ["Prabhat Kumar", "Geotechnical, Construction mgmt", "Bank screening, ground saturation, foundations; work windows, earthwork, siren and sensor plan"]],
      col_w=[2.6, 2.8, 6.9], size=13)

# 17 conclusions
s = slide("What we conclude", None)
text(s, 0.6, 1.3, 12.1, 5.6, [
    f"Model choice: on an unseen Indian flood U-Net ({iou('lio', 'unet')}) beats every foundation model; the FM's value here is "
    "that one network takes radar alone when monsoon cloud removes the optical image.",
    f"The delta's flood atlas from {AS['n_passes']} radar passes turns a Naraj flow forecast into a map; on held-out years it beats "
    f"flood climatology at high flows ({hf['model']['iou']:.2f} vs {hf['climatology']['iou']:.2f}).",
    f"In a 25-year flood about {n(EX.loc['T25']['people'])} people live on flooded land and {n(t25['hospital: people cut off'])} "
    "lose road access to a hospital; the critical links and banks to inspect are listed with coordinates.",
    "Deployment: siren and sensor sites, and a forecast-to-bulletin tool, ready for ClimMaTech's platform.",
    "Next: the field visit closes the loop — accuracy at random points, measured discharge and roughness, soil classes."],
     size=17, bullet=True)
