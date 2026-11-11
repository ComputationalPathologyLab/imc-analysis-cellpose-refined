# IMC Analysis of the Chondrosarcoma TMA

![Workflow](https://img.shields.io/badge/workflow-Steinbock%20IMC-2f6f73)
![Status](https://img.shields.io/badge/status-single--cell%20data%20complete-3b7a57)
![Data](https://img.shields.io/badge/data-chondrosarcoma%20TMA%2C%2015%20patients-5b6f95)
![Segmentation](https://img.shields.io/badge/segmentation-Cellpose%20cpsam__v2-7a5c99)
![Review](https://img.shields.io/badge/review-pathologist%20at%20four%20steps-8a6f3d)
![Phenotyping](https://img.shields.io/badge/phenotyping-in%20progress-9a5c5c)

## Overview

This repository holds the imaging mass cytometry (IMC) analysis of the
chondrosarcoma (CHS) tissue microarray (TMA) of the Humanitas sarcoma cohort.
The aim is to describe the tumour microenvironment of chondrosarcoma at
single-cell level: which immune and stromal cells are present, how many, and
where they lie relative to the tumour.

The workflow follows the Bodenmiller IMC pipeline (Windhager et al., 2023) and
adds the steps that sarcoma TMAs need. A pathologist reviews the data at four
points: the H&E section of every core, the annotation of artifacts and of the
evaluable area, the segmentation, and the choice of markers for phenotyping.

The same workflow was later applied to the chordoma TMA
([imc_analysis_chordoma](https://github.com/ComputationalPathologyLab/imc_analysis_chordoma)).

## Workflow

```text
raw channel images (imaging facility export)
-> panel generation
-> hot-pixel filter, channel stacks
-> Cellpose segmentation (nuclear + membrane composites)
-> intensity, morphology and neighbour measurement
-> CSV / AnnData / GraphML export
-> pathologist's manual review: evaluable area and excluded areas per core
-> cell status per object (clean, counted only, removed)
-> DNA status per core
-> core information and cell selections joined to every cell
-> large-object review
```

## Principles

- Every step is a numbered script in `scripts/`, called from a notebook cell and
  followed by a validation cell.
- Each script writes a log to `logs/` and numbered outputs to `results/`.
- The pathologist's decisions are stored as tables in `data/manual_review/` and
  applied by script; they are never edited by hand downstream.
- Flagged cores and cells are kept, so that their effect can be tested in
  sensitivity analyses.

## Notebooks

| Notebook | Role |
|---|---|
| `notebooks/01_Complete IMC Data Analysis Workflow.ipynb` | Raw inputs, panel, channel stacks, Cellpose segmentation, measurement, neighbours and export, each with a validation cell |

## Dataset

The TMA holds cores from 15 patients, 11 positions per patient, sampled from
defined areas of each tumour.

| TMA row | Sampled area |
|---|---|
| A–C | High-grade tumour |
| D | Low-grade tumour |
| E–F | Tumour with high inflammatory infiltrate |
| G–H | Tumour periphery, inside the tumour edge |
| I–J | Tumour border, non-neoplastic tissue just outside the edge |
| K | Non-neoplastic tissue far from the tumour |

The patient number equals 16 minus the TMA column. ROIs are named by
acquisition number and TMA position, for example `ROI101_C3`.

| Item | Value |
|---|---:|
| Positions on the TMA | 165 |
| ROIs acquired (Hyperion, 1 µm) | 136 |
| Channels per ROI (35 antibodies, 2 DNA, 6 technical) | 43 |
| Cores included after the H&E review | 121 |
| Cores excluded: content did not match the sampled area | 8 |
| Cores excluded by design: non-neoplastic row K | 7 |

## Directory Structure

| Path | Purpose |
|---|---|
| `data/panel.csv` | Steinbock panel: channels, names, segmentation roles |
| `data/roi_marker_availability.csv` | Channels present in each ROI |
| `data/images.csv` | Image metadata |
| `data/cells.csv`, `data/cells.h5ad` | Single-cell table and AnnData object |
| `data/manual_review/core_areas.csv` | Per core: evaluable area, excluded area, density denominator, DNA status, matrix %, inclusion |
| `data/manual_review/cell_flags.csv` | Per object: position relative to the evaluable and excluded areas, `cell_status` |
| `docs/review/` | Pathologist's review of the pipeline |
| `docs/presentations/` | Slides on the workflow and the manual review |
| `notebooks/` | Documented workflow |
| `scripts/` | Numbered scripts; `scripts/r/` holds R helpers for thresholds and clustering checks |
| `logs/` | Run logs |
| `results/` | Numbered tables and figures |

The channel stacks (about 10 GB), masks and per-cell measurement folders are not
stored in the repository; they are rebuilt by steps 2–5. The output folders of
scripts 11–13 are also rebuilt by running the scripts.

## Segmentation Panel

| Role | Channels | `cellpose` value |
|---|---|---:|
| Nuclear | DNA1 (191Ir), DNA2 (193Ir), SOX9 | 1 |
| Membrane / cytoplasm | S100, CD68, aSMA, CD31, CD3, CD66b | 2 |
| Technical, not analysed | 127I, 131Xe, 134Xe, 138Ba, 208Pb, 80ArAr | – |

SOX9, a nuclear marker of chondrosarcoma cells, is added to the nuclear image
because the DNA signal is weak or absent in many matrix-rich cores. CD20 is left
out for lack of signal and CD138 for its non-specific signal.

## Workflow Modules

### 1. Panel Generation

Script: `scripts/01_create_panel_from_raw.py`

- Build the panel from the channel files present in the raw data.
- Assign the nuclear and membrane segmentation markers.
- Flag technical channels with `analysis = 0`.

### 2. Preprocessing

Script: `scripts/02_preprocess_imc_images.py`

- Apply the steinbock hot-pixel filter to every channel: a pixel more than
  50 counts above all eight neighbours is set to its brightest neighbour.
- Stack the channels into one TIFF per ROI, named after the TMA core map.
- `scripts/validate_ome_tiff.py` checks that every stack is a valid OME-TIFF
  whose channel names match the panel.

### 3. Cellpose Segmentation

Script: `scripts/03_segment_cellpose.py`

- Build a nuclear and a membrane composite, each the pixel-wise maximum of its
  markers scaled between the 1st and 99.5th percentiles.
- Run Cellpose 4.2 (`cpsam_v2`) without retraining; model, versions and
  parameters are logged.

### 4. Single-Cell Measurement and Export

Scripts: `scripts/04_measure_intensities.py`, `scripts/05_measure_regionprops.py`,
`scripts/06_measure_neighbors.py`, `scripts/07_export_data.py`

- Mean intensity of every channel over the pixels of each cell.
- Area, centroid, axis lengths and eccentricity.
- Neighbours: cells whose outlines, expanded by 4 px, touch.
- Export as `cells.csv`, `cells.h5ad` and one GraphML graph per ROI.

### 5. Core Masking (exploratory)

Script: `scripts/08_corner_background_correction.py`

- Derive a tissue mask from the marker stack and set pixels outside the core to
  zero, without changing intensities inside the tissue.

### 6. Pathologist's Manual Review

Scripts: `scripts/10_apply_manual_review.py`, `scripts/apply_manual_review.py`,
`scripts/09_masks_to_geojson.py`

Outputs: `data/manual_review/cell_flags.csv`, `data/manual_review/core_areas.csv`

The pathologist drew the evaluable area of every core in QuPath and annotated
barium and lead deposits, antibody aggregates, single-antibody spots, folds and
necrosis. For every object:

| `cell_status` | Rule | Use |
|---|---|---|
| `outside_evaluable_area` | Centroid outside the evaluable area | Removed |
| `clean` | No pixel in an excluded area | Densities and phenotyping |
| `phenotype_not_assessable` | Up to 75% of pixels in excluded areas | Densities only |
| `aggregate_removed` | More than 75% of pixels in excluded areas | Removed |

The density denominator of each core is the evaluable area minus the excluded
areas. Script 09 writes the cell outlines, coloured by status, as QuPath
GeoJSON for visual checks.

### 7. DNA Status per Core

Script: `scripts/11_dna_status_per_core.py`

- An object is DNA-negative when arcsinh(DNA1) + arcsinh(DNA2) < 1.
- A core is valid below 20% DNA-negative objects, intermediate at 20–50% and
  DNA-negative above 50%.

### 8. Cell Annotation and Selections

Script: `scripts/12_annotate_cells.py`

- Join to every cell the core information (patient, sampled area, DNA status,
  inclusion, H&E flags, matrix %) and its review flags.
- Define the selections used downstream: included cores, cells counted for
  densities, cells available for phenotyping.

### 9. Large-Object Review

Script: `scripts/13_large_object_review.py`

- Apply the pathologist's classification of objects larger than 400 px: real
  large cells are kept, non-cellular objects removed, uncertain ones flagged
  for sensitivity analysis.

## Numbered Results

| Output | Description |
|---|---|
| `results/01_panel.csv` | Panel copy |
| `results/01_roi_marker_availability.csv` | Channels per ROI |
| `results/01b_channel_preview_ROI001_E10.png` | Channel preview of one core |
| `results/02_images.csv` | Image metadata copy |
| `results/03_preprocessed_tiff_inventory.csv` | TIFF stack inventory |
| `results/04_cellpose_mask_inventory.csv` | Mask inventory |
| `results/05_intensity_table_inventory.csv` | Intensity table inventory |
| `results/06_regionprops_table_inventory.csv` | Region property inventory |
| `results/07_neighbors_table_inventory.csv` | Neighbour table inventory |
| `results/08_cells.csv` | Exported single-cell table |
| `results/09_cells.h5ad` | Exported AnnData object |
| `results/10_graphml/` | One spatial graph per ROI |
| `results/hot_pixel_check/` | Before/after check of the hot-pixel filter on one core |

## Current Status

| Stage | Status |
|---|---|
| Panel generation | Complete |
| Hot-pixel filter and channel stacks | Complete |
| Cellpose segmentation | Complete |
| Single-cell measurement and export | Complete |
| H&E review and core selection | Complete |
| Artifact and evaluable-area annotation | Complete |
| Segmentation review | Complete |
| Marker selection for phenotyping | Complete |
| Large-object review | Complete |
| Cell phenotyping | In progress |
| Comparison with the IHC counts of the same cores | Planned |
| Spatial analysis | Planned |

## Current Summary

| Metric | Value |
|---|---:|
| Segmented objects, 136 ROIs | 79,739 |
| Objects in the 121 included cores | 62,792 |
| Clean cells, available for phenotyping | 56,734 |
| Counted only (partly on an excluded area) | 3,516 |
| Removed as aggregates | 1,880 |
| Centroid outside the evaluable area | 662 |
| Included cores with adequate / reduced / poor DNA signal | 36 / 18 / 67 |
| Median chondroid matrix on H&E, adequate vs poor DNA signal | 10% vs 80% |
| Markers suitable for phenotyping | 16 of 35 |

## Interpretation Boundaries

- The DNA signal is poor in 67 of 121 cores, mostly those rich in chondroid
  matrix, although the nuclei are intact on H&E. In these cores some non-tumour
  cells without a bright membrane marker may not be segmented.
- No spillover matrix was acquired for this panel, so crosstalk between adjacent
  metal channels is not corrected.
- The segmentation was checked visually, not against manual outlines.
- Only 16 of 35 markers are suitable for phenotyping; checkpoint markers are
  not used.

## Suggested Next Step

Complete the phenotyping with the pathologist's gating rules and a supervised
classifier, check the cell types against the IHC counts of the same cores, and
then run the spatial and sensitivity analyses.

## References

- Windhager J, Zanotelli VRT, Schulz D, et al. An end-to-end workflow for
  multiplexed image processing and analysis. *Nat Protoc*. 2023;18(11):3565–3613.
  https://doi.org/10.1038/s41596-023-00881-0
- Stringer C, Wang T, Michaelos M, Pachitariu M. Cellpose: a generalist algorithm
  for cellular segmentation. *Nat Methods*. 2021;18(1):100–106.
  https://doi.org/10.1038/s41592-020-01018-x
- Zanotelli VRT, Bodenmiller B. ImcSegmentationPipeline: a pixel classification
  based multiplexed image segmentation pipeline (v0.9). Zenodo; 2017.
  https://doi.org/10.5281/zenodo.3841961
