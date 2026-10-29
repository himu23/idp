"""Ground-saturation advisory: buildings that stay dry but stand on soil soaked by the flood next to them.

    python mahanadi/impact_ground.py      (after impact_exposure.py)

Floodwater raises the water table and saturates the ground around the flooded land. Shallow foundations of houses
there lose bearing capacity (effective stress drops), clayey ground softens, and when the water recedes the
increase in effective stress consolidates soft clay, so houses settle and crack weeks after the flood.
1. Advisory zone: land within 200 m of flooded land that is itself not flooded, on fine-grained soil (SoilGrids silt +
   clay >= 50 % in the top 30 cm, which is most of the delta). Settlements with >= 25 % of their people in the zone
   get a "check foundations after the flood" advisory. 200 m is a screening distance for silty clay over a monsoon;
   the field visit measures water levels in village wells at increasing distance from the flood edge (protocol H)
   to fix it.
2. What the advisory means, worked for typical delta soils (parameters are textbook-typical values, to be replaced
   by the IITB lab results of the field samples; see fieldkit/analysis/foundation_checks.py):
   - strip footing B = 1.0 m at D = 1.0 m; water table deep vs at ground level (Terzaghi with Vesic factors;
     effective unit weight in the q and gamma terms);
   - drained silty sand (c' = 0, phi' = 28 deg, gamma = 18 kN/m3) and undrained clay loam (cu 50 kPa stiff vs 30 kPa
     soaked);
   - consolidation settlement when the water table falls back by 2 m: s = mv * gamma_w * dh * H for a 4 m soft clay
     layer, mv = 0.25-0.5 m2/MN.
Outputs in runs/_atlas/impact: ground_summary.json, ground_advisory_settlements.csv
"""
import json
import math

import numpy as np
import pandas as pd
from scipy import ndimage

from impact_common import CTX, IMPACT, PIX_KM2, Grid, dump, read, scenarios

g = Grid()
scen, normal = scenarios(g)
pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))
fine = (np.nan_to_num(read(f"{CTX}/grid20_silt.tif")) + np.nan_to_num(read(f"{CTX}/grid20_clay.tif"))) >= 50
lab = read(f"{IMPACT}/settlement_labels.tif")
st = pd.read_csv(f"{IMPACT}/settlements.csv")
ZONE_PX = 10  # 200 m
out = {"zone_m": ZONE_PX * 20, "fine_soil_share_of_box": round(float(fine.mean()), 3), "scenarios": {}}
for name in ("T5", "T25", "T100", "freq10"):
    if name not in scen:
        continue
    F = scen[name]
    zone = ndimage.binary_dilation(F, iterations=ZONE_PX) & ~F & ~normal & fine
    share = ndimage.sum(pop * zone, lab, st.settlement.values) / np.maximum(st["pop"].values, 1)
    adv = st.assign(share=share, people=st["pop"] * share)
    adv = adv[adv.share >= 0.25].sort_values("people", ascending=False)
    out["scenarios"][name] = dict(zone_km2=round(float(zone.sum() * PIX_KM2), 1), people_in_zone=round(float(pop[zone].sum())),
                                  people_on_flooded_land=round(float(pop[F].sum())), advisory_settlements=int(len(adv)))
    if name == "T25":
        adv[["name", "lon", "lat", "pop", "share", "people"]].round(4).to_csv(f"{IMPACT}/ground_advisory_settlements.csv",
                                                                               index=False)
        g.save(f"{IMPACT}/ground_zone_T25.tif", zone, "uint8", None)
    print(name, out["scenarios"][name], flush=True)


def factors(phi):
    p = math.radians(phi)
    nq = math.exp(math.pi * math.tan(p)) * math.tan(math.radians(45 + phi / 2)) ** 2
    nc = (nq - 1) / math.tan(p) if phi > 0 else 5.14
    ng = 2 * (nq + 1) * math.tan(p)
    return nc, nq, ng


B, D, GW = 1.0, 1.0, 9.81
gs = 18.0
nc, nq, ng = factors(28)
q_dry = gs * D * nq + 0.5 * gs * B * ng
q_wet = (gs - GW) * D * nq + 0.5 * (gs - GW) * B * ng
cu_dry, cu_wet = 50.0, 30.0
qc_dry = 5.14 * cu_dry + gs * D
qc_wet = 5.14 * cu_wet + gs * D
settle = {mv: round(mv * 1e-3 * GW * 2.0 * 4.0 * 1000, 1) for mv in (0.25, 0.5)}  # mm
out["foundation_example"] = {
    "silty_sand_drained": dict(phi_deg=28, q_ult_dry_kPa=round(q_dry), q_ult_water_at_surface_kPa=round(q_wet),
                               reduction_pct=round(100 * (1 - q_wet / q_dry))),
    "clay_loam_undrained": dict(cu_stiff_kPa=cu_dry, cu_soaked_kPa=cu_wet, q_ult_stiff_kPa=round(qc_dry),
                                q_ult_soaked_kPa=round(qc_wet), reduction_pct=round(100 * (1 - qc_wet / qc_dry))),
    "drawdown_settlement_mm": {f"mv {k} m2/MN": v for k, v in settle.items()},
    "assumptions": "strip footing B 1 m at 1 m depth; gamma 18 kN/m3; Vesic factors; water table drop 2 m over a 4 m soft clay layer"}
dump(out, f"{IMPACT}/ground_summary.json")
print(json.dumps(out, indent=1))
print("GROUND_DONE")
