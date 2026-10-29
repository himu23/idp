"""Infinite-slope stability of an embankment / river-bank face: dry, steady seepage, and rapid drawdown.

    python fieldkit/analysis/embankment_stability.py <embankment_inspection.csv> [<segment_soils.csv>]

FS = c' / (gamma z sin(b) cos(b)) + (gamma_eff / gamma) tan(phi') / tan(b), slip surface parallel to the face at
depth z = 1.5 m. gamma_eff = gamma (dry face); gamma - gamma_w for seepage parallel to the slope (land side during a
flood) and for rapid drawdown (river side when the river falls faster than the bank drains — the classic failure
after a flood). gamma = 18 kN/m3.
phi' and c' by soil class (IS 1498 / USCS from soil_gradation.py; typical values, replace with direct-shear results):
SM 30 deg / 0 kPa, SP 32 / 0, ML 28 / 2, CL or CI 25 / 5, CH 22 / 8, unknown 26 / 3.
segment_soils.csv (optional): segment_id, soil_class. FS < 1.3 under drawdown or seepage = flag for repair.
"""
import math
import sys

import pandas as pd

PARAMS = {"SM": (30, 0), "SP": (32, 0), "SW": (33, 0), "ML": (28, 2), "MI": (27, 3), "CL": (25, 5), "CI": (25, 5),
          "CL-ML": (27, 3), "CH": (22, 8), "MH": (24, 6)}
G, GW, Z = 18.0, 9.81, 1.5


def fs(beta, phi, c, gamma_eff):
    b, p = math.radians(beta), math.radians(phi)
    if beta <= 0:
        return float("inf")
    return c / (G * Z * math.sin(b) * math.cos(b)) + (gamma_eff / G) * math.tan(p) / math.tan(b)


emb = pd.read_csv(sys.argv[1])
soils = pd.read_csv(sys.argv[2]).set_index("segment_id")["soil_class"] if len(sys.argv) > 2 else pd.Series(dtype=str)
rows = []
for _, r in emb.iterrows():
    cls = str(soils.get(r.segment_id, "unknown")).split("-")[0] if r.segment_id in soils.index else "unknown"
    phi, c = PARAMS.get(cls, (26, 3))
    for side, beta in (("river side", r.river_side_slope_deg), ("land side", r.land_side_slope_deg)):
        if pd.isna(beta):
            continue
        rows.append(dict(segment_id=r.segment_id, side=side, slope_deg=beta, soil_class=cls, phi_deg=phi, c_kPa=c,
                         FS_dry=round(fs(beta, phi, c, G), 2),
                         FS_seepage_or_rapid_drawdown=round(fs(beta, phi, c, G - GW), 2)))
out = pd.DataFrame(rows)
out["flag"] = out.FS_seepage_or_rapid_drawdown < 1.3
print(out.to_string(index=False))
out.to_csv(sys.argv[1].replace(".csv", "_stability.csv"), index=False)
