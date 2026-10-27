# IMC analysis of the chondrosarcoma TMA (Cellpose, refined)

## Overview

Imaging mass cytometry (IMC) analysis of a chondrosarcoma tissue microarray from the sarcoma cohort of Humanitas Research Hospital. The aim is to describe the tumour microenvironment of chondrosarcoma at single-cell level: which immune and stromal cells are present, in what numbers, and where they sit relative to the tumour.

The repository holds the processing pipeline, from the raw channel images exported by the imaging facility to single-cell tables ready for phenotyping and spatial analysis.

### The dataset

The tissue microarray contains cores from 15 patients, 11 positions per patient, sampled from defined areas of each tumour:

| TMA row | Area |
|---|---|
| A–C | high-grade tumour |
| D | low-grade tumour |
| E–F | tumour with high inflammatory infiltrate |
| G–H | tumour periphery (inside the tumour edge) |
| I–J | tumour border (non-neoplastic tissue just outside the edge) |
| K | distant normal tissue |

Of the 165 positions, 136 were acquired on the Hyperion at 1 µm resolution. Each region of interest (ROI) has 43 channels: 35 antibodies, two iridium DNA channels and six technical channels (127I, 131Xe, 134Xe, 138Ba, 208Pb, 80ArAr). Patient number equals 16 minus the TMA column, and images are named by acquisition number and TMA position, e.g. `ROI101_C3`.

## Methodology

The workflow is in `notebooks/01_Complete IMC Data Analysis Workflow.ipynb`. Each step calls a numbered script in `scripts/`, writes a log to `logs/` and is followed by a validation cell.

1. **Panel** (`01_create_panel_from_raw.py`). `panel.csv` is built from the channel files present in the raw data. Technical channels are flagged with `analysis = 0`. Segmentation uses DNA1, DNA2 and SOX9 as nuclear markers and S100, CD68, aSMA, CD31, CD3 and CD66b as membrane markers.
2. **Preprocessing** (`02_preprocess_imc_images.py`). The steinbock hot-pixel filter is applied to every channel: a pixel more than 50 counts above all eight neighbours is replaced by its brightest neighbour. The channels are then stacked into one TIFF per ROI and named after the TMA core map.
3. **Segmentation** (`03_segment_cellpose.py`). Cellpose 4.2 (`cpsam_v2`) is run on a nuclear and a membrane composite, each built as the pixel-wise maximum of its markers scaled between the 1st and 99.5th percentiles. Model, software versions and parameters are logged.
4. **Measurement** (`04_measure_intensities.py`, `05_measure_regionprops.py`, `06_measure_neighbors.py`). For every cell, steinbock measures the mean intensity of each marker over the cell's pixels, region properties (area, centroid, shape) and spatial neighbours (cells whose boundaries, expanded by 4 px, touch).
5. **Export** (`07_export_data.py`). Results are written as a single-cell table (`cells.csv`), an AnnData object (`cells.h5ad`) and one GraphML graph per image.

The stacked images (~10 GB) are not stored in the repository; they are regenerated from the raw data by step 2.

## References

- Windhager, J., Zanotelli, V. R. T., Schulz, D., Meyer, L., Daniel, M., Bodenmiller, B., & Eling, N. (2023). An end-to-end workflow for multiplexed image processing and analysis. *Nature Protocols*, *18*(11), 3565–3613. https://doi.org/10.1038/s41596-023-00881-0
- Zanotelli, V. R. T., & Bodenmiller, B. (2017). *ImcSegmentationPipeline: A pixel classification based multiplexed image segmentation pipeline* (Version 0.9). Zenodo. https://doi.org/10.5281/zenodo.3841961
