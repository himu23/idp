"""Build the project website (website/index.html + viewer.html + img/) from the result files.

    python report/build_website.py
Numbers come from results/analysis, results/atlas and results/impact, as in the report; the hero picture and the
scenario maps are drawn here from the atlas rasters. The viewer page is the map dashboard (dashboard/index.html)
wrapped as a stand-alone page. The interface follows the partner's site (Inter, floating pill navigation, black
buttons, tile grids, striped bands); it is a student-project site and carries no partner logo or wording.
"""
import glob
import html
import json
import os
import shutil

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AN, AT, IM, AF = (os.path.join(ROOT, "results", d) for d in ("analysis", "atlas", "impact", "atlas_figures"))
OUT = os.path.join(ROOT, "website")
IMG = os.path.join(OUT, "img")
os.makedirs(IMG, exist_ok=True)


def J(*p):
    path = os.path.join(*p)
    return json.load(open(path)) if os.path.exists(path) else {}


def C(*p):
    path = os.path.join(*p)
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


def n(x):
    try:
        return f"{float(x):,.0f}"
    except (TypeError, ValueError):
        return "–"


def e(s):
    return html.escape(str(s))


BENCH = {f"{s['protocol']}/{s['model']}/{s['mode']}/{s['modalities']}": s for s in json.load(open(os.path.join(AN, "summary.json")))}
u = lambda k: BENCH[k]["test_iou"]  # noqa: E731
AS, R20, TT = J(AT, "atlas_summary.json"), J(AN, "radar20m.json"), J(IM, "travel_time.json")
EXS, TRS, SIT = J(IM, "exposure_summary.json"), J(IM, "transport_summary.json"), J(IM, "siting_summary.json")
DEP, STR, GRD, OCN, CMP = (J(IM, f) for f in ("depth_summary.json", "structures_summary.json", "ground_summary.json",
                                             "ocean_summary.json", "cm_plan.json"))
S2C = J(IM, "s2_crosscheck.json")
EX, TR = C(IM, "exposure_scenarios.csv").set_index("scenario"), C(IM, "transport_scenarios.csv").set_index("scenario")
CL, SEN, SR, GEO = C(IM, "critical_links.csv"), C(IM, "sensor_sites.csv"), C(IM, "siren_sites.csv"), C(IM, "geotech_top20.csv")
SC, DRV, CYC, LR = C(IM, "bridge_scour.csv"), C(IM, "flood_drivers.csv"), C(IM, "cyclones_near_delta.csv"), C(IM, "link_raising.csv")
RP = {int(k): v for k, v in AS["gumbel"]["return_period_m3s"].items()}
V = AS["validation"]
HF = V["high_flow_passes"]
T25, TR25 = EX.loc["T25"], TR.loc["T25"]
OBS = [k for k in EX.index if k.startswith("observed_")][0]
RH = int(AS.get("heavy_rain_scenario", {}).get("rain_mm", 171))
LAKH = 2831.7  # m3/s per lakh cusec

# ---------------------------------------------------------------- figures from the analysis
imgs = {}
for src in [os.path.join(AN, "figures", f) for f in ("bars_lio.png", "frozen_vs_finetuned.png", "modality_ablation.png",
                                                       "label_efficiency_lio.png")] + glob.glob(os.path.join(AF, "*.png")):
    if os.path.exists(src):
        shutil.copy(src, os.path.join(IMG, os.path.basename(src)))
        imgs[os.path.basename(src)[:-4]] = f"img/{os.path.basename(src)}"


# ---------------------------------------------------------------- maps drawn from the atlas rasters
def pool(a, k):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def mix(pic, col, a):
    return pic * (1 - a[..., None]) + np.asarray(col, float) * a[..., None]


TOWNS = [("Cuttack", 85.883, 20.4625), ("Salepur", 86.11, 20.48), ("Kendrapara", 86.42, 20.50)]
MAP_LAND, MAP_RIVER, MAP_FLOOD = (237, 241, 245), (12, 60, 108), (240, 135, 20)
maps, towns, box_km, map_ratio = {}, [], 68.0, "3402 / 2232"
try:
    import rasterio
    from PIL import Image
    from rasterio.warp import transform
    from scipy import ndimage

    def rd(*p):
        with rasterio.open(os.path.join(*p)) as r:
            return r.read(1), r.bounds, r.crs

    bed, b, crs = rd(AT, "river_bed.tif")
    water = (bed > 0) | (rd(AT, "normal_water_latest.tif")[0] > 0)
    box_km = (b.right - b.left) / 1000
    map_ratio = f"{water.shape[1]} / {water.shape[0]}"
    for name, lo, la in TOWNS:
        x, y = transform("EPSG:4326", crs, [lo], [la])
        fx, fy = (x[0] - b.left) / (b.right - b.left), (b.top - y[0]) / (b.top - b.bottom)
        if 0.02 < fx < 0.98 and 0.05 < fy < 0.95:
            towns.append((name, round(fx * 100, 1), round(fy * 100, 1)))

    # hero: how often each pixel flooded on the radar passes (percent of monsoon passes), as a blue-grey radar picture
    fq = rd(AT, "flood_frequency.tif")[0]
    f2 = pool(np.where(fq == 255, 0, fq / 100.0), 2)
    w2 = pool(water.astype(float), 2)
    tex = ndimage.gaussian_filter(np.random.default_rng(7).standard_normal(w2.shape), 2.5)
    pic = np.ones(w2.shape + (3,)) * np.array([207, 216, 227], float) + (tex / np.abs(tex).max())[..., None] * 9
    pic = mix(pic, (84, 132, 190), np.clip(f2 * 4, 0, 1) ** 0.6 * 0.95)
    pic = mix(pic, (18, 50, 86), np.clip(w2 * 1.2, 0, 1))
    Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)).save(os.path.join(IMG, "hero_delta.webp"), quality=80, method=6)
    maps["hero"] = "img/hero_delta.webp"

    # one map per scenario: flooded land over the river bed
    w3 = pool(water.astype(float), 3)

    def scen_map(mask, name):
        pic = np.ones(w3.shape + (3,)) * np.array(MAP_LAND, float)
        pic = mix(pic, MAP_FLOOD, np.clip(pool(mask.astype(float), 3) * 1.8, 0, 1))
        pic = mix(pic, MAP_RIVER, np.clip(w3 * 1.15, 0, 1) * 0.92)
        Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)).save(os.path.join(IMG, f"{name}.webp"), quality=82, method=6)
        maps[name] = f"img/{name}.webp"

    with rasterio.open(os.path.join(AT, "scenarios_return_period.tif")) as r:
        for i, T in enumerate(sorted(RP)):  # bands are the return periods in ascending order
            scen_map(r.read(i + 1) == 1, f"scen_T{T}")
    scen_map(rd(AT, "observed_largest_flood.tif")[0] == 1, "scen_obs")
    for tag, mm in (("rain_dry", 20), ("rain_heavy", RH)):
        p = os.path.join(IM, "bulletins", f"flood_{round(RP[5])}_rain{mm}.tif")
        if os.path.exists(p):
            scen_map(rasterio.open(p).read(1) == 1, tag)
except ImportError as err:
    print("maps skipped:", err)


def table(df, cols, heads, num=(), tags=None):
    """Plain HTML table; missing values print as a dash, booleans as yes/no; `tags` maps a column to {value: css}."""
    if df is None or len(df) == 0:
        return ""
    h = "".join(f'<th{" class=num" if c in num else ""}>{e(t)}</th>' for c, t in zip(cols, heads))
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if not isinstance(v, str) and pd.isna(v):
                v = "–"
            elif isinstance(v, (bool, np.bool_)):
                v = "yes" if v else "no"
            elif isinstance(v, (float, np.floating)):
                v = f"{v:,.2f}" if abs(v) < 10 else f"{v:,.0f}"
            elif isinstance(v, (int, np.integer)):
                v = f"{int(v):,}"
            body = e(v)
            if tags and c in tags:
                body = f'<span class="tag {tags[c].get(v, "")}">{body}</span>'
            cells.append(f'<td{" class=num" if c in num else ""}>{body}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{h}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def fig(key, caption, wide=False):
    if key not in imgs:
        return ""
    return (f'<figure class="case{" wide" if wide else ""}"><div class="pic"><img src="{imgs[key]}" alt="{e(caption)}" loading="lazy"></div>'
            f'<figcaption>{e(caption)}</figcaption></figure>')


FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
        "December"]


def window_text(months):
    """Month set on a circular calendar -> 'December–April' style ranges."""
    if not months:
        return "December–April"
    idx = sorted({[m[:3] for m in FULL].index(m[:3]) for m in months})
    sset, blocks = set(idx), []
    for i in idx:
        if (i - 1) % 12 not in sset:
            j = i
            while (j + 1) % 12 in sset and (j + 1) % 12 != i:
                j = (j + 1) % 12
            blocks.append((i, j))
    if not blocks:
        return "all year"
    return ", ".join(FULL[a] if a == b else f"{FULL[a]}–{FULL[b]}" for a, b in blocks)


def sysname(s):
    """IBTrACS names -> page text: 'Unnamed' -> 'depression (unnamed)', 'Bulbul:Matmo' -> 'Bulbul (Matmo)'."""
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


# ---------------------------------------------------------------- numbers used in the copy
people_25, cut_25 = T25["people"], TR25["hospital: people cut off"]
sett = V.get("settlements", {}).get("high_flow_passes", {}).get("model", {})
auc = V.get("ranking_auc", {})
walls = STR.get("walls", {})
dcrit = walls.get("critical_depth_m", {})
ground_s = GRD.get("scenarios", {}).get("T25", {})
fe = GRD.get("foundation_example", {})
lrk = CMP.get("link_raising", {})
dep = CMP.get("deployment", {})
win = window_text(CMP.get("work_window_months", []))
scour_rng = STR.get("bridges", {}).get("pier_scour_T100_share50_range_m", [0, 0])
scour25 = STR.get("bridges", {}).get("pier_scour_T100_share25_range_m", [0, 0])
drv_counts = OCN.get("top20_flood_passes_driver_counts", {})
s2 = S2C.get("all/all_months", {})
s2f = S2C.get("outside_normal/all_months", {})
struct_links = lrk.get("links_needing_structure", [])
routes = lrk.get("people_routed_per_link", [0, 0])
rb = {mm: J(IM, "bulletins", f"bulletin_{round(RP[5])}_rain{mm}.json") for mm in (20, RH)}
rb25 = J(IM, "bulletins", f"bulletin_{round(RP[25])}.json")
WS = J(IM, "watershed_summary.json")
ws_text = (f"Hirakud dam controls about 59 % of the Mahanadi basin and passes {WS['jul_sep_share']:.0%} of the July–September flow at "
           f"Naraj, but only about half of a yearly flood peak (median {WS['median_share_hirakud_of_naraj_peak']:.0%} over {WS['years']} years): "
           f"the rest comes from the 58,000 km² of tributaries below the dam, within about a day. A delta warning needs the dam's "
           f"release plan and gauges on those tributaries. ") if WS else ""
obs_date = OBS.split("_")[1]
obs_day = pd.Timestamp(obs_date)
obs_drv = DRV[DRV.date == obs_day.strftime("%Y-%m-%d")].iloc[0] if len(DRV) and (DRV.date == obs_day.strftime("%Y-%m-%d")).any() else None
obs_q = float(next((p["q"] for p in AS.get("top_passes", []) if p["date"] == obs_day.strftime("%Y-%m-%d")), 0))
w230 = (dcrit.get("230 mm wall, f_t 0.1 MPa", 0.8), dcrit.get("230 mm wall, f_t 0.2 MPa", 1.0))
w115 = (dcrit.get("115 mm wall, f_t 0.1 MPa", 0.5), dcrit.get("115 mm wall, f_t 0.2 MPa", 0.65))

glance = [(n(AS["n_passes"]), "Sentinel-1 radar passes mapped, 2017–2026"),
          (f"{EXS.get('population_ghsl', 4.1e6) / 1e6:.1f} M", "people in the 3,038 km² study box"),
          (n(people_25), "people living on land flooded in a 25-year flood"),
          (n(cut_25), "people cut off from every hospital in that flood")]
glance_html = "".join(f"<div><b>{e(a)}</b><span>{e(b)}</span></div>" for a, b in glance)

sources = ["Sentinel-1 radar", "Sentinel-2 optical", "Sen1Floods11", "GloFAS v4 discharge", "ERA5 rain", "JRC Surface Water",
           "GHSL population", "ESA WorldCover", "Copernicus DEM", "SoilGrids", "IBTrACS storm tracks", "OpenStreetMap"]
src_set = "".join(f"<span>{e(s_)}</span>" for s_ in sources)

# mosaic over the hero picture: blocks of page colour, denser to the left, so the picture dissolves into the page
rng = np.random.default_rng(11)
cells = []
for row in range(5):
    for col in range(8):
        v = float(np.clip(1 - col / 4.2 + rng.uniform(-0.35, 0.35), 0, 1))
        v = min((0, 0.3, 0.6, 0.85, 1), key=lambda s_: abs(s_ - v))
        cells.append(f'<i style="opacity:{v}"></i>')
mosaic = "".join(cells)
hero_img = f'<img src="{maps["hero"]}" alt="">' if "hero" in maps else ""

