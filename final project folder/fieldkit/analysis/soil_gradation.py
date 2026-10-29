"""Lab results of embankment / bank soil samples -> classification and internal-erosion screening.

    python fieldkit/analysis/soil_gradation.py <sieve_analysis.csv> <atterberg.csv>

sieve_analysis.csv  sample_id, sieve_mm, mass_retained_g   (pan = sieve_mm 0)
atterberg.csv       sample_id, total_dry_mass_g, liquid_limit_pct, plastic_limit_pct (blank = non-plastic)

Per sample: gravel / sand / fines %, D10, D30, D60, Cu = D60/D10, Cc = D30^2/(D10 D60), PI = LL - PL,
classification by IS 1498 (L/I/H compressibility at LL 35 and 50) and USCS (ASTM D2487, L/H at LL 50),
A-line PI = 0.73 (LL - 20). Internal stability (suffusion) by Kenney & Lau (1986): H/F >= 1 for every F up to
0.20 (Cu > 3) or 0.30 (Cu <= 3), H = F(4d) - F(d); evaluated only above the finest sieve. Screening note:
non-plastic silts and fine uniform sands (SM/ML/SP with PI < 7) are the most prone to backward-erosion piping
under an embankment; clays (PI > 7) resist it.
"""
import sys

import numpy as np
import pandas as pd


def d_at(pct, sizes, finer):
    """Grain size at which `pct` % is finer (log-linear interpolation); NaN if outside the measured curve."""
    order = np.argsort(finer)
    f, s = finer[order], sizes[order]
    if pct < f.min() or pct > f.max():
        return np.nan
    return float(10 ** np.interp(pct, f, np.log10(s)))


def classify(gravel, sand, fines, cu, cc, ll, pi, scheme):
    a_line = 0.73 * (ll - 20) if np.isfinite(ll) else np.nan
    plastic = np.isfinite(pi) and pi > 7 and pi >= a_line
    silty = (not np.isfinite(pi)) or pi < 4 or (np.isfinite(a_line) and pi < a_line)
    if fines >= 50:
        if scheme == "IS":
            comp = "L" if ll < 35 else ("I" if ll <= 50 else "H")
        else:
            comp = "L" if ll < 50 else "H"
        if not np.isfinite(ll):
            return "M" + ("L" if scheme == "USCS" else "L") + " (non-plastic)"
        if plastic:
            return "C" + comp
        if silty:
            return "M" + comp
        return "CL-ML"
    major = "G" if gravel > sand else "S"
    well = (cu >= (4 if major == "G" else 6)) and (1 <= cc <= 3) if np.isfinite(cu) and np.isfinite(cc) else False
    grade = major + ("W" if well else "P")
    fine_sym = major + ("C" if plastic else ("M" if silty else "C-" + major + "M"))
    if fines < 5:
        return grade
    if fines > 12:
        return fine_sym
    return f"{grade}-{fine_sym}"


def kenney_lau(sizes, finer, cu):
    fmax = 0.20 if (np.isfinite(cu) and cu > 3) else 0.30
    order = np.argsort(sizes)
    s, f = sizes[order], finer[order] / 100
    s, f = s[s > 0], f[s > 0]
    ds = np.logspace(np.log10(s.min()), np.log10(s.max() / 4), 200)
    F = np.interp(np.log10(ds), np.log10(s), f)
    H = np.interp(np.log10(4 * ds), np.log10(s), f) - F
    sel = (F > 0.005) & (F <= fmax)
    if not sel.any():
        return np.nan, fmax
    return float((H[sel] / F[sel]).min()), fmax


def main():
    sv, at = pd.read_csv(sys.argv[1]), pd.read_csv(sys.argv[2]).set_index("sample_id")
    rows = []
    for sid, g in sv.groupby("sample_id"):
        g = g.sort_values("sieve_mm", ascending=False)
        total = float(at.loc[sid, "total_dry_mass_g"]) if sid in at.index and np.isfinite(at.loc[sid, "total_dry_mass_g"]) \
            else float(g.mass_retained_g.sum())
        sieves = g[g.sieve_mm > 0]
        finer = 100 * (1 - sieves.mass_retained_g.cumsum().to_numpy() / total)
        sizes = sieves.sieve_mm.to_numpy(float)
        p475 = np.interp(np.log10(4.75), np.log10(sizes[::-1]), finer[::-1])
        p075 = np.interp(np.log10(0.075), np.log10(sizes[::-1]), finer[::-1])
        gravel, sand, fines = 100 - p475, p475 - p075, p075
        d10, d30, d60 = (d_at(p, sizes, finer) for p in (10, 30, 60))
        cu = d60 / d10 if np.isfinite(d10) and np.isfinite(d60) else np.nan
        cc = d30 ** 2 / (d10 * d60) if np.isfinite(cu) and np.isfinite(d30) else np.nan
        ll = float(at.loc[sid, "liquid_limit_pct"]) if sid in at.index else np.nan
        pl = float(at.loc[sid, "plastic_limit_pct"]) if sid in at.index else np.nan
        pi = ll - pl if np.isfinite(ll) and np.isfinite(pl) else np.nan
        hf, fmax = kenney_lau(sizes, finer, cu)
        piping = ("high" if (fines >= 12 or sand > 50) and (not np.isfinite(pi) or pi < 7) and (d60 if np.isfinite(d60) else 1) < 0.5
                  else "low" if np.isfinite(pi) and pi > 7 else "moderate")
        rows.append(dict(sample_id=sid, gravel_pct=round(gravel, 1), sand_pct=round(sand, 1), fines_pct=round(fines, 1),
                         D10_mm=d10, D30_mm=d30, D60_mm=d60, Cu=cu, Cc=cc, LL=ll, PL=pl, PI=pi,
                         IS1498=classify(gravel, sand, fines, cu, cc, ll, pi, "IS"),
                         USCS=classify(gravel, sand, fines, cu, cc, ll, pi, "USCS"),
                         kenney_lau_min_HF=hf, kenney_lau_Fmax=fmax,
                         internally_stable=None if not np.isfinite(hf) else bool(hf >= 1.0),
                         piping_susceptibility=piping))
    out = pd.DataFrame(rows).round(4)
    print(out.T.to_string(header=False))
    out.to_csv(sys.argv[1].replace(".csv", "_result.csv"), index=False)


if __name__ == "__main__":
    main()
