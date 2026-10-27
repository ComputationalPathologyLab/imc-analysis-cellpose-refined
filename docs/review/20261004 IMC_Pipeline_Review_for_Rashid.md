# IMC pipeline review – CHS TMA (`260812_imcAnalysis_cellpose_AllImages`)

**From:** Vincenzo Guastafierro\
**To:** Rashid Hussain\
**Version:** 06/10/2026 – complete review of all steps: **Step 1 – raw data → multichannel stacks** (including Step 3, stacking), **Step 2 – panel and segmentation channels**, **Step 4 – Cellpose segmentation**, **Step 5 – single-cell intensity measurement**, **Steps 6–8 – region properties, neighbor graph, export**, **Step 9 – background assessment**, **Step 10 – single-cell feature processing**, **Step 11 – quality control**, **Step 12 – phenotyping**.

**Supporting files:** all files cited below are in this folder (`data/`, `phenotyping/`, `qupath/`, `figures/`, `marker_qc/`, `scripts/`); `README.md` lists them.

**Basis of the review:** I read the scripts, logs, `data/img`, `data/masks` and `data/cells.csv` in your project folder in read-only mode. I did not modify anything there; all checks ran on in-memory copies. Every number below was measured on the current Cellpose run (136 ROIs, 79 452 cells).

---

## Summary of issues

| ID | Step | Severity | Issue | Proposed fix |
|---|---|---|---|---|
| 1.1 | 1 | 🔴 high | Hot-pixel filter not applied to the pre-exported OME-TIFFs | Apply the steinbock filter (same function, threshold 50) before stacking; re-run downstream |
| 1.2 | 1 | 🟡 low | Stacks are `uint16`; steinbock keeps `float32` (fractional counts lost in the export) | Re-export from the original `.mcd` with steinbock when available |
| 1.3 | 1 | 🟠 medium | 10 images renamed in `data/img` after segmentation; masks and tables still use the old names | Fix names at the source (`data/raw`) and re-run, or apply the mapping below to every derived file |
| 1.4 | 1 | 🟠 medium | 27 ROIs are not 1000 × 1000 px; the legacy `.mcd` path would silently delete them | Set `--min-width/--min-height` default to 0; use tissue-area denominators; flag cells near the image border |
| 1.5 | 1 | 🟠 medium | Facility grid (rows A–K, columns 1–15) ≠ our nomenclature: rows = sampling region, facility column c = our patient 16 − c | Use the core map `20261005 TMA_core_map.csv` (ROI → region, patient) and join it to every output table |
| 2.1 | 2 | 🔴 high | Nuclear (Ir) signal absent in 71/136 cores although nuclei are present and well preserved on H&E: IMC-specific staining anomaly, more frequent in matrix-rich chondroid areas and in some patients | DAPI test on serial section + facility protocol; all-cell analyses on DNA-valid cores; keep DNA-negative cores for tumor-cell analyses without DNA filter |
| 2.2 | 2 | 🟠 medium | Composites = raw pixel-wise max, without per-channel normalization: bright channels dominate; marker set includes CD20 (no signal) and CD138 (doubtful) | Fixed per-channel scaling; new set S100, CD68, aSMA, CD31, CD3, CD66b (no CD20/CD138/CD163); benchmark mean vs max |
| 2.3 | 2 | 🟡 low | Technical channels (127I, 131Xe, 134Xe, 138Ba, 208Pb, 80ArAr) carried as markers | Add an `analysis` column (0 for technical channels); **do not** change `keep` (see below) |
| 2.4 | 2 | 🟡 low | SOX9 in the nuclear composite makes segmentation asymmetric (tumor vs non-tumor) | Keep (decision), document, run a with/without-SOX9 sensitivity check |
| 2.5 | 2 | 🟠 medium | Anucleate objects (no DNA): S100-driven profiles, aSMA fibers | Flag rather than delete; DNA filter à la Meyer 2026 with dataset-specific threshold; sensitivity analysis |
| 2.6 | 2 | 🟡 low | Notebook text ≠ code for segmentation channels | Align documentation |
| 4.1 | 4 | 🟠 medium | Segmentation never validated quantitatively; Cellpose run with default thresholds | Benchmark against a pathologist ground truth; tune `flow_threshold`/`cellprob_threshold` |
| 4.2 | 4 | 🟠 medium | 462 objects > 400 px in 75 cores (up to 4630 px) | Reviewed by pathologist: mostly real large S100+ cells → no size exclusion; join review classes (exclude `LO_non_cell` and 3 non-evaluable cores) |
| 4.3 | 4 | 🟡 low | Two size thresholds (Cellpose `min_size` 20, then area < 4 in step 08): the second is a no-op | One documented threshold (keep 20 px; 89% of 20–25 px objects in valid cores contain DNA) |
| 4.4 | 4 | 🟡 low | Model name/version not logged; masks completed outside the notebook after a crash | Log model, versions, host; make the run restartable per ROI |
| 4.5 | 4 | 🟡 low | 3047 cells (3.8%) touch Ba/Pb antibody aggregates | Flag `in_artifact` from the QuPath/automatic artifact mask before quantification |
| 4.6 | 4 | 🟡 low | 2907 very elongated objects (eccentricity > 0.95), mostly along aSMA fibers/vessels | Flag and review together with the anucleate flag (2.5) |
| 4.7 | 4 | 🟡 low | napari notebook labels masks as "Mesmer" | Rename |
| 5.1 | 5 | 🔴 high | Intensities inherit uncorrected upstream problems (hot pixels, channel spillover, aggregates) | Re-measure after hot-pixel filtering; compensate on mean counts before arcsinh; flag `in_artifact` cells |
| 5.2 | 5 | 🟠 medium | Lateral spillover between adjacent cells: S100+ tumor cells next to a macrophage show 7× higher CD68 | Flag cross-lineage double positives as suspect and resolve with neighbor context/image review; three options below |
| 5.3 | 5 | 🟡 low | Nuclear markers measured over the whole cell (diluted by cytoplasm) | Accept (IMC standard); optional nuclear-compartment measure in DNA-valid cores |
| 6.1 | 6 | 🟡 low | Centroid axes: `centroid-0` = y (row), `centroid-1` = x (column) | Always map x = `centroid-1`, y = `centroid-0` when matching QuPath/GeoJSON or plotting |
| 7.1 | 7 | 🟠 medium | Expansion graph (4 px) leaves 47% of cells isolated in DNA-negative/matrix-rich cores (19% in valid cores) | Add a distance-based graph (e.g. centroids ≤ 20–30 µm or kNN with max distance); use within-image permutation tests |
| 7.2 | 7 | 🟡 low | Graph built before exclusions (artifacts, non-cell objects, excluded cores) | Rebuild the graph after exclusions, or drop edges touching excluded cells |
| 8.1 | 8 | 🟡 low | `cells.h5ad` not readable in the scimap environment (anndata version); duplicated large outputs (`data/` vs `results/`) | Keep `cells.csv` as canonical; build AnnData in the analysis environment with metadata and flags; record versions |
| 9.1 | 9 | 🟡 low | Background assessment validated on few ROIs; its core mask assumes a round core with glass around it | Keep "no subtraction"; keep the notebook as a QC metric, not a correction; do not reuse its core mask as tissue area |
| 10.1 | 10 | 🟠 medium | Processing script `08_process_single_cell_features.py` missing from the project; never run on the current Cellpose data; name clash with `08_corner_background_correction.py` | Add the script (sketch below) with a unique number |
| 10.2 | 10 | 🔴 high | Pooled 99th-percentile censoring flattens rare positive populations: for 27/37 markers p99 < 3 counts, and for CD20, RORgT, CD15, CD86 p99 < 1 count | Exclude artifacts first; censor only the phenotyping matrix, at a marker-aware percentile (≥ 99.9 or above the positivity threshold) |
| 10.3 | 10 | 🟠 medium | Wrong order: exclusions (artifacts, non-cells, non-evaluable cores) and compensation not applied before computing percentiles | Order: exclusions → compensation (counts) → arcsinh → censoring for phenotyping only |
| 11.1 | 11 | 🟠 medium | QC notebook is descriptive only, run on the old Mesmer data; no core-level exclusion criteria | Core QC table (DNA status, tissue-normalized density, artifact fraction, pathologist flags, per-channel SNR) with explicit exclusion rules |
| 11.2 | 11 | 🔴 high | Several markers do not mark what they should in CHS (CD3/CD4/CD8 only in combination; CD31 also on macrophages; ERG not usable; CD15, PDL1 doubtful; CD20, RORgT no signal) | Pathologist-reviewed usability list; phenotype rules (T cells = CD3+ & (CD4+ or CD8+) & CD68−; endothelium = CD31+ & CD68−/CD163−) |
| 11.5 | 11 | 🔴 high | State/subtype markers (FoxP3, Tbet, GATA3, CTLA4, PD1, LAG3, CD80, CD86, CD10, CD21, CD138, CD47, CD72a, CD15) positive almost only on multi-positive aggregate-like objects; T cells threshold-dependent (4 → 215 cells for > 2 → > 1 counts) | Do not gate on them now; re-assess after hot-pixel filter, artifact exclusion, per-core thresholds |
| 11.3 | 11 | 🟠 medium | Strong between-patient intensity differences (S100 in S100+ cells: median 5–80 counts by patient, 15×) | Per-core/per-patient thresholds; batch assessment by patient and region |
| 12.1 | 12 | 🔴 high | Phenotyping run only on the old Mesmer data; implausible result (T cells 69%, tumor 3.6%; one SOM cluster = 83% of cells) | Re-run only after the upstream fixes; validate on images before any interpretation |
| 12.2 | 12 | 🔴 high | astir schema built on unusable/unreviewed or non-lineage markers (ERG, CD20, CD21, CD15, TFs, PDL1, CD47, Ki67) | Rebuild the schema from the reviewed usability list, or drop astir as primary method |
| 12.3 | 12 | 🟠 medium | mclust thresholds pooled over all cells, with an 80th-percentile fallback | Per-core thresholds; flag/forbid the fallback |
| 12.4 | 12 | 🟠 medium | SOM on z-scored pooled data, all schema markers, fixed 24 clusters | Cluster on usable lineage markers only; choose k on data; use clustering as exploratory/validation |
| 12.5 | 12 | 🟠 medium | Cluster categories (tumor/mixed/non-tumor) use an ambiguous reading of Meyer's thresholds; mixed clusters resolved by astir, not GMM; custom weighted scores | Hierarchical rule-based gating with pathologist rules, then a classifier |
| 12.6 | 12 | 🟠 medium | No image-based validation of phenotypes | Mandatory overlay review with the pathologist (scimap viewer) + per-core comparison with IHC |
| 12.7 | 12 | 🟡 low | Pathologist's chordoma gating rules (v2) not adapted to CHS → done (12.8: minimal and complete tables) | Final CHS tables (minimal: implement now; complete: if all antibodies worked); implement L1–L3 as a SCIMAP phenotype workflow |
| 2.7 | 2 | 🟠 medium | In DNA-negative cores, non-tumor cells without a strong membrane/cytoplasm marker are not segmented at all | Report marker-positive densities (not fractions) in those cores; optional H&E nuclear counts as denominator |

Severity: 🔴 can change biological results · 🟠 can break matching or comparability · 🟡 minor or for robustness.

---

## Step 1 – Raw data → multichannel stacks (`scripts/02_preprocess_imc_images.py`)

### 1.1 Hot-pixel filter not applied 🔴

**Evidence.**
- The script calls `steinbock preprocess imc images --hpf 50` only on the legacy `.mcd`/`.txt` path. For per-channel OME-TIFF folders (our case) it just stacks the channels, and the log says so: `hot_pixel_filter=not_applied_for_preexported_ome_tiff_channels`.
- I applied the steinbock rule to all 136 stacks: a pixel is hot if it exceeds the maximum of its 8 neighbors by more than 50 counts.

| Channel | Hot pixels (sum over 136 ROIs) | Cells with ≥ 1 hot pixel inside the mask | % of all cells |
|---|---|---|---|
| S100 | 4364 | 2122 | 2.67 |
| aSMA | 2979 | 787 | 0.99 |
| PDL1 | 5944 | 438 | 0.55 |
| CD31 | 5390 | 327 | 0.41 |
| SOX9 | 3375 | 320 | 0.40 |
| CD45RO | 2066 | 245 | 0.31 |
| CD68 | 2137 | 159 | 0.20 |

