"""Shallow foundation next to a flood: bearing capacity with the water table deep vs at ground level, and settlement
of soft clay when the water table falls back after the flood.

    python fieldkit/analysis/foundation_checks.py --phi 28 --c 0 [--B 1.0 --D 1.0 --gamma 18]
    python fieldkit/analysis/foundation_checks.py --cu_dry 50 --cu_wet 30 --mv 0.3 --H 4 --dh 2

Strip footing, Terzaghi's equation with Vesic factors: q_ult = c Nc + q Nq + 0.5 gamma' B Ngamma, where the
effective unit weight replaces gamma in the q and gamma terms when the water table reaches the ground (soaked
ground beside a flood). Undrained clay: q_ult = 5.14 cu + gamma D, with cu of the soaked clay. Settlement on
drawdown: s = mv * gamma_w * dh * H (one-dimensional consolidation; dh = fall of the water table, H = soft clay
thickness, mv from an oedometer test or a typical 0.2-0.5 m2/MN). Use the lab results of the field samples.
"""
import argparse
import math

ap = argparse.ArgumentParser()
ap.add_argument("--B", type=float, default=1.0)
ap.add_argument("--D", type=float, default=1.0)
ap.add_argument("--gamma", type=float, default=18.0)
ap.add_argument("--phi", type=float)
ap.add_argument("--c", type=float, default=0.0)
ap.add_argument("--cu_dry", type=float)
ap.add_argument("--cu_wet", type=float)
ap.add_argument("--mv", type=float, help="m2/MN")
ap.add_argument("--H", type=float, default=4.0)
ap.add_argument("--dh", type=float, default=2.0)
a = ap.parse_args()
GW = 9.81

if a.phi is not None:
    p = math.radians(a.phi)
    nq = math.exp(math.pi * math.tan(p)) * math.tan(math.radians(45 + a.phi / 2)) ** 2
    nc = (nq - 1) / math.tan(p) if a.phi > 0 else 5.14
    ng = 2 * (nq + 1) * math.tan(p)
    gd, gw_ = a.gamma, a.gamma - GW
    q1 = a.c * nc + gd * a.D * nq + 0.5 * gd * a.B * ng
    q2 = a.c * nc + gw_ * a.D * nq + 0.5 * gw_ * a.B * ng
    print(f"drained, phi' {a.phi} deg, c' {a.c} kPa: Nc {nc:.1f} Nq {nq:.1f} Ngamma {ng:.1f}")
    print(f"  q_ult water table deep: {q1:.0f} kPa; at ground level: {q2:.0f} kPa; loss {100 * (1 - q2 / q1):.0f} %")
    print(f"  safe bearing (FS 3): {q1 / 3:.0f} -> {q2 / 3:.0f} kPa")
if a.cu_dry is not None and a.cu_wet is not None:
    q1, q2 = 5.14 * a.cu_dry + a.gamma * a.D, 5.14 * a.cu_wet + a.gamma * a.D
    print(f"undrained clay: q_ult {q1:.0f} kPa (cu {a.cu_dry}) -> {q2:.0f} kPa soaked (cu {a.cu_wet}); loss {100 * (1 - q2 / q1):.0f} %")
if a.mv is not None:
    s = a.mv * 1e-3 * GW * a.dh * a.H
    print(f"settlement when the water table falls {a.dh} m over {a.H} m of clay (mv {a.mv} m2/MN): {s * 1000:.0f} mm")
