"""River-bank / embankment screening for geotechnical inspection: where to inspect banks and take soil samples.

    python mahanadi/impact_geotech.py

Major channels = connected areas of normal water larger than 1 km2. Bank zone = land within 300 m of a major
channel; "behind the bank" = land 300-1,500 m from it. For every 1 km x 1 km cell that contains bank zone:
  behind_freq   mean flood frequency behind the bank (water there points to overtopping, seepage/breach or
                blocked drainage; it is the load that saturates the bank toe);
  years_flooded number of years in which >= 5 % of the land behind the bank flooded at least once;
  soil          SoilGrids 2.0 sand/silt/clay of the top 30 cm in the bank zone -> USDA texture class;
                erodibility = 1 - min(clay, 35)/35 (clay-poor silts and sands erode and pipe most easily;
                plasticity is not available from SoilGrids, which is why the field samples matter);
  people        population within 2 km.
Priority = mean of the four percentile ranks. The field-inspection list is the 20 highest cells at least 3 km apart.
Outputs in runs/_atlas/impact: geotech_cells.csv, geotech_top20.csv, geotech_summary.json
"""
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from impact_common import ATLAS, CTX, IMPACT, Grid, dump, osm, read, read_all


def usda(sand, silt, clay):
    s2c, s15c = silt + 2 * clay, silt + 1.5 * clay
    if s15c < 15:
        return "sand"
    if s2c < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52) or (clay < 7 and silt < 50):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


g = Grid()
to_ll = Transformer.from_crs(g.crs, 4326, always_xy=True)
normal = read(f"{ATLAS}/normal_water_latest.tif").astype(bool)
lab, n = ndimage.label(normal, structure=np.ones((3, 3)))
size = np.bincount(lab.ravel())
size[0] = 0
channel = np.isin(lab, np.where(size * 400 / 1e6 > 1.0)[0])
dist = ndimage.distance_transform_edt(~channel) * 20.0
bank = (dist > 0) & (dist <= 300)
behind = (dist > 300) & (dist <= 1500)
freq = read(f"{ATLAS}/flood_frequency.tif").astype(np.float32)
freq[freq == 255] = np.nan
freq /= 100
ext, desc = read_all(f"{ATLAS}/max_extent_by_year.tif")
sand, silt, clay = (read(f"{CTX}/grid20_{p}.tif") for p in ("sand", "silt", "clay"))
p100 = pd.read_parquet(f"{IMPACT}/pop100.parquet")
ptree = cKDTree(p100[["x", "y"]].values)

C = 50  # 50 x 20 m = 1 km cells
rows = []
for i0 in range(0, g.H, C):
    for j0 in range(0, g.W, C):
        sl = (slice(i0, i0 + C), slice(j0, j0 + C))
        bk, bh = bank[sl], behind[sl]
        if bk.sum() < 50 or bh.sum() < 200:  # needs >= 2 ha of bank and 8 ha behind it in the cell
            continue
        f = freq[sl][bh]
        if np.isfinite(f).sum() < 100:
            continue
        yrs = int((ext[:, sl[0], sl[1]][:, bh].mean(1) >= 0.05).sum())
        sa, si, cl = (float(np.nanmean(a_[sl][bk])) for a_ in (sand, silt, clay))
        x, y = g.xy(i0 + C / 2, j0 + C / 2)
        rows.append(dict(row=i0 // C, col=j0 // C, x=float(x), y=float(y), behind_freq=float(np.nanmean(f)),
                         years_flooded=yrs, sand=sa, silt=si, clay=cl, texture=usda(sa, si, cl),
                         erodibility=1 - min(cl, 35) / 35,
                         people_2km=float(p100["pop"].values[ptree.query_ball_point([x, y], 2000)].sum())))
cells = pd.DataFrame(rows)
for k in ("behind_freq", "years_flooded", "erodibility", "people_2km"):
    cells[f"rank_{k}"] = cells[k].rank(pct=True)
cells["priority"] = cells[[c for c in cells if c.startswith("rank_")]].mean(1)
cells["lon"], cells["lat"] = to_ll.transform(cells.x.values, cells.y.values)
cells = cells.sort_values("priority", ascending=False)
cells.round(4).to_csv(f"{IMPACT}/geotech_cells.csv", index=False)
# the field list: highest-priority cells at least 3 km apart (adjacent high cells are one site, not twenty)
picked = []
for _, r in cells.iterrows():
    if all(np.hypot(r.x - q.x, r.y - q.y) >= 3000 for q in picked):
        picked.append(r)
    if len(picked) == 20:
        break
top = pd.DataFrame(picked)[["lon", "lat", "x", "y", "priority", "behind_freq", "years_flooded", "texture", "sand",
                             "silt", "clay", "people_2km"]].round(3)
top.insert(0, "rank", range(1, len(top) + 1))
top.to_csv(f"{IMPACT}/geotech_top20.csv", index=False)
emb = osm("embankments", g.crs)
print(top.to_string(index=False), flush=True)
dump(dict(cells=len(cells), years=desc, texture_counts=cells.texture.value_counts().to_dict(),
          osm_embankments=len(emb), osm_embankment_km=round(float(shapely.length(emb.geometry.values).sum()) / 1000, 1) if len(emb) else 0,
          channel_km2=round(channel.sum() * 400 / 1e6, 1)), f"{IMPACT}/geotech_summary.json")
print("GEOTECH_DONE")
