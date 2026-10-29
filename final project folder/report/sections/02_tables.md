**Table A. Unseen Indian flood (leave-India-out; test = 68 Assam chips).** Water IoU and companions on test; mean ± sd over seeds where n > 1. Calibrated = threshold chosen on validation. Non-perm. = IoU on pixels that are not JRC permanent water. Bolivia = official hold-out event (never trained on).

| Method | Group | n | Test IoU | F1 | Precision | Recall | Calibrated IoU (thr) | Non-perm. IoU | Bolivia IoU | Params (M) | Train (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Otsu (VH radar) | no training | 1 | **0.243** | 0.391 | 0.256 | 0.821 | 0.243 (0.10) | 0.199 | 0.403 | – | – |
| MNDWI > 0 | no training | 1 | **0.506** | 0.672 | 0.521 | 0.945 | 0.602 (0.55) | 0.450 | 0.556 | – | – |
| NDWI > 0 | no training | 1 | **0.647** | 0.786 | 0.868 | 0.718 | 0.672 (0.45) | 0.578 | 0.832 | – | – |
| Prithvi published ckpt | no training | 1 | **0.738** | 0.849 | 0.887 | 0.815 | 0.740 (0.45) | 0.685 | 0.668 | – | – |
| Simple CNN | from scratch | 3 | **0.766 ± 0.005** | 0.868 ± 0.003 | 0.936 ± 0.004 | 0.809 ± 0.007 | 0.766 (0.50) | 0.716 ± 0.006 | 0.779 ± 0.006 | – | 2.9 |
| U-Net | from scratch | 3 | **0.770 ± 0.006** | 0.870 ± 0.004 | 0.915 ± 0.015 | 0.829 ± 0.007 | 0.772 (0.47) | 0.722 ± 0.006 | 0.797 ± 0.003 | 7.8 | 3.1 |
| Prithvi-EO-2.0-300M | foundation model | 3 | **0.747 ± 0.006** | 0.855 ± 0.004 | 0.875 ± 0.025 | 0.837 ± 0.020 | 0.747 (0.58) | 0.697 ± 0.007 | 0.809 ± 0.004 | 324.2 | 15.1 |
| TerraMind-B | foundation model | 3 | **0.746 ± 0.014** | 0.854 ± 0.009 | 0.889 ± 0.004 | 0.822 ± 0.019 | 0.746 (0.50) | 0.695 ± 0.017 | 0.793 ± 0.019 | 103.4 | 11.8 |
| DOFA-B | foundation model | 3 | **0.717 ± 0.002** | 0.835 ± 0.001 | 0.877 ± 0.009 | 0.797 ± 0.010 | 0.717 (0.50) | 0.660 ± 0.003 | 0.797 ± 0.007 | 127.5 | 8.8 |
| Clay-v1-B | foundation model | 3 | **0.666 ± 0.012** | 0.800 ± 0.008 | 0.839 ± 0.034 | 0.765 ± 0.015 | 0.664 (0.33) | 0.602 ± 0.012 | 0.755 ± 0.017 | 107.6 | 10.5 |
| Satlas Swin-B | foundation model | 3 | **0.719 ± 0.012** | 0.836 ± 0.008 | 0.917 ± 0.009 | 0.768 ± 0.019 | 0.713 (0.57) | 0.660 ± 0.014 | 0.778 ± 0.013 | 93.0 | 9.1 |
| DeCUR ResNet-50 | foundation model | 3 | **0.714 ± 0.003** | 0.833 ± 0.002 | 0.889 ± 0.014 | 0.784 ± 0.014 | 0.706 (0.60) | 0.656 ± 0.005 | 0.778 ± 0.004 | 34.6 | 6.6 |
| Fusion 6 FMs: mean | fusion | 3 | **0.739 ± 0.004** | 0.850 ± 0.003 | 0.906 ± 0.005 | 0.800 ± 0.008 | 0.739 (0.50) | 0.685 ± 0.005 | 0.818 ± 0.004 | – | – |
| Fusion 6 FMs: val-weighted | fusion | 3 | **0.739 ± 0.004** | 0.850 ± 0.003 | 0.906 ± 0.005 | 0.801 ± 0.009 | 0.739 (0.50) | 0.685 ± 0.005 | 0.818 ± 0.004 | – | – |
| Fusion 6 FMs: learned layer | fusion | 3 | **0.743 ± 0.007** | 0.852 ± 0.005 | 0.917 ± 0.010 | 0.796 ± 0.015 | 0.749 (0.40) | 0.689 ± 0.010 | 0.805 ± 0.004 | – | – |
| Fusion all 8: mean | fusion | 3 | **0.752 ± 0.003** | 0.859 ± 0.002 | 0.921 ± 0.005 | 0.805 ± 0.006 | 0.752 (0.50) | 0.700 ± 0.004 | 0.817 ± 0.004 | – | – |
| Fusion all 8: learned layer | fusion | 3 | **0.774 ± 0.004** | 0.873 ± 0.002 | 0.928 ± 0.010 | 0.824 ± 0.012 | 0.778 (0.45) | 0.727 ± 0.005 | 0.804 ± 0.006 | – | – |
| Fusion top-3 (val): mean | fusion | 3 | **0.776 ± 0.003** | 0.874 ± 0.002 | 0.929 ± 0.007 | 0.825 ± 0.006 | 0.779 (0.47) | 0.728 ± 0.004 | 0.801 ± 0.006 | – | – |

**Table B. Official Sen1Floods11 split (test = 90 chips, 10 events).** Water IoU and companions on test; mean ± sd over seeds where n > 1. Calibrated = threshold chosen on validation. Non-perm. = IoU on pixels that are not JRC permanent water. Bolivia = official hold-out event (never trained on).

| Method | Group | n | Test IoU | F1 | Precision | Recall | Calibrated IoU (thr) | Non-perm. IoU | Bolivia IoU | Params (M) | Train (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Otsu (VH radar) | no training | 1 | **0.230** | 0.374 | 0.253 | 0.714 | 0.230 (0.10) | 0.163 | 0.403 | – | – |
| MNDWI > 0 | no training | 1 | **0.653** | 0.790 | 0.678 | 0.946 | 0.776 (0.60) | 0.548 | 0.556 | – | – |
| NDWI > 0 | no training | 1 | **0.758** | 0.862 | 0.922 | 0.810 | 0.686 (0.45) | 0.655 | 0.832 | – | – |
| Prithvi published ckpt | no training | 1 | **0.820** | 0.901 | 0.918 | 0.884 | 0.821 (0.45) | 0.747 | 0.668 | – | – |
| Simple CNN | from scratch | 3 | **0.840 ± 0.003** | 0.913 ± 0.002 | 0.940 ± 0.001 | 0.887 ± 0.004 | 0.841 (0.45) | 0.773 ± 0.004 | 0.794 ± 0.009 | – | 3.0 |
| U-Net | from scratch | 3 | **0.840 ± 0.002** | 0.913 ± 0.001 | 0.934 ± 0.010 | 0.892 ± 0.011 | 0.841 (0.47) | 0.773 ± 0.004 | 0.808 ± 0.005 | 7.8 | 3.2 |
| Prithvi-EO-2.0-300M | foundation model | 3 | **0.829 ± 0.015** | 0.906 ± 0.009 | 0.915 ± 0.003 | 0.898 ± 0.021 | 0.829 (0.57) | 0.761 ± 0.022 | 0.810 ± 0.003 | 324.2 | 12.5 |
| TerraMind-B | foundation model | 3 | **0.821 ± 0.000** | 0.902 ± 0.000 | 0.921 ± 0.004 | 0.884 ± 0.003 | 0.821 (0.55) | 0.749 ± 0.001 | 0.807 ± 0.007 | 103.4 | 11.3 |
| DOFA-B | foundation model | 3 | **0.820 ± 0.012** | 0.901 ± 0.007 | 0.922 ± 0.003 | 0.881 ± 0.011 | 0.820 (0.52) | 0.745 ± 0.018 | 0.792 ± 0.013 | 127.5 | 10.3 |
| Clay-v1-B | foundation model | 3 | **0.802 ± 0.009** | 0.890 ± 0.005 | 0.914 ± 0.003 | 0.867 ± 0.010 | 0.809 (0.38) | 0.718 ± 0.013 | 0.777 ± 0.007 | 107.6 | 12.4 |
| Satlas Swin-B | foundation model | 3 | **0.819 ± 0.010** | 0.900 ± 0.006 | 0.919 ± 0.001 | 0.882 ± 0.013 | 0.817 (0.58) | 0.747 ± 0.012 | 0.774 ± 0.043 | 93.0 | 14.2 |
| DeCUR ResNet-50 | foundation model | 3 | **0.827 ± 0.001** | 0.905 ± 0.001 | 0.921 ± 0.005 | 0.890 ± 0.003 | 0.826 (0.55) | 0.753 ± 0.001 | 0.789 ± 0.006 | 34.6 | 6.3 |
| Fusion 6 FMs: mean | fusion | 3 | **0.837 ± 0.012** | 0.911 ± 0.007 | 0.931 ± 0.002 | 0.893 ± 0.014 | 0.838 (0.48) | 0.769 ± 0.018 | 0.821 ± 0.002 | – | – |
| Fusion 6 FMs: val-weighted | fusion | 3 | **0.837 ± 0.012** | 0.911 ± 0.007 | 0.930 ± 0.001 | 0.893 ± 0.013 | 0.838 (0.48) | 0.768 ± 0.018 | 0.821 ± 0.001 | – | – |
| Fusion 6 FMs: learned layer | fusion | 3 | **0.825 ± 0.007** | 0.904 ± 0.004 | 0.938 ± 0.002 | 0.873 ± 0.007 | 0.831 (0.40) | 0.752 ± 0.011 | 0.805 ± 0.003 | – | – |
| Fusion all 8: mean | fusion | 3 | **0.840 ± 0.011** | 0.913 ± 0.006 | 0.936 ± 0.002 | 0.890 ± 0.013 | 0.840 (0.48) | 0.772 ± 0.017 | 0.823 ± 0.001 | – | – |
| Fusion all 8: learned layer | fusion | 3 | **0.836 ± 0.001** | 0.911 ± 0.001 | 0.942 ± 0.001 | 0.881 ± 0.001 | 0.838 (0.45) | 0.768 ± 0.002 | 0.809 ± 0.004 | – | – |
| Fusion top-3 (val): mean | fusion | 3 | **0.842 ± 0.001** | 0.914 ± 0.000 | 0.939 ± 0.003 | 0.891 ± 0.004 | 0.842 (0.48) | 0.776 ± 0.001 | 0.816 ± 0.005 | – | – |

**Table C. Frozen encoder vs full fine-tuning** (test water IoU; frozen = seed 0, fine-tuned = mean of seeds).

| Model | LIO frozen | LIO fine-tuned | Δ | Official frozen | Official fine-tuned | Δ | Trainable params frozen (M) |
|---|---|---|---|---|---|---|---|
| Prithvi-EO-2.0-300M | 0.723 | 0.747 | +0.024 | 0.808 | 0.829 | +0.021 | 20.3 |
| TerraMind-B | 0.714 | 0.746 | +0.032 | 0.825 | 0.821 | -0.004 | 15.5 |
| DOFA-B | 0.677 | 0.717 | +0.039 | 0.808 | 0.820 | +0.012 | 15.5 |
| Clay-v1-B | 0.619 | 0.666 | +0.047 | 0.774 | 0.802 | +0.028 | 15.5 |
| Satlas Swin-B | 0.670 | 0.719 | +0.048 | 0.786 | 0.819 | +0.032 | 5.1 |
| DeCUR ResNet-50 | 0.711 | 0.714 | +0.003 | 0.828 | 0.827 | -0.002 | 9.0 |

**Table D. Which sensor is needed? Modality ablation on the unseen Indian flood** (LIO test IoU, mean ± sd over seeds).

| Model | Radar only (S1) | Optical only (S2) | Radar + optical |
|---|---|---|---|
| U-Net | 0.513 ± 0.007 | 0.763 ± 0.006 | 0.770 ± 0.006 |
| TerraMind-B | 0.505 ± 0.021 | 0.755 ± 0.002 | 0.746 ± 0.014 |

**Table E. Fusion of the six fine-tuned foundation models** (test IoU, mean ± sd over seeds; best single model for reference).

| Variant | LIO (Assam) | Official | Bolivia (LIO models) |
|---|---|---|---|
| Best single FM by validation (TerraMind-B / TerraMind-B) | 0.746 ± 0.014 | 0.821 ± 0.000 | 0.793 ± 0.019 |
| Fusion 6 FMs: mean | 0.739 ± 0.004 | 0.837 ± 0.012 | 0.818 ± 0.004 |
| Fusion 6 FMs: val-weighted | 0.739 ± 0.004 | 0.837 ± 0.012 | 0.818 ± 0.004 |
| Fusion 6 FMs: learned layer | 0.743 ± 0.007 | 0.825 ± 0.007 | 0.805 ± 0.004 |
| Fusion all 8: mean | 0.752 ± 0.003 | 0.840 ± 0.011 | 0.817 ± 0.004 |
| Fusion all 8: learned layer | 0.774 ± 0.004 | 0.836 ± 0.001 | 0.804 ± 0.006 |
| Fusion top-3 (val): mean | 0.776 ± 0.003 | 0.842 ± 0.001 | 0.801 ± 0.006 |

Learned fuse-layer weights (official_ens, seed 0): clay +0.02, decur +0.01, dofa +0.17, prithvi +0.25, satlas -0.04, terramind +0.23.
Learned fuse-layer weights (official_ensall, seed 0): clay -0.13, cnn +0.15, decur +0.01, dofa +0.12, prithvi +0.14, satlas -0.06, terramind +0.19, unet +0.22.
Learned fuse-layer weights (lio_ens, seed 0): clay -0.09, decur +0.16, dofa +0.09, prithvi +0.27, satlas -0.04, terramind +0.30.
Learned fuse-layer weights (lio_ensall, seed 0): clay -0.16, cnn +0.28, decur +0.10, dofa +0.00, prithvi +0.22, satlas -0.10, terramind +0.23, unet +0.10.

**Table F. Per-event test IoU, official split** (mean over seeds; fine-tuned models and baselines).

| Event | Otsu (VH radar) | MNDWI > 0 | NDWI > 0 | Prithvi published ckpt | Simple CNN | U-Net | Prithvi-EO-2.0-300M | TerraMind-B | DOFA-B | Clay-v1-B | Satlas Swin-B | DeCUR ResNet-50 | Fusion 6 FMs: mean | Fusion 6 FMs: val-weighted | Fusion 6 FMs: learned layer | Fusion all 8: mean | Fusion all 8: learned layer | Fusion top-3 (val): mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Ghana | 0.11 | 0.67 | 0.51 | 0.57 | 0.57 | 0.58 | 0.56 | 0.55 | 0.57 | 0.62 | 0.58 | 0.66 | 0.59 | 0.59 | 0.53 | 0.59 | 0.53 | 0.57 |
| India | 0.39 | 0.71 | 0.81 | 0.88 | 0.91 | 0.91 | 0.89 | 0.89 | 0.88 | 0.86 | 0.89 | 0.88 | 0.89 | 0.89 | 0.90 | 0.90 | 0.91 | 0.92 |
| Mekong | 0.31 | 0.82 | 0.93 | 0.91 | 0.95 | 0.95 | 0.92 | 0.91 | 0.91 | 0.90 | 0.91 | 0.91 | 0.92 | 0.92 | 0.92 | 0.93 | 0.94 | 0.95 |
| Nigeria | 0.30 | 0.91 | 0.89 | 0.92 | 0.94 | 0.94 | 0.93 | 0.93 | 0.92 | 0.92 | 0.93 | 0.92 | 0.93 | 0.93 | 0.93 | 0.93 | 0.94 | 0.94 |
| Pakistan | 0.21 | 0.72 | 0.57 | 0.68 | 0.73 | 0.74 | 0.75 | 0.72 | 0.64 | 0.73 | 0.55 | 0.65 | 0.71 | 0.71 | 0.69 | 0.72 | 0.71 | 0.73 |
| Paraguay | 0.17 | 0.37 | 0.53 | 0.75 | 0.63 | 0.63 | 0.66 | 0.61 | 0.72 | 0.60 | 0.76 | 0.74 | 0.73 | 0.73 | 0.65 | 0.68 | 0.63 | 0.63 |
| Somalia | 0.16 | 0.57 | 0.71 | 0.77 | 0.85 | 0.85 | 0.80 | 0.80 | 0.78 | 0.71 | 0.79 | 0.78 | 0.80 | 0.80 | 0.80 | 0.82 | 0.83 | 0.85 |
| Spain | 0.41 | 0.75 | 0.79 | 0.81 | 0.86 | 0.86 | 0.84 | 0.84 | 0.83 | 0.81 | 0.82 | 0.82 | 0.84 | 0.84 | 0.84 | 0.85 | 0.86 | 0.86 |
| Sri-Lanka | 0.23 | 0.55 | 0.90 | 0.92 | 0.93 | 0.93 | 0.93 | 0.92 | 0.92 | 0.91 | 0.91 | 0.92 | 0.93 | 0.93 | 0.93 | 0.94 | 0.94 | 0.94 |
| USA | 0.08 | 0.77 | 0.70 | 0.77 | 0.81 | 0.81 | 0.80 | 0.81 | 0.79 | 0.73 | 0.78 | 0.78 | 0.80 | 0.80 | 0.81 | 0.81 | 0.83 | 0.82 |

**Table G. Label efficiency on the unseen Indian flood** (LIO test IoU, mean ± sd over seeds; nested subsets of the 212 non-Indian training chips; epochs scaled so every run gets ~1,000 updates).

| Model | 21 chips (10 %) | 53 chips (25 %) | 106 chips (50 %) | 212 chips (100 %) |
|---|---|---|---|---|
| Prithvi-EO-2.0-300M | 0.687 ± 0.015 | 0.711 ± 0.004 | 0.744 ± 0.009 | 0.747 ± 0.006 |
| TerraMind-B | 0.694 ± 0.009 | 0.715 ± 0.002 | 0.741 ± 0.015 | 0.746 ± 0.014 |
| U-Net | 0.736 ± 0.006 | 0.756 ± 0.015 | 0.773 ± 0.007 | 0.770 ± 0.006 |