# ---------------------------------------------------------------- scenario explorer
scen = []
for key, label in (("T2", "2-year"), ("T5", "5-year"), ("T10", "10-year"), ("T25", "25-year"), ("T100", "100-year"), (OBS, "Largest seen")):
    if key not in EX.index:
        continue
    r_, t_ = EX.loc[key], TR.loc[key]
    q = RP[int(key[1:])] if key.startswith("T") else obs_q
    lower = key.startswith("T") and q > AS["largest_observed_predictor_m3s"]
    if key.startswith("T"):
        note = (f"Flow above the largest in the radar record ({n(AS['largest_observed_predictor_m3s'])} m³/s): the map cannot grow further, "
                f"so this is a lower bound." if lower else f"A flood of this size or larger comes on average once in {key[1:]} years.")
    else:
        note = (f"{obs_day.day} {FULL[obs_day.month - 1]} {obs_day.year}: the largest flood on a near-complete pass, with "
                f"{n(obs_drv['rain_mm']) if obs_drv is not None else '–'} mm of rain in 7 days from a Bay of Bengal depression and only a "
                f"moderate river.")
    scen.append(dict(key=key, label=label, q=round(q), lakh=round(q / LAKH, 1), km2=round(float(r_["flood_km2"]), 1),
                     people=int(r_["people"]), sett=int(r_["settlements >= 10 % of people flooded"]),
                     road=round(float(r_["road km (all)"]), 1), cut=int(t_["hospital: people cut off"]),
                     img=maps.get(f"scen_{key}" if key.startswith("T") else "scen_obs", ""), note=note))
S0 = next(s_ for s_ in scen if s_["key"] == "T25")
seg = "".join(f'<button type="button" data-scen="{s_["key"]}" aria-pressed="{"true" if s_ is S0 else "false"}">{e(s_["label"])}</button>'
              for s_ in scen)
town_html = "".join(f'<span class="town{" r" if x > 80 else ""}" style="left:{x}%;top:{y}%">{e(t)}</span>' for t, x, y in towns)
sim_json = json.dumps({s_["key"]: s_ for s_ in scen}).replace("</", "<\\/")

# ---------------------------------------------------------------- specializations
disciplines = [
    ("Remote sensing", "rs", "#model", "bars_lio", "Which satellite model maps an Indian flood best, through monsoon cloud?",
     f"U-Net {u('lio/unet/full/default'):.3f} against the best foundation model {u('lio/prithvi/full/default'):.3f} on an unseen Assam flood; "
     f"a radar TerraMind + U-Net fusion maps all {n(AS['n_passes'])} passes",
     "Benchmark of 6 foundation models (92 runs), Sentinel-1 atlas, Sentinel-2 cross-check", "40 random ground-truth points"),
    ("Water resources", "wr", "#d-wr", "atlas_trigger_map", "Which Naraj flow floods which land, and what else drives the delta's floods?",
     f"The trigger map beats flood climatology at high flows (IoU {HF['model']['iou']:.2f} against {HF['climatology']['iou']:.2f}); "
     f"25-year flow {n(RP[25])} m³/s", "GloFAS discharge, ERA5 rain, per-pixel trigger discharge, held-out years, Gumbel",
     "Discharge and Manning's n at a road bridge"),
    ("Transportation systems", "tr", "#d-tr", "impact_T25_map", "Who loses the road to a hospital, and which links matter most?",
     f"{n(cut_25)} people cut off from any hospital in a 25-year flood; {n(TR25.get('town: extra person-hours of travel per day', 0))} "
     f"extra person-hours of travel a day", "OpenStreetMap road graph, flooded edges removed, shortest paths to hospitals, towns and dry schools",
     "Road closures at the 10 critical links"),
    ("Geotechnical", "gt", "#d-gt", "ground_advisory_map", "Which river banks fail first, and which dry houses sit on soaked ground?",
     f"{n(ground_s.get('people_in_zone', 0))} people within 200 m of 25-year flood water on silty clay; soaking cuts bearing capacity "
     f"by {fe.get('silty_sand_drained', {}).get('reduction_pct', 0)} %",
     "Bank screening, saturation advisory, foundation and drawdown checks", "Soil samples, well levels, bank slopes"),
    ("Structural", "st", "#d-st", "depth_T25_map", "Where do masonry walls crack, and how deep must bridge piers go?",
     f"{n(walls.get('T25', {}).get('people_deeper_than_1m', 0))} people where the 25-year flood is 1 m deep or more; pier scour "
     f"{scour25[0]:.0f}–{scour25[1]:.0f} m below HFL at a quarter of the 100-year flow (IRC:78)",
     "DEM flood depth, wall moment check, Lacey scour", "Deck clearance, HFL marks, foundation levels"),
    ("Ocean", "oc", "#d-oc", "flood_drivers", "How much do Bay of Bengal storms add to the delta's floods?",
     f"{OCN.get('systems_within_300km_since_2016', 0)} storms and depressions within 300 km since 2016; "
     f"{drv_counts.get('cyclone/depression', 0)} of the 20 largest floods followed one",
     "IBTrACS tracks matched to the atlas; river, rain and storm drivers", "Interviews on surge and tide-locked drainage"),
    ("Construction technology and management", "cm", "#d-cm", "construction_windows", "When can the delta be built in, and what does protection cost?",
     f"Work window {win}; raising {lrk.get('links_by_embankment', 0)} critical links takes about {n(lrk.get('earthwork_m3', 0))} m³ of "
     f"earthwork, {len(struct_links)} more need a bridge or vented causeway",
     "Monthly flood and storm climatology, earthwork take-off, deployment quantities and schedule", "Site sheets: access, mounting, signal"),
]
acc = []
for i, (name, k, link, im, q, res, meth, fld) in enumerate(disciplines):
    on = i == 0
    acc.append(f'''<div class="acc-item{" open" if on else ""}" data-img="{imgs.get(im, "")}" data-label="{e(name)}" data-alt="{e(name)}: {e(q)}">
  <button type="button" class="acc-head" id="acc-h-{k}" aria-expanded="{"true" if on else "false"}" aria-controls="acc-b-{k}"><span>{e(name)}</span><span class="pm" aria-hidden="true"></span></button>
  <div class="acc-body" id="acc-b-{k}" role="region" aria-labelledby="acc-h-{k}"{"" if on else " hidden"}>
    <p class="q">{e(q)}</p><p class="res">{e(res)}</p><p>{e(meth)}</p><p><span class="fl">At the site</span> {e(fld)}</p>
    <a class="btn-light" href="{link}">Read the analysis <span class="arrow" aria-hidden="true">→</span></a>
  </div>
</div>''')
acc_html = "\n".join(acc)
d0 = disciplines[0]

# ---------------------------------------------------------------- tables
ex_rows = []
for k in [f"T{t}" for t in (2, 5, 10, 25, 100)] + [OBS]:
    if k in EX.index:
        r_, t_ = EX.loc[k], TR.loc[k] if k in TR.index else None
        ex_rows.append(dict(s=f"{k[1:]}-year" if k.startswith("T") else f"largest seen ({obs_day:%d %b %Y})",
                            q=n(RP[int(k[1:])]) if k.startswith("T") else n(obs_q),
                            a=f"{r_['flood_km2']:.0f}", p=n(r_["people"]), c=f"{r_['cropland km2']:.0f}", rd=f"{r_['road km (all)']:.0f}",
                            h=int(r_["health facilities"]), cut=n(t_["hospital: people cut off"]) if t_ is not None else "–"))
cl_tab = table(CL[CL.scenario == "T25"].head(8).assign(road=lambda d: d.road.fillna("(unnamed)"),
                                                       where=lambda d: d.lat.map("{:.4f} N".format) + ", " + d.lon.map("{:.4f} E".format)),
               ["rank", "road", "highway", "people_routed", "flooded_km", "where"],
               ["#", "Road", "Class", "People routed", "Flooded km", "Location"], num={"rank", "people_routed", "flooded_km"})
sen_tab = table(SEN.assign(bridge=lambda d: d.name.fillna(d.ref).fillna("(unnamed)"),
                           where=lambda d: d.lat.map("{:.4f} N".format) + ", " + d.lon.map("{:.4f} E".format)),
                ["river", "bridge", "length_m", "km_from_naraj", "access_dry", "where"],
                ["River", "Bridge", "Length (m)", "km from Naraj", "Approaches dry (25-yr)", "Location"],
                num={"length_m", "km_from_naraj"})
sc_tab = ""
if len(SC):
    sc100 = SC[SC["T"] == 100].assign(river=lambda d: d.river.fillna("–"), bridge=lambda d: d.bridge.fillna("(unnamed)"))
    pv = sc100.pivot_table(index=["river", "bridge", "linear_waterway_m"], columns="share", values="pier_scour_below_HFL_m").reset_index()
    pv = pv.rename(columns={0.25: "q25", 0.5: "q50"}).sort_values("linear_waterway_m")
    sc_tab = table(pv, ["river", "bridge", "linear_waterway_m", "q25", "q50"],
                   ["River", "Bridge", "Waterway (m)", "Pier scour, ¼ of the flow (m)", "Pier scour, ½ of the flow (m)"],
                   num={"linear_waterway_m", "q25", "q50"})
lr_tab = table(LR.assign(earth=lambda d: np.where(d.get("design", "embankment raise") == "embankment raise", d.earthwork_m3, np.nan)),
               ["rank", "highway", "flooded_km", "depth_p90_m", "raise_m", "design", "earth"],
               ["#", "Road class", "Flooded km", "Depth p90 (m)", "Raise (m)", "Design", "Earthwork (m³)"],
               num={"rank", "flooded_km", "depth_p90_m", "raise_m", "earth"},
               tags={"design": {"bridge or vented causeway": "warn"}}) if "design" in LR else ""
cyc_tab = ""
if len(CYC):
    cy = CYC.dropna(subset=["max_flood_km2_on_a_pass"]).sort_values("max_flood_km2_on_a_pass", ascending=False).head(10)
    cyc_tab = table(cy.assign(name=lambda d: d.name.map(sysname)),
                    ["name", "closest_date", "min_dist_km", "max_wind_kt_near", "rain_week_mm", "max_flood_km2_on_a_pass"],
                    ["System", "Closest", "Distance (km)", "Wind (kt)", "Rain that week (mm)", "Largest flood on a pass (km²)"],
                    num={"min_dist_km", "max_wind_kt_near", "rain_week_mm", "max_flood_km2_on_a_pass"})
ex_tab = table(pd.DataFrame(ex_rows), ["s", "q", "a", "p", "c", "rd", "h", "cut"],
               ["Scenario", "Naraj flow (m³/s)", "Flooded land (km²)", "People on it", "Cropland (km²)", "Road under water (km)",
                "Health facilities", "Cut off from hospital"], num={"q", "a", "p", "c", "rd", "h", "cut"})
bul25 = os.path.join(IM, "bulletins", f"bulletin_{round(RP[25])}.txt")
bul_txt = open(bul25, encoding="utf-8").read().strip() if os.path.exists(bul25) else ""

struct_txt = ""
if struct_links:
    ranks = " and ".join(str(x["rank"]) for x in struct_links)
    struct_txt = (f" Links {ranks} would need raises of " + " and ".join(f"{x['raise_m']:.1f} m" for x in struct_links)
                  + ": at that height a bridge or a vented causeway replaces the embankment, and the depth there is checked at the site first.")
rain_pair, rain_ratio = "", "several times"
if all(rb.values()):
    k_ = round(rb[RH]["flooded_land_km2"] / max(rb[20]["flooded_land_km2"], 0.1))
    rain_ratio = {2: "twice", 3: "three times", 4: "four times", 5: "five times", 6: "six times"}.get(k_, f"{k_} times")
if all(rb.values()) and "rain_dry" in maps and "rain_heavy" in maps:
    rain_pair = f'''<div class="pair">
      <figure class="case"><div class="pic map"><img src="{maps['rain_dry']}" alt="Flooded land for the 5-year flow with a dry week" loading="lazy"></div>
        <figcaption><b>{n(RP[5])} m³/s, dry week ({rb[20]['rain_mm']:.0f} mm)</b> {rb[20]['flooded_land_km2']:.0f} km² flooded, {n(rb[20]['people_on_flooded_land'])} people on it</figcaption></figure>
      <figure class="case"><div class="pic map"><img src="{maps['rain_heavy']}" alt="Flooded land for the 5-year flow with a week of heavy rain" loading="lazy"></div>
        <figcaption><b>{n(RP[5])} m³/s, heavy-rain week ({rb[RH]['rain_mm']:.0f} mm)</b> {rb[RH]['flooded_land_km2']:.0f} km² flooded, {n(rb[RH]['people_on_flooded_land'])} people on it</figcaption></figure>
    </div>'''

# ---------------------------------------------------------------- partner gaps, network of sites, audit, roadmap
AUD = J(AN, "audit_training.json")
LRN = J(AT, "learned", "learned_summary.json")
cov15 = SIT.get("coverage", {}).get("1500", {})
specs = [(n(AS["n_passes"]), "Radar passes mapped", "Every Sentinel-1 pass over the delta, 2017–2026, through monsoon cloud"),
         ("20 m", "Flood-map resolution", "Radar TerraMind + U-Net fusion, about 5 s per pass on one GPU"),
         (n(people_25), "People on 25-year flood land", f"and {n(cut_25)} who lose road access to every hospital"),
         (f"{HF['model']['iou']:.2f} vs {HF['climatology']['iou']:.2f}", "Skill on years not seen",
          "Trigger map against flood climatology at high flows, pixel IoU")]
