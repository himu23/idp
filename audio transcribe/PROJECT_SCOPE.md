# IDP project scope: satellite water mapping during Indian flood events

Prepared 6 October 2026. Deadline: **9 November 2026**. Team: **five members**.

The user confirmed that the target is **any visible surface water during the event**, including rivers and lakes, and that the project should use **Sentinel-1 radar and Sentinel-2 optical imagery**. This document proposes the remaining implementation and evaluation decisions. It does not record completed comparison experiments. No remote VM access or training was performed during scope preparation.

## 1. Problem statement

Develop and evaluate a reproducible pipeline for mapping surface water from Sentinel-1 and Sentinel-2 imagery acquired during selected historical Indian flood events. Compare a small convolutional segmentation network and U-Net with segmentation methods based on six pretrained foundation-model families: **Prithvi-EO, TerraMind, CROMA, DOFA, Galileo, and TerraFM**. Include every family in feasibility screening; complete full comparisons for configurations that pass the input, label, runtime, and memory checks. Report any excluded family and its reason instead of silently dropping it. Use fixed event-separated datasets, common reference labels and quality rules, and controlled input comparisons. Evaluate water IoU, F1, precision, recall, consistency across events and repeated runs, observation coverage, and computational requirements on the available single-GPU VM.

The two main research questions are:

1. On unseen Indian flood events, do geospatial pretrained methods improve surface-water mapping compared with simpler networks under the available compute budget?
2. How does the radar–optical input package change mapping accuracy and assessment coverage, particularly under optical cloud? Isolating radar's contribution from additional optical bands requires the matched sensor controls described in section 7.

A finding that U-Net is comparable to a foundation model is a valid outcome. The deliverable is a defensible comparison, not a predetermined winning architecture or promised score.

Suggested title: **Comparative Evaluation of CNN, U-Net, and Geospatial Foundation Models for Surface-Water Mapping During Indian Flood Events Using Sentinel-1 and Sentinel-2 Imagery**.

## 2. What goes in, what happens, what comes out

```text
Aligned, near-date Sentinel-1 radar + Sentinel-2 optical imagery
               + sensor-quality information
                           ↓
               One of the tested methods
                           ↓
             Water score for each ground pixel
                           ↓
        Water / non-water map + assessment-quality layer
                           ↓
       Water extent, coverage, comparison with reference
```

During training the method also sees a matching reference water map. At inference that answer key is unavailable. Sensor-quality layers must be independently available; prediction masking must not use the test reference labels.

**Segmentation** means one decision per ground pixel. The output describes water at the observation time. It does not predict tomorrow's flooding or establish whether a now-dry location flooded earlier in the event.

Because the target includes normal rivers and lakes, the result is a **surface-water extent map during a flood event**. It is not automatically a map of newly inundated land. Estimating new flooding requires an additional pre-event or baseline-water comparison. Keep that as an optional extension and avoid calling the total water area the newly flooded area.

“Visible” means observable with the supplied sensors, not necessarily visible in a normal photograph. Radar can provide observations through cloud, but still has ambiguities around buildings, vegetation, terrain shadow, and rough water. Do not promise all water beneath vegetation or reliable urban flood mapping without suitable labels and evidence.

## 3. Exact meaning of the outputs

| Value | Meaning |
|---|---|
| `1` | Surface water present, including persistent rivers/lakes and event-related water |
| `0` | Surface water absent within an assessable, reliably labelled area |
| `-1` | Unknown/unassessable, or outside the declared study coverage |

Use two separate masks internally:

- **Reference-label validity:** whether the true answer is reliable enough for training/scoring.
- **Observation validity:** whether the inputs support a prediction. This can be applied at inference without the answer key.

The model learns water versus non-water only. Unknown labels are excluded from the loss and every water metric. `-1` is not a third physical class of water.

For optical-only methods, cloud/shadow/no-data may make a pixel unassessable. For radar-plus-optical methods, optical cloud alone should not automatically force `-1` if usable radar and the declared missing-optical handling are available. Sentinel-1's through-cloud observations are described in [ESA's flood-monitoring guidance](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Emergency_response). Keep sensor-specific validity information, mask corrupted measurements, and give all methods in a comparison group the same validity handling. Missing-radar fallback is outside the initial core: require usable radar for paired multimodal scenes.

