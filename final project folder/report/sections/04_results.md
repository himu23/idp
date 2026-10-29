## 4. Results: which model maps Indian flood water best?

All numbers in this section come from `results/analysis/summary.json` (92 training runs, three seeds per
fine-tuned model) and are reproduced by `scripts/analyze.py` and `scripts/make_tables.py`.

### 4.1 Overall ranking

{{TABLE:A}}

{{TABLE:B}}

![Test IoU on the unseen Indian flood (leave-India-out), mean ± sd over three seeds](../results/analysis/figures/bars_lio.png)

- **On the flood the models had never seen (Assam, Table A) the best single models are the two trained from
  scratch**: U-Net 0.770 ± 0.006 and the simple CNN 0.766 ± 0.005. The best foundation models, Prithvi-EO-2.0
  (0.747 ± 0.006) and TerraMind-B (0.746 ± 0.014), are about 0.02 IoU lower; Satlas, DOFA and DeCUR are at
  0.714–0.719 and Clay at 0.666.
- **On the official split (Table B)** U-Net and CNN reach 0.840; the foundation models range from 0.802 (Clay)
  to 0.829 (Prithvi).
- **Without training**, Otsu thresholding of radar VH gets 0.23–0.24, NDWI 0.65–0.76. The published Prithvi
  flood checkpoint gets 0.738 on Assam, but it is not an unseen-event score: 40 of the 68 Assam chips were in
  its training set and 14 in its validation set.
- With ~250 labelled chips and all 15 bands available, pre-training on large unlabelled archives did not
  beat a well-trained U-Net for this task. Water has a strong spectral signature (NDWI alone reaches 0.65–0.76),
  and a 7.8 M-parameter network learns it from a few hundred chips. Training time: 3 min for U-Net,
  6–15 min for the foundation models on one GPU.

The project scope listed CROMA, Galileo and TerraFM. None of them is in the backbone registry of TerraTorch
1.2.13 (1,467 backbones checked), the framework that gives all models here the same decoder, loss and data
pipeline. Adding them would have meant a second, different training pipeline, so they were replaced by Clay,
Satlas and SSL4EO-S12 DeCUR, which are in the same framework.

### 4.2 How much is lost on an unseen flood

Every model loses 0.07–0.14 IoU when the Indian event is not in training: U-Net 0.840 → 0.770, Prithvi
0.829 → 0.747, TerraMind 0.821 → 0.746, Clay 0.802 → 0.666. On the official split the India event itself is
scored at 0.86–0.92 by the trained models (Table F) because the model has seen other chips of the same flood. **For a new Indian
flood, the leave-India-out numbers are the ones to expect**, and this is the gap the mid-term result fell into.

### 4.3 Frozen encoder vs full fine-tuning

{{TABLE:C}}

![Frozen encoder vs full fine-tuning](../results/analysis/figures/frozen_vs_finetuned.png)

On the unseen flood, fine-tuning helps every foundation model, by +0.003 (DeCUR) to +0.048 (Satlas). On the
official split, frozen TerraMind (0.825) and frozen DeCUR (0.828) are as good as their fine-tuned versions,
while only 5–20 M decoder parameters are trained. What pre-training gives for free is enough for events like
those in training; moving to a new region needs the encoder to adapt.

### 4.4 Fusion ("fuse layer")

{{TABLE:E}}

- Fusing the six foundation models does **not** beat the best one on the unseen flood (0.739–0.743 vs
  0.746–0.747), but helps on the official split (0.837 vs 0.829).
- Adding the two from-scratch models to the pool changes this: the learned fuse layer over all eight reaches
  0.774 ± 0.004, and the mean of the three models with the best validation IoU (always U-Net and CNN, plus Prithvi in seed 0 and TerraMind in seeds 1 and 2) reaches
  **0.776 ± 0.003, the best leave-India-out result, with a small spread between seeds**.
- The learned weights give Clay and Satlas zero or negative weight and TerraMind and Prithvi the largest
  weights among the foundation models; the fuse layer learns which members to ignore.

### 4.5 Radar, optical or both?

{{TABLE:D}}

![Modality ablation](../results/analysis/figures/modality_ablation.png)

Radar alone gives 0.51 on Assam, optical alone 0.76, both 0.75–0.77. This test favours optical by
construction: Sen1Floods11 labels were drawn on the Sentinel-2 image, and pixels under cloud are labelled
"unknown" and excluded from scoring. During a monsoon flood the optical image is mostly cloud (61–95 % over the
Mahanadi delta on the flood dates, §6), so radar is the only sensor that sees the event. This answers the
team's dataset questions of 20 October: optical bands are the better input whenever the sky is clear, but the
operational flood map has to work from radar; Section 6 therefore uses the radar-only models.

### 4.6 Threshold calibration, events, and flood vs permanent water

![Threshold sweep on the unseen flood](../results/analysis/figures/threshold_sweep_lio.png)

- Choosing the decision threshold on validation (0.33–0.60 for the trained models) changes test IoU by
  less than 0.01; 0.5 is adequate for trained models. It matters for index methods (MNDWI 0.506 → 0.602) and for
  degraded input (the 20 m radar model of §6, where 0.3 is chosen).
- Water that is not JRC permanent water (closer to "flood") scores about 0.05 lower than all water for every
  model (U-Net 0.722 vs 0.770 on Assam).
- By event (Table F): Mekong, Nigeria and Sri Lanka score above 0.9 and India 0.86–0.92; Ghana (0.53–0.66), Paraguay and
  Pakistan are hardest. Bolivia, never trained on, is 0.75–0.82.

{{TABLE:F}}

![Error maps on Assam chips (U-Net, best foundation model, top-3 fusion)](../results/analysis/figures/error_maps_assam.png)

### 4.7 Label efficiency

{{TABLE:G}}

![Label efficiency on the unseen flood](../results/analysis/figures/label_efficiency_lio.png)

With only 21 training chips U-Net reaches 0.736, about what Prithvi and TerraMind reach with all 212 (0.747,
0.746). Every model is within 0.01 of its full-data score at 106 chips. In this task, foundation models are
not more label-efficient than a U-Net.

### 4.8 What we take forward

1. **Model for a clear-sky Indian flood map**: U-Net, or the top-3 fusion (U-Net + CNN + the best foundation model) when the extra cost is acceptable.
2. **Model for the monsoon (radar only)**: radar-only models score 0.65 on the official split and 0.51 on
   Assam. TerraMind-B is the only foundation model here that takes radar alone as a native input; averaged
   with a radar-only U-Net it gives 0.664 (official test), better than either alone (0.654, 0.649). This
   radar fusion is the production model of the Mahanadi atlas (§6).
3. **The foundation model's value in this project** is not a higher score on Sen1Floods11; it is that one
   pre-trained network takes optical, radar or both without redesign, which is what an operational system
   that loses its optical images under monsoon cloud needs.
