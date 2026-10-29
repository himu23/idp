"""River discharge from a field cross-section and surface-float timings (velocity-area, mid-section method).

    python fieldkit/analysis/discharge_velocity_area.py <cross_section.csv> <float_velocity.csv> [<water_surface_slope.csv>]

cross_section.csv   one row per vertical: site_id, station_m (distance from the left water edge), depth_m
                    (water surface to bed; 0 at both edges)
float_velocity.csv  one row per float run: site_id, trial, station_m (where across the channel the float
                    travelled), distance_m (marked reach length), time_s
water_surface_slope.csv (optional) site_id, reach_length_m, water_level_drop_m -> Manning's n

Method (ISO 748 mid-section): q_i = v_i * d_i * (b_{i+1} - b_{i-1}) / 2 and Q = sum(q_i).
Surface float speed v_s = distance/time, averaged per station over trials and interpolated to the verticals;
depth-mean velocity v = k * v_s with k = 0.85 (range 0.80-0.90 reported as the uncertainty; k depends on depth
and bed roughness). With a measured water-surface slope S, Manning's n = A R^(2/3) S^(1/2) / Q
(R = A / wetted perimeter), the roughness the hydraulic and PINN models need instead of an assumed value.
"""
import sys

import numpy as np
import pandas as pd

K, K_LO, K_HI = 0.85, 0.80, 0.90


def site_discharge(xs, fl):
    xs = xs.sort_values("station_m")
    b, d = xs.station_m.to_numpy(float), xs.depth_m.to_numpy(float)
    width = np.empty_like(b)
    width[1:-1] = (b[2:] - b[:-2]) / 2
    width[0], width[-1] = (b[1] - b[0]) / 2, (b[-1] - b[-2]) / 2
    fl = fl.assign(v_s=fl.distance_m / fl.time_s)
    per_station = fl.groupby("station_m").v_s.agg(["mean", "std", "count"]).reset_index()
    vs = np.interp(b, per_station.station_m, per_station["mean"], left=per_station["mean"].iloc[0],
                   right=per_station["mean"].iloc[-1])
    vs[(d <= 0)] = 0.0
    area = float(np.trapezoid(d, b)) if hasattr(np, "trapezoid") else float(np.trapz(d, b))
    wetted = float(np.sum(np.hypot(np.diff(b), np.diff(d))))
    q = {k: float(np.sum(k * vs * d * width)) for k in (K, K_LO, K_HI)}
    cv = float((fl.groupby("station_m").v_s.std() / fl.groupby("station_m").v_s.mean()).mean())
    return dict(top_width_m=round(b[-1] - b[0], 2), area_m2=round(area, 2), wetted_perimeter_m=round(wetted, 2),
                hydraulic_radius_m=round(area / wetted, 3) if wetted else np.nan, max_depth_m=round(d.max(), 2),
                mean_surface_velocity_ms=round(float(fl.v_s.mean()), 3), float_runs=len(fl),
                float_timing_cv=round(cv, 3) if np.isfinite(cv) else None,
                Q_m3s=round(q[K], 3), Q_low_m3s=round(q[K_LO], 3), Q_high_m3s=round(q[K_HI], 3),
                mean_velocity_ms=round(q[K] / area, 3) if area else np.nan)


def main():
    xs_all, fl_all = pd.read_csv(sys.argv[1]), pd.read_csv(sys.argv[2])
    slope = pd.read_csv(sys.argv[3]).set_index("site_id") if len(sys.argv) > 3 else None
    rows = []
    for site, xs in xs_all.groupby("site_id"):
        fl = fl_all[fl_all.site_id == site]
        if fl.empty or len(xs) < 3:
            print(f"{site}: needs >= 3 verticals and >= 1 float run")
            continue
        r = dict(site_id=site, **site_discharge(xs, fl))
        if slope is not None and site in slope.index:
            S = float(slope.loc[site, "water_level_drop_m"]) / float(slope.loc[site, "reach_length_m"])
            r["slope"] = round(S, 6)
            r["manning_n"] = round(r["area_m2"] * r["hydraulic_radius_m"] ** (2 / 3) * np.sqrt(S) / r["Q_m3s"], 4)
            r["manning_n_range"] = (round(r["area_m2"] * r["hydraulic_radius_m"] ** (2 / 3) * np.sqrt(S) / r["Q_high_m3s"], 4),
                                    round(r["area_m2"] * r["hydraulic_radius_m"] ** (2 / 3) * np.sqrt(S) / r["Q_low_m3s"], 4))
        rows.append(r)
    out = pd.DataFrame(rows)
    print(out.T.to_string(header=False))
    out.to_csv(sys.argv[1].replace(".csv", "_discharge_result.csv"), index=False)


if __name__ == "__main__":
    main()