A learned low-confidence abstention rule is a different experiment; it would require coverage and calibration evaluation. Do not equate uncertainty of a clear prediction with cloud cover, or allow a model to improve its score by arbitrarily withholding difficult pixels.

## 4. Inputs, resolution, dates, and study population

Recommended starting common grid: **30 m**, to reuse the local preparation route and match Prithvi's pretraining resolution. Check the additional models' expected resolution during screening; lock the common grid before full runs and disclose any pretraining-to-input resolution shift. This is a project choice, not a statement that both sensors natively measure every band at 30 m.

| Input | Proposed measurements | Purpose |
|---|---|---|
| Sentinel-2 L2A source package | Retain the twelve L2A bands where available, with band names, source resolutions, quality and scaling recorded | Support the expanded candidate list, including CROMA |
| Six-band optical comparison | B02, B03, B04, B8A, B11, B12 extracted from the same source package | Match the standard Prithvi input |
| Twelve-band multimodal comparison | The same twelve optical bands plus radar VV/VH for every method admitted to this group | Match released CROMA inputs and control information available to competitors |
| Sentinel-1 | VV and VH polarization measurements from one fixed, documented processed product | Complementary radar observations, including through cloud |
| Quality layers | Optical cloud/shadow/no-data and radar coverage/invalid regions | Identify usable measurements and report coverage |

Start from a documented analysis-ready radar product if available. Otherwise explicitly include calibration, terrain correction, radar units, and alignment in preprocessing, following the chosen product's [Copernicus processing documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html). Do not mix raw GRD, terrain-corrected backscatter, linear values, and decibels without a fixed conversion/product definition. Verify VV/VH availability and record orbit/acquisition metadata.

The old six-band image package is insufficient for an unchanged twelve-band CROMA checkpoint. Preserve the twelve-band source package and derive declared subsets; do not duplicate or zero-fill missing bands and describe them as equivalent observations. The twelve-band choice changes input availability and preprocessing/storage requirements, which must be measured.

Align all inputs and labels to the same coordinate system, extent, and pixel grid. Optical values use a fixed physical scaling; model-specific normalization may differ as required by pretraining. Compute fitted statistics on training data only.

Prefer same-day optical, radar, and label observations. Start with a proposed maximum 24-hour radar/optical separation, with labels near both; record actual gaps. If too few pairs survive, review a wider window before finalizing the dataset and disclose it. Flood water changes quickly, so geospatial alignment does not make differently dated images equivalent.

At 30 m, a square grid pixel represents 900 m². A 256 × 256 training crop covers 7.68 km per side. Narrow channels, building-level flooding, and small features remain limited by resolution. Do not resize coarse measurements and describe the result as newly acquired fine detail.

The population is the verified historical Indian flood events for which paired imagery and appropriate labels are available. Report the actual states, dates, groups, image pairs, chips, and labelled area after audit. A convenience sample does not establish performance across all of India.

## 5. Starting resources: what is verified and what needs checking

Local inspection on 6 October found:

- The original event catalogue has 221 rows.
- `data/selection/selection.csv` has 180 candidate optical scene–polygon pairs in 100 heuristic event groups: train 130 pairs/72 groups; validation 18 pairs/12 groups; test 32 pairs/16 groups.
- All 180 polygon paths exist locally. Selected scene identifiers are Sentinel-2 L2A; the HLS identifiers are empty.
- Optical acquisitions differ from label dates by up to two days.
- No `data/chips.csv` or image GeoTIFFs were found in the inspected local `data/` tree. This does not establish that prepared imagery is absent elsewhere.
- The project contains Prithvi preparation/training/evaluation code and a separate public Sen1Floods11 comparison notebook. The latter is a starting resource, not evidence of Indian-event performance.
- Older presentation notes describe prepared chips and completed Prithvi training. Drive folder metadata was visible, but the underlying package, checkpoint integrity, and results were not verified during this session. Inventory/recover these before regenerating data or training.

The 180 pairs are not yet a verified Sentinel-1/Sentinel-2 training package. Radar pairing and full-water labels still need checking. The existing preparation excludes historical water, which conflicts with the newly confirmed target that includes rivers and lakes.

“100 event groups” is the script's heuristic output, not a verified count of independent flood episodes. The script chains same-state label dates within seven days. Audit basin continuity, neighbouring regions, and cross-state floods before trusting independence.

