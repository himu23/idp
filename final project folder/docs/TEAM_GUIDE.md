# Prithvi Flood-IN: the whole project from the basics

For a team member who was not part of the work. Read it once from top to bottom (about 30 minutes), then read the
report sections of the part you will present. Every number here comes from the same result files as the report.

## 1. The project in one minute

When the Mahanadi rises, which fields, villages, roads, bridges and river banks in its delta go under water, and who
must be warned? Flood warning systems, including our industry partner ClimMaTech's, forecast the river level at a gauge
but cannot answer that. We (1) chose the best satellite model for mapping flood water with a fair test of eight
models, (2) used it to map every radar image of the delta since 2017, (3) linked those maps to the river flow at Naraj
so that a flow forecast becomes a flood map, (4) worked out what each flood means for each civil-engineering
specialization, and (5) built tools for the partner and a field visit that checks all of it on the ground.

## 2. Why the project looks like this

- **The IDP rules.** At the review on 14 October the coordinator asked for a real project with real stakeholders, a
  site visit whose measurements change the work, and input from several specializations. A team last year lost marks
  for a site visit that measured nothing.
- **The partner.** ClimMaTech (an IIT Mandi start-up) makes radar river gauges (Pravaah, Tarang), a camera unit
  (Doordrishti), solar sirens (Rakshak), rain gauges (Varshaq), a control centre and the Aagah app. Every one of these
  works at a point. Their own website lists a map layer for flood risk (River View) but nothing that shows flood extent.
- **The guide.** Prof. Basudev Biswal works on the Mahanadi basin. The Mahanadi delta below Naraj (around Cuttack and
  Kendrapara) floods every few years: a 3,038 km² study box holds about 4.1 million people.

## 3. Background you need

### 3.1 Two kinds of satellite image

**Sentinel-2** is an optical satellite, a camera with extra colours (13 bands). Water is easy to see in it, but clouds
block it, and the Mahanadi floods in the monsoon: on the big flood dates the delta was 61–95 % cloud. **Sentinel-1**
is a radar satellite. It sends microwaves and records the echo, so it sees through cloud, day and night. Calm water
reflects the radar away like a mirror and looks dark; land scatters it back and looks brighter. It passes over the
delta every 2–6 days. That is why the flood atlas uses radar.

### 3.2 What "mapping water" means for a model

A model takes an image tile (512 × 512 pixels, about 5 km × 5 km at 10 m) and gives every pixel a probability of being
water. Above a threshold (usually 0.5) the pixel is called water. This is called segmentation. The model learns from
images where people have marked the water by hand (the labels).

### 3.3 Foundation models and small networks

A **foundation model** is a large network (35 to 324 million parameters) pre-trained on millions of unlabelled
satellite images; it is then fine-tuned for a task. We tested six: Prithvi-EO-2.0 (IBM/NASA), TerraMind (IBM/ESA),
DOFA, Clay, Satlas and DeCUR. A **U-Net** (7.8 million parameters) and a three-layer **CNN** are small networks
trained from scratch, the baselines. **Fine-tuned** means all weights keep learning; **frozen** means only a small
decoder learns on top of the pre-trained features. **Fusion** averages or combines the predictions of several models.

### 3.4 How we score

- **IoU** (intersection over union) = overlap of predicted and true water ÷ their union; 1 is perfect. A water IoU of
  0.77 is good for this dataset.
- **Precision**: of the pixels we called water, the share that is water. **Recall**: of the true water, the share we found.
- **POD / FAR**: for villages, the share of flooded villages we flagged, and the share of our flags that were wrong.
- **ROC AUC**: how well a map ranks flooded land above dry land (0.5 = chance, 1 = perfect).

## 4. Part 1: choosing the model

**Data.** Sen1Floods11: 446 hand-labelled tiles from 11 floods worldwide, each with Sentinel-1 and Sentinel-2.
**Two tests.** The *official* split, comparable with published papers, and *leave-India-out*: train without any Indian
tile and test on all 68 tiles of the 2016 Assam flood, a flood no model saw. The second is the honest test for India.

**What we trained (92 runs, three seeds for most):**

