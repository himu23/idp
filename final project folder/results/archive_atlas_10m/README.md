# Archive: the atlas built with the 10 m-trained radar models

Key results of the first Mahanadi atlas (radar TerraMind-B + U-Net trained on 10 m Sentinel-1, threshold 0.30), kept
for comparison after the atlas was rebuilt with the same pair retrained on 20 m input (threshold 0.45). The rebuilt
atlas agreed better with Sentinel-2 images taken within a day of the radar passes, so it replaced this one; report
Appendix B gives the comparison (`compare.json`).

- `atlas_summary.json`, `atlas_passes.csv`: the atlas, held-out validation and design floods
- `s2_crosscheck.json`: agreement with Sentinel-2
- `*_summary.json`, `*_scenarios.csv`: the impact analyses on this atlas
- `learned_summary.json`, `learned_unconstrained/`: the learned flow + rain + history model with and without the physical
  constraints (the unconstrained run gave less flooded land for heavy than for typical rain at the 25-year flow)
