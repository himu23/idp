"""Flood depth from the elevation at the flood edge (FwDET-style), for the structural and road-raising estimates.

    python mahanadi/impact_depth.py

For each connected flood patch of a scenario, the water-surface elevation (WSE) is the median DEM elevation of
the patch's edge pixels (the shoreline); depth = WSE - DEM inside the patch, clipped to 0-6 m. Copernicus GLO-30 is
a surface model (crops, trees, roofs) with ~2 m vertical error, resampled to 20 m: depths are a screening estimate
to be checked against the flood marks measured at the ground-truth points (fieldkit protocol A).
Outputs in runs/_atlas/impact: depth_<scenario>.tif (decimetres, uint8; 255 = not flooded), depth_summary.json
"""
import numpy as np
from scipy import ndimage

from impact_common import CTX, IMPACT, PIX_KM2, Grid, dump, read, scenarios

g = Grid()
scen, normal = scenarios(g)
dem = read(f"{CTX}/grid20_dem.tif").astype(np.float64)
pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))
out = {}
for name in ("T2", "T5", "T10", "T25", "T100", "rain_T5") + tuple(k for k in scen if k.startswith("observed_")):
    if name not in scen:
        continue
    F = scen[name] & np.isfinite(dem)
    lab, n = ndimage.label(F, structure=np.ones((3, 3)))
    edge = F & ~ndimage.binary_erosion(F, structure=np.ones((3, 3)))
    ids = np.arange(1, n + 1)
    wse = np.asarray(ndimage.median(dem, np.where(edge, lab, 0), ids), dtype=np.float64)
    depth = np.zeros_like(dem)
    inside = lab > 0
    depth[inside] = np.clip(wse[lab[inside] - 1] - dem[inside], 0, 6)
    g.save(f"{IMPACT}/depth_{name}.tif", np.where(inside, np.round(depth * 10), 255), "uint8", 255)
    depth = np.round(depth * 10) / 10  # the stored 0.1 m steps, so every script counts the same pixels
    d = depth[inside]
    out[name] = dict(patches=int(n), flooded_km2=round(float(inside.sum() * PIX_KM2), 1),
                     median_depth_m=round(float(np.median(d)), 2) if d.size else 0,
                     p90_depth_m=round(float(np.percentile(d, 90)), 2) if d.size else 0,
                     area_deeper_1m_km2=round(float((depth >= 1).sum() * PIX_KM2), 1),
                     people_deeper_1m=round(float(pop[depth >= 1].sum())),
                     people_deeper_0_5m=round(float(pop[depth >= 0.5].sum())))
    print(name, out[name], flush=True)
dump(dict(method="median DEM of each flood patch's edge = water surface; depth = WSE - DEM, 0-6 m", scenarios=out),
     f"{IMPACT}/depth_summary.json")
print("DEPTH_DONE")