| Group | Runs | Question |
|---|---|---|
| Six foundation models, fully fine-tuned | 36 | Which one maps flood water best? |
| CNN and U-Net from scratch | 12 | Do foundation models beat small networks? |
| Six foundation models, frozen | 12 | How much do the pre-trained features know? |
| Radar only or optical only | 14 | Which satellite matters? |
| 10, 25 and 50 % of the labels | 18 | Do foundation models need fewer labels? |

Every model used the same recipe (same loss, optimiser, augmentation, 40 epochs) and the epoch with the best
validation score; the test tiles were used once, at the end.

**Results.** On the unseen Assam flood the U-Net scored 0.770, the best foundation model
(Prithvi) 0.747, and a fusion of the U-Net, the CNN and the best foundation model
0.776. The small network won because water is spectrally simple and a few hundred labelled
tiles are enough; the U-Net stayed ahead even with 10 % of the labels. Radar alone scores lower (about 0.65 on the
official test, against 0.82–0.84 with radar and optical together), but it is the only thing that sees a monsoon
flood, and TerraMind takes radar natively. **The model we use** is therefore the radar-only TerraMind + U-Net fusion: 0.646 IoU on
the 20 m radar the atlas reads. Retrained directly at 20 m, the pair reaches 0.681, ready
for the next atlas run.

**Was the training right?** A script re-checked all 92 runs from their saved outputs: correct settings, no tile in
two splits, no Indian tile in leave-India-out training, selection on validation only, every score recomputed: no
problems. Our TerraMind on the official test scores 89.7 mean IoU (radar +
optical) and 79.8 (radar only); the published paper reports 90.62 and 80.39.

## 5. Part 2: the flood atlas

The model mapped every Sentinel-1 pass over the delta from 2017 to October 2026: 590 passes, 457 in the
monsoon (June–November) and 133 in the dry season (February–March), at 20 m, about 5 seconds per pass on one GPU.
Water in the dry season and the river bed (178 km²) are "normal water"; water outside them on a monsoon
pass is **flood**. 905 km² flooded at least once. **Independent check:** for 60 passes a Sentinel-2
image exists within a day. On clear pixels the two agree with IoU 0.49 on all water, but the radar finds only
22% of the flood water Sentinel-2 sees: it misses shallow water among crops. Field points will check it again.

## 6. Part 3: from a river flow to a flood map

**River flow** at Naraj, the head of the delta, comes from GloFAS, a global model (daily, 1984–2026); the measured
CWC/WRD flows are requested. The flooded share of a pass follows the highest daily flow of the last five days
(rank correlation 0.76).

**Trigger discharge.** For each 20 m pixel we find the Naraj flow above which it is usually flooded. A forecast flow
then gives a map: every pixel whose trigger is below the forecast. **Tested on years it never saw** (each year
predicted from the other nine): IoU 0.23 over all monsoon passes against 0.14 for
"flood where it usually floods", and 0.23 against 0.07 at high flows. Per village it flags
17% of flooded villages. These scores are modest because floodplain flooding is patchy, and the honest
summary is: *where* the delta floods is very predictable from its past (ranking AUC 0.91),
*how much* floods on a given day only partly.

**Rain matters too.** The largest floods (September 2018 and 2021) came with heavy rain from Bay of Bengal
depressions, not with the highest river flows. At the 5-year flow, a dry week floods 25 km² and a
heavy-rain week 105 km² (past passes with similar flow and rain). A **learned model**
(gradient boosting) that adds rain and each pixel's flood history to the flow does best on heavy-rain passes
(0.22 against 0.17) and ranks land best (AUC 0.95).

**Design floods.** A Gumbel fit to 42 yearly maxima gives 17,897 m³/s for the 2-year flood, 23,940 for the 5-year,
32,997 for the 25-year and 40,470 for the 100-year. The largest flow in the radar record is
28,378 m³/s, so maps for the 10- to 100-year floods are the same, a lower bound.

## 7. Part 4: the specializations, briefly

- **Transportation:** roads as a network; in the 25-year flood 36,941 people lose road access to
  every hospital and everyday trips grow by 12,023 person-hours a day; ten critical
  roads carry most of the cut routes.
