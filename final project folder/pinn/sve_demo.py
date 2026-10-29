"""1-D Saint-Venant flood routing demo (MacCormack scheme), wide rectangular channel.

Restored from Appendix A.1 of the mid-term report so it can be re-run; adds a figure.
Illustrative only: synthetic channel, not calibrated to a real river.
"""
import json

import numpy as np

g = 9.81; L = 20000; dx = 250; B = 50.0; S0 = 5e-4; n = 0.035
x = np.arange(0, L + dx, dx); N = len(x)


def normal_depth(Q):
    return (Q * n / (B * np.sqrt(S0))) ** 0.6   # Manning, wide channel: Q = B h^(5/3) sqrt(S0)/n


Qb, Qp, tp, sig = 50.0, 400.0, 3 * 3600, 2400.0
inflow = lambda t: Qb + (Qp - Qb) * np.exp(-0.5 * ((t - tp) / sig) ** 2)  # noqa: E731
h0 = normal_depth(Qb); A = np.full(N, B * h0); Q = np.full(N, Qb)


def flux(A, Q):
    h = A / B
    return Q, Q ** 2 / A + g * B * h ** 2 / 2


def src(A, Q):
    h = A / B; R = A / (B + 2 * h); Sf = n ** 2 * Q * np.abs(Q) / (A ** 2 * R ** (4 / 3))
    return np.zeros_like(A), g * A * (S0 - Sf)


t = 0; T = 10 * 3600; stations = {0: [], 8000: [], 20000: []}; times = []
idx = {k: int(k / dx) for k in stations}; nextrec = 0
while t < T:
    c = np.max(np.abs(Q / A) + np.sqrt(g * A / B)); dt = 0.8 * dx / c          # CFL = 0.8
    F1, F2 = flux(A, Q); S1, S2 = src(A, Q)
    Ap = A.copy(); Qp_ = Q.copy()                                              # predictor (forward)
    Ap[:-1] = A[:-1] - dt / dx * (F1[1:] - F1[:-1]) + dt * S1[:-1]
    Qp_[:-1] = Q[:-1] - dt / dx * (F2[1:] - F2[:-1]) + dt * S2[:-1]
    G1, G2 = flux(Ap, Qp_); T1, T2 = src(Ap, Qp_)
    An = A.copy(); Qn = Q.copy()                                               # corrector (backward)
    An[1:] = 0.5 * (A[1:] + Ap[1:] - dt / dx * (G1[1:] - G1[:-1]) + dt * T1[1:])
    Qn[1:] = 0.5 * (Q[1:] + Qp_[1:] - dt / dx * (G2[1:] - G2[:-1]) + dt * T2[1:])
    t += dt; Qn[0] = inflow(t); An[0] = An[1]                                  # upstream: inflow hydrograph
    An[-1] = An[-2]; Qn[-1] = Qn[-2]                                           # downstream: transmissive
    A, Q = An, Qn
    if t >= nextrec:
        times.append(round(t / 3600, 2)); [stations[k].append(float(Q[idx[k]])) for k in stations]; nextrec += 900
out = {"t_h": times, "Q": {str(k): v for k, v in stations.items()}}
for k, v in stations.items():
    i = int(np.argmax(v)); print(f"x={k/1000:>4.0f} km peak Q={max(v):6.1f} m3/s at t={times[i]:.2f} h")
json.dump(out, open("sve_demo.json", "w"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(figsize=(6.4, 3.2))
for (k, v), c in zip(stations.items(), ["#2a78d6", "#eb6834", "#1baf7a"]):
    ax.plot(times, v, color=c, lw=2, label=f"x = {k/1000:.0f} km")
ax.set_xlabel("Time (h)"); ax.set_ylabel("Discharge Q (m$^3$/s)")
ax.spines[["top", "right"]].set_visible(False); ax.grid(color="#e6e5e0", lw=0.6)
ax.legend(frameon=False); ax.set_title("Flood-wave routing, synthetic channel (MacCormack)", loc="left", fontsize=10)
fig.tight_layout(); fig.savefig("sve_demo_hydrographs.png", dpi=160)