specs_html = "".join(f'<div><b>{e(v)}</b><span class="lab">{e(l_)}</span><span class="sub">{e(t)}</span></div>' for v, l_, t in specs)

learned_line, learned_card = "", ""
if LRN:
    li = LRN["pixel_iou"]
    la = LRN.get("ranking_auc", {})
    lh = LRN["settlements"]["high_flow_passes"]
    learned_line = (f" A learned flow + rain + history model, tested on years it never saw, maps heavy-rain passes better than the "
                    f"trigger map (IoU {li['heavy_rain_passes']['learned']['iou']:.2f} against {li['heavy_rain_passes']['trigger']['iou']:.2f}) "
                    f"and ranks flood-prone land best (AUC {la.get('all_passes', {}).get('learned', 0):.2f}).")
    learned_card = (f"Gradient boosting per pixel and pass with the physical direction of each input imposed, fitted without the "
                    f"year it predicts. Pixel IoU {li['all_passes']['learned']['iou']:.2f} against {li['all_passes']['trigger']['iou']:.2f} for the "
                    f"trigger map, {li['heavy_rain_passes']['learned']['iou']:.2f} against {li['heavy_rain_passes']['trigger']['iou']:.2f} on heavy-rain "
                    f"passes; ranking AUC {la.get('all_passes', {}).get('learned', 0):.2f} against {la.get('all_passes', {}).get('climatology', 0):.2f} "
                    f"for flood history alone. At high flows it catches {lh['learned']['POD']:.0%} of flooded villages against "
                    f"{lh['trigger']['POD']:.0%}, with more false alarms ({lh['learned']['FAR']:.0%} against {lh['trigger']['FAR']:.0%}).")

sc_l = LRN.get("scenarios_all_years_model", {}) if LRN else {}
learned_rain = (f'<p class="note">The learned flow + rain model gives the same picture: at the 5-year flow it floods '
                f'{sc_l["T5 dry week"]["flood_km2"]:.0f} km² in a dry week, {sc_l["T5 typical rain"]["flood_km2"]:.0f} km² with typical '
                f'rain and {sc_l["T5 heavy rain"]["flood_km2"]:.0f} km² with heavy rain.</p>') if sc_l else ""
gaps = [
    ("River View · platform", "A flood-risk map layer with no flood extent behind it",
     "Their architecture lists a live map of river levels and flood risk. We add the layers it needs for the Mahanadi delta: "
     "where land floods, at which Naraj flow it starts, and who lives there.",
     f"{n(AS['n_passes'])} radar passes · held-out IoU {HF['model']['iou']:.2f} vs {HF['climatology']['iou']:.2f} at high flows · "
     f"past floods rank flood-prone land at AUC {auc.get('high_flow_passes', {}).get('clim', 0):.2f}"),
    ("AI forecasting · 30 min to 48 h", "A forecast level is not a list of villages",
     "The forecast-to-bulletin tool turns a forecast Naraj flow, with or without rain, into a flood map, the settlements to warn "
     "and the roads under water, as GeoTIFF, GeoJSON and text for the control centre and the app.",
     f"25-year flow: {T25['flood_km2']:.0f} km², {n(people_25)} people, {int(T25['settlements >= 10 % of people flooded'])} settlements to warn"),
    ("Research group · reconstructions", "Satellite evidence gathered by hand, and blocked by cloud",
     "Their Nepal reconstruction measured flood width by hand at 36 cross-sections; the optical pass was 75–79 % cloud and the "
     "only radar pass came two days early. Our radar model maps every Sentinel-1 pass automatically, through cloud.",
     f"Chosen by {AUD.get('n_checked', 92)} audited training runs · about 5 s per pass · {s2.get('iou', 0):.2f} IoU against Sentinel-2 water"),
    ("Solution pages · network design", "Site layouts drawn as illustrations",
     "Each solution page shows an illustrative layout. For the delta the network is placed with data: sirens where the most "
     "exposed people live, one radar gauge at the head of each distributary on a bridge that stays reachable.",
     f"{cov15.get('sirens', 40)} sirens reach {cov15.get('share', 0):.0%} of {n(SIT.get('exposed_people', 0))} exposed people at 1.5 km · "
     f"{len(SEN)} sensor bridges with coordinates"),
    ("Pravaah · discharge", "Discharge needs a surveyed section and a velocity factor",
     "Their FAQ says level and surface velocity become discharge only with a surveyed cross-section and a surface-to-mean "
     "velocity factor. Field protocols B and C measure both, with Manning's n, at a road bridge near Naraj.",
     "Velocity-area and Manning scripts ready · GloFAS flow at Naraj to compare"),
    ("Varshaq · rain gauge", "Rain that is not yet linked to flooded land",
     "The largest floods of the delta came with heavy rain from Bay of Bengal depressions, not with the highest river flows. "
     "Rain changes which land floods at the same flow." + learned_line,
     f"5-year flow: {rb[20].get('flooded_land_km2', 0):.0f} km² in a dry week, {rb[RH].get('flooded_land_km2', 0):.0f} km² in a "
     f"heavy-rain week · {drv_counts.get('rain', 0)} of the 20 largest floods had heavy rain" if all(rb.values()) else ""),
    ("Flood warning · Aagah app", "Time to evacuate and reroute, but who and which roads?",
     "Their flood-warning page promises time to evacuate people, reroute traffic and secure infrastructure. Each bulletin names "
     "the settlements with people on flooded land, the roads that close and the villages that lose their hospital.",
     f"25-year flood: {int(TR25['hospital: settlements cut off'])} settlements cut off from any hospital; "
     f"{n(TR25.get('town: extra person-hours of travel per day', 0))} extra person-hours of travel a day"),
    ("Rakshak Control Centre", "Operators draw each alert area by hand",
     "The control centre asks operators to draw an area or upload boundaries, and accepts alerts from other systems in CAP. "
     "Every forecast now also writes a CAP 1.2 alert with one area per settlement to warn.",
     f"25-year flow: {rb25.get('settlements_to_warn', 0)} alert areas; 5-year flow in a dry week: {rb[20].get('settlements_to_warn', 0)}"),
    ("Dam and reservoir · solution", "Level at the dam, but not the water spread",
     "The same radar model maps reservoir water area on every pass, through cloud, which gives an area record for Hirakud "
     "to set beside the level gauge.", "Next step: the atlas pipeline on the Hirakud reservoir"),
]
gaps_html = "".join(f'<article class="gap"><span class="svc">{e(a_)}</span><h3>{e(b_)}</h3><p>{e(c_)}</p><span class="ev">{e(d_)}</span></article>'
                    for a_, b_, c_, d_ in gaps)

site_items = []
for k_, (_, r_) in enumerate(SEN.iterrows(), 1):
    bname = r_["name"] if isinstance(r_["name"], str) else (r_["ref"] if isinstance(r_["ref"], str) else "unnamed bridge")
    access = (f"the bridge nearest Naraj on the {r_['river']} whose approaches stay dry in the 25-year flood, so it can be reached "
              f"during the flood" if r_["access_dry"] else
              f"the bridge nearest Naraj on the {r_['river']}; no bridge on it keeps dry approaches in the 25-year flood, so it is "
              f"read remotely and serviced before the monsoon")
    site_items.append(
        f'<li><span class="n">{k_}</span><div><h3>{e(r_["river"])} <span class="pill">Pravaah-type gauge</span></h3>'
        f'<p>{e(bname)}, {r_["length_m"]:,.0f} m long, {r_["km_from_naraj"]:.0f} km from Naraj · {r_["lat"]:.4f} N, {r_["lon"]:.4f} E</p>'
        f'<p class="why"><b>Why here:</b> {e(access)}. A gauge here measures how much of the flood this branch takes; '
        f'{n(r_["people_in_hazard_10km"])} people live in the flood hazard within 10 km.</p></div></li>')
top3 = ", ".join(SR.head(3).settlement.tolist()) if len(SR) else ""
site_items.append(
    f'<li><span class="n">{len(SEN) + 1}</span><div><h3>Sirens <span class="pill">Rakshak-type siren</span></h3>'
    f'<p>{cov15.get("sirens", 40)} sites; the first three: {e(top3)}.</p>'
    f'<p class="why"><b>Why here:</b> each site is picked to cover the most people still uncovered who live on land flooded in '
    f'the 25-year flood or in at least 10 % of passes; {cov15.get("sirens", 40)} sirens reach {cov15.get("share", 0):.0%} of them '
    f'at a 1.5 km audible range.</p></div></li>')
sites_html = "".join(site_items)

ref_tm = {"s1s2": 90.62, "s1": 80.39}  # TerraMind paper (Jakubik et al. 2025), Sen1Floods11 mIoU, PANGAEA protocol
om = AUD.get("official_test_miou", {})
rd = AUD.get("radar_db_percentiles_10_50_90", {})
audit_html = ""
if AUD:
    audit_html = f'''<div class="audit">
    <div><b>{AUD.get("n_checked", 0)} of {AUD.get("n_jobs", 0)} runs re-checked, {len(AUD.get("problems", []))} problems</b><p>Each run used the arguments it was queued with; no chip sits in two splits; under leave-India-out no India chip reaches training or validation; every test score recomputed from the saved predictions matches.</p></div>
    <div><b>Matches the published TerraMind numbers</b><p>Our TerraMind-B on the official Sen1Floods11 test: mean IoU {om.get("official_terramind_full_s0", {}).get("miou", 0) * 100:.1f} with radar and optical, {om.get("official_terramind_s1_full_s0", {}).get("miou", 0) * 100:.1f} with radar alone; the TerraMind paper (arXiv:2504.11171) reports {ref_tm["s1s2"]} and {ref_tm["s1"]}.</p></div>
    <div><b>The delta's radar looks like the training radar</b><p>Median backscatter of dry land: {rd.get("mahanadi_atlas_dry", {}).get("VV", [0, 0])[1]:.1f} dB in the delta, {rd.get("sen1floods11_train_dry", {}).get("VV", [0, 0])[1]:.1f} dB in Sen1Floods11 (VV); water sits 8–11 dB lower in both, so the archive conversion holds.</p></div>
  </div>'''

R20N = J(AN, "radar20m_r20.json")
if R20N:
    gain = R20N["mean"]["avg20"] - R20.get("mean", {}).get("avg20", 0)
    r20_card = ("done", "Done", "Retrained the radar models at 20 m",
                f"TerraMind-B and U-Net trained on radar degraded to the 20 m overview the atlas reads. On 20 m input the fusion "
                f"scores {R20N['mean']['avg20']:.3f} against {R20.get('mean', {}).get('avg20', 0):.3f} for the 10 m-trained pair "
                f"(threshold from validation: {R20N['calibrated_test_iou']:.3f} against {R20.get('calibrated_test_iou', 0):.3f}).",
                "Ready to swap into the atlas" if gain >= 0.005 else "No clear gain: the 10 m models stay")
else:
    r20_card = ("", "Next", "Train on 20 m radar directly",
                f"The atlas reads 20 m radar; the fusion loses {R20.get('mean', {}).get('native', 0) - R20.get('mean', {}).get('avg20', 0):.3f} IoU "
                f"going from 10 m to 20 m input ({R20.get('mean', {}).get('native', 0):.3f} to {R20.get('mean', {}).get('avg20', 0):.3f}). "
                f"Training at 20 m should win part of it back.", "Two models, about 20 minutes on two GPUs")
road = [("done", "Done", "Flow + rain + history model", learned_card or "Gradient-boosted model per pixel and pass, fitted without the year it predicts.",
         "Uses the 457 monsoon passes already mapped"),
        ("", "Next", "Teach the radar model the delta",
         f"Sixty radar passes have a Sentinel-2 image within a day. Their water masks become weak labels to fine-tune the U-Net on the "
         f"delta, tested on dates left out.", f"Target: flood-water recall {s2f.get('recall', 0):.2f} against Sentinel-2"),
        r20_card,
        ("", "Planned", "Hirakud reservoir water area",
         "The same pipeline on the Hirakud reservoir gives a water-area record on every pass, for the dam and reservoir solution.",
         "Same model, a new area of interest"),
        ("", "Planned", "Nowcast Naraj from upstream gauges",
         f"Flow changes below Hirakud reach Naraj about {TT.get('hirakud_below', {}).get('best_lag_days', 1)} day later. A model on "
         f"upstream gauges, such as a Pravaah network, would forecast the flow the flood map needs.", "Needs observed gauge records"),
        ("", "After the visit", "Calibrate on field truth",
         "Forty random ground-truth points give the atlas its accuracy on the ground and per-land-cover thresholds.",
         "POD and FAR at 40 points")]
road_html = "".join(f'<article><span class="st {c_}">{e(t_)}</span><h3>{e(h_)}</h3><p>{e(p_)}</p><span class="gain">{e(g_)}</span></article>'
                    for c_, t_, h_, p_, g_ in road)

