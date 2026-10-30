"""OSM layers from a Geofabrik extract when the public Overpass servers are overloaded (they returned 502/504
for every query on 28 Oct 2026). Writes the same osm_<layer>.geojson files as fetch_context.py, for the layers
that are still missing (roads, which need node ids for the network graph, come from Overpass).

    python mahanadi/fetch_osm_pbf.py <eastern-zone-latest.osm.pbf> <out_dir> [basin]

Reads the GDAL OSM driver layers 'points', 'lines' and 'multipolygons' inside the AOI; other tags are parsed
from the hstore column other_tags.
"""
import os
import re
import sys

import geopandas as gpd
import pandas as pd
import pyogrio

from basins import BASINS  # noqa: E402

pbf, out = sys.argv[1], sys.argv[2]
BBOX = tuple(BASINS[sys.argv[3] if len(sys.argv) > 3 else "mahanadi"]["bbox"])
KV = re.compile(r'"([^"]+)"=>"((?:[^"\\]|\\.)*)"')


def load(layer):
    df = pyogrio.read_dataframe(pbf, layer=layer, bbox=BBOX)
    tags = df["other_tags"].fillna("").map(lambda s: dict(KV.findall(s)))
    for key in ("amenity", "healthcare", "railway", "embankment", "emergency", "building", "place", "name:en",
                "waterway", "man_made", "bridge", "layer"):
        vals = tags.map(lambda d: d.get(key))
        if key in df.columns:
            df[key] = df[key].where(df[key].notna(), vals)
        else:
            df[key] = vals
    df = df.rename(columns={"name:en": "name_en"})
    df["osm_id"] = df["osm_id"].astype(str)
    return df.drop(columns=["other_tags"])


pts, lines, polys = load("points"), load("lines"), load("multipolygons")
polys_c = polys.copy()
polys_c["geometry"] = polys_c.geometry.representative_point()
lay = {
    # roads from the extract have no OSM node ids, so they serve the exposure counts but not the routing graph
    # (impact_transport.py needs the Overpass roads layer)
    "roads": lines[lines["highway"].isin(["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
                                          "residential", "living_street", "service", "track", "road"]) |
                   lines["highway"].fillna("").str.endswith("_link")],
    "railways": lines[lines["railway"] == "rail"],
    "waterways": lines[lines["waterway"].isin(["river", "canal", "stream", "drain"])],
    "embankments": lines[(lines["embankment"] == "yes") | lines["man_made"].isin(["embankment", "dyke"])],
    "places": pts[pts["place"].isin(["city", "town", "village", "hamlet", "suburb", "neighbourhood", "locality"])],
    "health": pd.concat([pts, polys_c])[lambda d: d["amenity"].isin(["hospital", "clinic", "doctors"]) | d["healthcare"].notna()],
    "schools": pd.concat([pts, polys_c])[lambda d: d["amenity"].isin(["school", "college", "university"])],
    "emergency": pd.concat([pts, polys_c])[lambda d: d["emergency"].notna() | (d["amenity"] == "shelter") | (d["building"] == "shelter")],
}
for name, gdf in lay.items():
    path = f"{out}/osm_{name}.geojson"
    if os.path.exists(path):
        print("keep existing", path)
        continue
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=4326)
    keep = [c for c in ("osm_id", "name", "name_en", "highway", "bridge", "railway", "waterway", "place", "amenity", "healthcare",
                        "embankment", "man_made", "emergency", "building", "geometry") if c in gdf.columns]
    gdf[keep].to_file(path, driver="GeoJSON")
    print(f"osm {name}: {len(gdf)} features (Geofabrik extract)")
