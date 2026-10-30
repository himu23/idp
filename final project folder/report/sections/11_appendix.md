## Appendix A. Verification of the training

`scripts/audit_training.py` re-checks every benchmark run on the lab server from its stored outputs
(`results/analysis/audit_training.json`).

| Check | Result |
|---|---|
| Every queued job has results made with the arguments it was queued with | 92 of 92 |
| No chip in two of train / validation / test | yes, every run |
| Leave-India-out: no India chip in training or validation; test = the 68 India chips | yes, every run |
| Model selection on validation only (stored best validation IoU = maximum of the history; test touched once) | yes, every run |
| Test IoU recomputed from the saved probabilities equals the stored value | yes, every run |
| Frozen runs train only the decoder | 5%–26% of the parameters |
| Spread over three seeds (sd of test IoU) | at most 0.017 |
| Problems found | 0 |

**Comparison with published numbers.** On the official Sen1Floods11 test split, mean IoU over water and dry (the
metric of the foundation-model papers) for seed 0:

| Model | Water IoU | Mean IoU (%) | Published mean IoU (%) |
|---|---|---|---|
| TerraMind-B, radar + optical | 0.821 | 89.7 | 90.62 |
| TerraMind-B, radar only | 0.654 | 79.8 | 80.39 |
| Prithvi-EO-2.0-300M | 0.824 | 89.9 | – |
| U-Net (from scratch) | 0.838 | 90.7 | – |

The published values are from the TerraMind paper (Jakubik et al. 2025, arXiv:2504.11171, Table 7; PANGAEA protocol
with a different decoder and schedule), so a gap of about one point is expected; our runs reproduce them.

**The atlas input looks like the training input.** Median radar backscatter (dB) after the gamma0-to-sigma0 conversion
used by `atlas_infer.py`, for 24 random July–October passes of the delta and 60 random Sen1Floods11 training chips:

| Pixels | VV | VH |
|---|---|---|
| Sen1Floods11 training chips, water | -17.9 | -25.8 |
| Mahanadi atlas passes, water | -19.4 | -23.1 |
| Sen1Floods11 training chips, dry | -9.7 | -16.1 |
| Mahanadi atlas passes, dry | -8.7 | -15.2 |

Dry land differs by about 1 dB, and water lies 8–11 dB below dry land in both, so the conversion holds.

**Runs whose best epoch was the last one.** 5 of 92 runs
(lio_cnn_full_s1, lio_unet_full_s0, lio_unet_s2_full_s1, official_clay_frozen_s0, official_terramind_full_s2). The headline U-Net gained 0.002 validation IoU over its last five
epochs (converged); the frozen Clay run and the optical-only U-Net (seed 1) were still improving, so those two scores
may be slightly low. Neither changes a ranking or a conclusion.

## Appendix B. Retraining the radar models at the atlas resolution

The atlas reads Sentinel-1 from the 20 m overviews, and the radar models of §4 were trained at 10 m. Both radar-only
models (TerraMind-B and U-Net, official split, seed 0) were retrained with the radar degraded on the GPU exactly as the
overview is made (2 × 2 average in linear power, bilinear back to 10 m; `floodfm/train.py --s1_res 20`) and scored by
`scripts/test_resolution.py` on the official test split:

| Input to the fusion | 10 m-trained pair | 20 m-trained pair |
|---|---|---|
| Native 10 m radar | 0.664 | 0.607 |
| 20 m overview (the atlas input) | 0.640 | 0.695 |
| 20 m overview, threshold from validation | 0.646 (at 0.30) | 0.681 (at 0.45) |

The 20 m-trained pair is better on the atlas input, so the atlas was rebuilt with it (all 590 passes mapped again,
threshold 0.45); every Mahanadi result in this report comes from the rebuilt atlas. The independent
Sentinel-2 check decided it:

| Atlas built with | Sentinel-2, all water: IoU (precision / recall) | Sentinel-2, flood water: IoU (precision / recall) | Held-out high flow: trigger map vs climatology (IoU) | Villages at high flow: POD / FAR | Land flooded at least once (km²) |
|---|---|---|---|---|---|
| 10 m-trained pair (threshold 0.30) | 0.487 (0.60 / 0.73) | 0.180 (0.51 / 0.22) | 0.225 vs 0.070 | 17% / 65% | 905 |
| 20 m-trained pair (threshold 0.45) | 0.563 (0.75 / 0.69) | 0.196 (0.63 / 0.22) | 0.198 vs 0.038 | 21% / 62% | 1,137 |

The Sentinel-2 check is the like-for-like comparison, because the optical reference is the same for both atlases: the
rebuilt atlas agrees better on all water and on flood water, mainly because it reports less false water (higher
precision). The held-out scores are not like for like, because each atlas is scored against its own observed maps.
The rebuilt atlas sees more flooded land, much of it rain-fed (the flooded share of a pass follows the 7-day rain with
rank correlation 0.51, against 0.38 before), which the river flow alone predicts
less well, so the trigger map's pixel score falls while its lead over climatology and its village-level skill improve. The flow
predictor is chosen by rank correlation and moved from the 5-day peak flow to the
3-day peak flow (rank correlation 0.765 against 0.764, practically a tie), so
66 rather than 85 passes count as high flow. The earlier atlas is kept in
`results/archive_atlas_10m/`.

**Three seeds.** Seeds 1 and 2 of both radar models were trained at 10 m and at 20 m (`server/run_r20_seeds.sh`) and each
pair scored the same way; the threshold is chosen on validation for every pair.

| Seed | 10 m-trained pair, 20 m input | same, threshold from validation | 20 m-trained pair, 20 m input | same, threshold from validation |
|---|---|---|---|---|
| 0 | 0.640 | 0.646 | 0.695 | 0.681 |
| 1 | 0.673 | 0.666 | 0.684 | 0.684 |
| 2 | 0.651 | 0.654 | 0.673 | 0.667 |
| Mean ± sd | 0.655 ± 0.014 | 0.655 ± 0.008 | 0.684 ± 0.009 | 0.677 ± 0.007 |

Training at 20 m wins on every seed, by 0.022 IoU on average with the threshold from validation: the gain is well outside the seed-to-seed spread.