# ---------------------------------------------------------------- page
CSS = """
/* Layout: floating pill navigation over a left-aligned hero; bands alternate plain, surface, diagonal stripes and
   diamonds; one 1280 px column; tiles, cards and the accordion stack to one column on phones.
   One light theme on purpose, like the partner's site: every colour is set here and nowhere else. */
:root {
  color-scheme: light;
  --bg: #ffffff; --surface: #f9fafb; --ink: #000000; --muted: #555555; --soft: #64748b; --line: #e5e7eb; --hover: rgba(0, 0, 0, 0.04);
  --navy: #0c3c6c; --accent: #0c9ce4; --accent-ink: #0a64a0; --accent-soft: #e8f4fc; --signal: #fc9c24;
  --warn-soft: #fff4e6; --warn-ink: #9a4a00;
  --inv-bg: #000000; --inv-fg: #ffffff; --inv-muted: #b8c0ca; --inv-hover: #222222; --inv-line: #33383f; --inv-accent: #38b6f5;
  --glass: rgba(255, 255, 255, 0.82); --stripe: #f2f4f7; --paper: #ffffff;
  --map-land: #edf1f5; --map-ink: #16202b; --map-river: #0c3c6c; --map-flood: #f08714;
  --term-bg: #0b0f14; --term-fg: #e6edf3; --term-muted: #8b98a7; --term-line: #232b35;
  --label-bg: #000000; --label-fg: #ffffff; --inv-signal: #fc9c24; --hero-filter: none;
  --shadow: 0 8px 32px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
  --shadow-lg: 0 20px 45px -8px rgba(15, 23, 42, 0.14), 0 8px 16px rgba(15, 23, 42, 0.04);
  --sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Consolas, monospace;
  --ease: cubic-bezier(.16, 1, .3, 1);
  --section-y: clamp(64px, 8vw, 112px);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 108px; }
body { background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 16px; line-height: 1.6; letter-spacing: -0.01em;
  font-feature-settings: "cv11", "ss01"; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 60; background: var(--bg); }
::selection { background: var(--navy); color: var(--inv-fg); }
h1, h2, h3, h4 { margin: 0; color: var(--ink); text-wrap: balance; letter-spacing: -0.03em; line-height: 1.1; font-weight: 500; }
h3, h4 { font-weight: 600; letter-spacing: -0.015em; line-height: 1.3; }
p { margin: 0; color: var(--muted); line-height: 1.7; }
a { color: inherit; }
img { max-width: 100%; }
a:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.container { width: 100%; max-width: 1280px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
@media (min-width: 768px) { .container { padding-left: max(40px, env(safe-area-inset-left, 0px)); padding-right: max(40px, env(safe-area-inset-right, 0px)); } }
section { padding-block: var(--section-y); }
.eyebrow { font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--soft); }
h2 { font-size: clamp(30px, 4.2vw, 52px); }
.lede { font-size: clamp(16px, 1.5vw, 18px); max-width: 62ch; }

/* header */
.site-header { position: fixed; z-index: 50; top: calc(18px + env(safe-area-inset-top, 0px)); left: max(24px, env(safe-area-inset-left, 0px));
  right: max(24px, env(safe-area-inset-right, 0px)); max-width: 1200px; margin: 0 auto; height: 68px; display: flex; align-items: center;
  justify-content: space-between; gap: 12px; padding: 0 12px 0 24px; border-radius: 9999px; background: var(--glass);
  -webkit-backdrop-filter: blur(24px); backdrop-filter: blur(24px); border: 1px solid var(--line); box-shadow: var(--shadow); }
.brand { display: inline-flex; align-items: center; gap: 10px; font-weight: 600; font-size: 16px; letter-spacing: -0.02em; text-decoration: none; color: var(--ink); white-space: nowrap; }
.mark { flex: none; width: 22px; height: 22px; border-radius: 5px; background: conic-gradient(var(--navy) 0 25%, var(--accent) 0 50%, var(--navy) 0 75%, var(--signal) 0); }
.nav-links { display: flex; align-items: center; gap: 2px; height: 100%; }
.nav-item { display: flex; align-items: center; gap: 7px; height: 40px; padding: 0 14px; border-radius: 9999px; font-size: 14px; font-weight: 500; color: var(--ink); text-decoration: none; white-space: nowrap; transition: background .2s, color .2s; }
.nav-item:hover, .nav-item:focus-visible { background: var(--hover); color: var(--accent-ink); }
.chev { width: 6px; height: 6px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: translateY(-2px) rotate(45deg); }
.has-mega { height: 100%; display: flex; align-items: center; }
.mega { position: absolute; top: calc(100% + 10px); left: 50%; width: min(900px, calc(100vw - 48px)); opacity: 0; visibility: hidden;
  transform: translate(-50%, 12px) scale(.98); transition: opacity .35s var(--ease), transform .35s var(--ease), visibility .35s;
  background: var(--bg); border: 1px solid var(--line); border-radius: 24px; padding: 28px; box-shadow: var(--shadow-lg);
  display: grid; grid-template-columns: 1fr 1fr 1fr 1.4fr; gap: 28px; }
.mega::before { content: ""; position: absolute; top: -16px; left: 0; right: 0; height: 16px; }
.has-mega:hover .mega, .has-mega:focus-within .mega { opacity: 1; visibility: visible; transform: translate(-50%, 0) scale(1); }
.mm-col { display: flex; flex-direction: column; gap: 4px; border-right: 1px solid var(--line); padding-right: 20px; }
.mm-head { font-size: 12px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--accent-ink); margin-bottom: 8px; }
.mm-col a { font-size: 14px; padding: 6px 0; text-decoration: none; color: var(--ink); }
.mm-col a:hover { color: var(--accent-ink); }
.mm-feature { background: var(--surface); border-radius: 12px; padding: 22px; display: flex; flex-direction: column; gap: 10px; }
.mm-feature b { font-weight: 600; }
.mm-feature p { font-size: 13px; line-height: 1.55; }
.header-cta { display: inline-flex; align-items: center; height: 44px; padding: 0 20px; border-radius: 9999px; background: var(--inv-bg); color: var(--inv-fg); font-size: 14px; font-weight: 500; text-decoration: none; white-space: nowrap; transition: background .2s; }
.header-cta:hover { background: var(--inv-hover); }
.header-end { display: flex; align-items: center; gap: 8px; }
.menu-btn { display: none; align-items: center; gap: 8px; height: 40px; padding: 0 14px; border-radius: 9999px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); font: 500 14px var(--sans); cursor: pointer; }
.menu-btn .bars { width: 14px; height: 10px; background: linear-gradient(currentColor 0 0) top / 100% 1.5px no-repeat, linear-gradient(currentColor 0 0) center / 100% 1.5px no-repeat, linear-gradient(currentColor 0 0) bottom / 100% 1.5px no-repeat; }
.mobile-nav { position: fixed; z-index: 49; top: calc(96px + env(safe-area-inset-top, 0px)); left: max(24px, env(safe-area-inset-left, 0px)); right: max(24px, env(safe-area-inset-right, 0px));
  background: var(--bg); border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow-lg); padding: 10px; display: grid; gap: 2px; max-height: calc(100vh - 120px); overflow-y: auto; }
.mobile-nav a { padding: 12px 14px; border-radius: 12px; text-decoration: none; font-weight: 500; color: var(--ink); }
.mobile-nav a:hover { background: var(--hover); }
@media (max-width: 1100px) { .nav-links { display: none; } .menu-btn { display: inline-flex; } }
@media (max-width: 768px) {
  .site-header { top: calc(10px + env(safe-area-inset-top, 0px)); left: max(12px, env(safe-area-inset-left, 0px)); right: max(12px, env(safe-area-inset-right, 0px)); height: 58px; padding: 0 8px 0 16px; }
  .header-cta { display: none; }
  .mobile-nav { top: calc(76px + env(safe-area-inset-top, 0px)); left: max(12px, env(safe-area-inset-left, 0px)); right: max(12px, env(safe-area-inset-right, 0px)); } }

/* buttons */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 14px 28px; border-radius: 4px; font: 500 15px var(--sans); letter-spacing: -0.01em; text-decoration: none; cursor: pointer; transition: background .2s, transform .2s, border-color .2s; }
.btn-primary { background: var(--inv-bg); color: var(--inv-fg); border: 1px solid var(--inv-bg); }
.btn-primary:hover { background: var(--inv-hover); transform: translateY(-1px); }
.btn-outline { background: var(--bg); color: var(--ink); border: 1px solid var(--line); }
.btn-outline:hover { border-color: var(--ink); }
.arrow { display: inline-block; transition: transform .2s; }
.btn:hover .arrow, .btn-light:hover .arrow, .more:hover .arrow { transform: translateX(3px); }
.more { display: inline-flex; gap: 6px; font-weight: 600; font-size: 14px; color: var(--ink); text-decoration: none; border-bottom: 2px solid var(--accent); padding-bottom: 3px; }
.badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 13px; border: 1px solid var(--line); border-radius: 9999px; background: var(--bg); font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--ink); box-shadow: var(--shadow); }
.badge .mark { width: 14px; height: 14px; border-radius: 3px; }

/* hero */
.hero { position: relative; overflow: hidden; display: flex; flex-direction: column; padding-top: clamp(128px, 12vw, 156px); padding-bottom: clamp(40px, 5vw, 64px); }
.hero-art { position: absolute; top: 0; bottom: 0; right: 0; width: 64%; background: var(--map-land); }
.hero-art img { width: 100%; height: 100%; object-fit: cover; object-position: 35% 50%; display: block; filter: var(--hero-filter); }
.mosaic { position: absolute; inset: 0; display: grid; grid-template-columns: repeat(8, 1fr); grid-template-rows: repeat(5, 1fr); }
.mosaic i { background: var(--bg); }
.hero-art::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, var(--bg) 0%, transparent 22%), linear-gradient(0deg, var(--bg) 0%, transparent 18%); }
.art-chip { position: absolute; z-index: 1; right: max(20px, env(safe-area-inset-right, 0px)); top: calc(112px + env(safe-area-inset-top, 0px)); display: inline-flex; align-items: center; gap: 8px; padding: 7px 12px; border-radius: 9999px; background: var(--glass); -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); border: 1px solid var(--line); font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--ink); box-shadow: var(--shadow); }
.art-chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--accent); }
.hero-inner { position: relative; z-index: 1; }
.hero-text { max-width: 640px; }
.hero h1 { font-size: clamp(42px, 6.2vw, 80px); letter-spacing: -0.045em; line-height: 1.02; margin-top: 24px; }
.hero .lede { margin-top: 24px; max-width: 50ch; }
.cta-row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 34px; }
.rise { animation: rise .9s var(--ease) both; }
.rise.d1 { animation-delay: .08s; } .rise.d2 { animation-delay: .16s; } .rise.d3 { animation-delay: .24s; }
@keyframes rise { from { transform: translateY(18px); } to { transform: none; } }
.spec-band { border-bottom: 1px solid var(--line); background: var(--bg); }
.spec-band .specs { border: 0; }
.glance { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: clamp(48px, 7vw, 96px); border: 1px solid var(--line); border-radius: 16px; background: var(--bg); box-shadow: var(--shadow); overflow: hidden; }
.glance div { padding: 22px 24px; border-left: 1px solid var(--line); min-width: 0; }
.glance div:first-child { border-left: 0; }
.glance b { display: block; font-size: clamp(26px, 2.8vw, 36px); font-weight: 500; letter-spacing: -0.035em; line-height: 1.2; font-variant-numeric: tabular-nums; color: var(--ink); }
.glance span { display: block; margin-top: 4px; font-size: 14px; line-height: 1.45; color: var(--muted); }
@media (max-width: 900px) {
  .hero-art { position: relative; order: 2; width: auto; height: 240px; margin-top: 8px; }
  .hero-art::after { background: linear-gradient(180deg, var(--bg) 0%, transparent 35%); }
  .mosaic { display: none; }
  .art-chip { top: auto; bottom: 12px; right: max(16px, env(safe-area-inset-right, 0px)); }
  .glance { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .glance div:nth-child(3) { border-left: 0; }
  .glance div:nth-child(n+3) { border-top: 1px solid var(--line); } }
@media (max-width: 440px) { .glance { grid-template-columns: minmax(0, 1fr); } .glance div { border-left: 0; } .glance div + div { border-top: 1px solid var(--line); } .cta-row .btn { width: 100%; } }

/* data strip */
.sources { border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); background: var(--bg); }
.sources-inner { padding-block: 26px; display: flex; align-items: center; gap: 28px; }
.sources-label { flex: none; font-size: 11px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--ink); }
.marquee { flex: 1; min-width: 0; overflow: hidden; -webkit-mask-image: linear-gradient(90deg, transparent, #000 6% 94%, transparent); mask-image: linear-gradient(90deg, transparent, #000 6% 94%, transparent); }
.track { display: flex; width: max-content; animation: marquee 48s linear infinite; }
.track:hover { animation-play-state: paused; }
.set { display: flex; align-items: center; gap: 44px; padding-right: 44px; }
.set span { font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--soft); white-space: nowrap; }
@keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
@media (max-width: 700px) { .sources-inner { flex-direction: column; align-items: flex-start; gap: 14px; } .marquee { width: 100%; } }

/* problem */
.band-surface { background: var(--surface); border-bottom: 1px solid var(--line); }
.center-head { text-align: center; max-width: 860px; margin: 0 auto; display: grid; justify-items: center; gap: 20px; }
.mini-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-top: 52px; }
.mini { background: var(--bg); border: 1px solid var(--line); border-radius: 16px; padding: 24px 22px; display: grid; gap: 10px; align-content: start; transition: transform .3s var(--ease), box-shadow .3s var(--ease); }
.mini:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.dash { display: flex; gap: 3px; }
.dash i { width: 12px; height: 3px; border-radius: 2px; background: var(--navy); }
.dash i:nth-child(2) { background: var(--accent); }
.dash i:nth-child(3) { background: var(--signal); }
.mini h3 { font-size: 17px; margin-top: 6px; }
.mini p { font-size: 14px; line-height: 1.6; }
.statement { margin: 56px auto 0; max-width: 940px; text-align: center; display: grid; gap: 14px; }
.statement p { font-size: clamp(18px, 2vw, 23px); font-weight: 500; letter-spacing: -0.02em; line-height: 1.5; color: var(--ink); }
@media (max-width: 1000px) { .mini-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .mini-cards { grid-template-columns: minmax(0, 1fr); } }

/* atlas: stripes + scenario explorer */
.band-stripes { background: repeating-linear-gradient(135deg, var(--bg) 0 34px, var(--stripe) 34px 68px); border-bottom: 1px solid var(--line); }
.split { display: grid; grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr); gap: clamp(32px, 5vw, 72px); align-items: start; }
.big-h2 { font-size: clamp(32px, 4.6vw, 58px); max-width: 16ch; }
.lead-h3 { font-size: clamp(21px, 2.2vw, 28px); font-weight: 600; letter-spacing: -0.025em; line-height: 1.25; margin-top: 36px; }
.prose p + p { margin-top: 14px; }
.prose b { color: var(--ink); font-weight: 600; }
.kv { margin-top: 28px; border-top: 1px solid var(--line); }
.kv div { display: flex; justify-content: space-between; align-items: baseline; gap: 18px; padding: 13px 0; border-bottom: 1px solid var(--line); }
.kv span { font-size: 14px; color: var(--muted); }
.kv b { font-size: 18px; font-weight: 600; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--ink); }
.sim { position: relative; background: var(--bg); border: 1px solid var(--line); border-radius: 20px; box-shadow: var(--shadow-lg); padding: 20px; display: grid; gap: 16px; min-width: 0; }
.sim-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.sim-top h3 { font-size: 17px; }
.chip { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 9999px; background: var(--bg); border: 1px solid var(--line); box-shadow: var(--shadow); font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--ink); }
.chip::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--signal); }
.seg { display: flex; flex-wrap: wrap; gap: 6px; }
.seg button { font: 500 13px var(--sans); padding: 8px 13px; border-radius: 9999px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); cursor: pointer; transition: background .2s, color .2s, border-color .2s; }
.seg button:hover { border-color: var(--ink); }
.seg button[aria-pressed="true"] { background: var(--inv-bg); color: var(--inv-fg); border-color: var(--inv-bg); }
.sim-map { position: relative; border-radius: 12px; overflow: hidden; background: var(--map-land); aspect-ratio: MAP_RATIO; max-width: 100%; }
.sim-map img { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.town { position: absolute; display: flex; align-items: center; gap: 5px; transform: translate(-4px, -50%); font-size: 11px; font-weight: 600; color: var(--map-ink); text-shadow: 0 0 3px var(--map-land), 0 0 3px var(--map-land), 0 0 2px var(--map-land); pointer-events: none; white-space: nowrap; }
.town::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--map-ink); box-shadow: 0 0 0 1.5px var(--map-land); }
.town.r { flex-direction: row-reverse; transform: translate(calc(-100% + 4px), -50%); }
.scale { position: absolute; left: 12px; bottom: 10px; width: SCALE_PCT%; font-size: 10px; font-weight: 600; color: var(--map-ink); text-shadow: 0 0 3px var(--map-land); }
.scale::before { content: ""; display: block; height: 5px; border: 1.5px solid var(--map-ink); border-top: 0; margin-bottom: 2px; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); }
.sw { display: inline-block; width: 11px; height: 11px; border-radius: 3px; vertical-align: -1px; margin-right: 6px; }
.sw.fl { background: var(--map-flood); } .sw.rv { background: var(--map-river); } .sw.ld { background: var(--map-land); box-shadow: inset 0 0 0 1px var(--line); }
.sim-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.sim-stats div { background: var(--bg); padding: 12px 14px; min-width: 0; }
.sim-stats b { display: block; font-size: 20px; font-weight: 600; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; color: var(--ink); }
.sim-stats span { display: block; font-size: 12px; line-height: 1.4; color: var(--muted); }
.sim-note { font-size: 13px; line-height: 1.55; min-height: 3.1em; }
@media (max-width: 960px) { .split { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 520px) { .sim { padding: 14px; } .sim-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 28px; }
.pair figcaption b { display: block; color: var(--ink); font-weight: 600; }
@media (max-width: 640px) { .pair { grid-template-columns: minmax(0, 1fr); } }
.sub-h { display: grid; gap: 12px; margin-top: clamp(56px, 7vw, 88px); max-width: 760px; }
.sub-h h3 { font-size: clamp(22px, 2.4vw, 30px); font-weight: 500; letter-spacing: -0.03em; }

/* figures */
.figs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 36px; }
@media (max-width: 760px) { .figs { grid-template-columns: minmax(0, 1fr); } }
.case { margin: 0; background: var(--bg); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; min-width: 0; transition: transform .3s var(--ease), box-shadow .3s var(--ease), border-color .3s; }
.case:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.case .pic { background: var(--paper); padding: 14px; border-bottom: 1px solid var(--line); }
.case .pic.map { padding: 0; background: var(--map-land); }
.case img { display: block; width: 100%; height: auto; }
.case figcaption { padding: 14px 18px 16px; font-size: 13.5px; line-height: 1.55; color: var(--muted); }
.case.wide { grid-column: 1 / -1; }

/* method tiles */
.band-diamond { background: conic-gradient(from 45deg, var(--surface) 25%, var(--stripe) 0 50%, var(--surface) 0 75%, var(--stripe) 0) 0 0 / 240px 240px; border-bottom: 1px solid var(--line); }
.chess { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--ink); border: 1px solid var(--ink); margin-top: 52px; box-shadow: var(--shadow-lg); }
.tile { background: var(--bg); color: var(--ink); padding: clamp(26px, 3vw, 40px); min-height: 250px; display: flex; flex-direction: column; gap: 10px; transition: background .4s var(--ease), color .4s var(--ease); }
.tile .no { font-size: 12px; font-weight: 600; letter-spacing: .04em; }
.tile h3 { font-size: 22px; font-weight: 500; letter-spacing: -0.02em; color: inherit; margin-top: 16px; }
.tile p { font-size: 14px; line-height: 1.6; color: var(--muted); transition: color .4s var(--ease); }
.tile .key { margin-top: auto; padding-top: 16px; font-size: 13px; font-weight: 600; color: var(--accent-ink); font-variant-numeric: tabular-nums; transition: color .4s var(--ease); }
.tile.ink, .tile:not(.ink):hover { background: var(--inv-bg); color: var(--inv-fg); }
.tile.ink p, .tile:not(.ink):hover p { color: var(--inv-muted); }
.tile.ink .key, .tile:not(.ink):hover .key { color: var(--inv-accent); }
.tile.ink:hover { background: var(--bg); color: var(--ink); }
.tile.ink:hover p { color: var(--muted); }
.tile.ink:hover .key { color: var(--accent-ink); }
@media (max-width: 900px) { .chess { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .chess { grid-template-columns: minmax(0, 1fr); } .tile { min-height: 0; } }
.center-link { text-align: center; margin-top: 36px; }

/* model */
.facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 24px; margin-top: 44px; }
.fact { border-top: 1px solid var(--ink); padding-top: 16px; min-width: 0; }
.fact b { display: block; font-size: clamp(30px, 3.4vw, 44px); font-weight: 500; letter-spacing: -0.04em; line-height: 1.1; font-variant-numeric: tabular-nums; color: var(--ink); }
.fact span { display: block; margin-top: 6px; font-size: 14px; line-height: 1.5; color: var(--muted); }
@media (max-width: 900px) { .facts { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 440px) { .facts { grid-template-columns: minmax(0, 1fr); } }
.note { font-size: 14px; color: var(--muted); max-width: 80ch; margin-top: 22px; }

/* specializations */
.acc-wrap { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: clamp(32px, 5vw, 64px); align-items: start; margin-top: 52px; }
.acc-visual { position: sticky; top: 112px; }
.visual-card { position: relative; border-radius: 20px; overflow: hidden; background: var(--paper); border: 1px solid var(--line); box-shadow: var(--shadow-lg); aspect-ratio: 4 / 3; max-width: 100%; }
.visual-card img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; padding: 18px 18px 64px; }
.visual-label { position: absolute; left: 16px; bottom: 16px; background: var(--label-bg); color: var(--label-fg); border-radius: 9999px; padding: 9px 16px; font-size: 13px; font-weight: 600; }
.acc { display: grid; gap: 12px; }
.acc-item { border: 1px solid var(--line); border-radius: 16px; background: var(--bg); color: var(--ink); transition: background .35s var(--ease), color .35s var(--ease), border-color .35s; }
.acc-item.open { background: var(--inv-bg); color: var(--inv-fg); border-color: var(--inv-bg); box-shadow: var(--shadow-lg); }
.acc-head { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 20px 22px; background: none; border: 0; border-radius: 16px; color: inherit; font: 600 18px/1.3 var(--sans); letter-spacing: -0.015em; text-align: left; cursor: pointer; }
.pm { flex: none; position: relative; width: 30px; height: 30px; border-radius: 50%; border: 1px solid var(--line); }
.acc-item.open .pm { border-color: var(--inv-line); }
.pm::before, .pm::after { content: ""; position: absolute; left: 50%; top: 50%; width: 11px; height: 1.5px; background: currentColor; transform: translate(-50%, -50%); transition: transform .3s var(--ease); }
.pm::after { transform: translate(-50%, -50%) rotate(90deg); }
.acc-item.open .pm::after { transform: translate(-50%, -50%) rotate(0deg); }
.acc-body { padding: 0 22px 22px; display: grid; gap: 12px; }
.acc-body p { font-size: 14px; color: var(--inv-muted); }
.acc-body .q { font-size: 15px; color: var(--inv-fg); }
.acc-body .res { font-size: 15px; font-weight: 500; color: var(--inv-fg); }
.fl { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--inv-signal); margin-right: 6px; }
.btn-light { justify-self: start; display: inline-flex; align-items: center; gap: 8px; margin-top: 6px; padding: 11px 18px; border-radius: 4px; background: var(--inv-fg); color: var(--inv-bg); font-size: 14px; font-weight: 500; text-decoration: none; }
@media (max-width: 960px) { .acc-wrap { grid-template-columns: minmax(0, 1fr); } .acc-visual { position: static; } }

/* analyses */
.details { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: clamp(32px, 5vw, 72px); align-items: start; margin-top: 52px; }
.toc { position: sticky; top: 112px; display: grid; gap: 2px; }
.toc .eyebrow { margin-bottom: 10px; }
.toc a { padding: 8px 12px; border-radius: 8px; font-size: 14px; color: var(--muted); text-decoration: none; }
.toc a:hover { background: var(--hover); color: var(--ink); }
.detail { padding-bottom: 56px; border-bottom: 1px solid var(--line); scroll-margin-top: 108px; min-width: 0; }
.detail + .detail { padding-top: 56px; }
.detail:last-child { border-bottom: 0; padding-bottom: 0; }
.detail h3 { font-size: clamp(24px, 2.6vw, 34px); font-weight: 500; letter-spacing: -0.03em; line-height: 1.15; margin: 12px 0 18px; }
.detail .prose { max-width: 72ch; }
@media (max-width: 960px) { .details { grid-template-columns: minmax(0, 1fr); } .toc { position: static; display: flex; flex-wrap: wrap; gap: 8px; } .toc .eyebrow { width: 100%; margin: 0; } .toc a { border: 1px solid var(--line); border-radius: 9999px; padding: 7px 13px; } }

/* tables */
.tablewrap { overflow-x: auto; margin-top: 24px; border: 1px solid var(--line); border-radius: 12px; background: var(--bg); }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th { text-align: left; font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); padding: 11px 14px; border-bottom: 1px solid var(--line); background: var(--surface); white-space: nowrap; }
td { padding: 10px 14px; border-bottom: 1px solid var(--line); vertical-align: top; color: var(--ink); }
tr:last-child td { border-bottom: 0; }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.tag { display: inline-block; padding: 2px 9px; border-radius: 9999px; font-size: 12px; font-weight: 600; white-space: nowrap; background: var(--accent-soft); color: var(--accent-ink); }
.tag.warn { background: var(--warn-soft); color: var(--warn-ink); }

/* field visit */
.steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 48px; }
.step { background: var(--bg); border: 1px solid var(--line); border-radius: 16px; padding: 28px; display: grid; gap: 14px; align-content: start; min-width: 0; }
.step .day { font-size: 12px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--accent-ink); }
.step h3 { font-size: 19px; }
.step ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; font-size: 14px; line-height: 1.6; color: var(--muted); }
@media (max-width: 900px) { .steps { grid-template-columns: minmax(0, 1fr); } }

/* deployment */
.terminal { background: var(--term-bg); color: var(--term-fg); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; box-shadow: var(--shadow-lg); min-width: 0; }
.terminal .bar { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--term-line); font-size: 12px; color: var(--term-muted); }
.terminal .bar i { width: 10px; height: 10px; border-radius: 50%; background: var(--term-line); }
.terminal .bar span { margin-left: 8px; font-family: var(--mono); }
.terminal pre { margin: 0; padding: 18px; overflow-x: auto; font: 12.5px/1.6 var(--mono); white-space: pre; color: var(--term-fg); }

/* team, call to action, footer */
.team { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; margin-top: 44px; }
.person { border: 1px solid var(--line); border-radius: 16px; padding: 22px; background: var(--bg); display: grid; gap: 6px; align-content: start; }
.person b { font-weight: 600; color: var(--ink); }
.person span { font-size: 14px; line-height: 1.5; color: var(--muted); }
@media (max-width: 1000px) { .team { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 480px) { .team { grid-template-columns: minmax(0, 1fr); } }
.cta-band { background: var(--surface); border-top: 1px solid var(--line); text-align: center; }
.cta-band h2 { font-size: clamp(34px, 5.2vw, 64px); }
.cta-band .center-head { gap: 22px; }
footer { border-top: 1px solid var(--line); background: var(--bg); padding-block: 64px 40px; }
.foot-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) repeat(4, minmax(0, 1fr)); gap: 40px; }
.foot-brand { display: grid; gap: 16px; align-content: start; }
.foot-brand p { font-size: 14px; max-width: 38ch; }
.foot-col h4 { font-size: 12px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--ink); margin-bottom: 14px; }
.foot-col a, .foot-col span { display: block; padding: 5px 0; font-size: 14px; color: var(--soft); text-decoration: none; }
.foot-col a:hover { color: var(--accent-ink); }
.foot-bottom { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px 24px; margin-top: 56px; padding-top: 24px; border-top: 1px solid var(--line); font-size: 13px; color: var(--soft); }
.foot-bottom p { font-size: 13px; color: var(--soft); }
@media (max-width: 960px) { .foot-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .foot-brand { grid-column: 1 / -1; } }
/* spec strip (value, blue label, note) */
.specs { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); background: var(--bg); }
.specs > div { padding: 30px 28px; border-left: 1px solid var(--line); min-width: 0; }
.specs > div:first-child { border-left: 0; }
.specs b { display: block; font-size: clamp(28px, 3vw, 38px); font-weight: 500; letter-spacing: -0.035em; line-height: 1.15; color: var(--ink); font-variant-numeric: tabular-nums; }
.specs .lab { display: block; margin-top: 8px; font-size: 14px; font-weight: 600; color: var(--accent-ink); }
.specs .sub { display: block; margin-top: 2px; font-size: 13px; line-height: 1.5; color: var(--muted); }
@media (max-width: 900px) { .specs { grid-template-columns: repeat(2, minmax(0, 1fr)); } .specs > div:nth-child(3) { border-left: 0; } .specs > div:nth-child(n+3) { border-top: 1px solid var(--line); } }
@media (max-width: 440px) { .specs { grid-template-columns: minmax(0, 1fr); } .specs > div { border-left: 0; } .specs > div + div { border-top: 1px solid var(--line); } }
.eyebrow.blue { color: var(--accent-ink); }
/* gap cards */
.gaps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 48px; }
.gap { background: var(--bg); border: 1px solid var(--line); border-radius: 16px; padding: 24px; display: flex; flex-direction: column; gap: 10px; min-width: 0; transition: transform .3s var(--ease), box-shadow .3s var(--ease); }
.gap:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.gap .svc { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--soft); }
.gap h3 { font-size: 18px; line-height: 1.3; }
.gap p { font-size: 14px; line-height: 1.6; }
.gap .ev { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--line); font-size: 13px; font-weight: 600; line-height: 1.5; color: var(--accent-ink); }
@media (max-width: 1000px) { .gaps { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .gaps { grid-template-columns: minmax(0, 1fr); } }
/* a real network of sites */
.net { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); gap: clamp(32px, 5vw, 64px); align-items: start; margin-top: 48px; }
.net-map { position: sticky; top: 112px; }
.net-map .case { box-shadow: var(--shadow-lg); }
.net-note { margin-top: 10px; font-size: 13px; color: var(--muted); }
.sites { list-style: none; margin: 0; padding: 0; display: grid; gap: 22px; }
.sites li { display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 14px; }
.sites .n { width: 30px; height: 30px; border-radius: 50%; background: var(--inv-bg); color: var(--inv-fg); display: grid; place-items: center; font-size: 13px; font-weight: 600; }
.sites h3 { font-size: 17px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.sites .pill { font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 9999px; background: var(--accent-soft); color: var(--accent-ink); }
.sites p { font-size: 14px; line-height: 1.6; margin-top: 4px; }
.sites .why b { color: var(--ink); }
@media (max-width: 960px) { .net { grid-template-columns: minmax(0, 1fr); } .net-map { position: static; } }
/* checked, not assumed */
.audit { margin-top: 40px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; border: 1px solid var(--line); border-radius: 16px; overflow: hidden; background: var(--surface); }
.audit > div { padding: 22px 24px; border-left: 1px solid var(--line); min-width: 0; }
.audit > div:first-child { border-left: 0; }
.audit b { display: block; font-size: 15px; color: var(--ink); }
.audit p { font-size: 13.5px; line-height: 1.6; margin-top: 6px; }
@media (max-width: 900px) { .audit { grid-template-columns: minmax(0, 1fr); } .audit > div { border-left: 0; } .audit > div + div { border-top: 1px solid var(--line); } }
/* roadmap of further training */
.road { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 44px; }
.road article { background: var(--bg); border: 1px solid var(--line); border-radius: 16px; padding: 24px; display: grid; gap: 10px; align-content: start; min-width: 0; }
.road .st { justify-self: start; font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; padding: 3px 10px; border-radius: 9999px; background: var(--accent-soft); color: var(--accent-ink); }
.road .st.done { background: var(--inv-bg); color: var(--inv-fg); }
.road h3 { font-size: 17px; }
.road p { font-size: 14px; line-height: 1.6; }
.road .gain { font-size: 13px; font-weight: 600; color: var(--ink); }
@media (max-width: 1000px) { .road { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .road { grid-template-columns: minmax(0, 1fr); } }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .rise, .track { animation: none; }
  .track { width: auto; } .set { flex-wrap: wrap; row-gap: 10px; } .set[aria-hidden] { display: none; }
  .mini, .case, .tile, .acc-item, .mega, .btn, .arrow { transition: none; } }
""".replace("MAP_RATIO", map_ratio).replace("SCALE_PCT", f"{10 / box_km * 100:.2f}")

