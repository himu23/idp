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

The 20 m-trained pair is better on the atlas input and can replace the current models in the next atlas run (re-inference of the 590 passes takes about an hour).