- Hot pixels are present in every ROI: 31 416 in the 37 antibody channels, in 2686 of 5032 ROI × channel combinations. The technical channel 80ArAr has millions, which is expected and irrelevant.

**Why it matters.** Mean cell area is about 58 px. One pixel of value > 50 raises the cell mean by about 1 count, while most markers have cell medians of 0.1–0.6. A single hot pixel can therefore turn a negative cell into a "positive" one. For rare populations (PDL1+, CD31+, ERG+) 0.4–0.6% false hits is of the same order as the true population. Censoring at the 99th percentile does not remove these cells: it caps them at a value that is still in the positive range.

**How the steinbock filter works** (`steinbock/preprocessing/imc.py`, verified on the current source):

```python
def filter_hot_pixels(img: np.ndarray, thres: float) -> np.ndarray:
    kernel = np.ones((1, 3, 3), dtype=bool)
    kernel[0, 1, 1] = False                      # 8-neighborhood, center excluded
    max_neighbor_img = maximum_filter(img, footprint=kernel, mode="mirror")
    return np.where(img - max_neighbor_img > thres, max_neighbor_img, img)
```

It works channel by channel and only touches pixels that are *isolated* spikes: brighter than every one of their 8 neighbors by more than `thres`. Those pixels are replaced by the brightest neighbor. Real signal from a cell spans many pixels, so it is never affected.

**Proposed fix.** Add the same function to `02_preprocess_imc_images.py` and apply it to the stack before writing. Keep `float32` as steinbock does.

```python
# --- add near the imports ---------------------------------------------------
from scipy.ndimage import maximum_filter

def filter_hot_pixels(img, thres):
    """Identical to steinbock.preprocessing.imc.filter_hot_pixels (C x Y x X)."""
    kernel = np.ones((1, 3, 3), dtype=bool)
    kernel[0, 1, 1] = False
    max_neighbor_img = maximum_filter(img, footprint=kernel, mode="mirror")
    return np.where(img - max_neighbor_img > thres, max_neighbor_img, img)

# --- in write_marker_folder_images(), replace the stacking block -----------
        stack = np.stack(channel_arrays, axis=0).astype(np.float32)
        if hpf is not None:
            filtered = filter_hot_pixels(stack, float(hpf))
            n_hot = (filtered != stack).reshape(stack.shape[0], -1).sum(axis=1)
            stack = filtered
            log_lines.append(
                f"{roi_dir.name}: hot_pixels_replaced="
                + ",".join(f"{row['name']}:{int(n)}" for row, n in zip(panel_rows, n_hot) if n)
            )
        # ... tifffile.imwrite(output_path, stack, ...) unchanged
```

`hpf` must be passed down from `args.hpf`, which already exists (default `"50"`). Replace the log line `hot_pixel_filter=not_applied…` with `hot_pixel_filter=applied;hpf=50`. **Everything downstream has to be re-run**: segmentation inputs change slightly, intensities change.

### 1.2 `uint16` stacks vs `float32` 🟡

Steinbock writes images as `float32` (`io.img_dtype`). Our stacks are `uint16` because the exported OME-TIFFs are `uint16`, so the fractional part of the counts is lost in the export. At our signal levels (cell medians 0.1–6 counts) this rounding is not negligible. Vincenzo is asking the facility for the original `.mcd` files: with them we could run the standard `steinbock preprocess imc images --hpf 50`, which fixes 1.1 and 1.2 together.

### 1.3 Ten images renamed after segmentation 🟠

`data/img/` was modified on 15/09: ROI032–041 were renamed with their TMA coordinate. Every file produced before that date still uses the old name: `data/masks`, `data/intensities`, `data/regionprops`, `data/neighbors`, `data/graphs`, `data/images.csv`, `data/roi_marker_availability.csv`, `data/cells.csv`/`.h5ad`, `results/04–07` inventories.

**I checked that the content is identical.** For all ten pairs, the cell means recomputed from the renamed image with the old mask match `cells.csv` exactly (DNA2 and S100, tolerance 0.001). None of the 136 TMA positions is duplicated.

| Current name in `data/img` (**recommended name**) | Name still used in masks / tables |
|---|---|
| `ROI032_I13.tiff` | `ROI032_ROI_032.tiff` |
| `ROI033_G12.tiff` | `ROI033_ROI_033.tiff` |
| `ROI034_G13.tiff` | `ROI034_ROI_034.tiff` |
| `ROI035_C1.tiff` | `ROI035_ROI_035.tiff` |
| `ROI036_K6.tiff` | `ROI036_ROI_036.tiff` |
| `ROI037_F10.tiff` | `ROI037_ROI_037.tiff` |
| `ROI038_E15.tiff` | `ROI038_ROI_038.tiff` |
| `ROI039_F14.tiff` | `ROI039_ROI_039.tiff` |
| `ROI040_D7.tiff` | `ROI040_ROI_040.tiff` |
| `ROI041_D5.tiff` | `ROI041_ROI_041.tiff` |

**Why it matters.** Vincenzo's QuPath artifact annotations (GeoJSON) are made on the images in `data/img`, so they carry the new names. Matching them to `cells.csv` by name would miss these ten ROIs.

**Proposed fix.** The cleanest option is to rename the ROI folders in `data/raw/` with the same mapping and re-run from step 2. That re-run is needed anyway for 1.1, and all names then derive from one source. If a re-run is not possible yet, a one-off script can apply the mapping to every derived file:

```python
from pathlib import Path
import pandas as pd

W = Path("260812_imcAnalysis_cellpose_AllImages")
mapping = {f"ROI{k:03d}_ROI_{k:03d}": new for k, new in zip(range(32, 42),
           ["ROI032_I13", "ROI033_G12", "ROI034_G13", "ROI035_C1", "ROI036_K6",
            "ROI037_F10", "ROI038_E15", "ROI039_F14", "ROI040_D7", "ROI041_D5"])}

for sub, ext in [("masks", ".tiff"), ("intensities", ".csv"), ("regionprops", ".csv"),
                 ("neighbors", ".csv"), ("graphs", ".graphml")]:
    for old, new in mapping.items():
        src = W / "data" / sub / f"{old}{ext}"
        if src.exists():
            src.rename(src.with_name(f"{new}{ext}"))

for table, col in [("data/cells.csv", "Image"), ("data/images.csv", "image")]:
    df = pd.read_csv(W / table)
    df[col] = df[col].replace({f"{o}.tiff": f"{n}.tiff" for o, n in mapping.items()})
    df.to_csv(W / table, index=False)
# then regenerate cells.h5ad, graphs export and the results/ inventories (step 07)
```

### 1.4 27 ROIs are not 1000 × 1000 px 🟠

All of them belong to the last acquisitions (ROI103–131). Fifteen are row-A cores cut by the slide edge; the others are smaller rectangles drawn on individual cores. The full list is in Appendix A.

**Consequences and fixes**

1. **Silent loss on re-run (bug).** On the `.mcd` path, `filter_preprocessed_images()` uses `--min-width 1000 --min-height 1000` by default and *deletes* (`unlink`) every smaller image. Re-running from `.mcd` with default arguments would drop all 27 ROIs, including the row-A cores already annotated in QuPath.
   → Change the defaults to `0`, or pass `--min-width 0 --min-height 0`.
2. **Counts per ROI are not comparable.** ROI area ranges from 0.23 to 1.18 mm², and even square ROIs do not contain the same amount of tissue. Densities must be **cells per mm² of tissue**, where tissue area = tissue outline − excluded artifact areas.
   - An automatic tissue mask (smoothed sum of antibody channels + Otsu) works on cellular cores but **fails on matrix-rich chondroid cores**, where the matrix gives almost no signal and there is no glass to threshold against.
     A quick test on 6 cores with a count-density mask (number of channels with ≥ 1 count, smoothed + Otsu) gave good outlines on cellular cores (ROI031, ROI129) but wrong or inverted ones on matrix-rich cores (ROI003, ROI107, ROI130, ROI047).
   - Proposal: **automatic draft + pathologist review.**
     1. Vincenzo annotates `Tissue` on ~8–10 training cores covering cellular, matrix-rich and edge-cut cores.
     2. A random-forest pixel classifier (ilastik-like, multichannel + texture features) is trained on those cores and applied to all 136.
     3. The resulting `Tissue` polygons are exported as GeoJSON together with the `Artifacts` pre-annotation; Vincenzo reviews and corrects them in QuPath.

     The outline must **include the chondroid matrix**, because cells per mm² of tissue is then a cellularity measure, which is biologically meaningful for chondrosarcoma grade.
3. **Edge effects in spatial analysis.** Narrow images have a larger fraction of cells near the border, and those cells have artificially fewer neighbors. → Flag cells whose centroid is within ~10 px of the image border and exclude them from neighborhood statistics (keep them for composition).
4. **Background assessment (notebook 03)** assumes an outside-core region of glass. Row-A and inner rectangular ROIs may have little or no glass, so the estimate there is unreliable. This does not change the current conclusion (no background subtraction), but it should be noted.

```python
# densities and border flag (after export; cells = cells.csv, images = images.csv)
import json
import pandas as pd, geopandas as gpd

def _class_name(c):
    # QuPath writes "classification": {"name": ..., "color": ...}; depending on the
    # reader it arrives as a dict or as a JSON string
    if isinstance(c, str):
        try:
            c = json.loads(c)
        except ValueError:
            return c
    return c.get("name") if isinstance(c, dict) else None

def roi_areas_mm2(geojson_path):
    g = gpd.read_file(geojson_path)
    cls = g["classification"].apply(_class_name)
    tissue = g[cls == "Tissue"].geometry.union_all()
    artifacts = g[cls == "Artifacts"].geometry.union_all()
    usable = tissue.difference(artifacts)
    return usable, usable.area / 1e6            # 1 px = 1 µm

def flag_border(cells, images, margin=10):
    sz = images.set_index("image")[["width_px", "height_px"]]
    w = cells["Image"].map(sz["width_px"]); h = cells["Image"].map(sz["height_px"])
    x, y = cells["centroid-1"], cells["centroid-0"]
    cells["near_border"] = (x < margin) | (y < margin) | (x > w - margin) | (y > h - margin)
    return cells
```

### 1.5 TMA design and nomenclature mismatch 🟠

The CHS TMA (one slide) has 15 patients × 11 cores, each core from a different tumor area. The facility acquisition grid uses rows A–K and columns 1–15:

| Facility row | Region (our design) |
|---|---|
| A, B, C | High-grade (highest mitotic activity or atypia) |
| D | Low-grade |
| E, F | High inflammatory infiltrate |
| G, H | Tumor periphery (tumor within 1 mm of the interface) |
| I, J | Tumor border (**non-neoplastic** tissue within 1 mm of the interface) |
| K | Non-neoplastic (no longer acquired in future TMAs) |

**Facility column c = our patient 16 − c** (column 1 = patient 15, column 15 = patient 1). ROI names carry the facility position (e.g. `ROI101_C3` = high-grade core of *our patient 13*).

**Fix.** Never use the facility column as patient ID. Join the core map `data/20261005 TMA_core_map.csv` to every table (columns `roi`, `facility_position`, `patient_id`, `region`, `tumor_region`, `dna_status`, plus per-core DNA metrics):

```python
core_map = pd.read_csv("20261005 TMA_core_map.csv")
core_map["Image"] = core_map["roi"] + ".tiff"
cells = cells.merge(core_map[["Image", "patient_id", "region", "tumor_region", "dna_status"]],
                    on="Image", how="left", validate="many_to_one")
assert cells["patient_id"].notna().all()   # catches naming mismatches (see 1.3)
```

---

## Step 2 – Panel and segmentation channels (`data/panel.csv`, `scripts/03_segment_cellpose.py`)

Current set-up: Cellpose 4.2.1, default model `cpsam_v2`, no diameter, `flow_threshold 0.4`, `cellprob_threshold 0`, `min_size 20`.
- Nuclear composite = pixel-wise max of DNA1, DNA2, SOX9.
- Cytoplasm composite = pixel-wise max of CD20, CD68, CD138, CD31, S100, CD3, aSMA.