JS = """
(function () {
  var data = JSON.parse(document.getElementById("sim-data").textContent);
  var btns = document.querySelectorAll("[data-scen]");
  var img = document.getElementById("sim-img");
  function fmt(x) { return Number(x).toLocaleString("en-US"); }
  function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
  function show(key) {
    var s = data[key];
    if (!s) return;
    btns.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-scen") === key ? "true" : "false"); });
    if (s.img) { img.src = s.img; img.alt = "Flooded land in the " + s.label + " scenario"; }
    set("sim-q", fmt(s.q) + " m³/s");
    set("sim-lakh", s.lakh.toFixed(1) + " lakh cusec");
    set("sim-km2", fmt(Math.round(s.km2)) + " km²");
    set("sim-people", fmt(s.people));
    set("sim-sett", fmt(s.sett));
    set("sim-road", s.road.toFixed(1) + " km");
    set("sim-cut", fmt(s.cut));
    set("sim-note", s.note);
  }
  btns.forEach(function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-scen")); }); });

  var items = document.querySelectorAll(".acc-item");
  var vImg = document.getElementById("acc-img"), vLab = document.getElementById("acc-label");
  function open(it) {
    items.forEach(function (x) {
      var on = x === it;
      x.classList.toggle("open", on);
      x.querySelector(".acc-head").setAttribute("aria-expanded", on ? "true" : "false");
      x.querySelector(".acc-body").hidden = !on;
    });
    if (it.getAttribute("data-img")) { vImg.src = it.getAttribute("data-img"); vImg.alt = it.getAttribute("data-alt"); }
    vLab.textContent = it.getAttribute("data-label");
  }
  items.forEach(function (it) { it.querySelector(".acc-head").addEventListener("click", function () { open(it); }); });

  var mb = document.getElementById("menu-btn"), mn = document.getElementById("mnav");
  function closeMenu() { mn.hidden = true; mb.setAttribute("aria-expanded", "false"); }
  mb.addEventListener("click", function () {
    var willOpen = mn.hidden;
    mn.hidden = !willOpen;
    mb.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });
  mn.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", closeMenu); });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape" && !mn.hidden) { closeMenu(); mb.focus(); } });
})();
"""

