# IDP flood data kit

Prepared 12 Oct 2026. Everything below was downloaded and checked, not copied from documentation.

## 1. Plain-language summary

**Where Siddik's notebook data comes from**

- The notebook downloads **Sen1Floods11**, a public flood dataset made by the company Cloud to Street (Bonafilia et al., 2020).
- It comes from a copy on Hugging Face (`blumenstiel/Sen1Floods11`, uploaded by an IBM researcher). The original is in a public Google Cloud bucket (`gs://sen1floods11`).
- The file we downloaded is exactly the one the notebook uses. Its checksum matches.
- It has **446 small image squares ("chips")**, each about 5 km × 5 km at 10 m pixels, from **11 flood events** worldwide.
- Each chip has:
  - a radar image (Sentinel-1)
  - an optical image (Sentinel-2)
  - a **hand-drawn water map**: 1 = water, 0 = dry, −1 = cannot tell (usually cloud)

**Does it label all surface water, or only flood water?**

- It labels **all surface water**, including normal rivers and lakes.
- We checked this: **96.4%** of normal river/lake pixels are marked as water. That matches our project scope.

**How much of it is India**

- **68 chips**, all from **one flood**: the Assam / Brahmaputra flood of **12 Aug 2016**.
- There are also **467 more India chips** from the same flood. These have computer-made (automatic) labels, not hand-drawn ones.

**More data we found and checked**

1. **WorldFloods v2:** 4 Indian scenes from Cyclone Fani, May 2019, in Odisha. One of them covers **Cuttack / the Mahanadi delta**. Optical only.
2. **Microsoft's 10-year radar flood archive:**
   - It covers all of India. We used it as an "event finder".
   - It gave us the **biggest Mahanadi-delta flood dates of 2016–2024**: 29 May 2021, 16 Aug 2022, 14–16 Sep 2021, 8 Sep 2018, 26 Aug 2020, and more.
3. **A free, no-login source (Microsoft Planetary Computer)** for pulling **new** Sentinel-1 + Sentinel-2 images for any Indian place and date.
   - We tested it on the **Mahanadi delta flood of 16 Aug 2022** and it worked.
   - The optical image was **97% cloud**. The radar image clearly shows the flood.
4. **Big new IBM/ESA dataset (ImpactMesh-Flood):**
   - Radar + optical, about 24,600 samples, 206 floods.
   - Very good for training, but **it has no Indian samples**.
   - MMFlood and S1S2-Water also have **no Indian samples**.

**What this means for the team**

- Use **Sen1Floods11** as the common dataset for all 5 models. It is the same data as the notebook.
- Add the India extras on top:
  - the 467 automatic-label India chips, for training only
  - the 4 WorldFloods Odisha scenes
  - our own new Mahanadi pulls
- For an honest "unseen Indian flood" test, keep the Indian flood out of training completely.

## 2. Folder layout to use on the GCP VM (one common data folder)

```
~/idp_data/                          <- shared by all 5 people, read-only after it is built
  sen1floods11/sen1floods11_v1.1/    446 hand-labelled chips (same as notebook)
  sen1floods11/weak/                 467 India chips with automatic labels (S1Weak, S2Weak, *LabelWeak)
  worldfloods_v2_india/              4 Odisha scenes (Cyclone Fani 2019)
  india_new/<event>/                 our own S1+S2 pulls (script 04)
  manifests/                         CSV lists from this kit (which chip, which split, stats)
~/idp_models/
  00_baselines_cnn_unet/  01_prithvi/  02_terramind/  03_clay/  04_croma_or_dofa/  05_galileo_or_terrafm/
```

## 3. Commands (run on the VM, in order)

```bash
pip install -r requirements.txt
bash scripts/01_download_sen1floods11.sh ~/idp_data          # 1.8 GB + 3.3 GB India weak chips (~5 min)
python3 scripts/02_audit_sen1floods11.py ~/idp_data/sen1floods11/sen1floods11_v1.1 ~/idp_data/manifests ~/idp_data/sen1floods11/Sen1Floods11_Metadata.geojson
python3 scripts/03_audit_weak_chips.py ~/idp_data/sen1floods11/weak ~/idp_data/manifests/sen1floods11_handlabeled_manifest.csv ~/idp_data/manifests/sen1floods11_india_weak_chips.csv
bash scripts/05_download_worldfloods_india.sh ~/idp_data       # ~120 MB
python3 scripts/06_find_flood_dates_ai4g.py --tile N18E084 --bbox 85.3 19.8 87.0 21.0 --out ~/idp_data/manifests/mahanadi_dates.csv
python3 scripts/04_pull_india_s1s2.py --bbox 86.05 20.30 86.20 20.45 --date 2022-08-16 --days 3 --out ~/idp_data/india_new/mahanadi_20220816
```

Each script states its inputs and outputs at the top. All of them ran successfully in this session (outputs are in `manifests/` and `figures/`).

## 4. Verified facts about Sen1Floods11 (from our own audit, `manifests/`)