Each composite is normalized to its 1st–99.5th percentile per image.

### 2.1 Nuclear (DNA) signal absent in 71 cores 🔴

> **We flag a possible anomaly, not a confirmed failure.** In 71 cores the cells are real (S100 matches H&E), but their nuclei give almost no iridium (DNA) signal. Examples:
> - **DNA-negative:** ROI003_C4, ROI101_C3, ROI107_A5. S100+ lacunar cells with no DNA dot inside; median DNA1 per cell 0.09–0.13.
> - **Valid:** ROI031_K10, ROI014_C5, and the S100-rich ROI072_H14. Nuclei clearly visible inside the cells; median DNA1 per cell 8–21.
>
> In the S100-rich valid cores ROI072_H14, ROI011_E14, ROI008_E12 and ROI056_B13, nuclei look **normal on H&E** (V.G., 05/10), consistent with their IMC DNA signal. The H&E appearance of the nuclei in the DNA-negative cores is the next thing to check.

- **26%** of all cells have arcsinh(DNA1) + arcsinh(DNA2) < 1 (the exclusion criterion of Meyer et al. 2026).
- At core level: **46 cores** with < 20% DNA-negative cells (*valid*), **19** intermediate, **71** with > 50% (*DNA-negative cores*).
- **The pattern follows the TMA design (1.5), not the position on the slide.** DNA-negative cores are concentrated in **tumor regions**, while non-neoplastic tissue is mostly valid:

| Region | Cores | DNA-negative | Intermediate | Valid |
|---|---|---|---|---|
| High-grade (A–C) | 44 | 26 | 9 | 9 |
| Low-grade (D) | 11 | 9 | 2 | 0 |
| High inflammatory (E–F) | 24 | 15 | 2 | 7 |
| Tumor periphery (G–H) | 23 | 12 | 5 | 6 |
| Tumor border, non-neoplastic (I–J) | 27 | 8 | 0 | 19 |
| Non-neoplastic (K) | 7 | 1 | 1 | 5 |

- **By patient** (our numbering) there are three groups:
  - **tumor cores valid:** patients 2 and 6; partly 3, 4, 12, 15;
  - **tumor cores DNA-negative but border/non-neoplastic cores of the same patient valid:** patients 1, 7, 8, 9, 14. Since this happens *within the same patient*, it points to a tumor-tissue-specific factor;
  - **all cores DNA-negative, border included:** patients 5, 10 (except K6), 11, 13. This points to a patient-level, likely pre-analytical, factor.

  Patient 1 even has one valid high-grade core (A15) next to DNA-negative ones (B15, C15).
- My earlier reading of a "gradient on the slide" (rows I–K vs A–H) is superseded: rows are region types.

**Pathologist review (V.G., 05/10).** On visual inspection the DNA-negative cores are **matrix-rich, hypocellular chondroid cores**, and the S100+ cells match the cell distribution seen on H&E. Two consequences:
- the cells segmented in these cores are **real tumor cells**; the S100-driven segmentation finds them correctly;
- part of the low image-level DNA is expected, because there are fewer cells (median 193 cells per core vs 741 in valid cores).

**However, low cellularity does not explain the missing DNA *inside* the cells that are present:**

| Check | Valid cores | DNA-negative cores |
|---|---|---|
| Brightest DNA pixel inside each cell (median) | 21.5 | **4.0** |
| Cells containing at least one nuclear-level DNA pixel (≥ 10) | 90% | **17%** |
| Nuclear-like DNA pixels in the image (3 × 3 mean > 8) vs expected if every cell had a ~25 px nucleus | 9552 vs 13 300 | **92 vs 3625** |
| Valid cores with very few cells (79–199 cells): DNA-negative cells | 4–10% | – |
| Macrophages (CD68 > 2, S100 < 1): median DNA / % DNA-negative | 7.48 / 2% (n = 1274) | **0.37 / 79%** (n = 220) |
| S100+ cells with DNA in S100-rich valid cores (e.g. ROI072_H14, 73% S100+ cells) | 84% | – |

(First three rows: 10 random cores per group.) Hypocellular valid cores have nucleated cells; S100+ cells in valid cores show a DNA dot inside; in DNA-negative cores neither the S100+ lacunar cells nor the S100− macrophages do (figures: `figures/DNA_matrix_comparison.png`, `figures/S100_valid_core_comparison_ROI072_H14.png`).

**Open question, to be settled on H&E.** Do the chondrocyte nuclei in the DNA-negative cores look normal on hematoxylin?
- If yes, the nuclei exist but the iridium intercalator did not label them. That is a staining issue, possibly tissue-type related (chondroid matrix).
- If the nuclei are pale or ghost-like, it is pre-analytical, e.g. decalcification.

A useful control: valid cores that are morphologically similar (matrix-rich chondroid with lacunar cells). If such cores have nuclear DNA, tissue type alone is not the cause.

**H&E review list** (hematoxylin quality of the nuclei, amount of matrix, bone trabeculae or other signs of decalcification, cellularity):

| Group | Patient (facility column) | DNA-negative cores | Valid cores of the same patient (internal control) |
|---|---|---|---|
| All negative | 13 (col 3) | C3 ROI101, I3 ROI089 (border), K3 ROI047 (non-neoplastic) | – |
| All negative | 10 (col 6) | C6 ROI136, I6 ROI088 (border) | K6 ROI036 |
| Tumor only | 9 (col 7) | C7 ROI079, D7 ROI040 | I7 ROI004, J7 ROI030 (border) |
| Tumor only | 1 (col 15) | B15 ROI058, C15 ROI075 | **A15 ROI110** (high-grade, valid), J15 ROI024 |
| Tumor valid | 2 (col 14) | – | C14 ROI028, H14 ROI072 |
| Tumor valid | 6 (col 10) | – | B10 ROI018, F10 ROI037 |

**H&E review (V.G., 05/10; serial section, some cores missing on H&E).**

| Patient | Core | IMC DNA | H&E |
|---|---|---|---|
| 13 | C3 | negative | sharp nuclei, abundant chondroid matrix |
| 13 | I3 (border) | negative | nuclei OK, no matrix (non-tumor) |
| 13 | K3 (non-neoplastic) | negative | nuclei OK, skeletal muscle |
| 10 | C6 | negative | sharp nuclei (few), abundant matrix |
| 10 | I6 (border) | negative | nuclei present but slightly faded, no matrix |
| 10 | K6 | valid | sharp nuclei |
| 9 | C7, D7 | negative | nuclei OK but few, abundant matrix |
| 9 | I7, J7 (border) | valid | nuclei OK, non-tumor |
| 1 | B15, C15 | negative | sharp nuclei, medium nuclear density, abundant matrix |
| 1 | A15 | **valid** | sharp nuclei, **many nuclei**, abundant matrix |
| 1 | J15 (border) | valid | sharp nuclei, non-tumor |
| 2 | C14, H14 | valid | sharp nuclei, many nuclei, little/moderate matrix |
| 6 | B10, F10 | valid | sharp nuclei; little or no matrix; many non-tumor cells / red blood cells |

**Interpretation.**
1. **Nuclei are present and well preserved on H&E in the DNA-negative cores.** The missing iridium signal is therefore not due to absent nuclei, and not to nuclear damage visible on hematoxylin. Strong acid decalcification, which usually weakens hematoxylin too, becomes less likely (only I6 looks slightly faded).
2. **Tumor component.** Valid tumor cores have many nuclei and/or little matrix (C14, H14, B10, F10, A15). DNA-negative tumor cores have abundant matrix with few to medium nuclei. The same patient can have both (patient 1: A15 valid vs B15/C15 negative), so the factor acts at the level of the tissue area, not the patient.
3. **Patient component.** In patients 13 and 10 even non-tumor border cores without matrix are DNA-negative while their nuclei look fine on H&E. Matrix alone does not explain this.
4. **Conclusion.** This is an **IMC-specific nuclear (Ir intercalator) staining anomaly**, more frequent in matrix-rich chondroid areas and in some patients, whose cause cannot be established from the data. Possible contributors to discuss with the facility:
   - Ir intercalator concentration and incubation time;
   - retention of the cationic intercalator by the strongly anionic cartilage matrix;
   - the pre-analytics of those blocks (fixation, decalcification method).

**Suggested tests.**
- A DNA counterstain (DAPI or Hoechst) on an unstained serial section of the affected cores. If DAPI is fine, the problem is the IMC Ir step; if DAPI is weak too, DNA accessibility in the tissue is impaired.
- Ask the facility for the staining protocol and any notes for this slide.
- Check fixation and decalcification records for patients 10 and 13.

**The analysis strategy does not change:** keep DNA-negative cores for tumor-cell analyses without the DNA filter; all-cell analyses on DNA-valid cores.

**The status is visible numerically, not only on images.** In the per-cell intensity tables (`data/intensities/<ROI>.csv`, `data/cells.csv`, columns DNA1/DNA2):

| ROI | Status | DNA1 median per cell | DNA2 median per cell | Cells with DNA1 < 0.5 |
|---|---|---|---|---|
| ROI031_K10 | valid | 21.1 | 37.2 | 0% |
| ROI014_C5 | valid | 8.1 | 14.4 | 0% |
| ROI003_C4 | DNA-negative | 0.09 | 0.15 | 99% |
| ROI107_A5 | DNA-negative | 0.13 | 0.22 | 97% |

At pixel level the 99.9th percentile of DNA1/DNA2 is about 27/46 counts in valid cores and 4/5 in DNA-negative cores. Per-core values for all 136 ROIs are in `data/20261005 TMA_core_map.csv` (columns `dna_status`, `DNA1_median_per_cell`, `DNA2_median_per_cell`, `DNA_pixel_p99`) and in Appendix B. An automatic core-level QC flag is therefore straightforward: `dna_status = dna_negative` if > 50% of cells have summed arcsinh DNA < 1.

For visual review in QuPath/napari, use a **fixed display range across cores** (e.g. DNA1 0–20, DNA2 0–30). Auto-contrast stretches the noise of DNA-negative cores until it looks like signal.

**Consequence for segmentation.** In DNA-negative cores Cellpose builds cells on the cytoplasm composite: 80% of DNA-negative objects there are S100 > 2. These are real tumor cells, but non-tumor cells without a strong membrane marker are not detected, so cell-type *fractions* are biased towards tumor (see 2.7).

**Proposal (updated after the pathologist review).**
1. Run the primary compositional and spatial analyses (all cell types) on DNA-valid cores; evaluate intermediate cores one by one.
2. **Keep DNA-negative cores for tumor-cell analyses**, since the S100+ cells are real (tumor density per mm² of tissue, tumor marker expression). Do **not** apply the DNA filter to them.
3. In DNA-negative cores, report non-tumor populations only as marker-positive densities (2.7).
4. Settle the cause on H&E (above); decide on re-staining/re-acquisition only if needed.

### 2.2 Channel aggregation 🟠

A raw pixel-wise max lets the brightest channels dominate the composite, while faint but clean markers contribute little. Measured on the cell pixels of 15 DNA-valid cores, this is which channel provides the maximum:

| Channel | Current composite (raw max) | After per-channel normalization (99.5th pct) |
|---|---|---|
| S100 | 35% | 23% |
| aSMA | 30% | 21% |
| CD68 | 20% | 16% |
| CD138 | 6% | 14% |
| CD31 | 5% | 12% |
| CD3 | 2% | 8% |
| CD20 | 2% | 5% |

Three channels provide 85% of the current cytoplasm composite. T cells (CD3) and B cells (CD20) contribute almost nothing to the segmentation input, although they are in the panel precisely to delineate those cells. Steinbock aggregates each channel group with `--aggr` (default `mean`) after optional channel-wise `--minmax` or `--zscore` normalization. Proposed change:

```python
def channel_norm(img, lo=1, hi=99.5):
    l, h = np.percentile(img, [lo, hi])
    return np.clip((img.astype(np.float32) - l) / (h - l + 1e-6), 0, 1)

def composite(stack, idx, aggr=np.mean):
    return aggr(np.stack([channel_norm(stack[i]) for i in idx]), axis=0)

nuclear_composite  = composite(stack, nuclear_indices)    # DNA1, DNA2, SOX9
membrane_composite = composite(stack, membrane_indices)   # chosen membrane/cytoplasm markers
```

