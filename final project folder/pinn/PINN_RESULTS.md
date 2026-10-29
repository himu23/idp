# PINN track: Saint-Venant equations (mentor repository Barbhuiya12/PINN)

All numbers below were produced on the lab server (CPU, TensorFlow 1.15 in a Python 3.7 environment
built with micromamba; same package pins as the repository's `SETUP.sh`). Logs are in `results/logs/`,
figures in `results/figures/`. The case number for our team was never assigned, so we used **case 3**
(the reach the Phase-2 exercise is written against) for all from-scratch work, and validated all six
cases from the published weights.

## 1. Environment check and reproduction of every case (published weights)

`python phase4_validation/validate.py --case N`

| Case | Reach | ε_h (ours) | ε_h (paper) | RMSE | NSE | Deviation |
|---|---|---|---|---|---|---|
| 1 | analytical, flat bed | 3.0750e-03 | 3.075e-03 | 0.001 m | 0.9999 | 0.0 % |
| 2 | analytical, sloping bed | 3.6845e-02 | 3.685e-02 | 0.076 m | 0.9952 | 0.0 % |
| 3 | HEC-RAS sub-reach | 6.6354e-03 | 6.635e-03 | 0.054 m | 0.9997 | 0.0 % |
| 4 | same reach, 10× longer | 3.0928e-01 | 3.093e-01 | 1.771 m | 0.7837 | 0.0 % |
| 5 | full reach | 9.8755e-02 | 9.876e-02 | 0.387 m | 0.9294 | 0.0 % |
| 6 | full reach, 2 gauges (Fourier features) | 1.3962e-01 | 1.396e-01 | 0.674 m | 0.9080 | 0.0 % |

Linear interpolation between gauges, for comparison: ε_h = 0.519 (case 5, NSE −0.95) and 0.369
(case 6, NSE 0.36). The PINN is 5× (case 5) and 2.6× (case 6) more accurate than interpolation on
the same gauges.

## 2. Phase 1 — what the network is shown (case 3)

4,896 collocation points carry physics only. Initial profile, both boundaries and two interior gauges
(cross-sections 16 and 32) carry data: **the model sees 8.9 % of the reference field** and has to
reconstruct the other 91.1 % from the equations. Figure: `case3_phase1_overview.png`.

## 3. Phase 2 — residuals written from the equations (completed exercise)

`pinn/p2b_residuals_completed.py` implements the two residuals and checks them against the engine on
every collocation point:

| | Case 3 (4,896 pts) | Case 5 (36,567 pts) |
|---|---|---|
| continuity: max |ours − engine| | 0.000 → MATCH | 0.000 → MATCH |
| momentum: max |ours − engine| | 0.000 → MATCH | 0.000 → MATCH |
| mean |continuity residual| of the trained model | 1.53e-01 | 4.56e-02 |
| mean |momentum residual| of the trained model | 6.64e-02 | 1.70e-01 |

What the engine actually implements (the three "traps"):

1. **Continuity is non-conservative.** The engine uses `h_t + u·h_x = 0`; the full form for a
   rectangular channel is `h_t + u·h_x + h·u_x = 0`. The two agree only if velocity is uniform along
   the reach (`u_x ≈ 0`). Evaluated on the trained solution, the dropped term `|h·u_x|` is on average
   **5 % of the retained terms on case 3** (mean 8.4e-3, max 2.9e-2) but **23 % on case 5**
   (median 11 %, max 0.13). The assumption is acceptable on the 1 km case-3 reach and clearly
   violated on the longer case-5 reach, where mass is not conserved by the loss the network minimises.
2. **Manning's n is hard-coded to 0.015** inside `fun_r_momentum` (`engine/SVE_module_dynamic_h.py:381`);
   the value passed to the constructor is ignored.
3. **Friction uses |u|u, not u².** With u² the friction term would accelerate reverse flow instead of
   opposing it. `tf.pow(tf.square(R), 2/3)` equals `R^(4/3)` for R > 0; squaring first keeps the power's
   argument non-negative during training.

Loss balance at the trained optimum (case 3, `p2c_loss_balance.py`): continuity 3.0e-2, momentum 2.5e-2,
upstream/downstream velocity boundary 3.1e-2, depth boundary 3.7e-3, initial depth 3.7e-3, gauge
observations 6.7e-4 (u) and 5.5e-4 (h). The physics and velocity-boundary terms dominate; the gauges
are fitted almost exactly because their adaptive weights grow to 128 (u) and 55 (h).

## 4. Phase 3 — retraining case 3 from scratch

`python phase3_training/train.py --case 3` (8,000 Adam iterations, seed 1234), then
`validate.py --case 3 --trained`:

| Run | ε_h | RMSE | NSE | vs paper |
|---|---|---|---|---|
| Published weights | 6.635e-03 | 0.054 m | 0.9997 | — |
| **Our retrain, Adam + L-BFGS-B** | **6.457e-03** | **0.052 m** | **0.9997** | **2.7 % better** |
| Our retrain, `--no-bfgs` (Adam only) | 6.457e-03 | 0.052 m | 0.9997 | identical |

Training took 334 s on CPU. Figure: `case3_trained_profiles.png` (PINN vs HEC-RAS reference at four
times; the only visible miss is the drawdown near the upstream end at the last time step).

### Finding: the L-BFGS-B stage does nothing on case 3

`docs/05_known_issues.md` (item 1) states that the L-BFGS-B refinement "is where most of the published
accuracy comes from". In our run it changed nothing:

- `train_bfgs_safe` (the course wrapper) evaluates the loss at 3.212 with the adaptive weights pinned
  at their final Adam values.
- The first trial step blows the momentum residual up to 3.07e+08; the line search returns to the
  start point and SciPy stops after 16 evaluations with the weights unchanged (log lines 2439–2454
  of `train_case3.log`).
- Consequently the Adam-only run gives a bit-identical ε_h (6.4574e-03).

So, for case 3, all of the accuracy comes from the 8,000 Adam iterations, and our Adam-only model is
already 2.7 % better than the published one. Whether L-BFGS-B helps on the longer cases (4–6) remains
open; the first thing to check is the initial step size (the wrapper uses SciPy's defaults).

## 5. Classical solver for comparison (`sve_demo.py`)

The MacCormack finite-difference solver from the mid-term report (Appendix A.1) was restored as a
runnable script. It reproduces the mid-term numbers exactly: peak 400 → 313.7 m³/s at 8 km (+0.76 h)
→ 229.8 m³/s at 20 km (+2.25 h). Figure: `sve_demo_hydrographs.png`.

## 6. Verdict (Phase 4 question: would we recommend it to a river agency with two gauges?)

On a short reach with a calibrated HEC-RAS model already available (case 3), no: the PINN reproduces
HEC-RAS to 5 cm RMSE, but it needs HEC-RAS boundary series to do so and adds 5–6 minutes of training per
reach. Its real value appears on long reaches with sparse gauges (cases 5–6), where it beats linear
interpolation by a factor of 2.6–5 in ε_h. Even there two caveats from this work apply: the
continuity residual drops a term that is 11–23 % of the retained terms on case 5, and the published
observations are noise-free (SNR 500 dB), so robustness to real gauge error is untested.