- **Structural:** a 230 mm brick wall cracks at about a metre of water, and 3,626 people live where
  the 25-year flood is that deep; bridge piers may scour 7–24 m below the flood level.
- **Geotechnical:** twenty river-bank sites to inspect; 415,549 people in dry houses within 200 m of the
  flood on soft soil, where foundations weaken and later settle.
- **Ocean:** 11 of the 20 largest floods followed a Bay of Bengal storm.
- **Construction management:** build in December–April; raising 8 critical roads takes about
  17,442 m³ of earthwork; a schedule for sirens and gauges.
- **Water resources and the watershed:** Hirakud dam controls about 59 % of the basin, but only about half of a
  flood peak at Naraj (median 48%) comes from it; the rest comes from the tributaries
  below the dam within a day.
- **Remote sensing:** Parts 1 and 2.

## 8. Part 5: the tools

- **Bulletin tool** (`mahanadi/forecast_to_impact.py`): type a forecast flow (m³/s or lakh cusec, optionally rain);
  get a flood map, the settlements to warn, the roads under water and a CAP alert, the format ClimMaTech's control
  centre accepts. For the 25-year flow it names 24 settlements.
- **Map viewer** (`dashboard/index.html`): every scenario with roads, sirens, gauges and banks; works offline.
- **Siting:** 40 sirens reach 49% of exposed people at 1.5 km; one radar gauge on each distributary.
- **Website** (`website/`): the whole project in the partner's visual style.

## 9. Part 6: the field visit

Three days in the delta, with protocols A–H in `fieldkit/FIELD_VISIT_KIT.md`: 40 random ground-truth points (did this
spot flood, how deep), discharge and roughness at a road bridge, bridge and river-bank inspections with soil samples
for the IIT Bombay lab, water levels in village wells, siren and gauge sites, and interviews with WRD, CWC, ClimMaTech
and villagers. Each measurement has a script that turns it into a number in report chapter 8. Load
`fieldkit/checkpoints/checkpoints.gpx` on a phone before going.

## 10. Honest limits

River flow is modelled, not gauged. Depth comes from a 30 m elevation model (about 2 m error). Soil, masonry and
riverbed values are textbook values until the lab tests. The flow split between the delta's branches is unknown.
The radar misses shallow water among crops. Floods larger than any since 2017 are lower bounds. Say these plainly if
asked: each one has a next step.

## 11. Questions you may be asked

- **Why not just use the published Prithvi flood model?** It was trained on the official split, which includes Indian
  tiles, so its Indian score is not an unseen test; on our unseen test it scored 0.738, below the U-Net.
- **If the U-Net won, why use a foundation model at all?** For the monsoon only radar works, and TerraMind takes radar
  natively; the radar fusion is the model we deploy.
- **How do you know the atlas is right?** Sentinel-2 on the same days, years held out from fitting, and the field points.
- **Why is the pass-level score only about 0.2?** Floodplain flooding is patchy, the observed maps are themselves
  radar maps, and rain drives the largest floods; the frequency map ranks land with AUC above 0.9.
- **Why are the 10- to 100-year maps identical?** The radar has not yet seen a flood larger than about a 10-year one.
- **Did you check the training?** Yes: 92 of 92 runs re-checked, no problems, published TerraMind scores reproduced.
- **What does ClimMaTech get?** A flood-extent layer, bulletins with CAP alerts, a network of sites placed with data,
  and a field method to turn gauge readings into discharge.
- **What is next?** The field visit, observed flows, the 20 m models in the atlas, Sentinel-2 labels for the delta.

## 12. Where everything is

| What | Where |
|---|---|
| The plan, roles and timeline | `PLAN.md` |
| Final report | `report/FINAL_REPORT.docx` (Appendix E is a glossary) |
| Slides, with speaker notes | `report/Prithvi_Flood-IN_Final.pptx`; text in `docs/SLIDES_TEXT.docx` |
| Executive summary | `docs/EXECUTIVE_SUMMARY.docx` |
| Field visit kit and GPS points | `fieldkit/` |
| Map viewer and website | `dashboard/index.html`, `website/` |
| How to re-run anything | `README.md` |
