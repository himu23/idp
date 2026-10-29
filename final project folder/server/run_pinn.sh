#!/bin/bash
# Full PINN track on CPU: reproduce every case from the published weights, complete the
# Phase-2 residual exercise, explore case 3, retrain case 3 from scratch with and without
# the L-BFGS-B stage, and validate the retrained models.
P=/home1/vineet/floodfm/pinn
cd $P/PINN
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=6 TF_CPP_MIN_LOG_LEVEL=2 PYTHONWARNINGS=ignore
PY=$P/env/bin/python
mkdir -p results/logs
echo "== validate all cases (paper weights)"
for c in 1 2 3 4 5 6; do $PY phase4_validation/validate.py --case $c > results/logs/validate_paper_case$c.log 2>&1; grep -E "eps_h|deviation" results/logs/validate_paper_case$c.log; done
echo "== phase 1 (case 3)"
$PY phase1_data_exploration/p1c_explore_plots.py --case 3 > results/logs/p1c_case3.log 2>&1; tail -20 results/logs/p1c_case3.log
echo "== phase 2 residuals (completed exercise, case 3 and 5)"
for c in 3 5; do PINN_ROOT=$P/PINN $PY /home1/vineet/floodfm/code/pinn/p2b_residuals_completed.py --case $c > results/logs/p2b_case$c.log 2>&1; cat results/logs/p2b_case$c.log | grep -v "^$" | tail -16; done
$PY phase2_loss_analysis/p2c_loss_balance.py --case 3 > results/logs/p2c_case3.log 2>&1; tail -25 results/logs/p2c_case3.log
echo "== phase 3: retrain case 3 (published protocol) and the --no-bfgs experiment"
$PY phase3_training/train.py --case 3 > results/logs/train_case3.log 2>&1; tail -5 results/logs/train_case3.log
$PY phase4_validation/validate.py --case 3 --trained > results/logs/validate_trained_case3.log 2>&1; grep -E "eps_h|RMSE|NSE|interp" results/logs/validate_trained_case3.log
mkdir -p results/trained_models_bfgs && cp -r results/trained_models/* results/trained_models_bfgs/ 2>/dev/null
$PY phase3_training/train.py --case 3 --no-bfgs > results/logs/train_case3_nobfgs.log 2>&1; tail -5 results/logs/train_case3_nobfgs.log
$PY phase4_validation/validate.py --case 3 --trained > results/logs/validate_trained_case3_nobfgs.log 2>&1; grep -E "eps_h|RMSE|NSE|interp" results/logs/validate_trained_case3_nobfgs.log
echo PINN_RUN_DONE
