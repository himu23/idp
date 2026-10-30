#!/bin/bash
# Seeds 1 and 2 of the radar-only pair (TerraMind-B and U-Net, official split), trained at 10 m and at 20 m, so the
# 20 m comparison of report Appendix B has a spread over three seeds. Waits until the candidate atlas has finished
# mapping the passes (the GPUs are then free), trains both models side by side, then scores every pair.
#   bash code/server/bg.sh logs/r20_seeds.log bash code/server/run_r20_seeds.sh
H=/home1/vineet/floodfm
cd $H
until grep -q "== build" logs/r20_candidate.log; do sleep 30; done
export PYTHONWARNINGS=ignore PYTHONPATH=code
PY="nice $H/env/bin/python"
run() {  # gpu model seed extra-args run-name
  CUDA_VISIBLE_DEVICES=$1 $PY -m floodfm.train --model $2 --protocol official --mode full --seed $3 --modalities s1 $4 \
      --save_ckpt --out runs/$5 > logs/$5.log 2>&1 || echo "FAILED $5"
}
echo "== train $(date +%T)"
( run 0 terramind 1 "" official_terramind_s1_full_s1; run 0 terramind 2 "" official_terramind_s1_full_s2
  run 0 terramind 1 "--s1_res 20" official_terramind_s1_full_s1_r20; run 0 terramind 2 "--s1_res 20" official_terramind_s1_full_s2_r20 ) &
( run 1 unet 1 "" official_unet_s1_full_s1; run 1 unet 2 "" official_unet_s1_full_s2
  run 1 unet 1 "--s1_res 20" official_unet_s1_full_s1_r20; run 1 unet 2 "--s1_res 20" official_unet_s1_full_s2_r20 ) &
wait
echo "== score $(date +%T)"
for s in 1 2; do
  for r in "" "_r20"; do
    CUDA_VISIBLE_DEVICES=0 $PY code/scripts/test_resolution.py code runs/official_terramind_s1_full_s${s}${r} \
        runs/official_unet_s1_full_s${s}${r} > logs/test_resolution_s${s}${r}.log 2>&1 || echo "FAILED score s${s}${r}"
  done
done
echo "R20_SEEDS_DONE $(date +%T)"