Older notes already contain test scores. That historical split can support a disclosed comparison but cannot be described as a newly untouched holdout. Prefer additional independent test events where feasible; otherwise freeze the reused split before new experiments and disclose prior inspection. Do not reconstruct or claim old results as verified from prose alone.

## 6. Labels are the central acceptance gate

**The current event-inundation polygons cannot simply be reused as full-water labels.** If they omit normal river channels, training `outside polygon = 0` teaches the model to call real water non-water.

Required target construction:

1. Establish a valid mapped reference footprint. The bounding box of positive polygons alone does not prove exhaustive mapping or credible negatives.
2. Use date-matched water references or carefully reviewed annotations that include persistent rivers/lakes as well as event water.
3. Existing flood polygons may supply positive event-water areas. An independent baseline-water layer can help recover persistent water, but do not blindly union a stale historical water layer with event polygons and declare the result ground truth.
4. Visually/independently review water boundaries, seasonal wetlands, fields, reservoirs, and reference negatives. Disagreement or uncertain coverage becomes `-1` until resolved.
5. Record label source, observation time, modality, processing, annotator/review status, and uncertainty. If reference polygons were radar-derived, disclose shared sensor/source limitations.
6. Reference labels under optical cloud can support multimodal evaluation only if independently trustworthy. A model's own radar or optical threshold predictions are not independent ground truth for demonstrating its accuracy.
7. Separate strict test references from automatically generated/weak training labels. If only weak labels are feasible, frame conclusions as agreement with that reference and retain a manually checked test subset.

Before full training, each pair must also pass actual image/label footprint overlap, raster alignment, valid measurements, time-match review, duplicate checks, and event grouping. Inspect overlays before trusting numbers.

Two existing preparation choices need explicit revision/review:

- Permanent/historical water must no longer be universally ignored: confirmed persistent water is a positive target. The existing occurrence threshold of 10% includes intermittent/seasonal water and is not a strict permanent-water definition. Historical products require date/season review before being used as reference positives.
- The chip builder currently balances flood and dry tiles in every split. Sampling can be balanced for training; validation and test should retain the declared eligible mapped footprint. An intentionally balanced test set must be labelled as such and cannot establish natural-prevalence false alarms. Include verified dry examples and, where feasible, no-flood scenes as a separate check.

These are scope requirements, not code changes completed in this session. Set a dataset freeze before training; record every retained/discarded pair and reason. Do not select test cases simply because they agree with an optical water index or look easy.

## 7. Expanded model set and controlled comparisons

A geospatial foundation model is broadly pretrained on Earth-observation data. Its encoder reads the imagery; a segmentation decoder turns the learned features into the water map. CNN/U-Net describe architectures, foundation model describes pretraining/reuse, and water segmentation describes the task. These are different attributes, not mutually exclusive categories.

### 7.1 All six foundation-model families are included

