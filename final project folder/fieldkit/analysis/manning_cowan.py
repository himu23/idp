"""Manning's n of a channel reach from field observation (Cowan 1956, values from Chow 1959, Table 5-5).

    python fieldkit/analysis/manning_cowan.py <manning_cowan.csv>

n = (n0 + n1 + n2 + n3 + n4) * m5, one row per reach. Columns take the words below (case-insensitive); for the
ranges in Chow's table the mid value is used and the low/high ends are reported. Compare with the n
back-calculated from discharge + slope (discharge_velocity_area.py) and with the n = 0.015 the PINN uses.
"""
import sys

import pandas as pd

TABLE = {
    "base_material": {"earth": (0.020,), "rock cut": (0.025,), "fine gravel": (0.024,), "coarse gravel": (0.028,)},
    "irregularity": {"smooth": (0.000,), "minor": (0.005,), "moderate": (0.010,), "severe": (0.020,)},
    "section_variation": {"gradual": (0.000,), "alternating occasionally": (0.005,),
                          "alternating frequently": (0.010, 0.015)},
    "obstructions": {"negligible": (0.000,), "minor": (0.010, 0.015), "appreciable": (0.020, 0.030),
                     "severe": (0.040, 0.060)},
    "vegetation": {"low": (0.005, 0.010), "medium": (0.010, 0.025), "high": (0.025, 0.050),
                   "very high": (0.050, 0.100)},
    "meandering": {"minor": (1.000,), "appreciable": (1.150,), "severe": (1.300,)},
}


def cowan(row):
    lo = hi = 0.0
    for k in ("base_material", "irregularity", "section_variation", "obstructions", "vegetation"):
        v = TABLE[k][str(row[k]).strip().lower()]
        lo, hi = lo + v[0], hi + v[-1]
    m = TABLE["meandering"][str(row["meandering"]).strip().lower()][0]
    return round(m * (lo + hi) / 2, 4), round(m * lo, 4), round(m * hi, 4)


if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1])
    df[["n", "n_low", "n_high"]] = df.apply(lambda r: pd.Series(cowan(r)), axis=1)
    print(df[["site_id", "n", "n_low", "n_high"]].to_string(index=False))
    df.to_csv(sys.argv[1].replace(".csv", "_result.csv"), index=False)
