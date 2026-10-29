"""Structural screening: masonry walls against flood depth, and scour at the major bridges (IRC:78, Lacey).

    python mahanadi/impact_structures.py      (after impact_depth.py and impact_siting.py)

1. Walls. Water on one side of an unreinforced brick wall gives a base moment M = gamma_w d^3 / 6 per metre of wall;
   the wall cracks when M exceeds its out-of-plane capacity f_t t^2 / 6 (self-weight ignored, conservative), so the
   critical depth is d_crit = (f_t t^2 / gamma_w)^(1/3). With f_t = 0.1-0.2 MPa (flexural tension of brick masonry):
   230 mm wall 0.8-1.0 m, 115 mm wall 0.5-0.6 m, close to the ~1 m reported for flood-damaged masonry. People living
   on land deeper than d_crit (impact_depth.py) are the structural-damage screening list. Mud (kutcha) walls lose
   strength with soaking at any depth.
2. Bridges. Lacey regime scour as in IRC:78: d_sm = 1.34 (Db^2 / Ksf)^(1/3), Db = Q / L (discharge per metre of
   linear waterway), Ksf = 1.76 sqrt(dm); maximum scour below HFL: 2.0 d_sm at piers, 1.27 d_sm in a straight
   reach / at abutments. Q = share of the Naraj design flood carried by the branch (+10 % as IRC:78 allows for
   catchments above 25,000 km2); the split between distributaries is not known here (asked from WRD in the field), so
   shares of 25, 50 and 75 % are reported. dm = 0.3 mm (fine sand bed; replaced by the field sieve result).
Outputs in runs/_atlas/impact: structures_summary.json, bridge_scour.csv, wall_risk_settlements.csv
"""
import json

import numpy as np
import pandas as pd
from scipy import ndimage

from impact_common import ATLAS, CTX, IMPACT, Grid, dump, read

g = Grid()
GW = 9.81e3  # N/m3
out = {"walls": {}, "bridges": {}}
wall_cases = {f"{t * 1000:.0f} mm wall, f_t {ft / 1e6:.1f} MPa": (t, ft) for t in (0.23, 0.115) for ft in (0.1e6, 0.2e6)}  # Pa
dcrit = {k: round((ft * t * t / GW) ** (1 / 3), 2) for k, (t, ft) in wall_cases.items()}
out["walls"]["critical_depth_m"] = dcrit
D_SCREEN = 1.0  # m, 230 mm wall with f_t ~0.15 MPa

pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))
lab = read(f"{IMPACT}/settlement_labels.tif")
st = pd.read_csv(f"{IMPACT}/settlements.csv")
rows = []
for name in ("T5", "T25", "T100"):
    try:
        dd = read(f"{IMPACT}/depth_{name}.tif").astype(np.float64)
    except Exception:
        continue
    depth = np.where(dd == 255, 0, dd / 10)
    deep = depth >= D_SCREEN
    out["walls"][name] = dict(people_deeper_than_1m=round(float(pop[deep].sum())),
                              people_deeper_than_0_6m=round(float(pop[depth >= 0.6].sum())))
    if name == "T25":
        share = ndimage.sum(pop * deep, lab, st.settlement.values) / np.maximum(st["pop"].values, 1)
        hit = st.assign(share=share, people=st["pop"] * share)
        hit = hit[hit.share >= 0.05].sort_values("people", ascending=False)
        hit[["name", "lon", "lat", "pop", "share", "people"]].round(4).to_csv(f"{IMPACT}/wall_risk_settlements.csv", index=False)
        out["walls"]["settlements_with_5pct_people_deeper_1m_T25"] = int(len(hit))

S = json.load(open(f"{ATLAS}/atlas_summary.json"))
RP = {int(k): v for k, v in S["gumbel"]["return_period_m3s"].items()}
sen = pd.read_csv(f"{IMPACT}/sensor_sites.csv")
major = pd.read_csv(f"{IMPACT}/major_bridges.csv")
br = pd.concat([sen, major.sort_values("water_m", ascending=False).head(6)]).drop_duplicates(["lon", "lat"])
DM = 0.3
ksf = 1.76 * np.sqrt(DM)
for _, b in br.iterrows():
    L = float(b.length_m)
    for T in (25, 100):
        for share in (0.25, 0.5, 0.75):
            Q = RP[T] * share * 1.10
            db = Q / L
            dsm = 1.34 * (db ** 2 / ksf) ** (1 / 3)
            rows.append(dict(river=b.get("river"), bridge=b.get("name") if isinstance(b.get("name"), str) else b.get("ref"),
                             lat=b.lat, lon=b.lon, linear_waterway_m=round(L), T=T, share=share, Q_m3s=round(Q),
                             Db_m3s_per_m=round(db, 2), d_sm_m=round(dsm, 2), pier_scour_below_HFL_m=round(2.0 * dsm, 1),
                             abutment_scour_below_HFL_m=round(1.27 * dsm, 1)))
sc = pd.DataFrame(rows)
sc.to_csv(f"{IMPACT}/bridge_scour.csv", index=False)
mid = sc[(sc["T"] == 100) & (sc.share == 0.5)]
q25 = sc[(sc["T"] == 100) & (sc.share == 0.25)]
out["bridges"] = dict(dm_mm=DM, silt_factor=round(ksf, 3), bridges=int(len(br)),
                      pier_scour_T100_share25_range_m=[float(q25.pier_scour_below_HFL_m.min()), float(q25.pier_scour_below_HFL_m.max())],
                      pier_scour_T100_share50_range_m=[float(mid.pier_scour_below_HFL_m.min()), float(mid.pier_scour_below_HFL_m.max())],
                      note="the share of the Naraj flow each branch carries is unknown; minor distributaries carry far less than half")
dump(out, f"{IMPACT}/structures_summary.json")
print(json.dumps(out, indent=1))
print(mid[["river", "bridge", "linear_waterway_m", "Q_m3s", "Db_m3s_per_m", "pier_scour_below_HFL_m"]].to_string(index=False))
print("STRUCTURES_DONE")