| Family | Proposed starting variant | Role in the study | Input/implementation check before full training |
|---|---|---|---|
| **TerraMind** | Small; Tiny only if profiling requires it | Priority radar–optical candidate, plus optical comparator | Validate the twelve-band optical + VV/VH path, six-band optical subset, quality handling, and segmentation head. [Model card](https://huggingface.co/ibm-esa-geospatial/TerraMind-1.0-small) |
| **CROMA** | Base | Priority radar–optical alternative | Released joint encoder expects two radar and twelve optical channels. Verify band order, normalization, spatial features and segmentation decoder. [Official repository](https://github.com/antofuller/croma) |
| **Prithvi-EO 2.0** | Pilot existing 300M route; 100M if resources favour it | Optical comparator | Standard input is six optical bands; use one locked variant and general pretrained weights for the main pretraining comparison. [Model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M) |
| **DOFA** | ViT-Base candidate; lock exact release/checkpoint in pilot | Additional flexible-band/multisensor candidate | Verify wavelength metadata, release-specific normalization, supported joint radar–optical inference and decoder. Support for each sensor separately does not automatically establish the proposed joint path. [Official repository](https://github.com/zhu-xlab/DOFA) |
| **Galileo** | Compact released encoder chosen after profiling | Additional multimodal/spatiotemporal candidate | Verify modality/band groups, masking, positional/time metadata and usable spatial outputs. Use the same single paired observation as other methods; extra dates/weather/elevation are not silently added. [Official repository](https://github.com/nasaharvest/galileo) |
| **TerraFM** | Published Base candidate | Additional Sentinel-1/Sentinel-2 pretrained candidate | Verify exact optical/radar product, band requirements, joint inference, spatial feature access and segmentation fine-tuning route. [Official repository](https://github.com/mbzuai-oryx/TerraFM) |

Small CNN and U-Net remain the two learned baselines. Start them from random weights. Foundation-model methods start from declared general pretrained encoders and train a segmentation decoder; record any additional supervised history. These choices form a comparison of complete methods, not a universal ranking of architectures.

### 7.2 Compare within input groups

| Group | Planned configurations | Inputs shared within the group |
|---|---|---|
| **A: six-band optical** | CNN, U-Net, Prithvi, TerraMind | The same six Sentinel-2 bands |
| **B: twelve-band optical + radar** | CNN, U-Net, TerraMind, CROMA; add DOFA, Galileo and TerraFM when their exact input paths pass screening | The same twelve Sentinel-2 bands plus VV/VH |

There are **eight priority configurations** (four in A and four in B) and **up to eleven configurations** when all three additional families can enter B. All six foundation families must receive a documented feasibility assessment, even if a family cannot complete full training.

Use the same paired-scene inventory, reference labels, event partitions, physical grid and comparison masks. Group A uses a declared optical subset of B's imagery. Model-specific normalization/layout may differ as required by the released weights; the physical measurements available within each group must match.

If DOFA, Galileo or TerraFM cannot use B's input contract directly, specify its supported subset and compare against CNN/U-Net on that exact subset, or report it as not feasible within the deadline. Such matched controls add configurations and must be charged to the run budget. Do not present different bands, extra dates, different radar products or input adaptations as a controlled architecture comparison.

**A versus B is not a pure test of adding radar**, because B also has more optical bands. To isolate radar's contribution, add a twelve-band optical-only control for each selected B method (CNN/U-Net/TerraMind, and other methods with a supported optical path) and compare it with that method's twelve-band-plus-radar version. These sensor controls are an explicit extension after the main comparison, with separate compute accounting. Without them, report a comparison of input packages rather than attributing all gains to radar.

Lock cloudy-optical handling in the pilot for each admitted method. Adding a mask, replacing invalid values, or relying on a missing-modality mechanism must be implemented and checked, not merely assumed. The same common valid-input rules govern each group's evaluation.

### 7.3 Screening and promotion to full runs

1. Record one exact checkpoint/revision per family, input contract, pretraining history, decoder, dependencies and intended frozen/unfrozen strategy.
2. On a shared small training subset, validate loading, forward/backward/optimizer steps, masked loss, finite predictions, checkpoint save/reload and spatial output alignment. Use validation only for any development checks; never consult test scores for admission.
3. Measure GPU/RAM, epoch-equivalent runtime, data preparation and remaining integration work. All eight model families (CNN/U-Net plus six foundation families) appear in the screening table with pass/fail/pending status and reasons.
4. By **14 October**, lock the feasible full-run configurations and input groups. Prioritize reliable CNN/U-Net controls, TerraMind and CROMA, with Prithvi optical comparison; admit DOFA/Galileo/TerraFM as their measured feasibility and total budget permit.
5. No model is excluded merely for a low early validation score. Admission is based on valid implementation and resource feasibility; validation selects settings/checkpoints. Compare every admitted method with the same agreed tuning allowance, and publish the admission decision.

The intended expanded study includes all six families; three-seed full training of every variant is not promised before the VM and integration costs are measured. A missing full result must be explicitly reported as an implementation/resource limitation, not a performance defeat.

The Prithvi Sen1Floods11-adapted checkpoint is a separately labelled transfer baseline because it used additional supervised flood data. A new Prithvi radar-fusion architecture remains outside the core. Use consistent segmentation decoders where compatible and document differences where not. Freeze/unfreeze strategy and input adaptations are part of each method.

Add a cheap optical water-index threshold baseline using development data and the same reference masks. A radar threshold baseline is optional. Neither replaces CNN/U-Net controls.

## 8. Shared training protocol

Proposed defaults to lock after a training-only pilot:

- Same pairs, reference maps, event split, grid, augmentation rules, and crop footprint within each input group. Start with 256 × 256 native-grid crops; verify compatibility with every admitted encoder and change the common crop size before full runs if needed. Additional bands must not cause candidate-specific scene exclusions; freeze a common inventory or report a separate input group.
- A common masked binary cross-entropy objective. A two-logit cross-entropy implementation is equivalent for this binary objective. Use training-derived class weights consistently if needed; skip all-invalid crops.
- AdamW with method-appropriate learning rates and the same three-trial tuning allowance per configuration. Identical learning rates are not required for fairness. Log all trials and total compute.
- Proposed 30-epoch ceiling, early stopping after five epochs without validation improvement, and best-checkpoint selection by mean per-event validation water IoU on the declared common comparison area.
- Main binary threshold 0.5. Any separately optimized threshold uses validation only and is reported as a secondary result.
- Three recorded seeds for selected settings; report all runs and mean ± standard deviation. Do not report only the best seed.
- Pilot full fine-tuning with mixed precision and small batches. If a frozen-encoder strategy is necessary, choose it before final runs and label it explicitly. Report which parameters are trained, decoder, starting weights, effective batch size, and parameter count.
- Full-scene inference through a fixed tile/stitching rule, counting each ground pixel once. The reference map never controls inference-time prediction masking.
- All tuning uses development data. Final test inspection follows protocol/configuration freeze; test failures become reported limitations, not prompts for more test-directed tuning.

The previous 35-run estimate is replaced by a configuration-count budget. Let **K** be the number of admitted configurations, including any extra matched-input or sensor controls:

| Protocol | Full training runs | Eight priority configurations | Eleven expanded configurations |
|---|---|---|---|
| Three learning-rate trials + two additional seeds for each selected setting | 5K | 40 | 55 |
| Two learning-rate trials + two additional seeds | 4K | 32 | 44 |
| One selected setting, three seeds, with no learning-rate search | 3K | 24 | 33 |

Reuse each winning tuning trial as its first repeat; failed trials still consume compute and must be logged. **Feasibility pilots, failed integrations, source-data preparation and final inference are additional costs**, not included in these full-run counts. Each extra admitted control increases K.

Plan around the eight priority configurations first, while screening all six foundation families. Extend to eleven if measured runtime and integration allow. Freeze any reduced trial/seed allowance equally across comparable methods before full training; one-run results are preliminary. Publish full results for every admitted configuration and an explicit status for every screened family.

## 9. Evaluation that remains fair under cloud

Use two evaluation views:

1. **Common observable area:** pixels with reliable labels and usable inputs for all compared methods, including clear optical observations. This supports fair accuracy comparisons within matched-input groups. A radar-only attribution additionally requires the matched optical-band sensor controls in section 7.
2. **Additional radar-supported area:** reliably labelled pixels where radar is usable but optical is obscured. Evaluate multimodal methods here and report the added assessment coverage. Optical-only methods have unavailable predictions there, not incorrect dry predictions.

Keep the main multimodal evaluation validity fixed across those methods. Model-specific missing predictions/errors must be reported, rather than shrinking each model's test set to its successful pixels. Coverage reporting prevents misleading high scores obtained by assessing only easy areas.

For valid labels, count correctly predicted water (TP), false water detections (FP), and missed water (FN):

- Water IoU = TP / (TP + FP + FN).
- Water F1 = 2TP / (2TP + FP + FN).
- Precision = TP / (TP + FP).
- Recall = TP / (TP + FN).

Example: 100 true water pixels, 80 detected, and 20 false detections gives IoU 80/120 = 0.667 and F1 160/200 = 0.800. For the same binary counts, F1 = 2IoU/(1+IoU), so they do not provide independent rankings. Precision and recall explain the false-alarm/missed-water tradeoff.

Primary ranking within each group: mean per-event water IoU on its declared common evaluation area, averaged over seeds. Also report pooled IoU/F1, per-event precision/recall, coverage, and seed variation. State how undefined ratios/no-positive events are handled and retain false-positive counts on verified dry scenes.

Compare methods by matched event results. An event-resampling interval is useful when enough independent events exist. Millions of correlated pixels are not millions of independent experiments. If differences are small or inconsistent, describe comparable performance and compute tradeoffs.

Also report training GPU-hours, peak GPU memory, total/trainable parameters, and inference time for equal-area scenes on the same machine. Compare representative failures near river edges, agriculture, settlements, cloud, vegetation, and radar ambiguities where the dataset contains them. State reference-label limitations.

Water-area calculation: count predicted water over assessable pixels and multiply by projected pixel area. At 30 m this is 900 m² per square grid pixel. Report unassessed area alongside mapped water area. Do not call this total-event flood damage or new-inundation area.

## 10. Compute and cost boundary

The supplied VM is reported to have one GPU, 64 GB RAM, and 1 TB disk. The message says L4 with 16 GB VRAM; NVIDIA lists the standard L4 with 24 GB. Verify the actual device, available memory, shared use, usable disk, time quota, and cost allowance. This plan conservatively budgets around 16 GB usable GPU memory until measured.

Sequential baseline training and cropped foundation-model fine-tuning are plausible on a single GPU; exact duration/feasibility needs profiling. Training foundation models from scratch is outside scope.

The pilot must include a training forward/backward/optimizer step, validation, checkpoint writing, and scene inference for each method. Measure peak GPU/RAM, epoch time, checkpoint size, and data footprint. Model loading alone does not establish that training fits.

Estimate GPU-hours using each admitted configuration's measured epoch duration, expected epochs and tuning/repeat count, then add pilots, failed runs, validation, checkpoint I/O and final inference. Different encoders and twelve-band inputs need separate measurements.

Illustration only, at the 30-epoch ceiling:

| Full-run scenario | At 5 minutes/epoch | At 20 minutes/epoch |
|---|---|---|
| 40 runs: eight priority configurations, three-trial search and repeats | 100 GPU-hours | 400 GPU-hours |
| 55 runs: eleven expanded configurations, same protocol | 137.5 GPU-hours | 550 GPU-hours |

These arithmetic scenarios exclude additional costs and are **not measured predictions**. Add measured pilot/integration overhead and any extra controls before committing to the expanded comparison. Check the actual hours available to the team as well as provider quota/cost.

Run one GPU job at a time, retain logs/resumable checkpoints, and preserve immutable manifests. Inventory existing artifacts before expensive regeneration. Remote access/data transfer requires authorization under the user's workspace rules; VM login instructions supplied as context were not treated as a request to connect in this scope session.

## 11. Milestones and responsibilities

| Dates, 2026 | Deliverable | Completion evidence |
|---|---|---|
| 6–9 October | Freeze target, labels, paired-scene inventory and twelve-band source plan; assign all six candidates | Reviewed river/non-water examples; provenance; exact checkpoint/input requirements; candidate ownership |
| 10–14 October | Common preprocessing and feasibility screening of CNN/U-Net plus all six foundation families | Aligned overlays; backward/checkpoint/inference checks; resource measurements; admission/status table; viable labels; fixed input groups and K |
| 15–23 October | Tune every admitted configuration; integrate additional candidates that passed the 14 October gate | Matched-input controls; trial logs; validation-selected settings; measured run budget; explicit exclusions |
| 24–30 October | Repeats and final comparison for all admitted configurations | Event/pooled metrics, coverage, seed variation and compute; every candidate has a reported status; extra controls only within the locked budget |
| 31 October–5 November | Failure analysis and report/demo | Georeferenced maps, representative errors, reproducible results bundle |
| 6–8 November | Verification and submission buffer | Reloaded saved models and reproduced inference; report/slides checked |
| 9 November | Submission | Complete project package |

Suggested five-person ownership, adjustable for skills:

| Member | Main ownership | Shared dependency |
|---|---|---|
| 1 | Indian event inventory and reference-water labels | Agree label rules with everyone |
| 2 | Sentinel-1/Sentinel-2 pairing, twelve-band source package, quality and manifests; Galileo input/pilot support | Deliver declared subsets from the same aligned source data |
| 3 | CNN/U-Net in both input groups; CROMA encoder/decoder pilot | Establish matched controls and use the common evaluator |
| 4 | Prithvi/TerraMind pilots and integrations; VM profiling and shared job queue | Log exact weights/configurations/resources; publish admission decisions |
| 5 | DOFA/TerraFM pilots; shared metrics, leakage checks and report integration | Candidate tests use the shared evaluator; all members contribute maps and report sections |

All members review labels and conclusions. Share one preprocessing manifest/evaluator rather than letting each model owner create a different dataset. One GPU job queue serves the team.

14 October is a feasibility gate for both data and the expanded candidate list. If full-water labels or radar pairs are insufficient, narrow to a reviewed pilot and state that conclusions are preliminary. If an encoder cannot be integrated in time or exceeds measured resources, record the specific blocker and omit full training transparently. A public benchmark can validate the pipeline but does not replace an Indian-event evaluation. Prioritize correct labels, matched controls and completed comparisons over incomplete model integrations.

## 12. Deliverables and scope boundary

Core deliverables:

1. A precise surface-water task definition with documented `0/1/-1` semantics.
2. A verified Indian paired-sensor dataset manifest, label provenance, sensor timestamps, exclusion reasons, and fixed event splits.
3. A screening/status table for CNN, U-Net and all six foundation families; full trained comparisons for admitted configurations across declared input groups (eight priority, up to eleven expanded before extra controls), plus a simple spectral baseline.
4. Preprocessing/training/shared-evaluation/inference code, dependencies, configurations, seeds, selected weights and logs.
5. Tables covering per-event/pooled IoU, F1, precision, recall, coverage, repeat variation and compute, with bands, starting weights, decoder, tuning allowance and admission/exclusion status disclosed.
6. Georeferenced water-score/maps and a held-out-event inference demonstration.
7. Report/slides explaining the findings, failure modes, dataset bias, and limits.

Optional only after the core: twelve-band optical controls to isolate radar effects; derive newly inundated land from a baseline-water map; add a geographic/year holdout; study limited-label training; test radar-only inputs; or design Prithvi radar fusion. Pick at most one substantial extension. Radar-causality claims require the sensor controls even if they are otherwise optional.

Outside the core: future forecasting/early warning, water depth, damage/mortality estimation, real-time deployment, foundation-model pretraining, nationwide/all-weather reliability claims, and guaranteed recovery of urban/vegetated floods.

## 13. Remaining decisions

Confirmed: 9 November deadline; five members; Sentinel-1 and Sentinel-2; any visible surface water including rivers/lakes; expanded foundation-model list **Prithvi, TerraMind, CROMA, DOFA, Galileo and TerraFM**.

Still to resolve before implementation:

- Locate and verify the latest imagery/chips, masks, manifests, checkpoints, and past results.
- Establish a reliable full-water reference and mapped coverage; determine what fraction can be independently labelled under optical cloud.
- Confirm the processed radar product, spatial resolution, temporal pairing tolerance, and valid paired-scene count.
- Verify twelve-band source availability and each candidate's exact input path; lock matched-input groups and any additional controls. Prithvi radar fusion remains an optional separate implementation.
- Measure VM resources and confirm GPU-hour/cost allowance; lock crop size, checkpoint variants, decoder/freeze strategy, admitted configuration count K and common search/repeat allowance by 14 October.
- Audit event independence and decide whether enough new events exist for a fresh final holdout.

## Primary sources checked on 6 October 2026

- [Prithvi-EO-2.0: pretraining, optical bands, HLS resolution and variants](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M).
- [Prithvi 100M variant](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-100M-TL).
- [Prithvi checkpoint already adapted to Sen1Floods11](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL-Sen1Floods11).
- [TerraMind Small: optical/radar inputs and selectable optical bands](https://huggingface.co/ibm-esa-geospatial/TerraMind-1.0-small).
- [CROMA: released joint radar–optical encoder, input channels and preprocessing](https://github.com/antofuller/croma).
- [DOFA: multisensor models, variable-band inputs and release-specific weights](https://github.com/zhu-xlab/DOFA).
- [Galileo: pretrained remote-sensing encoders, modality masks and input construction](https://github.com/nasaharvest/galileo).
- [TerraFM: Sentinel-1/Sentinel-2 pretraining and released models](https://github.com/mbzuai-oryx/TerraFM).
- [Sen1Floods11 dataset repository](https://github.com/cloudtostreet/Sen1Floods11).
- [JRC water occurrence and permanent/seasonal-water definitions](https://global-surface-water.appspot.com/faq).
- [NVIDIA L4 specifications](https://www.nvidia.com/en-us/data-center/l4/).
