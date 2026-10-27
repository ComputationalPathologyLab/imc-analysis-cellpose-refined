# CHS IMC – manual review release 20261012_v1

Frozen release of the pathologist's inputs for the CHS TMA (136 IMC ROIs): the evaluable area of every core, the
excluded areas (automatic and drawn), and the core-level decisions. **Never edited after release**: any change is a
new release (`_v2`, …). Integrity: `MANIFEST.sha256` (`shasum -a 256 -c MANIFEST.sha256`); the files are read-only.

- Source: QuPath project `CHS_IMC`, annotations exported with script `03` (12/10/2026 23:26).
- Automatic classes: `auto_artifacts.py` run **v5** (12/10/2026), computed on the hot-pixel-filtered stack
  (steinbock `filter_hot_pixels`, threshold 50). Parameters and per-channel thresholds: `auto_artifacts_v5/params.json`.
- Rules: `rules/20261010 Annotation_class_rules.md` is the authoritative definition of every class and of the cell
  rules; `rules/20261010 Single_pass_review_protocol.md` records how the review was done.

## Contents
| Path | What |
|---|---|
| `geojson/<ROI>.geojson` | one file per ROI, as exported by QuPath: `Evaluable_area` + every kept polygon |
| `auto_artifacts_v5/components.csv` | every candidate region of v5, written or not (`exported`), with its measurements |
| `auto_artifacts_v5/params.json` | v5 parameters and per-channel thresholds |
| `core_review/20261006 CHS_core_review.xlsx` | one row per TMA position: inclusion (`evaluable_for_IMC`), H&E findings, flags; sheet "Legend" |
| `rules/` | rules document and review protocol |
| `summary/polygons_per_core_and_class.csv` | per ROI and class: written by v5, kept, deleted (drawn classes: kept only) |
| `summary/polygons_total_per_class.csv` | the same, summed |
| `summary/areas_per_core.csv` | per ROI: `Evaluable_area`, excluded area inside it, density denominator (pixels, pixel-center rasterization) |

## Classes
- **`Evaluable_area`** (one polygon per ROI, drawn by the pathologist): where cells are counted; the density
  denominator before subtraction.
- **Excluded areas** (every polygon present in the release is accepted; there is no reclassification):
  - automatic: `Artifacts_auto`, `Artifacts_auto_large`, `Artifacts_auto_low`, `Artifacts_auto_faint`, `Spot_auto`,
    `Spot_auto_large`;
  - drawn: `Artifacts` (folds; in this release one band in G10), `Necrosis` (B10), `Hemorrhage` (none drawn).

| Class | Source | Written (v5) | Kept | Deleted | Kept in the 121 included cores |
|---|---|---|---|---|---|
| `Artifacts_auto` | automatic (v5) | 6178 | 6178 | 0 | 5715 |
| `Artifacts_auto_large` | automatic (v5) | 484 | 482 | 2 | 464 |
| `Artifacts_auto_low` | automatic (v5) | 4516 | 4501 | 15 | 3971 |
| `Artifacts_auto_faint` | automatic (v5) | 3185 | 3184 | 1 | 2783 |
| `Spot_auto` | automatic (v5) | 3561 | 3561 | 0 | 3024 |
| `Spot_auto_large` | automatic (v5) | 205 | 205 | 0 | 171 |
| `Artifacts` | drawn by V.G. | – | 1 | – | 1 |
| `Necrosis` | drawn by V.G. | – | 1 | – | 1 |
| `Hemorrhage` | drawn by V.G. | – | 0 | – | 0 |

All deletions are in G10: automatic polygons lying inside the drawn `Artifacts` band, so redundant with it.

## How to use it
1. **Rasterize** every polygon on the ROI pixel grid (1 px = 1 µm; x = column, y = row, identity transform) with the
   **pixel-center convention**: a pixel is inside if its center is inside (rasterio `all_touched=False`). The
   automatic polygons follow pixel edges, so this gives back exactly their pixels.
2. **Excluded mask** = union of all excluded classes (no priority between classes needed).
3. **Cells and `Evaluable_area`:** a cell belongs to the core if its **centroid** is inside the `Evaluable_area`
   polygon (point-in-polygon on the GeoJSON; centroid in the same coordinates, pixel center = column + 0.5,
   row + 0.5). Cells with the centroid outside are left out of every analysis.
4. **Cells and excluded areas** (cells that belong to the core): fraction of the cell's pixels inside the excluded
   mask:
   - 0 → counted and phenotyped;
   - > 0 and ≤ 75% → counted in densities, phenotype not assessable (excluded from intensities and phenotyping);
   - > 75% → aggregate segmented as a cell: removed from everything.
5. **Density denominator** = `Evaluable_area` minus the excluded mask (`summary/areas_per_core.csv`, column
   `denominator_px`, as a reference).
6. **Store per cell** `frac_in_evaluable` and `frac_in_excluded`, so that sensitivity analyses with other rules need
   no recomputation.
7. **Cores:** downstream analyses use the cores with `evaluable_for_IMC` = `yes` (121). The other 15 are excluded
   (`exclusion_reason`) but their polygons are reviewed too. Flags for sensitivity analyses: `he_core` (core partial
   or missing on H&E) and `special_area_flag` (`hemorrhage_not_drawn`, `necrosis_not_drawn`, `fold_HE_only`); meaning
   and handling in the rules document, section "H&E findings not drawn on IMC".

In the 121 included cores: `Evaluable_area` 95.69 mm², of which 0.73% excluded (median per core 0.51%, max 7.10% in B10); denominator 95.00 mm².

## Notes
- Some automatic polygons are exported by QuPath as a MultiPolygon: two parts that touch at one vertex (diagonal
  pixels). Their pixels are identical to the v5 polygon.
- QuPath properties (`id`, `isLocked`, `color`, `measurements`) can be ignored. The polygon `name` gives the rule and
  the channels involved, e.g. `single (GranzymeB)` or `faint (CD138+LAG3+…)`.
- The cell-rule numbers in the rules document were estimated on the current Cellpose masks. Recompute them on the
  final segmentation, and re-check the 75% threshold there.