NAV = [("#problem", "Problem"), ("#how", "How it works"), ("#atlas", "Atlas"), ("#partner", "For ClimMaTech"),
       ("#deploy", "Deployment"), ("#team", "Team")]
nav_main = "".join(f'<a class="nav-item" href="{h}">{e(t)}</a>' for h, t in NAV[:3])
nav_rest = "".join(f'<a class="nav-item" href="{h}">{e(t)}</a>' for h, t in NAV[3:])
mobile_links = "".join(f'<a href="{h}">{e(t)}</a>' for h, t in NAV[:3] + [("#specializations", "Specializations")] + NAV[3:]) + \
    '<a href="viewer.html">Open the flood map</a>'
mega = '''<div class="mega" role="group" aria-label="Specializations">
  <div class="mm-col"><span class="mm-head">Water and sensing</span><a href="#model">Remote sensing</a><a href="#d-wr">Water resources</a><a href="#d-oc">Ocean</a></div>
  <div class="mm-col"><span class="mm-head">Infrastructure</span><a href="#d-tr">Transportation systems</a><a href="#d-st">Structural</a><a href="#d-gt">Geotechnical</a></div>
  <div class="mm-col"><span class="mm-head">Delivery</span><a href="#d-cm">Construction and management</a><a href="#field">Field visit</a><a href="#training">More training</a></div>
  <div class="mm-feature"><b>Interactive flood map</b><p>Every design flood with the land, roads and settlements it reaches, siren and sensor sites, and the banks to inspect.</p>
    <a class="more" href="viewer.html">Open the flood map <span class="arrow" aria-hidden="true">→</span></a></div>
</div>'''

