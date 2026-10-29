"""Vertical clearance of bridges above the high flood level (HFL), from the field inspection sheet.

    python fieldkit/analysis/bridge_clearance.py <bridge_inspection.csv> [design_discharge_m3s]

Measured on the day: deck_to_water_m (tape / laser from the deck edge to the water surface), deck_thickness_m
(deck slab + girder depth below the deck edge), hfl_mark_above_water_m (height of the highest flood mark on a
pier or abutment above the same water surface; or the level local engineers give).
Clearance = (deck_to_water - deck_thickness) - hfl_mark_above_water = soffit above HFL.
Required minimum vertical clearance, IRC:5-2015 cl. 106.2.1 (check the edition in use):
  Q (m3/s)   <0.3: 150 mm | 0.3-3: 450 | 3-30: 600 | 30-300: 900 | 300-3000: 1200 | >3000: 1500 mm
For the Mahanadi distributaries Q > 3000 m3/s, i.e. 1.5 m (default design discharge 5000 m3/s; pass the
branch's design flood, e.g. from the GloFAS return-period table, to change it).
"""
import sys

import pandas as pd

IRC5 = [(0.3, 0.150), (3, 0.450), (30, 0.600), (300, 0.900), (3000, 1.200), (float("inf"), 1.500)]


def required(q):
    return next(c for lim, c in IRC5 if q < lim)


if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1])
    q = float(sys.argv[2]) if len(sys.argv) > 2 else 5000.0
    df["soffit_above_water_m"] = df.deck_to_water_m - df.deck_thickness_m
    df["clearance_above_hfl_m"] = df.soffit_above_water_m - df.hfl_mark_above_water_m
    df["required_m_IRC5"] = required(q)
    df["meets_IRC5"] = df.clearance_above_hfl_m >= df.required_m_IRC5
    print(df[["bridge_id", "river", "soffit_above_water_m", "hfl_mark_above_water_m", "clearance_above_hfl_m",
              "required_m_IRC5", "meets_IRC5", "pier_scour_visible", "debris_accumulation"]].to_string(index=False))
    df.to_csv(sys.argv[1].replace(".csv", "_result.csv"), index=False)