Which variant is best should be decided on data. Vincenzo will annotate ~200–300 cells in 4–6 crops covering dense, matrix-rich and DNA-poor areas. We then compare:
- (a) the current set-up;
- (b) per-channel normalization + mean;
- (c) (b) plus a candidate pan-membrane marker (**CD47**, ubiquitously expressed, to be checked visually),

using F1 at IoU 0.5. Fewer, cleaner membrane markers are preferable (Lukas Hatscher's advice). Cell-level signal in DNA-valid cores (fraction of cells with mean > 1 count) is a first, objective filter:

| Marker | Median per cell | Cells > 1 | Comment |
|---|---|---|---|
| aSMA | 0.59 | 37% | keep |
| S100 | 0.55 | 31% | keep (tumor) |
| CD68 | 0.21 | 17% | keep (macrophages) |
| CD3 | 0.06 | 1% | keep (only T-cell marker; few T cells in CHS) |
| MHC-II | 0.16 | 2% | optional, check visually |
| CD31 | 0.17 | 2% | staining judged poor on visual review → evaluate separately before use |
| CD138 | 0.19 | 2% | drop (plasma cells rare in CHS) |
| CD47 | 0.19 | 1% | **not usable as pan-membrane marker** (too weak) |
| CD20 | 0.04 | 0% | drop (adds noise only) |

**Segmentation markers revised after the usability review (V.G., 06/10).**

*How many?* Steinbock sets no maximum: every channel flagged in the `cellpose`/`deepcell` column is aggregated (default `--aggr mean`, optional `--minmax`/`--zscore`) into one nuclear and one cytoplasm/membrane image. Mesmer takes exactly 2 channels, Cellpose up to 3. What published workflows use:

| Source | Nuclear channels | Membrane/cytoplasm channels |
|---|---|---|
| Bodenmiller example data (steinbock / IMCDataAnalysis, Windhager et al. 2023) | 3: HistoneH3, DNA1, DNA2 | 5: CD163, CD20, CD3, CD8a, E-cadherin |
| Meyer et al. 2026 (Cellpose) | 3: Ir191, Ir193, H3 | 5: CA9, panCK, SMA, CD8a, CD68 |
| Roseth et al. 2025 (Mesmer) | 3: HistoneH3, Ir191, Ir193 | 4: CD98, CD3, CD138, CD45 |
| L. Hatscher (expert advice) | – | ~7 + 3 acceptable; 15 + 6 not advisable (noise) |

The usual choice is **2–3 nuclear and 4–6 membrane/cytoplasm markers**: clean, membrane- or cytoplasm-localized, together covering the main cell types. A broad marker (E-cadherin/panCK for carcinomas, CD45 for immune cells) is preferred when available; the CHS panel has none (no CD45, vimentin or HLA-I).

**Decision (V.G., 06/10).**
- **Nuclear:** DNA1, DNA2, SOX9.
- **Cytoplasm/membrane (6): S100, CD68, aSMA, CD31, CD3, CD66b.** This is within the published range (4–6) and Hatscher's limit.
  - **CD68 rather than CD163:** one macrophage marker was requested, the better stained of the two. CD68 marks 7.7% of cells in DNA-valid cores with only 13% multi-positive; CD163 marks 0.7% with 61% multi-positive. CD68 also covers all macrophages, not only M2.
  - **CD20 not included (confirmed by V.G.):** in this CHS dataset it has essentially no signal (1 cell > 2 counts in DNA-valid cores; p99 = 0.24 counts). A near-empty channel adds only noise: per-channel normalization stretches its noise to the same scale as real signal (max aggregation), or dilutes the other markers (mean aggregation). In histotypes rich in B cells (CH, DDLPS in the previous IHC study) CD20 should be included, so the segmentation set may need to be **histotype-specific**.
- **CD3 caveat:** CD3 positivity is partly driven by aggregates. Objects created by aggregates are removed by the artifact mask (`in_artifact`, 4.5).

**Normalization: use a fixed scale per channel, not per-image percentiles.** The current script normalizes each composite to its own 1st–99.5th percentile, *per image*. In a core where a population is absent (e.g. no neutrophils), this stretches pure noise to full scale. A fixed, data-derived scale per channel avoids that, e.g. the median across reference cores of the per-core 99.9th percentile (`data/QuPath_display_ranges.csv`):

```python
FIXED_MAX = {"DNA1": 64, "DNA2": 111, "SOX9": 8,                      # nuclear
             "S100": 54, "CD68": 6, "aSMA": 70, "CD31": 5, "CD3": 3, "CD66b": 4}

def composite(stack, names, aggr):           # aggr = np.mean or np.max
    chans = [np.clip(stack[ix[n]].astype(np.float32) / FIXED_MAX[n], 0, 1) for n in names]
    return aggr(np.stack(chans), axis=0)

nuclear  = composite(stack, ["DNA1", "DNA2", "SOX9"], np.max)
membrane = composite(stack, ["S100", "CD68", "aSMA", "CD31", "CD3", "CD66b"], aggr)   # test mean AND max
```

**Benchmark:** compare **mean vs max** aggregation (both with fixed per-channel scaling) against the pathologist ground truth (4.1).

### 2.3 Technical channels 🟡

`steinbock.io.read_panel()` drops `keep == 0` rows, and the remaining names are used to label the intensity columns. Since the stacks already contain all 43 channels, setting `keep = 0` now would misalign column names with image channels. Add a column instead:

```python
panel["analysis"] = (~panel["name"].isin(
    ["127I", "131Xe", "134Xe", "138Ba", "208Pb", "80ArAr"])).astype(int)
# downstream (08_process_single_cell_features.py etc.):
markers = panel.loc[(panel["keep"] == 1) & (panel["analysis"] == 1), "name"].tolist()
```

138Ba and 208Pb stay available for the automatic artifact mask.

### 2.4 SOX9 in the nuclear composite 🟡

Decision: **keep it.** In DNA-valid cores DNA dominates the nuclear composite. In DNA-poor cores SOX9 is the only nuclear signal, and only for tumor cells. Document the asymmetry and run a sensitivity check on DNA-valid cores (segmentation with vs without SOX9: cell counts, area, per-type counts).

### 2.5 Anucleate objects 🟠

Removing objects without nuclear signal is standard cell-level QC: Meyer et al. 2026 exclude cells with summed arcsinh DNA < 1. In chondrosarcoma, however, part of the anucleate S100+ profiles are probably real tumor cells cut outside the nucleus (12–23% in good cores). Proposal:
- add `dna_sum = arcsinh(DNA1) + arcsinh(DNA2)` and a flag `anucleate = dna_sum < t`, with `t` chosen on the histogram and checked on images (the "< 1" of Meyer was defined on 3 DNA channels incl. H3);
- exclude anucleate objects from analyses by default;
- run a sensitivity analysis keeping S100+/SOX9+ anucleate profiles as tumor;
- aSMA-driven anucleate objects (~108 in good cores, elongated) are removed by the same flag.

### 2.6 Documentation 🟡

The notebook table lists DNA1, DNA2, 191Ir, 193Ir and CD45RO; the code uses DNA1, DNA2, SOX9 (nuclear) and CD3, CD20, CD31, CD68, CD138, aSMA, S100 (membrane). Align the text with the code.

### 2.7 Undetectable non-tumor cells in DNA-negative cores 🟠

> **Flag:** in cores with low DNA signal, **non-tumor cells are difficult to identify**. Without a nucleus to anchor them, they are segmented only if they carry a bright cytoplasm/membrane marker.

In cores without DNA signal, a cell is segmented only if it carries a bright cytoplasm/membrane marker. Non-tumor cells without one (most stromal cells, T cells with weak CD3, cells of lineages not represented in the composite) are simply absent from the masks. **This cannot be repaired computationally.** In those cores:
- do not report cell-type *fractions*: the denominator (all cells) is incomplete;
- report marker-positive *densities* (cells/mm² of tissue);
- if needed, use nuclear counts from the H&E serial section (QuPath cell detection) as an approximate total-cell denominator;
- flag these cores in every output table (`dna_status = dna_negative`).

The list of DNA-negative and intermediate cores is in Appendix B (and `data/20261005 TMA_core_map.csv`).

---

## Step 4 – Cellpose segmentation (`scripts/03_segment_cellpose.py`)

Set-up: Cellpose 4.2.1, `models.CellposeModel(gpu=False)`, whose default model in this version is **`cpsam_v2`** (Cellpose-SAM, checked in the v4.2.1 source); no diameter; `flow_threshold 0.4`, `cellprob_threshold 0.0`, `min_size 20`. Result: 79 452 objects, median area 58 px (valid cores 53 px; DNA-negative cores 81 px, where objects are drawn on the S100 cytoplasm).

### 4.1 No quantitative validation of the segmentation 🟠
The parameters are the defaults and were never compared to a reference. Visual QC (scimap notebook) covers only a few ROIs.
**Fix.** Benchmark against a pathologist ground truth:
- Vincenzo corrects the Cellpose masks in 4–6 crops (~150 × 150 µm: dense, matrix-rich, stroma, DNA-poor), about 200–300 cells.
- Compare: current set-up / per-channel-normalized mean composites (2.2) / reduced marker set, plus a small grid of `flow_threshold` (0.4, 0.6) × `cellprob_threshold` (−1, 0, 1).
- Metric: F1 at IoU ≥ 0.5, plus split and merge counts.

### 4.2 Large objects 🟠
462 objects > 400 px (0.6%; 109 > 1000 px, max 4630 px) in 75 cores. They are concentrated in a few cores: ROI048_K9 (64), ROI047_K3 (39), ROI046_J3 (26), all non-neoplastic or border cores, plus several DNA-negative tumor cores (10–17 each).
**Fix.** Add a flag and exclude flagged objects by default; final decision after pathologist review core by core. One GeoJSON per core (class `Large_object`) is in `qupath/large_objects_geojson/`, with a summary in `data/large_objects_per_core.csv`.

```python
cells["large_object"] = cells["area"] > 400        # threshold to confirm after review
```

**Pathologist review completed (V.G., 05/10)** on all 75 cores (reviewed GeoJSONs in `qupath/large_objects_reviewed/`). Classes:
- **3 cores excluded entirely** (`Core_not_evaluable`): ROI048_K9 (skeletal muscle + vessels), ROI047_K3 (skeletal muscle), ROI046_J3, together 129 objects;
- elsewhere: **240 `LO_cell`**, **63 `LO_uncertain`**, **30 `LO_non_cell`**, **0 `LO_merged`**.

Large objects are mostly **real large S100+ tumor cells** (chondrocytes in large lacunae, median S100 65–150). `LO_non_cell` objects are S100-negative and, in DNA-valid cores, aSMA-high (vessel walls). In DNA-valid cores no `LO_cell` contains ≥ 2 nuclei. Merges could not be judged in DNA-negative cores, where nuclei are invisible.

**Revised fix.** Do **not** exclude objects by size. Join the review classes to the cell table instead:
- keep `LO_cell`;
- exclude `LO_non_cell` and all cells of `Core_not_evaluable` cores;
- treat `LO_uncertain` as a sensitivity analysis.

Matching is done by position (polygon vs mask label, IoU > 0.5), not by name, because QuPath duplicates names when several objects are edited together (`scripts/check_large_objects_review.py`; set the project path at the top). The resulting join table is `data/large_objects_review_classes.csv`: one row per reviewed object, with `roi`, `cell` (= mask label = `Object` in `cells.csv`) and `review_class`; per-core counts in `data/large_objects_review_per_core.csv`. For future datasets an automatic rule can approximate the review: large + S100-high → keep; large + S100-low + aSMA-high → non-cell.

### 4.3 Size thresholds 🟡
Cellpose already removes objects < 20 px, so the area < 4 filter in step 08 removes nothing. In valid cores **89% of 20–25 px objects contain DNA** (95% for 25–40 px), so they are mostly real small nuclei or cells. In DNA-negative cores only 10% do. A gallery of 48 examples for review is in `figures/small_objects_gallery_20-25px.png` (object list: `data/small_objects_gallery_list.csv`).
**What keeping 20 px implies.** Objects < 20 µm² (equivalent diameter < 5 µm) are discarded before any table is written, so we cannot see what was removed. The 20–22 px bin is still populated (1296 objects), so the threshold cuts the tail of a real distribution: a small fraction of genuine small profiles (tangentially cut lymphocyte nuclei, small immune cells) is probably lost, alongside fragments and noise. Expected effect: a slight undercount of small immune cells (mostly relevant in the high-inflammatory rows E–F), and negligible effect on tumor cells, which are large.

**Fix.** Keep a single, documented threshold: `min_size = 20` in Cellpose, and set `--min-area 20` in step 08 (or drop that filter). **Decision (V.G., 05/10): keep 20 px.** Test `min_size` 10 / 15 / 20 in the benchmark on lymphocyte-rich crops (rows E–F) to quantify what is lost. In DNA-negative cores small objects are mostly noise (10% contain DNA) and are removed anyway by the anucleate/no-membrane flags (2.5).

### 4.4 Reproducibility 🟡
- The log does not record the model name or versions.
- In the notebook the run crashed at ROI002 (TIFF read error), and the masks were completed outside the notebook, probably on the HPC.

**Fix.**
```python
import cellpose, torch, platform, socket
model = models.CellposeModel(gpu=gpu)                      # or pretrained_model="cpsam_v2" explicitly
log_lines += [f"cellpose_version: {cellpose.version}",
              f"model: {getattr(model, 'pretrained_model', 'default')}",
              f"torch: {torch.__version__}; python: {platform.python_version()}; host: {socket.gethostname()}"]
# restartable: skip ROIs whose mask already exists, catch and log per-ROI errors
for image_path in image_paths:
    out = masks_dir / image_path.name
    if out.exists() and not overwrite:
        continue
    try:
        ...  # segmentation as now
    except Exception as e:
        log_lines.append(f"ERROR {image_path.name}: {e!r}")
```

### 4.5 Cells touching antibody aggregates 🟡
3047 cells (3.8%) overlap Ba/Pb aggregate hotspots (≥ 15 px), where many antibody channels are 20–60× above tissue level.
**Fix.** Before quantification, flag cells that overlap the artifact mask (Vincenzo's QuPath `Artifacts` + the automatic Ba/Pb pre-annotation): `in_artifact = True` → excluded by default.

### 4.6 Elongated objects 🟡
2907 objects (3.7%) have eccentricity > 0.95, mostly along aSMA fibers and vessels.
**Fix.** Flag them and review together with the anucleate flag (2.5). Remove them only if they are also anucleate.

### 4.7 Documentation 🟡
The napari notebook still labels the masks "Mesmer cell masks". Rename the label to "Cellpose (cpsam_v2) masks".

---

## Step 5 – Single-cell intensity measurement (`scripts/04_measure_intensities.py`)

`steinbock measure intensities` computes, for every cell and every channel, the **mean pixel value inside the mask** (steinbock default, also used by Meyer et al. 2026). **The measurement itself is correct:** recomputing the means from `data/img` and `data/masks` reproduces `cells.csv` exactly (checked on DNA2 and S100, tolerance 0.001). The problems lie in what is fed to it.

### 5.1 Problems inherited from earlier steps 🔴

| Inherited problem | Effect on intensities | Solution |
|---|---|---|
| **Hot pixels not filtered** (1.1) | A single pixel > 50 counts raises a 58-px cell mean by ~1 count; 5062 cell × channel hits (S100 2.7% of cells, PDL1 0.55%, CD31 0.41%, SOX9 0.40%) | Apply the steinbock hot-pixel filter in step 02, then re-run segmentation and measurement |
| **Integer (`uint16`) images** (1.2) | Fractional counts lost; relevant at cell means of 0.1–6 counts | Re-export from the original `.mcd` (float32) |
| **Channel (mass) spillover not compensated** (no spillover matrix) | Signal from neighboring masses adds to each channel | When a spillover slide/matrix is available, compensate **at this level**: on the mean counts per cell, *before* the arcsinh transformation, e.g. `CATALYST::compCytof(sce, sm, transform = TRUE, cofactor = 1)`, as in the Bodenmiller workflow. Not after transformation, as planned in the draft notebook |
| **Antibody aggregates (Ba/Pb hotspots)** (4.5) | 3047 cells (3.8%) overlap aggregates where 20–60 channels are strongly elevated | Flag `in_artifact` from the QuPath/automatic artifact mask and exclude these cells before any downstream use |
| **Name mismatch ROI032–041** (1.3) | Intensity tables for 10 ROIs carry old names | Fix names at source and re-run (see 1.3) |
| **Excluded cores / non-cell objects** (4.2) | 3 non-evaluable cores and `LO_non_cell` objects are in the table | Join the review classes and drop them before transformation and phenotyping |

### 5.2 Lateral spillover between adjacent cells 🟠

In dense tissue part of a cell's signal is assigned to its neighbor (imperfect boundaries, 1 µm laser spot). Measured on DNA-valid cores:

| S100+ cells (S100 > 3, CD68 ≤ 3) | n | CD68 median inside the cell |
|---|---|---|
| without a CD68+ neighbor | 7064 | 0.20 |
| **with a CD68+ neighbor** (steinbock neighbor graph) | 571 | **1.47** (7×) |

The same trend is visible for CD3 (0.08 → 0.19), but only 25 cells have a T-cell neighbor.

**Pathologist's assessment (V.G.):** an S100+CD68+ population has **no biological meaning in chondrosarcoma** (S100 marks tumor cells, CD68 macrophages). A double positive for markers of different lineages on the same cell is **a strong warning sign, not an automatic artifact**: it is often a tumor cell next to a cell of another lineage (lateral spillover), and it must be flagged and reviewed rather than discarded or blindly re-labeled.

**Three possible solutions:**
1. **Computational compensation of lateral spillover.** REDSEA (Bai et al., *Front Immunol* 2021, [doi:10.3389/fimmu.2021.652631](https://doi.org/10.3389/fimmu.2021.652631)) subtracts from each cell the signal estimated to come from its neighbors along the shared boundary. It was validated on MIBI and cyclic immunofluorescence, so it must be tested on our IMC data before adoption.
2. **Rules at phenotyping.** Flag cross-lineage double positives (S100+CD68+, S100+CD3+, S100+CD20+) as `suspect_double`. When the cell has a neighbor of the "foreign" lineage, the foreign marker is most likely spillover: assign the cell to its dominant lineage or require a higher threshold for the foreign marker. Isolated double positives (no such neighbor) are reviewed on the image. Example:
   ```python
   foreign_pos = (cells.CD68 > thr_CD68) & (cells.S100 > thr_S100)
   cells.loc[foreign_pos & cells.has_CD68_neighbor, "CD68_pos"] = False
   ```
3. **Better cell boundaries.** Improve segmentation (Step 2 aggregation, Step 4 benchmark) so that less of a neighbor's signal falls inside the mask.

### 5.3 Minor points 🟡

- **Nuclear markers** (SOX9, Ki67, FoxP3, Tbet, GATA3, ERG) are averaged over the whole cell, so their signal is diluted by the cytoplasm. This is standard in IMC. A nuclear-compartment measurement would need a separate nuclear mask, which is possible only in DNA-valid cores.
- **Mean vs median:** keep the mean (standard). The median would be more robust to residual hot pixels, but with the filter in place it is not needed.

---

## Steps 6–8 – Region properties, neighbor graph, export (`scripts/05–07_*.py`)

These steps run the standard steinbock commands (v0.16.1): `measure regionprops`, `measure neighbors --type expansion --dmax 4`, `export csv / anndata / graphs`. They work as intended. The points below concern how their outputs are used.

### 6.1 Region properties – coordinate convention 🟡
`cells.csv` contains `area`, `centroid-0`, `centroid-1`, `axis_major_length`, `axis_minor_length`, `eccentricity` (1 px = 1 µm). **`centroid-0` is the row (y) and `centroid-1` is the column (x)**, while QuPath/GeoJSON use (x, y). The scimap notebook maps them correctly. Every new script that joins QuPath annotations (artifacts, tissue, large-object review) must do the same.
**Fix.** Document it, and use one helper everywhere:
```python
def cell_xy(cells):
    return cells["centroid-1"].to_numpy(), cells["centroid-0"].to_numpy()   # x, y in µm
```

### 7.1 Neighbor graph in matrix-rich tissue 🟠
With `--type expansion --dmax 4`, two cells are neighbors only if their boundaries, each expanded by 4 px, touch. That suits dense tissue, but chondroid cores are sparse:

| Cores | Cells | Median neighbors per cell | Isolated cells (0 neighbors) | Median distance to nearest cell (µm) |
|---|---|---|---|---|
| DNA-valid | 47 635 | 2 | 19% | 9.8 |
| Intermediate | 13 902 | 1 | 30% | 13.2 |
| DNA-negative (matrix-rich) | 17 915 | 1 | **47%** | 18.4 |

In matrix-rich cores half of the cells have no neighbors at all. Neighborhood statistics (interaction tests, cellular neighborhoods/districts) are therefore underpowered there, and graph density differs systematically between cores.

**Fix.**
- Build a complementary distance-based graph, e.g. centroid distance ≤ 20–30 µm or kNN (k = 5–10) with a maximum distance. `imcRtools::buildSpatialGraph()` supports `expansion`, `knn`, `centroid` and `delaunay`.
- Choose the threshold on biological grounds and report it.
- Use within-image permutation tests (e.g. `imcRtools::testInteractions`), which account for each image's cell density.
- Compare cores with similar cellularity, or stratify by region/DNA status.

### 7.2 Graph built before exclusions 🟡
The graph includes cells that will be excluded (aggregates, `LO_non_cell`, the 3 non-evaluable cores). Excluded objects create false neighbor relations.
**Fix.** Rebuild the graph after the exclusions, or drop every edge touching an excluded cell:
```python
keep = set(map(tuple, cells.loc[~cells.excluded, ["Image", "Object"]].values))
edges = edges[[(i, o) in keep and (i, n) in keep
               for i, o, n in zip(edges.Image, edges.Object, edges.Neighbor)]]
```

**Image-border cells:** only 1.8% of cells lie within 10 µm of the image border (2.4% in non-square ROIs), and their median number of neighbors equals that of interior cells. The border flag proposed in 1.4 is therefore low priority.

### 8.1 Export 🟡
- `cells.h5ad` could not be read in the scimap environment (anndata version mismatch), and the notebook falls back to rebuilding AnnData from `cells.csv`.
- `data/cells.csv` and `results/08_cells.csv` (and the two `.h5ad`) are identical copies of large files, which risks divergence after edits.
- Docker runs the `linux/amd64` steinbock image under emulation on Apple Silicon. That is only a warning, but worth recording.

**Fix.**
- Keep **`cells.csv` as the single canonical table**.
- Build the AnnData object in the analysis environment from `cells.csv` + core map (1.5) + flags (`dna_status`, `anucleate`, `in_artifact`, review classes, `excluded`).
- Record the package versions; keep only one copy of large outputs.

---

## Step 9 – Background assessment (`notebooks/03_corner_background_correction.ipynb`, `scripts/08_corner_background_correction.py`)

The notebook estimates, per channel, the background outside the TMA core and tests subtracting it. **Its conclusion is correct and we agree: no background subtraction.** Outside the core most pixels are 0, and the positive ones are around 1 count (quantized ion counts), so there is no stable additive baseline as in fluorescence. The Bodenmiller workflow does not subtract background either.

### 9.1 Scope of the assessment 🟡
- The assessment was run on ROI001 and "a broader sample".
- The core mask (broad composite, percentile threshold, morphology) assumes a round core surrounded by glass. That does not hold for the 27 non-square ROIs (row A cut by the slide edge, inner rectangles), nor for matrix-rich chondroid cores where the matrix gives almost no signal.

**Fix.**
- Keep the decision (no subtraction).
- Keep the notebook as a **QC metric** (per-channel tissue/outside ratio, i.e. signal-to-background) rather than a correction.
- Do **not** reuse its core mask as the tissue-area denominator. Use the pathologist-reviewed `Tissue` polygons instead (1.4).
- Technical channels with high baselines (127I ~19 counts everywhere, 80ArAr) are excluded via the `analysis` column (2.3).

---

## Step 10 – Single-cell feature processing (`notebooks/02_single_cell_feature_processing.ipynb`)

Planned sequence: remove objects with area < 4 px → censor each marker at its 99th percentile (pooled over all cells) → arcsinh (cofactor 1). The area filter and the censoring come from Roseth et al. 2025 (myeloma), the cofactor from both Roseth and Meyer 2026. Meyer does not censor.

### 10.1 Script missing, step never run on current data 🟠
- The notebook calls `scripts/08_process_single_cell_features.py`, which is **not** in the project (the notebook output says `Processing script exists: False`, and the cell fails).
- `results/` contains no `11_*` outputs for the current Cellpose run.
- The number 08 is already taken by `08_corner_background_correction.py`.

**Fix:** add the script with a unique number (e.g. `09_process_single_cell_features.py`) implementing the order in 10.3.

### 10.2 Pooled 99th-percentile censoring flattens rare populations 🔴
Censoring replaces every value above the marker's 99th percentile with the 99th percentile. If a marker is truly positive in fewer than 1% of cells, the p99 falls **inside the noise of the negative cells**: all real positives are compressed to the same value as the noisiest negatives. Measured on raw mean counts (all 79 452 cells):

| Marker | p99 (counts) | Cells > 3 counts | Max / p99 |
|---|---|---|---|
| CD20 | 0.24 | 0.0% | 110 |
| RORgT | 0.48 | 0.0% | 19 |
| CD15 | 0.64 | 0.0% | 6393 |
| CD86 | 0.67 | 0.1% | 74 |
| CD3 | 1.11 | 0.0% | 90 |
| FoxP3 | 1.18 | 0.3% | 8457 |
| Ki67 | 1.43 | 0.2% | 32 |
| PD1 | 1.58 | 0.4% | 9225 |
| ERG | 1.78 | 0.3% | 7465 |
| PDL1 | 5.60 | 1.9% | 3148 |
| CD68 | 6.49 | 3.6% | 9 |
| S100 | 159.6 | 34.6% | 37 |

- For **27 of 37 markers** p99 < 3 counts, and for CD20, RORgT, CD15, CD86 it is < 1 count.
- The extreme maxima (FoxP3, PD1, ERG, CD15, PDL1: 3000–9000 × p99) are the reason censoring was introduced: they come from **aggregates and hot pixels**, which should be removed at the source (1.1, 4.5), not by clipping biology.
- The p99 also differs strongly between **DNA-valid and DNA-negative cores** (e.g. PDL1 2.73 vs 14.56, CD10 0.57 vs 3.23, S100 61.6 vs 212.5) and between ROIs (S100 p99 per ROI 0.37–465; PDL1 0.19–6713). A single pooled cut-off mixes very different populations.

**Fix.**
1. Remove the outlier sources first: hot-pixel filter, `in_artifact`, `LO_non_cell`, non-evaluable cores.
2. Keep raw and arcsinh-transformed values for all analyses, and apply censoring **only to the matrix used for clustering/phenotyping** (as Lukas Hatscher recommended).
3. Use a **marker-aware cut-off**: percentile ≥ 99.9, and never below the marker's positivity threshold.
```python
def censor_for_phenotyping(X, pos_thr, q=99.9):
    """X: arcsinh values (cells x markers); pos_thr: per-marker positivity threshold (same scale)."""
    Xc = X.copy()
    for m in X.columns:
        cut = max(np.percentile(X[m], q), pos_thr.get(m, 0) * 1.5)
        Xc[m] = X[m].clip(upper=cut)
    return Xc
```

**Pathologist expectation (V.G.):** in CHS a low inflammatory infiltrate and few proliferating cells are expected. This agrees with our previous IHC study on the cohort (CHS: lowest lymphocytic infiltrate among the 8 histotypes except helper T cells, lowest CD68 macrophage density, relatively the highest neutrophil (CD66b) density). In the DNA-valid tumor cores, cells with mean > 2 counts are 0.1% for CD3, 0.3% for Ki67 and FoxP3, and ~0% for CD20. For these markers **even a 99.9th percentile can fall inside the noise**, so they should **not be censored at all** in the phenotyping matrix; outliers are handled by artifact removal.

### 10.3 Order of operations 🟠
The current plan censors and transforms everything before any exclusion or compensation. Proposed order:
1. **Exclusions:** non-evaluable cores, `LO_non_cell`, `in_artifact`, anucleate rule (2.5; not applied to S100+ cells in DNA-negative cores), size (single 20 px threshold, 4.3).
2. **Channel spillover compensation** on mean counts, when a matrix is available (5.1).
3. **arcsinh, cofactor 1**, on all antibody markers (`analysis == 1`).
4. **Censoring only for the phenotyping matrix** (10.2).
5. Save raw, transformed and censored matrices as separate numbered outputs, with all flags as columns.

---

## Step 11 – Quality control (`notebooks/04_quality_control.ipynb`)

The notebook summarizes cell counts, areas and marker distributions *after* transformation, without excluding anything. Its outputs come from the old Mesmer run (`20260717_imcAnalysis`, 321 476 cells), not from the current Cellpose data. Compared with the Bodenmiller QC chapter (per-channel image SNR, cell coverage, cell density, cell-level SNR, batch assessment, visual inspection) and with Meyer et al. 2026 (image exclusion for low marker expression, few cells, small tissue area, low coverage), a core-level and a marker-level QC are missing. Below is what that QC shows on the current data.

### 11.1 Core-level QC 🟠
| Metric (current Cellpose data) | Value |
|---|---|
| Cell coverage of the image (sum of cell areas / image area) | median **3.6%**; 96/136 cores < 5%; 28 < 2% |
| Cells per mm² of image | median 421; 10th percentile 102 |
| Cores with < 100 cells | 15 |
| DNA status | 46 valid, 19 intermediate, 71 DNA-negative (2.1) |
| Pathologist exclusions | 3 non-evaluable cores (4.2) |

Low coverage is **expected** in chondrosarcoma (abundant matrix, hypocellular tissue), so Meyer's "low coverage" criterion cannot be applied as is. Coverage and density must be computed on the **tissue** area (pathologist-reviewed `Tissue` polygons minus `Artifacts`), not on the image area.

**Fix.** Build one QC table per core and use explicit exclusion rules. Columns:
- core map (patient, region);
- `dna_status`;
- cells;
- tissue area;
- cells/mm² tissue;
- artifact area fraction;
- `in_artifact` cell fraction;
- pathologist flags;
- per-channel image SNR (Otsu foreground/background, as in the Bodenmiller book).

Suggested rules:
- exclude cores flagged non-evaluable;
- flag (do not exclude) cores with < 50 cells or tissue < 0.1 mm², and review them visually;
- keep DNA-negative cores only for tumor-cell analyses (2.1).

### 11.2 Marker-level QC: what each marker actually marks in CHS 🔴
Co-expression between lineage markers in DNA-valid cores (cells with mean > 2 counts), compared with the overlap expected by chance:

| Observation | Data | Interpretation |
|---|---|---|
| **CD15** | 0.1% of cells > 2 counts, while CD66b 1.0% | No usable signal (neutrophils should be CD15+CD66b+). Treat as failed |
| **CD3** | 61 cells > 2 counts, of which 95–97% also CD4+, CD8+ and CD68+ | Signal driven by aggregates, almost no specific T-cell signal |
| **CD8** | only 15% of CD8+ cells are CD3+; 62% are CD68+; CD68+CD8+ 3.9× chance | Largely non-specific or spillover |
| **CD4** | 76% of CD4+ cells CD68+, 52% CD163+; CD4+CD68+ 6.2× chance | Mostly **macrophages** (CD4 is expressed by monocytes/macrophages) |
| **CD31** | 70% of CD31+ cells CD68+, 67% CD163+, only 32% ERG+; CD163+CD31+ 59× chance | Mostly **macrophages** (CD31/PECAM-1 is expressed by monocytes/macrophages); also judged poorly stained on visual review |
| **ERG** | 72 cells > 2 counts; 72% CD31+, but 72% of positives are multi-positive | Few vessels in cartilage; **judged not usable** on visual review (V.G.) |
| CD68 + CD163 | 7.4× chance | Expected biology (M2 macrophages) |
| CD68 + S100 | 1.3× chance; strongly neighbor-dependent (5.2) | Lateral spillover artifact |
| CD56 + S100 | 2.8× chance | Possibly genuine tumor expression; check visually |
| **CD20** | ~0% of cells | Consistent with very low B cells in CHS (previous IHC: median 38) |

The previous IHC study on the same TMA found the same pattern in CHS: CD3 lowest (median 25 vs CD8 126 and CD4 1458), macrophages the main infiltrate, relatively more neutrophils. The high CD4 in CHS by IHC may also partly reflect CD4 on macrophages.

**Fix.**
1. **Marker usability list, after pathologist review (V.G., 06/10).** The review used an automatic triage of all 35 antibodies (positive cells, fraction of multi-positive cells, enrichment in aggregates, hot pixels, cell-level contrast) plus galleries of 24 random positive cells per marker (`marker_qc/galleries/`; triage and numeric evaluation tables in `marker_qc/`):

| Verdict | Markers |
|---|---|
| **Usable** | S100, SOX9, CD68, CD163, aSMA, CD31, CD66b, CD56, CD11c, GranzymeB, TIM3, Ki67*, MHC-II* |
| **Usable only in combination** | CD3, CD4, CD8 |
| **Doubtful** | CD15 (excluded), PDL1 (state flag, re-assess after cleaning) |
| **Not usable** | ERG |
| **Almost no signal** | CD20, RORgT |
| **Not usable (visual review)** | GATA3, LAG3 |
| **Excluded for now (numeric evaluation, 11.5): re-assess after hot-pixel filter + artifact mask** | FoxP3, Tbet, CTLA4, PD1, CD80, CD86, CD10, CD21, CD138, CD47, CD72a |
| **Clean but not needed** | CD45RO (memory states need CD44, absent from the CHS panel) |

\* usable for phenotyping, **not** for segmentation.

2. **Phenotype rules** (pathologist decision, V.G.):
   - **T cells = CD3+ AND (CD4+ OR CD8+) AND CD68−**;
   - **endothelium = CD31+ AND CD68−/CD163−** (ERG judged not usable; CD31 is also expressed by macrophages, hence the exclusion);
   - **macrophages = CD68+ and/or CD163+**, regardless of CD4/CD31;
   - **neutrophils = CD66b+** (CD15 doubtful);
   - cross-lineage double positives are flagged as suspect and resolved using neighbor context and image review (5.2), not discarded automatically.
3. Automate the co-expression table above as a recurring QC output (observed vs expected double positives for every pair of lineage markers).

### 11.3 Between-patient intensity differences 🟠
The median S100 in S100+ tumor cells varies from 5 to 80 counts between patients (15×): patients 4, 6, 9, 14 ≈ 50–80; most others ≈ 10. This does not follow the DNA status. It may be biological, pre-analytical or staining-related. In any case a **single pooled threshold** (current mclust on all cells, step 12) will call positives mainly in the high-intensity patients.

**Fix.**
- Thresholds per core (or per patient), as recommended by Lukas Hatscher for TMAs.
- Batch assessment as in the Bodenmiller workflow: per-patient/per-region ridge plots of key markers; UMAP of a subsample colored by patient, region and DNA status.

### 11.4 External validation against IHC (pending) 🟡
The QuPath per-core exports of the previous IHC study (number of cells, positive cells, % positive for CD3, CD4, CD8, CD20, CD68, CD163, CD66b) on the same TMA cores will allow a direct per-core comparison of % positive cells (IHC vs IMC, unit-free). The density values reported in the thesis (cells/mm²) are not used as reference: several exceed the physical maximum (~12 500 cells/mm²), so the area/denominator definition must be clarified first. The mapping between the IHC dearray (rows A–O = patients, columns 1–11 = regions) and the Hyperion grid is being checked.

### 11.5 Numeric evaluation of state and subtype markers 🔴
On visual review the state/subtype markers were hard to judge, so they were also assessed numerically on DNA-valid cores (cells > 2 counts). Three measures per marker:
- the fraction of positives that are **multi-positive** (≥ 4 lineage markers > 2, typical of aggregates or "sticky" objects);
- **where** the positives lie: macrophages (CD68 or CD163 > 2), tumor (S100/SOX9 > 2, not macrophage), neutrophils (CD66b > 2);
- **subcellular localization**, measured within each positive cell:
  - periphery/center ratio (> 1 = membrane-like, < 1 = central blob);
  - nucleus/cytoplasm ratio (DNA-high vs DNA-low pixels; > 1 = nuclear).

| Marker | Positives | Multi-positive | On macrophages | Periphery / center | Nucleus / cytoplasm | Reading |
|---|---|---|---|---|---|---|
| *Reference:* CD68 | 3683 | 14% | 100% | 1.91 | 0.59 | clean cytoplasmic/membrane |
| *Reference:* aSMA | 12 981 | 4% | 11% | 1.83 | 0.75 | clean cytoplasmic |
| *Reference:* Ki67 | 130 | 48% | 78% | 0.45 | **1.99** | nuclear |
| FoxP3 | 135 | **94%** | 92% | 0.28 | 1.13 | mostly aggregates; few true nuclear signals |
| Tbet | 279 | 85% | 85% | 0.30 | 0.65 | not nuclear → non-specific |
| GATA3 | 289 | 79% | 79% | 0.39 | 0.76 | not nuclear → non-specific |
| CTLA4 | 84 | 89% | 90% | 0.27 | 0.89 | aggregate-like |
| PD1 | 185 | 88% | 77% | 0.28 | 0.95 | aggregate-like |
| LAG3 | 253 | 88% | 88% | 0.30 | 0.71 | aggregate-like |
| CD80 | 203 | 80% | 88% | 0.45 | 0.97 | aggregate-like |
| CD86 | 50 | 94% | 86% | 0.18 | 0.06 | aggregate-like |
| CD10 | 150 | 81% | 95% | 0.43 | 0.68 | aggregate-like |
| CD21 | 198 | 86% | 89% | 0.39 | 1.03 | aggregate-like |
| CD138 | 423 | 64% | 69% | 0.39 | 0.91 | mostly aggregate-like |
| CD47 | 354 | 75% | 75% | 0.33 | 0.75 | not on tumor (24%) → not usable as tumor CD47 |
| PDL1 | 558 | 49% | 53% | 0.39 | 0.98 | mixed; re-assess after artifact removal |
| CD45RO | 955 | **25%** | 35% | 0.78 | 1.10 | the cleanest of this group |
| CD72a | 218 | 82% | 87% | 0.42 | 0.57 | aggregate-like |
| CD15 | 34 | 94% | 94% | 0.28 | – | not usable |

For comparison, the lineage/state markers judged usable look clean: GranzymeB 18% multi-positive, TIM3 16%, CD56 25% (43% of positives on tumor cells, supporting tumor expression), CD11c 22% (93% on macrophages). MHC-II is 63% multi-positive.

**T cells depend strongly on the threshold.** With the pathologist rule (CD3+ AND (CD4+ OR CD8+) AND CD68−):
- 4 cells at > 2 counts;
- 22 at > 1.5;
- **215 at > 1** (151 of them not multi-positive).

CD3 has a very low dynamic range (p99 ≈ 1.1 counts), so a fixed threshold of 2 is too strict. Per-core GMM thresholds are needed (12.3).

**Conclusion for CHS (current data).** The state/subtype markers (FoxP3, Tbet, GATA3, CTLA4, PD1, LAG3, CD80, CD86, CD10, CD21, CD138, CD47, CD72a, CD15) are positive almost exclusively on "everything-positive" objects with compact central signal, i.e. aggregates or sticky cells. They cannot support gates now. **Re-assess them after** the hot-pixel filter, artifact exclusion and per-core thresholds. Until then, the definitive CHS table uses lineage markers and only Ki67, GranzymeB and TIM3 as state flags (PDL1 pending).

---

## Step 12 – Phenotyping (`notebooks/05_broad_compartment_assignment.ipynb`)

Current approach, modeled on Meyer et al. 2026:
1. **astir** gives probabilistic support for 7 broad compartments.
2. **mclust** sets positive/negative thresholds per marker.
3. **CATALYST SOM** clustering (24 metaclusters) on the astir markers.
4. Clusters are labeled tumor / mixed / non-tumor from the astir non-tumor fraction.
5. Each cell gets a final label from cluster category + astir + a weighted marker score.

An earlier **rule-based** notebook (`04_rule_based_phenotyping`, June, chordoma test data, 15 203 cells) used an Excel rule table with mclust/80th-percentile thresholds and left 62% of cells `Unassigned`. It was then replaced by the astir/SOM approach.

### 12.1 Run on old data; implausible result 🔴
Notebook 05 was run on the July **Mesmer** run (321 476 cells), not on the current Cellpose data. Its result is not plausible for CHS: **T cells 69%, myeloid 11%, unassigned 11%, tumor 3.6%**, with one SOM cluster holding 83% of all cells. In the current data, cells with T-cell markers are ≤ 1%, and the previous IHC study found CHS the "coldest" histotype. The result reflects upstream problems (over-segmentation, censoring, unreviewed markers) rather than biology.
**Fix.** Re-run only after the upstream fixes (1.1, 2.x, 4.x, 10.x), and do not interpret any phenotype before image validation (12.6).

### 12.2 astir marker schema 🔴
The schema mixes lineage markers with markers that are unusable, unreviewed or not lineage-defining:
- *Tumor:* Brachyury/Brachiury (not in the CHS panel; spelling variants), SOX9, S100, **Ki67, PDL1, CD47** (proliferation/checkpoint/ubiquitous, not tumor lineage);
- *Endothelium:* CD31, **ERG** (not usable);
- *Myeloid:* CD68, CD163, CD11c, CD66b, **CD15** (doubtful), MHC-II, **CD80, CD86** (unreviewed);
- *T cells:* CD3, CD4, CD8, **CD45RO, FoxP3, Tbet, GATA3, RORgT** (unreviewed or no signal);
- *B/plasma:* **CD20, CD21, CD138** (no signal / doubtful), plus CD72a in the output;
- *NK:* CD56 only.

astir also needs every compartment to be separable by its markers, while here several T/B markers carry little or no specific signal. On top of that, Lukas Hatscher's benchmark (spCellEval) found astir to perform poorly for imaging data.
**Fix.** If astir is kept, rebuild the schema **only** from the pathologist-reviewed lineage markers (11.2):
- tumor: S100, SOX9;
- macrophages: CD68, CD163;
- neutrophils: CD66b;
- T cells: CD3 + CD4/CD8;
- endothelium: CD31;
- stroma: aSMA;
- NK-like: CD56.

Use it only as one line of evidence, not as the primary assignment.

### 12.3 Thresholds (mclust) 🟠
`mclust_marker_thresholds.R` fits two Gaussians on **all cells of all cores pooled**. Two problems:
- with the 15× between-patient differences in intensity (11.3), pooled thresholds call positives mainly in the bright patients;
- when the fit fails, the threshold silently becomes the **80th percentile**, i.e. 20% positive cells by construction, which is wrong for rare markers.

**Fix.**
- Thresholds per core (or per patient), e.g. mclust per core with a minimum number of cells and a sanity check against the pooled fit.
- Better still, Lukas Hatscher's approach: manual per-core thresholds on 20–30 representative cores, set on the image by the pathologist, then a tree-based classifier (random forest / XGBoost) for the rest.
- Never use a percentile fallback: flag the marker/core instead.

### 12.4 Clustering (CATALYST SOM) 🟠
- Input: z-scored (pooled) values of all schema markers, including noisy ones.
- The number of clusters is fixed at 24, copied from Meyer's tumor panel instead of being chosen on these data (Meyer selected k with silhouette/RMSD).
- Result: one cluster with 83% of cells.

**Fix.**
- Cluster only on the usable lineage markers (arcsinh, censored only for this matrix, 10.2).
- Choose k on data (silhouette, stability), and use clustering as an **exploratory and validation** tool alongside the rules, as Lukas Hatscher recommended ("explore clustering, but expect a blob; merge sub-clusters and check on the image").

### 12.5 Cluster categories and final assignment 🟠
- Thresholds 0.15/0.50 on the astir non-tumor fraction: Meyer's text reads "based on the fraction of non-tumor cells predicted by astir (tumor ≥50%; mixed, 15–50%; non-tumor, <15%)". Taken literally this is contradictory (a cluster with ≥ 50% non-tumor cells labeled "tumor"). Our implementation uses one possible reading (tumor if < 15% non-tumor); the other is that the fraction refers to tumor cells. Table S2 or the authors' code would settle it.
- Mixed clusters are resolved first by astir thresholds, whereas Meyer uses GMM.
- The final weighted marker score (Brachyury ×3, SOX9 ×2, …; ties → `Unassigned`) is an ad-hoc construct, not from the reference study.

**Fix.** Replace the cascade with an explicit **hierarchical gating** built on the pathologist's rules:
1. **Level 0, QC:** excluded cores, `in_artifact`, `LO_non_cell`, anucleate rule (not applied to S100+ cells in DNA-negative cores), `suspect_double` flag.
2. **Level 1, tumor vs non-tumor:** S100/SOX9 with per-core thresholds.
3. **Level 2, non-tumor lineages:**
   - macrophages: CD68+ and/or CD163+;
   - neutrophils: CD66b+;
   - T cells: CD3+ AND (CD4+ OR CD8+) AND CD68−;
   - endothelium: CD31+ AND CD68−/CD163−;
   - pericytes: aSMA+ CD31− within 15 µm of an endothelial cell; CAF/smooth muscle: aSMA+ CD31− farther away;
   - NK: CD56+ AND GranzymeB+ (CD3−, CD68−, SOX9−, S100−);
   - dendritic-like: CD11c+/MHC-II+ CD68−.
4. **Level 3, states as flags, not identities:** Ki67+, GranzymeB+, TIM3+, CD56+ tumor (PDL1 only after review).

Then train a classifier on pathologist-validated cells to scale to all cores. Report `Unassigned` explicitly.

### 12.6 No image validation 🟠
No phenotype has been overlaid on the images. Lukas Hatscher considers this the most important step: heatmaps and embeddings can look fine with 30% of cells misassigned.
**Fix.**
- Systematic overlay review with the pathologist, using the scimap `image_viewer` notebook already prepared, on a predefined set of cores (one per region type, valid and DNA-negative).
- A per-core comparison of % positive cells with the previous IHC study (11.4).

### 12.7 Pathologist gating rules (chordoma v2) and their CHS adaptation
Vincenzo's rule set (`Chordoma_IMC_Gating_Rules_v2.xlsx`, `Chordoma_IMC_Phenotyping_Strategy.xlsx`, `Chordoma_IMC_Phenotyping_Guide.docx`; probably the "Excel rule table" used in the June rule-based notebook) is a **hierarchical gating** design:
- L1 tissue compartments → L2 myeloid/lymphoid → L3 lineages → L4 subtypes;
- one identity per cell plus stacked **state flags**;
- negative gates;
- explicit precedence rules (e.g. NKT vs NK);
- a CD45 proxy;
- spatial qualifiers (pericyte ≤ 15 µm from endothelium, Tfh ≤ 30 µm from FDC);
- `Unassigned` tracked as a QC metric.

**It is the right backbone for 12.5** and maps directly onto a SCIMAP phenotype workflow (pos/neg/anypos/allpos), the approach used by Lukas Hatscher.

The rules were written for chordoma. Applied to the CHS panel and to the reviewed marker list (11.2), gate by gate (first draft; superseded by the final tables in 12.8):

| Status in CHS | Gates |
|---|---|
| ✅ applicable as is (4) | L3.5 immature DC, L3.7 CD4 T, L3.8 CD8 T (with CD68−), F1 Ki67 flag |
| ✏️ to adapt (16) | L1.1 tumor (Brachyury → SOX9/S100), L1.2 endothelium (no ERG; CD31+ CD68− CD163−), L1.3a/b pericytes/CAF, L1.4 immune proxy (drop CD20/CD138/CD21, add CD163), L2.1/L2.2, L3.1/L3.2 macrophages (no CD172a; CD163-based), L3.4 mature DC (S100 conflicts with the tumor marker → require CD11c+ SOX9−), L3.6 neutrophils (CD66b only; CD10 unreviewed), L3.11 NK (exclude SOX9/S100: CD56 may be tumor), L4.5–4.9 CD8 axes (GranzymeB; TIM3 only), L4.14–4.17 NK states, F6, F7 |
| ⛔ not applicable now (12) | L3.3, L3.9 DN T/NKT (CD3 alone unreliable), L3.10 B, L3.12 plasma, L3.13 FDC, L4.1–4.4b CD4 subsets, L4.M memory (CD44 absent), L4.10–4.13 B subsets (BCL2 absent), L4.18–4.19, F3, F4, F5 TLS |
| ❓ to decide (1) | F2 PDL1+ tumor (PDL1 doubtful; re-assess after artifact removal) |

**Main adaptations:**
- **Tumor anchor:** in CHS, S100 is both the tumor marker and the mature-DC confirmatory marker, so the two gates need SOX9/CD11c to be told apart.
- **Region awareness:** SOX9+/S100+ cells in border/non-neoplastic cores (rows I–K) are non-neoplastic chondroid/Schwann/adipose cells, not tumor.
- **Double positives:** negative gates send spillover doubles to `Unassigned`; resolve them by neighbor context first (5.2).
- **T-cell subtyping:** in CHS, stop at L3 unless the transcription-factor and checkpoint markers pass review *and* cell numbers allow it.
- **Thresholds:** per core (12.3).
- **Chordoma:** for the CH TMA most v2 gates remain valid (Brachyury, BCL2, CD44, ERG are in the CH panel), but the marker review must be repeated on CH data.

### 12.8 Definitive CHS phenotyping tables (pathologist-approved, 06/10)
Two versions in `phenotyping/`:

1. **`20261006 CHS_Phenotyping_minimal.xlsx`: to implement now.**
   - **Lineage gates:**
     - tumor: (SOX9+ OR S100+) AND CD68− CD163− CD11c− CD31−, not T, not NK; **CD56 is not a negative gate**;
     - endothelium: CD31+ AND CD68− AND CD163− AND aSMA−;
     - **pericytes** (aSMA+ CD31− CD68− SOX9−, ≤ 15 µm from an endothelial cell) **kept separate from CAF/smooth muscle** (same markers, > 15 µm from endothelium). Pericytes are CD31−: PECAM-1 is endothelial. aSMA+ CD31+ cells get an `aSMA+CD31+ mixed` flag (endothelium–pericyte boundary or lateral spillover);
     - macrophages CD163+ / CD163−;
     - **S100+ mature DC** (CD11c+ MHC-II+ S100+ CD68− SOX9−) kept as a separate population;
     - immature DC;
     - neutrophils (CD66b+);
     - CD4 T and CD8 T (CD3+ with CD4/CD8, CD68−);
     - **NK = CD56+ AND GranzymeB+** (CD3−, CD68−, SOX9−, S100−).
   - **State flags:** Ki67, GranzymeB, TIM3, **CD56+ tumor** (CD56+ GranzymeB− S100+ SOX9+, tumor expression of CD56), PDL1 (only after hot-pixel filter + artifact mask). Plus the M2-like fraction and total immune density per mm² of tissue.
   - Thresholds per core.
   - A second sheet lists **every excluded marker with the reason and whether to re-assess it**.
2. **`20261006 CHS_Phenotyping_complete.xlsx`: the full CHS-adapted hierarchy (v2 logic)**, to use if all antibodies worked (e.g. after cleaning or on a re-stained section). Every gate is flagged with the markers that **did not work in our setting** and whether it is usable on current data:
   - 7 gates usable as they are (including the CD56+ tumor flag);
   - 15 only in their minimal adaptation;
   - 12 not usable.

   Both files also contain the **excluded markers** sheet, the shared definitions (T, NK, tumor) and the gating principles.

---

## Appendix A – ROIs that are not 1000 × 1000 px

| ROI | Size (H × W px) | Image area (mm²) | Cells (current run) |
|---|---|---|---|
| ROI103_I10 | 803 × 522 | 0.42 | 199 |
| ROI104_I8 | 444 × 522 | 0.23 | 80 |
| ROI105_G6 | 900 × 743 | 0.67 | 72 |
| ROI106_J1 | 1116 × 841 | 0.94 | 121 |
| ROI107_A5 | 442 × 1033 | 0.46 | 122 |
| ROI108_A13 | 579 × 1261 | 0.73 | 872 |
| ROI109_J5 | 933 × 1261 | 1.18 | 120 |
| ROI110_A15 | 756 × 1161 | 0.88 | 1033 |
| ROI111_E5 | 597 × 685 | 0.41 | 148 |
| ROI112_J10 | 971 × 842 | 0.82 | 334 |
| ROI113_I15 | 1049 × 584 | 0.61 | 179 |
| ROI114_G11 | 671 × 584 | 0.39 | 171 |
| ROI115_F9 | 671 × 584 | 0.39 | 35 |
| ROI116_J13 | 946 × 1061 | 1.00 | 362 |
| ROI117_A1 | 530 × 1061 | 0.56 | 300 |
| ROI118_A2 | 530 × 1061 | 0.56 | 261 |
| ROI119_A12 | 530 × 1216 | 0.64 | 140 |
| ROI120_H8 | 819 × 1007 | 0.82 | 129 |
| ROI121_A8 | 530 × 1216 | 0.64 | 162 |
| ROI122_A7 | 530 × 1216 | 0.64 | 107 |
| ROI123_A6 | 530 × 1216 | 0.64 | 51 |
| ROI124_A10 | 530 × 1216 | 0.64 | 299 |
| ROI125_A11 | 530 × 1216 | 0.64 | 67 |
| ROI128_A14 | 530 × 1216 | 0.64 | 448 |
| ROI129_A4 | 530 × 1216 | 0.64 | 528 |
| ROI130_A3 | 530 × 1216 | 0.64 | 27 |
| ROI131_A9 | 401 × 1216 | 0.49 | 13 |

## Appendix B – DNA status per core

DNA-negative cell = arcsinh(DNA1) + arcsinh(DNA2) < 1. Status: **DNA-negative** > 50% DNA-negative cells, **intermediate** 20–50%, **valid** < 20%. Totals: 46 valid, 19 intermediate, 71 DNA-negative. Full table: `data/20261005 TMA_core_map.csv`.

### DNA-negative (71)

| ROI | TMA position | Cells | DNA-negative cells | DNA pixel p99 |
|---|---|---|---|---|
| ROI003_C4 | C4 | 450 | 99% | 2 |
| ROI009_G3 | G3 | 263 | 99% | 2 |
| ROI015_D2 | D2 | 225 | 95% | 2 |
| ROI019_I5 | I5 | 238 | 84% | 2 |
| ROI034_G13 | G13 | 720 | 74% | 3 |
| ROI038_E15 | E15 | 566 | 91% | 2 |
| ROI040_D7 | D7 | 177 | 94% | 2 |
| ROI041_D5 | D5 | 349 | 98% | 2 |
| ROI042_H6 | H6 | 193 | 99% | 2 |
| ROI043_G5 | G5 | 280 | 95% | 2 |
| ROI046_J3 | J3 | 40 | 98% | 2 |
| ROI047_K3 | K3 | 42 | 100% | 2 |
| ROI050_G8 | G8 | 293 | 67% | 2 |
| ROI051_I11 | I11 | 236 | 84% | 2 |
| ROI052_D8 | D8 | 238 | 89% | 2 |
| ROI055_B4 | B4 | 625 | 80% | 2 |
| ROI058_B15 | B15 | 314 | 63% | 2 |
| ROI059_J6 | J6 | 63 | 98% | 2 |
| ROI062_E7 | E7 | 220 | 92% | 2 |
| ROI063_B6 | B6 | 120 | 97% | 2 |
| ROI065_D1 | D1 | 1031 | 82% | 2 |
| ROI066_E13 | E13 | 1202 | 57% | 3 |
| ROI068_H15 | H15 | 211 | 96% | 2 |
| ROI069_H13 | H13 | 722 | 65% | 3 |
| ROI071_J11 | J11 | 275 | 98% | 2 |
| ROI075_C15 | C15 | 404 | 64% | 3 |
| ROI076_D15 | D15 | 442 | 76% | 3 |
| ROI077_F7 | F7 | 454 | 78% | 3 |
| ROI078_D12 | D12 | 243 | 75% | 3 |
| ROI079_C7 | C7 | 169 | 83% | 3 |
| ROI080_B3 | B3 | 128 | 100% | 2 |
| ROI082_B11 | B11 | 244 | 84% | 2 |
| ROI083_C11 | C11 | 158 | 84% | 2 |
| ROI084_E11 | E11 | 131 | 95% | 2 |
| ROI085_F11 | F11 | 141 | 96% | 2 |
| ROI088_I6 | I6 | 9 | 89% | 2 |
| ROI089_I3 | I3 | 33 | 82% | 2 |
| ROI090_G2 | G2 | 434 | 70% | 3 |
| ROI091_H5 | H5 | 291 | 90% | 2 |
| ROI092_D9 | D9 | 114 | 96% | 3 |
| ROI093_B5 | B5 | 69 | 91% | 2 |
| ROI094_B7 | B7 | 159 | 71% | 3 |
| ROI095_F8 | F8 | 549 | 56% | 5 |
| ROI096_F5 | F5 | 241 | 63% | 3 |
| ROI097_B9 | B9 | 104 | 80% | 2 |
| ROI098_D6 | D6 | 95 | 73% | 3 |
| ROI099_F3 | F3 | 165 | 99% | 2 |
| ROI100_B2 | B2 | 238 | 100% | 2 |
| ROI101_C3 | C3 | 215 | 97% | 3 |
| ROI102_F15 | F15 | 754 | 90% | 3 |
| ROI105_G6 | G6 | 72 | 97% | 2 |
| ROI107_A5 | A5 | 122 | 97% | 3 |
| ROI109_J5 | J5 | 120 | 68% | 2 |
| ROI111_E5 | E5 | 148 | 76% | 3 |
| ROI115_F9 | F9 | 35 | 97% | 2 |
| ROI118_A2 | A2 | 261 | 71% | 3 |
| ROI119_A12 | A12 | 140 | 77% | 3 |
| ROI120_H8 | H8 | 129 | 77% | 2 |
| ROI121_A8 | A8 | 162 | 54% | 3 |
| ROI122_A7 | A7 | 107 | 87% | 3 |
| ROI123_A6 | A6 | 51 | 96% | 2 |
| ROI125_A11 | A11 | 67 | 94% | 3 |
| ROI126_F6 | F6 | 103 | 94% | 2 |
| ROI127_E9 | E9 | 128 | 91% | 2 |
| ROI130_A3 | A3 | 27 | 100% | 2 |
| ROI131_A9 | A9 | 13 | 85% | 2 |
| ROI132_G15 | G15 | 373 | 72% | 2 |
| ROI133_E6 | E6 | 102 | 91% | 2 |
| ROI135_C2 | C2 | 260 | 84% | 2 |
| ROI136_C6 | C6 | 124 | 80% | 2 |
| ROI137_C8 | C8 | 294 | 65% | 3 |

### Intermediate (19)

| ROI | TMA position | Cells | DNA-negative cells | DNA pixel p99 |
|---|---|---|---|---|
| ROI001_E10 | E10 | 1108 | 24% | 8 |
| ROI002_F12 | F12 | 172 | 23% | 4 |
| ROI006_B12 | B12 | 448 | 36% | 4 |
| ROI007_K15 | K15 | 1389 | 22% | 11 |
| ROI012_H12 | H12 | 632 | 24% | 5 |
| ROI020_G1 | G1 | 1418 | 31% | 6 |
| ROI026_C12 | C12 | 623 | 39% | 5 |
| ROI035_C1 | C1 | 1789 | 45% | 6 |
| ROI053_B8 | B8 | 550 | 27% | 10 |
| ROI060_C10 | C10 | 434 | 34% | 5 |
| ROI064_C9 | C9 | 395 | 22% | 3 |
| ROI067_G14 | G14 | 1012 | 43% | 4 |
| ROI074_D14 | D14 | 813 | 28% | 4 |
| ROI081_G10 | G10 | 651 | 26% | 10 |
| ROI087_H10 | H10 | 626 | 49% | 4 |
| ROI117_A1 | A1 | 300 | 35% | 3 |
| ROI124_A10 | A10 | 299 | 46% | 3 |
| ROI128_A14 | A14 | 448 | 24% | 5 |
| ROI134_D4 | D4 | 795 | 47% | 3 |