page = f'''<title>Prithvi Flood-IN</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="What floods when the Mahanadi rises: a satellite flood atlas, flow-to-flood maps and engineering impacts for the Mahanadi delta. IIT Bombay Integrated Design Project with ClimMaTech.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>{CSS}</style>

<header class="site-header">
  <a class="brand" href="#top"><span class="mark" aria-hidden="true"></span>Prithvi Flood-IN</a>
  <nav class="nav-links" aria-label="Sections">
    {nav_main}
    <div class="has-mega"><a class="nav-item" href="#specializations">Specializations <span class="chev" aria-hidden="true"></span></a>{mega}</div>
    {nav_rest}
  </nav>
  <div class="header-end">
    <a class="header-cta" href="viewer.html">Open the flood map</a>
    <button type="button" class="menu-btn" id="menu-btn" aria-expanded="false" aria-controls="mnav"><span class="bars" aria-hidden="true"></span>Menu</button>
  </div>
</header>
<nav class="mobile-nav" id="mnav" aria-label="Sections" hidden>{mobile_links}</nav>

<main id="top">
<section class="hero">
  <div class="hero-art">
    {hero_img}
    <div class="mosaic" aria-hidden="true">{mosaic}</div>
    <span class="art-chip">How often the delta flooded · {n(AS["n_passes"])} radar passes</span>
  </div>
  <div class="container hero-inner">
    <div class="hero-text">
      <span class="badge rise"><span class="mark" aria-hidden="true"></span>IIT Bombay · Civil Engineering IDP 2026</span>
      <h1 class="rise d1">What floods when the Mahanadi rises.</h1>
      <p class="lede rise d2">A river forecast says how much water reaches Naraj. We turn that number into the fields, villages, roads, bridges and river banks that go under, from every radar image of the delta since 2017 and the engineering of seven civil-engineering specializations.</p>
      <div class="cta-row rise d3"><a class="btn btn-primary" href="viewer.html">Open the flood map <span class="arrow" aria-hidden="true">→</span></a><a class="btn btn-outline" href="#how">How it works</a></div>
    </div>
  </div>
</section>

<div class="spec-band"><div class="container"><div class="specs">{specs_html}</div></div></div>

<div class="sources" aria-label="Data sources" style="border-top:0"><div class="container sources-inner">
  <span class="sources-label">Built on open data</span>
  <div class="marquee"><div class="track"><div class="set">{src_set}</div><div class="set" aria-hidden="true">{src_set}</div></div></div>
</div></div>

<section id="problem" class="band-surface"><div class="container">
  <div class="center-head">
    <span class="badge"><span class="mark" aria-hidden="true"></span>The problem in the field</span>
    <h2>Warning systems see the river at a point. Nobody sees what that flow floods.</h2>
    <p class="lede">ClimMaTech, our industry partner, forecasts river level and flow 30 minutes to 48 hours ahead and warns villages through sirens and an app. Each of those numbers belongs to one gauge. Their own architecture lists a map-based River View layer for flood risk; this project builds what such a layer needs for one delta.</p>
  </div>
  <div class="mini-cards">
    <article class="mini"><div class="dash" aria-hidden="true"><i></i><i></i><i></i></div><h3>What exists</h3><p>Radar gauges on bridges and spillways, solar sirens, a control room and the Aagah app, all working from the water level at a point.</p></article>
    <article class="mini"><div class="dash" aria-hidden="true"><i></i><i></i><i></i></div><h3>What is missing</h3><p>Which fields, villages, roads, bridges and embankments go under at the forecast flow, and who must be warned first.</p></article>
    <article class="mini"><div class="dash" aria-hidden="true"><i></i><i></i><i></i></div><h3>Where</h3><p>The Mahanadi delta below Naraj: 3,038 km² of study box, {EXS.get("population_ghsl", 0) / 1e6:.1f} million people, a damaging flood every few years.</p></article>
    <article class="mini"><div class="dash" aria-hidden="true"><i></i><i></i><i></i></div><h3>Who uses it</h3><p>The partner's control room, the Odisha Water Resources Department and CWC, and the district administrations that order evacuations.</p></article>
  </div>
  <div class="statement">
    <span class="eyebrow">Refined problem statement</span>
    <p>For the Mahanadi delta, turn a river-flow forecast at Naraj into a map of what floods and whom it affects, with a satellite model chosen by a fair benchmark, and use that map to plan where warnings and sensors go, checked and calibrated at the site.</p>
  </div>
</div></section>

<section id="atlas" class="band-stripes"><div class="container">
  <div class="split">
    <div>
      <span class="eyebrow">Remote sensing · water resources</span>
      <h2 class="big-h2" style="margin-top:16px">A flood atlas of the delta, linked to the flow at Naraj.</h2>
      <h3 class="lead-h3">Every Sentinel-1 pass since 2017, mapped through monsoon cloud and matched with the river.</h3>
      <div class="prose" style="margin-top:18px">
        <p>The radar model mapped all {n(AS["n_passes"])} passes over the delta. Water outside the river bed and the dry-season water is flood: {n(AS["flooded_ever_km2"])} km² went under at least once. Matching each pass with the GloFAS discharge at Naraj gives every 20 m pixel the flow at which it starts to flood, so a forecast flow becomes a map.</p>
        <p>Pick a flood on the right to see the land it reaches. From the 10-year flood upwards the map is a lower bound: the radar record has not yet seen a larger river.</p>
      </div>
      <div class="kv">
        <div><span>Rank correlation of flooded share with the Naraj flow</span><b>{AS["predictor_spearman"][AS["predictor"]]:.2f}</b></div>
        <div><span>Held-out years, high flows: trigger map against flood climatology (IoU)</span><b>{HF["model"]["iou"]:.2f} vs {HF["climatology"]["iou"]:.2f}</b></div>
        <div><span>Villages flooded on a held-out high-flow pass that the map flagged</span><b>{sett.get("POD", 0):.0%}</b></div>
        <div><span>Agreement with Sentinel-2 water within a day (IoU, clear pixels)</span><b>{s2.get("iou", 0):.2f}</b></div>
      </div>
    </div>
    <div class="sim" aria-label="Scenario explorer">
      <div class="sim-top"><h3>What floods at Naraj flow…</h3><span class="chip">From {n(AS["n_passes"])} radar passes</span></div>
      <div class="seg" role="group" aria-label="Flood scenario">{seg}</div>
      <div class="sim-map"><img id="sim-img" src="{S0["img"]}" alt="Flooded land in the {e(S0["label"])} scenario">{town_html}<span class="scale">10 km</span></div>
      <div class="legend"><span><i class="sw fl"></i>Flooded land</span><span><i class="sw rv"></i>River bed and normal water</span><span><i class="sw ld"></i>Dry land</span></div>
      <div class="sim-stats">
        <div><b id="sim-q">{n(S0["q"])} m³/s</b><span id="sim-lakh">{S0["lakh"]:.1f} lakh cusec</span></div>
        <div><b id="sim-km2">{n(S0["km2"])} km²</b><span>flooded land</span></div>
        <div><b id="sim-people">{n(S0["people"])}</b><span>people living on it</span></div>
        <div><b id="sim-sett">{n(S0["sett"])}</b><span>settlements with 10 % or more flooded</span></div>
        <div><b id="sim-road">{S0["road"]:.1f} km</b><span>road under water</span></div>
        <div><b id="sim-cut">{n(S0["cut"])}</b><span>people cut off from any hospital</span></div>
      </div>
      <p class="sim-note" id="sim-note">{e(S0["note"])}</p>
    </div>
  </div>
  <div class="figs">{fig("atlas_timeseries", "River flow at Naraj and flooded land on every radar pass", True)}{fig("atlas_trigger_map", "The Naraj flow at which each pixel starts to flood")}{fig("atlas_frequency_map", "How often the land flooded, 2017–2026")}</div>
  <div class="sub-h"><span class="eyebrow">The river is not the only driver</span><h3>The same river flow floods {rain_ratio} as much land in a week of heavy rain.</h3>
    <p>The largest floods in the record (September 2018 and 2021) came with heavy rain from Bay of Bengal depressions, not with the highest river flows. Looking up past passes with a similar flow and similar 7-day rain shows the effect for the 5-year flow:</p></div>
  {rain_pair}
  {learned_rain}
  <p class="note">Floodplain flooding is patchy and the observed maps are themselves radar maps, so pass-level scores are modest. Where the delta floods is very predictable from its past floods (ranking skill {auc.get("high_flow_passes", {}).get("clim", 0):.2f}); how much of it floods on a given day only partly ({auc.get("high_flow_passes", {}).get("model", 0):.2f} for the trigger map). The frequency map says where to prepare, the trigger map at which flow to act, and the rain forecast has to be read with the river forecast.</p>
</div></section>

<section id="how" class="band-diamond"><div class="container">
  <div class="center-head">
    <span class="eyebrow">How it works</span>
    <h2>From a radar pass to a warning</h2>
    <p class="lede">Six steps in order, each tested on data it had not seen. Hover or tap a tile to bring it forward.</p>
  </div>
  <div class="chess">
    <article class="tile" tabindex="0"><span class="no">01</span><h3>Choose the model</h3><p>Six geospatial foundation models against a CNN and a U-Net, 92 training runs, scored on an Indian flood none of them saw.</p><span class="key">U-Net {u("lio/unet/full/default"):.3f} · best foundation model {u("lio/prithvi/full/default"):.3f}</span></article>
    <article class="tile ink" tabindex="0"><span class="no">02</span><h3>Map every pass</h3><p>A radar-only TerraMind + U-Net fusion maps every Sentinel-1 pass over the delta, monsoon and dry season.</p><span class="key">{n(AS["n_passes"])} passes · {n(AS["flooded_ever_km2"])} km² flooded at least once</span></article>
    <article class="tile ink" tabindex="0"><span class="no">03</span><h3>Link to river flow</h3><p>Each 20 m pixel gets the Naraj flow at which it starts to flood, fitted without the year it predicts.</p><span class="key">IoU {HF["model"]["iou"]:.2f} vs {HF["climatology"]["iou"]:.2f} at high flows</span></article>
    <article class="tile" tabindex="0"><span class="no">04</span><h3>Count the impact</h3><p>People, roads, hospitals, bridges, river banks and foundations for every design flood.</p><span class="key">{n(cut_25)} people cut off in a 25-year flood</span></article>
    <article class="tile" tabindex="0"><span class="no">05</span><h3>Plan the response</h3><p>Sirens where exposed people live, a sensor on each distributary, raised links, the months to build in.</p><span class="key">{dep.get("sirens", 40)} sirens · {dep.get("sensor_sites", 6)} river sensors · {e(win)}</span></article>
    <article class="tile ink" tabindex="0"><span class="no">06</span><h3>Check at the site</h3><p>Random field points, discharge, soils, wells and bridges measure what the models assume, and change the numbers.</p><span class="key">40 ground-truth points · 8 field protocols</span></article>
  </div>
  <p class="center-link"><a class="more" href="#specializations">See the seven analyses <span class="arrow" aria-hidden="true">→</span></a></p>
</div></section>

<section id="model"><div class="container">
  <div class="center-head" style="text-align:left;justify-items:start;margin:0">
    <span class="eyebrow">Remote sensing · model selection</span>
    <h2>On a flood it had never seen, a U-Net beat every foundation model.</h2>
    <p class="lede">92 training runs on Sen1Floods11 with one recipe: six geospatial foundation models (Prithvi-EO-2.0, TerraMind, DOFA, Clay, Satlas, DeCUR), frozen and fine-tuned, against a CNN and a U-Net, three seeds each. The test that matters is the leave-India-out split: a 2016 Assam flood that no model saw in training.</p>
  </div>
  <div class="facts">
    <div class="fact"><b>{u("lio/unet/full/default"):.3f}</b><span>U-Net water IoU on the unseen Assam flood</span></div>
    <div class="fact"><b>{u("lio/prithvi/full/default"):.3f}</b><span>best foundation model (Prithvi-EO-2.0)</span></div>
    <div class="fact"><b>{u("lio/enstop3_mean/full/default"):.3f}</b><span>fusion of U-Net, CNN and the best foundation model</span></div>
    <div class="fact"><b>{R20.get("calibrated_test_iou", 0):.3f}</b><span>radar-only TerraMind + U-Net on 20 m radar, the model that maps the monsoon</span></div>
  </div>
  {audit_html}
  <div class="figs">{fig("bars_lio", "Test IoU on the unseen Indian flood, mean ± sd over three seeds")}{fig("modality_ablation", "Radar only, optical only and both: optical wins under clear sky, radar is all that sees a monsoon flood")}</div>
</div></section>

<section id="specializations" class="band-surface" style="border-top:1px solid var(--line)"><div class="container">
  <div class="center-head" style="text-align:left;justify-items:start;margin:0;max-width:780px">
    <span class="eyebrow">Seven specializations, one flood</span>
    <h2>Every civil-engineering discipline gets its own question.</h2>
    <p class="lede">The same flood scenarios feed seven analyses, one per specialization of the department. Each owner also has a measurement to make at the site that can change the answer.</p>
  </div>
  <div class="acc-wrap">
    <div class="acc-visual"><div class="visual-card"><img id="acc-img" src="{imgs.get(d0[3], "")}" alt="{e(d0[0])}: {e(d0[4])}"><span class="visual-label" id="acc-label">{e(d0[0])}</span></div></div>
    <div class="acc">{acc_html}</div>
  </div>
</div></section>

<section id="analyses"><div class="container">
  <div class="center-head" style="text-align:left;justify-items:start;margin:0;max-width:780px">
    <span class="eyebrow">The analyses</span>
    <h2>What each specialization found</h2>
  </div>
  <div class="details">
    <nav class="toc" aria-label="Analyses"><span class="eyebrow">On this page</span><a href="#d-tr">Transportation systems</a><a href="#d-st">Structural</a><a href="#d-gt">Geotechnical</a><a href="#d-oc">Ocean</a><a href="#d-cm">Construction and management</a><a href="#d-wr">Water resources and watershed</a></nav>
    <div>
      <article class="detail" id="d-tr"><span class="eyebrow">Transportation systems</span><h3>A flooded road is a lost hospital trip.</h3>
        <div class="prose"><p>The OpenStreetMap road network becomes a graph, flooded sections are cut, and each village's trip to a hospital, a town and a dry school is compared with dry weather. In the 25-year flood <b>{n(cut_25)} people</b> in {int(TR25["hospital: settlements cut off"])} settlements lose road access to every hospital, and everyday trips grow by about {n(TR25.get("town: extra person-hours of travel per day", 0))} person-hours a day. Ten critical links carry most of the cut-off routes; raising them is costed under construction.</p></div>
        <div class="figs">{fig("impact_T25_map", "25-year flood: roads cut, critical links (circles) and health facilities in the flood", True)}</div></article>

      <article class="detail" id="d-st"><span class="eyebrow">Structural</span><h3>Brick walls crack at about a metre of water; bridge piers must go deep.</h3>
        <div class="prose"><p>Flood depth comes from the ground elevation at the flood edge. A 230 mm brick wall cracks at about {w230[0]:.1f}–{w230[1]:.1f} m of water, and <b>{n(walls.get("T25", {}).get("people_deeper_than_1m", 0))} people</b> live where the 25-year flood is a metre deep or more. At {STR.get("bridges", {}).get("bridges", 0)} major bridges, IRC:78 scour reaches {scour25[0]:.0f}–{scour25[1]:.0f} m below the high flood level if a branch carries a quarter of the 100-year flow; how the flow splits between branches is the missing input.</p></div>
        <div class="figs">{fig("depth_T25_map", "Estimated depth in the 25-year flood; circles: settlements with people on land deeper than 1 m", True)}</div></article>

      <article class="detail" id="d-gt"><span class="eyebrow">Geotechnical</span><h3>River banks to inspect, and dry houses on soaked ground.</h3>
        <div class="prose"><p>Bank cells are ranked by how often water stands behind the bank, the soil and the people nearby, giving twenty sites for the field team to sample. Houses that stay dry but stand within 200 m of flood water on silty clay sit on soaked ground: <b>{n(ground_s.get("people_in_zone", 0))} people</b> in the 25-year flood. Soaking cuts a footing's bearing capacity by about {fe.get("silty_sand_drained", {}).get("reduction_pct", 0)} %, and the clay settles when the water table drops, the cracks that appear weeks after a flood.</p></div>
        <div class="figs">{fig("ground_advisory_map", "Ground-saturation advisory zone around 25-year flood water", True)}</div></article>

      <article class="detail" id="d-oc"><span class="eyebrow">Ocean engineering</span><h3>The Bay of Bengal floods the delta from above.</h3>
        <div class="prose"><p>{OCN.get("systems_within_300km_since_2016", 0)} cyclones and depressions passed within 300 km of the delta since 2016, and {drv_counts.get("cyclone/depression", 0)} of the 20 largest floods seen by radar followed one; {drv_counts.get("rain", 0)} came with heavy rain. Surge and high tide also hold back the drainage of the lower delta, so a tide record is the first ocean dataset to add.</p></div>
        <div class="figs">{fig("flood_drivers", "The 20 largest floods on radar and their drivers", True)}</div></article>

      <article class="detail" id="d-cm"><span class="eyebrow">Construction technology and management</span><h3>Build in {e(win)}; raise the links that matter.</h3>
        <div class="prose"><p>Forty-two years of flows and storm tracks leave <b>{e(win)}</b> free of flood days and nearly free of storms, the window for road raising, embankment repair and installing sensors. Raising {lrk.get("links_by_embankment", 0)} critical links takes about <b>{n(lrk.get("earthwork_m3", 0))} m³</b> of earthwork (about ₹{lrk.get("cost_crore_rs_at_350_per_m3", 0):.2f} crore at an assumed rate); {len(struct_links)} more would need a bridge or vented causeway.</p></div>
        <div class="figs">{fig("gantt", "Deployment schedule for the next monsoon, inside the construction window", True)}</div></article>

      <article class="detail" id="d-wr"><span class="eyebrow">Water resources and the watershed</span><h3>Half of a flood peak comes from below the dam.</h3>
        <div class="prose"><p>{ws_text}A Gumbel fit to {AS["gumbel"]["n_years"]} years of annual maxima at Naraj gives {n(RP[2])} m³/s for the 2-year flood and {n(RP[25])} for the 25-year ({RP[25] / LAKH:.1f} lakh cusec).</p></div>
        <div class="figs">{fig("atlas_area_vs_discharge", "Flooded share of each pass against the Naraj flow", True)}</div></article>
    </div>
  </div>
</div></section>

<section id="partner" class="band-surface" style="border-top:1px solid var(--line)"><div class="container">
  <div class="center-head">
    <span class="eyebrow blue">For ClimMaTech</span>
    <h2>What the partner's system lacks, and what this project adds</h2>
    <p class="lede">We downloaded all 50 pages of climmatech.com, read the product, solution, platform, fact-sheet and case-study pages in full and searched the blog. Each card names one of their services, the gap we found and what this project adds, with the number behind it.</p>
  </div>
  <div class="gaps">{gaps_html}</div>
</div></section>

<section id="field" class="band-stripes" style="border-top:1px solid var(--line)"><div class="container">
  <div class="center-head" style="text-align:left;justify-items:start;margin:0;max-width:780px">
    <span class="eyebrow">Field visit</span>
    <h2>Measure what the models cannot know.</h2>
    <p class="lede">Three days in the delta, built around the gaps: random points to test the map, a discharge and roughness measurement, bridge and bank inspections with soil samples for the IIT Bombay lab, village wells, sensor-site checks and interviews. Every sheet has a script, and every result can change a number.</p>
  </div>
  <div class="steps">
    <article class="step"><span class="day">Day 1 · Cuttack and Naraj</span><h3>Engineers and the river</h3><ul><li>Interviews with WRD and CWC engineers</li><li>The Naraj gauge and barrage</li><li>Cross-section, float timings and slope at a road bridge: discharge and Manning's n</li></ul></article>
    <article class="step"><span class="day">Day 2 · Cuttack–Salepur side</span><h3>Ground truth and banks</h3><ul><li>Ground-truth points GT01–GT20 with flood marks</li><li>Water levels in village wells at 0–500 m from the flood edge</li><li>Bank inspection and soil samples at the top-ranked sites</li></ul></article>
    <article class="step"><span class="day">Day 3 · Kendrapara side</span><h3>Links, facilities, sites</h3><ul><li>Ground-truth points GT21–GT40</li><li>Critical road links and flooded health facilities</li><li>Siren and sensor sites: signal, mounting, access in a flood</li></ul></article>
  </div>
  <div class="tablewrap"><table><thead><tr><th>At the site</th><th>Changes</th></tr></thead><tbody>
    <tr><td>40 random ground-truth points, flood marks, villagers' years</td><td>Atlas accuracy (POD / FAR / CSI); DEM depth check</td></tr>
    <tr><td>Cross-section and float timings at a bridge</td><td>Discharge against GloFAS; Manning's n for the Saint-Venant model</td></tr>
    <tr><td>Bridge deck, flood marks, scour, foundation levels</td><td>IRC:5 clearance, IRC:78 scour check, critical links</td></tr>
    <tr><td>Bank inspection and soil samples for the IIT Bombay lab</td><td>IS 1498 class, piping, rapid-drawdown stability, bank ranking</td></tr>
    <tr><td>Water levels in village wells at 0–500 m from the flood edge</td><td>Distance of the ground-saturation advisory</td></tr>
    <tr><td>Siren and sensor sites: signal, mounting, flood access</td><td>Final deployment list</td></tr>
    <tr><td>Interviews: WRD, CWC, ClimMaTech, villages</td><td>Problem statement; which flow floods which village</td></tr>
  </tbody></table></div>
</div></section>

<section id="training"><div class="container">
  <div class="center-head">
    <span class="eyebrow blue">More training</span>
    <h2>What we trained next, and what comes after</h2>
    <p class="lede">Each step targets a measured weakness of the current maps, uses data we already hold or can measure, and has a test that decides whether it helped.</p>
  </div>
  <div class="road">{road_html}</div>
</div></section>

<section id="deploy" class="band-surface" style="border-top:1px solid var(--line)"><div class="container">
  <div class="split">
    <div>
      <span class="eyebrow">Deployment</span>
      <h2 style="margin-top:16px">From a forecast to a bulletin in seconds.</h2>
      <div class="prose" style="margin-top:20px">
        <p>A forecast flow at Naraj (m³/s or lakh cusec, and optionally the forecast rain) goes in; a flood map, the settlements to warn and the roads under water come out, ready for a control room or a phone alert.</p>
        <p>Sirens go where exposed people live: {dep.get("sirens", 40)} sirens reach {SIT.get("coverage", {}).get("1500", {}).get("share", 0):.0%} of the {n(SIT.get("exposed_people", 0))} exposed people at a 1.5 km audible range, and phone alerts reach the rest. One radar gauge on each main distributary measures how the flood splits between the branches.</p>
      </div>
    </div>
    <div class="terminal"><div class="bar"><i></i><i></i><i></i><span>forecast_to_impact.py --q {round(RP[25])}</span></div><pre>{e(bul_txt)}</pre></div>
  </div>
  <div class="center-head" style="margin-top:clamp(56px, 7vw, 88px)">
    <span class="eyebrow blue">Where it observes</span>
    <h2>A network of sites, chosen from the data</h2>
    <p class="lede">The partner's solution pages draw illustrative layouts. This one is the Mahanadi delta, with every site placed by the analysis and a reason you can check.</p>
  </div>
  <div class="net">
    <div class="net-map">{fig("siting_map", "Siren sites with 1.5 km coverage and the river-sensor bridges", False)}<p class="net-note">The Mahanadi delta. Real sites, from impact_siting.py.</p></div>
    <ol class="sites">{sites_html}</ol>
  </div>
</div></section>

<section id="next" class="band-surface" style="border-top:1px solid var(--line)"><div class="container">
  <div class="center-head" style="text-align:left;justify-items:start;margin:0">
    <span class="eyebrow">What comes next</span>
    <h2>One next step per specialization</h2>
  </div>
  <div class="tablewrap"><table><thead><tr><th>Specialization</th><th>Next step</th><th>Why</th></tr></thead><tbody>
    <tr><td>Remote sensing</td><td>SWOT water-surface elevations and NISAR L-band radar</td><td>Measured water levels for depth; flooding under crops and trees</td></tr>
    <tr><td>Water resources</td><td>Refit with observed CWC flows; a 2-D HEC-RAS model calibrated on the atlas</td><td>Floods larger than any seen since 2017</td></tr>
    <tr><td>Transportation systems</td><td>Closures in time during flood onset; school and market access; evacuation timing</td><td>When villages are cut off, not only whether</td></tr>
    <tr><td>Structural</td><td>Depth–damage curves for kutcha and pucca houses</td><td>Money at risk, for the cost–benefit of protection</td></tr>
    <tr><td>Geotechnical</td><td>2-D seepage of the top embankments; bank-line migration from Landsat since 1990</td><td>Piping and erosion risk in numbers</td></tr>
    <tr><td>Ocean</td><td>Paradip tide record, surge hindcasts, sea-level rise</td><td>Compound river, rain and surge flooding</td></tr>
    <tr><td>Construction technology and management</td><td>Life-cycle cost, O&amp;M plan, procurement through GeM</td><td>From a plan to an executable project</td></tr>
  </tbody></table></div>
</div></section>

<section id="team"><div class="container">
  <div class="center-head" style="text-align:left;justify-items:start;margin:0">
    <span class="eyebrow">Team</span>
    <h2>Five students, seven specializations</h2>
  </div>
  <div class="team">
    <div class="person"><b>Nikhil Upadhyay</b><span>Team lead · water resources and ocean: flow-to-flood model, design floods, storm drivers; organises the visit</span></div>
    <div class="person"><b>Vineet Jangir</b><span>Remote sensing: benchmark of six foundation models, fusion, the 20 m radar model</span></div>
    <div class="person"><b>Prakhar Gupta</b><span>Remote sensing: flood atlas from every Sentinel-1 pass, Sentinel-2 check, map viewer</span></div>
    <div class="person"><b>Himanshu Shete</b><span>Transportation and structural: hospital access, critical links, walls, bridge scour; integration of the impact chain, bulletin tool, website and report</span></div>
    <div class="person"><b>Prabhat Kumar</b><span>Geotechnical and construction management: banks, ground saturation, foundations, work windows, deployment plan</span></div>
  </div>
  <p class="note">Faculty guide: Prof. Basudev Biswal, Department of Civil Engineering, IIT Bombay. Industry partner: ClimMaTech Pvt. Ltd. (IIT Mandi), Dr. Vivek Gupta and Siddik Barbhuiya.</p>
</div></section>

<section class="cta-band"><div class="container">
  <div class="center-head">
    <span class="eyebrow">Explore the data</span>
    <h2>See what a forecast floods.</h2>
    <p class="lede">Pick a flood and see the land, villages and roads that go under, with the sirens and sensors that would warn them.</p>
    <a class="btn btn-primary" href="viewer.html">Open the flood map <span class="arrow" aria-hidden="true">→</span></a>
  </div>
</div></section>
</main>

<footer><div class="container">
  <div class="foot-grid">
    <div class="foot-brand">
      <a class="brand" href="#top"><span class="mark" aria-hidden="true"></span>Prithvi Flood-IN</a>
      <p>A flood atlas, flow-to-flood maps and engineering impacts for the Mahanadi delta. Integrated Design Project, Department of Civil Engineering, IIT Bombay, 2026.</p>
      <span class="badge" style="justify-self:start"><span class="mark" aria-hidden="true"></span>IIT Bombay · CE IDP 2026</span>
    </div>
    <div class="foot-col"><h4>Project</h4><a href="#problem">Problem</a><a href="#atlas">Atlas</a><a href="#how">How it works</a><a href="#model">Model</a><a href="#team">Team</a></div>
    <div class="foot-col"><h4>Specializations</h4><a href="#d-tr">Transportation</a><a href="#d-gt">Geotechnical</a><a href="#d-st">Structural</a><a href="#d-oc">Ocean</a><a href="#d-cm">Construction</a><a href="#d-wr">Water resources</a></div>
    <div class="foot-col"><h4>Use it</h4><a href="viewer.html">Flood map</a><a href="#deploy">Bulletin tool</a><a href="#partner">For ClimMaTech</a><a href="#field">Field visit</a><a href="#training">More training</a></div>
    <div class="foot-col"><h4>Data</h4><span>Sentinel-1 and -2 (Planetary Computer)</span><span>GloFAS v4 and ERA5 (Open-Meteo)</span><span>GHSL, WorldCover, Copernicus DEM</span><span>SoilGrids, IBTrACS</span><span>© OpenStreetMap contributors</span></div>
  </div>
  <div class="foot-bottom"><p>© 2026 Prithvi Flood-IN team, IIT Bombay. Not an official ClimMaTech product or flood warning.</p><p>Faculty guide: Prof. Basudev Biswal</p></div>
</div></footer>

<script type="application/json" id="sim-data">{sim_json}</script>
<script>{JS}</script>
'''
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n").write(page)

dash = os.path.join(ROOT, "dashboard", "index.html")
if os.path.exists(dash):
    body = open(dash, encoding="utf-8").read()
    # the viewer carries its own header; on the site its "Project site" link points back to the home page
    body = body.replace('<a class="home" href="#" data-home hidden>', '<a class="home" href="index.html" data-home>')
    viewer = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
              '<style>html,body{margin:0}</style></head><body>\n' + body + "\n</body></html>\n")
    open(os.path.join(OUT, "viewer.html"), "w", encoding="utf-8", newline="\n").write(viewer)
print("website written:", OUT, "figures", len(imgs), "maps", len(maps), "towns", towns)