| Item | Value |
|---|---|
| Source | `gs://sen1floods11/v1.1` (Cloud to Street); HF copy `blumenstiel/Sen1Floods11` = hand-labelled part only, simplified folders, Copernicus DEM added |
| File checked | `sen1floods11_v1_1.tar.gz`, 1,771,556,385 bytes, SHA-256 `d836b0c9…640a4f` (matches HF) |
| Products per chip | `S1GRDHand` (VV, VH, dB, float32), `S2L1CHand` (13 bands B1–B12 incl. B8A, top-of-atmosphere, int16), `LabelHand`, `S1OtsuLabelHand`, `JRCWaterHand`, `CopernicusDEM` |
| Grid | EPSG:4326, 8.98e-5° (~10 m), 512 × 512 |
| Splits | train 252 / val 89 / test 90 / Bolivia hold-out 15. All 10 countries appear in more than one split, so the splits share events. |
| Label meaning | 1 water, 0 not water, −1 unknown (mostly cloud). Covers all surface water: 96.4% of JRC permanent-water pixels are labelled water; 28.6% of all water pixels are permanent water. |
| India | Assam (Brahmaputra), 92.15–94.16°E, 24.85–28.28°N, S1 and S2 both 12 Aug 2016, descending orbit 77. 68 hand chips (40/14/14) + 467 weak chips. |
| Full original bucket | Hand-labelled 1.75 GB; weakly labelled 4,384 chips / 33 GB (12 events incl. Colombia); permanent-water set 814 chips; 4 model checkpoints |

Per-country numbers are in `manifests/sen1floods11_summary_by_country.csv`. Per-chip numbers (water %, unknown %, permanent-water %, radar/optical validity, Otsu-vs-hand IoU, mean elevation) are in `sen1floods11_handlabeled_manifest.csv`.

## 5. Important cautions (read before training)

1. **The India chips are a single event.**
   - The official split puts that one Assam flood in train, val *and* test, so an "India score" from it is not an unseen-event test.
   - For a fair Indian test, train on the other 10 countries and test on all 68 India chips ("leave-India-out").
   - In that set-up, **do not** add the 467 India weak chips to training, because they come from the same flood.
2. **Weak labels are noisy.**
   - The radar-made and optical-made India weak labels agree poorly (median IoU 0.14).
   - 101 of the 467 weak chips overlap hand-labelled chips, including 23 test and 18 val chips. Drop those if the weak chips are used.
   - Use weak chips for **training only, never for testing**.
3. **The processing differs between sources.**
   - Sen1Floods11 is S2 **L1C** (top-of-atmosphere) and S1 **GRD σ0 dB** (Google Earth Engine).
   - The Planetary Computer pulls are S2 **L2A** (surface reflectance) and S1 **RTC γ0**.
   - Normalise each source with its own statistics, or keep them as separate test sets. Do not mix them silently.
4. **WorldFloods v2 is CC BY-NC (non-commercial).** That is fine for coursework, but it should not go into a ClimMaTech product.
5. **Microsoft AI4G detections are model output, not ground truth.** Use them to find dates, not to score models.
6. **The radar threshold mask in the Mahanadi preview is a first look, not a label.** Real labels for new Indian events need NDEM polygons + JRC permanent water + a manual check.

## 6. Which data fits which foundation model (to check during setup)

| Model | Inputs it expects | Sen1Floods11 provides |
|---|---|---|
| CNN / U-Net (baselines) | anything | 13 S2 + 2 S1 (notebook already does this) |
| Prithvi-EO-2.0 | 6 optical bands (Blue, Green, Red, NIR-narrow, SWIR1, SWIR2), HLS-style | B2, B3, B4, B8A, B11, B12 from S2L1CHand |
| TerraMind | S2L1C or S2L2A + S1GRD or S1RTC | S2L1C + S1GRD exactly (notebook config) |
| Clay | S2 L2A, S1 RTC and others, with wavelength/date metadata | L1C/GRD only: needs adaptation; PC pulls give L2A/RTC |
| CROMA | 12 S2 bands + S1 VV/VH | 13 bands available (drop B10) + VV/VH |
| DOFA / Galileo / TerraFM | flexible bands with wavelengths / S1+S2 | check each during screening |

## 7. Files in this kit

- `scripts/` contains the 6 scripts above, all tested here.
- `manifests/`:
  - per-chip and per-country Sen1Floods11 tables
  - the India weak-chip audit
  - the dataset comparison table (`datasets_checked_2026-10-12.csv`)
  - the Mahanadi flood-date list (`mahanadi_delta_flood_dates_ai4g.csv`)
  - the WorldFloods India scene list
  - metadata of the test pull
- `figures/`:
  - India Sen1Floods11 examples
  - WorldFloods Cuttack example
  - the new Mahanadi 16 Aug 2022 pull

## Sources

- Bonafilia et al. (2020), *Sen1Floods11*, CVPR Workshops: https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html
- Original dataset repository: https://github.com/cloudtostreet/Sen1Floods11 (bucket `gs://sen1floods11`)
- Notebook copy: https://huggingface.co/datasets/blumenstiel/Sen1Floods11
- WorldFloods v2 (Portalés-Julià et al., 2023, *Scientific Reports*): https://huggingface.co/datasets/isp-uv-es/WorldFloodsv2
- ImpactMesh-Flood: https://huggingface.co/datasets/ibm-esa-geospatial/ImpactMesh-Flood
- Microsoft AI for Good flood dataset (*Nature Communications*, 2025): https://huggingface.co/datasets/ai-for-good-lab/ai4g-flood-dataset
- MMFlood: https://huggingface.co/datasets/links-ads/mmflood · S1S2-Water mirror: https://huggingface.co/datasets/idomogalla/s1s2_water · Kuro Siwo: https://huggingface.co/datasets/orion-ai-lab/Kuro-Siwo-GeoTIFFs
- Microsoft Planetary Computer STAC (sentinel-1-rtc, sentinel-2-l2a, jrc-gsw): https://planetarycomputer.microsoft.com
