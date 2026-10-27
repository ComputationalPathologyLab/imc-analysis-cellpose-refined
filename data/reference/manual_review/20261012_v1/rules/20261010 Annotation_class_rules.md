# Annotation class rules – CHS IMC (`CHS_IMC` QuPath project)

Reference for V.G., Claude and Rashid: one section per class, with its exact definition, who handles it, and what the
pipelines do with it. **Cores included in the downstream analyses: 121 since 11/10/2026** ("Core inclusion" below).
**The polygons are reviewed on all 136 cores.** The evidence below was computed on the first set of 108 cores; it is
not recomputed, because it supports the rules, not final numbers. Built class by class with V.G. Status labels: **decided** (V.G., date) · **proposed** (to
confirm) · **to define**.

## Core inclusion in the downstream analyses – decided (V.G. 11/10/2026)
**Reference (ground truth):** the region expected from the TMA grid:
- A–C high-grade;
- D low-grade;
- E–F high inflammatory infiltrate;
- G–H tumor periphery (should contain CHS);
- I–J non-neoplastic border (should not contain CHS);
- K non-neoplastic.

The cores were sampled by hand, so a core can miss its region. The H&E serial section is checked against the
expectation (core review sheet, `region_check`):

| H&E finding | Handling | Cores (CHS) |
|---|---|---|
| 1. As expected | **included** | 112 |
| 2. Not as expected | **excluded** from the downstream analyses: it would contaminate them (`out of scope (region mismatch on H&E)`) | G9, H9, H11 (G–H without CHS); I5, J2, J5, J11 (I–J with CHS) |
| 3. Core partial or missing on H&E | **flag** (`he_core`). Claude compares with the IMC (fraction of S100+ cells, ROI coverage, H&E–IMC registration); V.G. confirms the handling | in: E4, G5, G15, H8, I2, I8 (partial, not missing: audit 11/10), I10, I15, J10; out: G11 (no CHS in the visible part + 3% S100+) |

- **What "as expected" checks: only the presence or absence of CHS** (V.G. 11/10). Grade (A–C vs D) and the
  inflammatory infiltrate (E–F) are taken from the grid label and are not verified on H&E. This is a stated limitation.
- **The H&E always wins over the IMC** for cores present and evaluable on H&E (V.G. 11/10). The IMC image quality
  does not exclude a core. Example: J3 is as expected on H&E but almost empty on IMC (40 objects, 26 > 400 px, no
  DNA). It is included, and its `Core_not_evaluable` mark from the large-object review of 05/10 is superseded. The IMC
  is used only for scenario 3.
- **Exception:** row K is excluded by design, although its cores are as expected.
- **Flagged cores (scenario 3)** stay in, and a sensitivity analysis without them is possible. A flagged core is
  excluded only when the visible H&E and the IMC both contradict the expected region.
- **The polygon review covers every core, excluded ones included** (V.G. 11/10). An excluded core may still be used
  later for other purposes, e.g. a G–J core with CHS as tumor, or row K as a non-neoplastic reference. The column
  `evaluable_for_IMC` therefore means "included in the downstream analyses".
- **Before reusing this on another histotype**, the same three scenarios apply, with the expected content of that TMA.

## Order of operations (pipelines)
1. Extract the stacks from the `.mcd`, then apply the **hot-pixel filter**: the steinbock `filter_hot_pixels`
   function, threshold 50, applied to all channels. 50 is the value recommended in the steinbock docs; `--hpf` has
   no default.
2. Compute the automatic classes on the **filtered** stack (`Scripts/auto_artifacts.py`, parameters in the release
   `params.json`). The pixel grid is identical to Rashid's TIFFs, so the QuPath polygons stay valid.
3. Keep the cells whose centroid is inside `Evaluable_area` (centroid rule, V.G. 12/10), then exclude the areas of
   the released polygons (`releases/YYYYMMDD_vN/`) from the analyses. **No pixel masks**
   (V.G. 10/10): every class that is kept ends up as a drawn area given to Rashid. The rule for cells touching an
   excluded area is in "Cells touching an excluded area" below (rule B, refined with a 75% threshold).

## Summary
| Class | Made by | Reviewed by V.G.? | What the pipelines do | Status |
|---|---|---|---|---|
| `Evaluable_area_auto` | `auto_tissue.py` (v2: one disc per core, or whole image) | yes, corrected → `Evaluable_area` | nothing (draft only); **class removed from QuPath 11/10** after the review | done 11/10 |
| `Evaluable_area` | V.G. | – | cells inside counted (**centroid rule**, 12/10); density denominator | decided 07/10; border rule 12/10 |
| `Artifacts_auto` (≤ 200 px) | `auto_artifacts.py` | ~~by exception~~ **no: accepted by rule (12/10)** | excluded area unless deleted | decided 10/10; review revised 12/10 |
| `Artifacts_auto_large` (> 200 px) | `auto_artifacts.py` | ~~one by one~~ **sample of 15 ROIs, 0 errors → accepted by rule (12/10)** | excluded area unless deleted | decided 10/10; review revised 12/10 |
| `Artifacts_auto_low` (Ba/Pb 10–20) | `auto_artifacts.py` | ~~by exception~~ **no: accepted by rule (12/10)** | excluded area unless deleted | decided 10/10; **12/10: every `_low` written (from v5), accepted by rule** |
| `Artifacts_auto_faint` (Ba/Pb 5–10 with multi-channel antibody signal) | `auto_artifacts.py` (from v5) | **no** (hidden in the viewer, as `Spot_auto`) | **excluded area** (accepted by rule) | decided 12/10 |
| `Spot_auto` | `auto_artifacts.py` | **no** (hidden in the viewer) | **excluded area** (accepted by rule, without review) | decided 10/10 |
| `Spot_auto_large` | `auto_artifacts.py` | ~~one by one~~ **sample, 0 errors → accepted by rule (12/10)** | excluded area unless deleted | decided 10/10; review revised 12/10 |
| `Artifacts` (folds only) | V.G. | – | excluded area; area subtracted from `Evaluable_area` | decided 10/10; **none drawn (12/10)** |
| `Necrosis` (only cores with necrosis on H&E) | V.G. | – | as `Artifacts` | decided 10/10; **drawn in B10 only (12/10)** |
| `Hemorrhage` (cores with red blood cells on H&E, only where needed) | V.G. | – | as `Artifacts` | decided 10–11/10; **none drawn (12/10)** |

H&E findings that could not be drawn on IMC are carried as **core-level flags** in the core review sheet (section
"H&E findings not drawn on IMC" below, V.G. 12/10).

## `Evaluable_area` / `Evaluable_area_auto` – decided (V.G. 07/10)
- `Evaluable_area` is the area where cells are counted and the denominator of densities. `Artifacts`, `Necrosis`
  and `Hemorrhage` are subtracted from it. It must include the chondroid matrix and detached tissue fragments (V.G. 10/10);
  glass and holes stay out.
- `Evaluable_area_auto` is only a starting point (`auto_tissue/README.md`). V.G. corrects it in the single pass per
  core and saves the result as `Evaluable_area`.
- **Done 11/10/2026 on all 136 cores.** Against the draft:
  - 49 kept as is;
  - 55 edited (vertices moved; including A13, redrawn as a polygon after a first attempt as an open line);
  - 32 redrawn.
  
  Then the class `Evaluable_area_auto` was removed from the QuPath class list. The drafts stay on disk in
  `auto_tissue/20261007_v2/`. Check and trace: `annotations_check/20261011_evaluable_area/README.md`. Cells left
  outside the areas: 1.1% in the included cores, almost all on the core edge.
- **Edges corrected 12/10/2026 (V.G.)** where the outline left a strip or corner of tissue out
  (`annotations_check/20261012_evaluable_outside_groups/README.md`): C3, C14, F3, F6, F10, I4, J4 and A14 redrawn;
  C1, C5, D1, D7, G10 and H10 corrected; A10 edited. Cells left outside in the included cores: 677 → **430 (0.7%)**,
  almost all single cells on the core edge (`annotations_check/20261012_evaluable_outside_groups_after/`).

### Cells on the `Evaluable_area` border: centroid rule – decided (V.G. 12/10/2026)
**A segmented cell belongs to the core's `Evaluable_area` if its centroid is inside the outline.** Otherwise it is
left out of every analysis (not counted, not phenotyped).
- This is only the first check. A cell that belongs to the area then goes through the rule for excluded areas
  ("Cells touching an excluded area" below): 0% inside excluded polygons → counted and phenotyped; > 0 and ≤ 75% →
  counted, phenotype not assessable; > 75% → removed from everything.
- **Why the centroid:** densities are cells / area, and the outline crosses some cells. Each cell has one centroid, so
  each cell falls on exactly one side of the line, and the count matches the area (the logic of the counting-chamber
  rule). Counting every cell that touches the area would act as if the area were one cell radius larger
  (overestimate); counting only cells fully inside, as if it were one radius smaller (underestimate).
- **Why not rule B here:** "any pixel inside" is the rule for excluded areas because there the risk is a contaminated
  signal. Outside the `Evaluable_area` there is only glass or the core margin, with no contamination: the border is
  a counting question only.
- **Evidence** (`annotations_check/20261012_evaluable_border/README.md`, export of 12/10 16:04, cells as discs): 875 of
  60 579 cells in the included cores (1.4%) cross the outline. Against the centroid rule, "any pixel" counts +0.27%
  (max +2.2% per core), "fully inside" −1.2% (down to −20% in A9, which has 13 cells). The effect is small overall,
  but it matters for small cores and for the two pipelines to count the same cells.
- **Implementation:** point-in-polygon test of the cell centroid against the `Evaluable_area` polygon of the release,
  in QuPath coordinates (x = column + 0.5, y = row + 0.5 for a pixel's center, the convention of "Open points for the
  pipelines"). Rashid also stores, for every cell, the fraction of its pixels inside the rasterized `Evaluable_area`
  (`frac_in_evaluable`), as he does for the excluded areas, so that a sensitivity analysis with another border rule
  needs no recomputation.

## Shared definitions of the automatic classes – decided (V.G. 10/10/2026)
Computed on the hot-pixel-filtered stack. Evidence: `auto_artifacts/rule_check/README.md`.

**Channels**
- **Antibody channels:** the 35 channels other than 127I, 131Xe, 134Xe, 138Ba, 208Pb, 80ArAr, DNA1 and DNA2.

**Units.** Every threshold is in **ion counts per pixel**. Each 1-µm² pixel is one laser-ablated spot, and its value
in a channel is the number of ions of that mass detected there, measured on Rashid's stack after the hot-pixel
filter. These are the values shown in QuPath. Most pixels are 0 or 1 in every channel.

**Two kinds of thresholds** (explained to V.G. 12/10):
- **Ba and Pb:** fixed counts (20, 10, 5), the same for both metals and in every core. At each pixel, the higher of
  the two metals is used. They are not percentiles: 20 was chosen partly because it is close to the Ba q99.9 (23),
  but the rule uses the fixed number.
- **Antibody channels:** derived from each channel's own q99.9 (below).

**Per-channel thresholds.** Fixed, the same in every core. q99.9 is the channel's 99.9th percentile pooled over all
pixels of the 136 images, glass included (about 130 million pixels; `auto_artifacts/channel_quantiles.csv`). Only
1 pixel in 1000 is above it. Values per channel are in `params.json`.
- **'Lit'** (12/10, V.G.; used only by the Ba/Pb 5–10 rule) = above 1 × q99.9. For example CD3 3, FoxP3 3, CD163 4,
  CD56 5, CD31 5, PDL1 7, CD68 8. It replaced the QuPath display maxima of the first measurements: the two are equal in
  18/33 channels, q99.9 is 1–2 counts lower in 15 and higher in 2 (MHC-II, CD68). The q99.9 comes from the data, so it
  can be recomputed on another histotype, whereas the display ranges were set by eye.
- **'High'** = above max(3 × q99.9, 10). For example CD68 24, CD163 12, PDL1 21, CD3 10, S100 654, aSMA 210.
  - The floor of 10 counts applies to channels whose q99.9 is ≤ 3, where 3× would be reached by counting noise.
  - One 'high' channel alone never flags anything: in rare markers a true positive cell can be 'high'.
- **'Single'** = above max(20 × q99.9, 50). For example PDL1 140, CD31 100, S100 4360.

**Why q99.9, and not q99 or q99.99** (V.G. 12/10)

| Channel | Median | q99 | **q99.9** | q99.99 |
|---|---|---|---|---|
| CD3 | 0 | 1 | **3** | 5 |
| FoxP3 | 0 | 1 | **3** | 7 |
| CD163 | 0 | 2 | **4** | 14 |
| CD56 | 0 | 2 | **5** | 10 |
| CD31 | 0 | 2 | **5** | 44 |
| CD68 | 0 | 2 | **8** | 29 |
| PDL1 | 0 | 2 | **7** | 470 |

- **The q99 is in the noise.** In 18 of the 33 antibody channels (S100 and aSMA excluded) it is 1 count, a single ion.
  Counts are integers: at q99 (1–2 counts) there is no room above noise; at q99.9 (3–8 counts, median 4) there is.
- **The q99 would flag almost every region.** A typical speck has about 14 pixels. Across 33 channels that is 462
  pixel–channel pairs. At the 99th percentile, about 4–5 pairs per speck would pass by chance, so almost every region,
  controls included, would have ≥ 3 lit channels. At the 99.9th percentile the chance expectation is about 0.5 per
  speck, in line with the controls measured on 12/10 (0.27 lit channels on average). This is why the Ba/Pb 5–10 rule
  separates specks (22.7% hit) from controls (1.7%).
- **The q99.99 is already the intensity of bright real cells** (CD31 44, CD68 29, PDL1 470). It would see only
  strong aggregates, which the other rules already catch, and miss the faint deposits that the 5–10 rule is meant
  to find.
- **One family of thresholds:** lit = 1×, high = 3×, single = 20× the same q99.9.
- **Limit:** the q99.9 is pooled with glass, where everything is 0, so inside tissue a single pixel passes it more
  often than 1 time in 1000. In matched on-cell controls, 20% of positions have ≥ 1 lit channel without any Ba. A
  single lit channel is therefore never evidence on its own; the 5–10 rule asks for several channels or lineages.

**Ba/Pb thresholds** (CHS; V.G. 10/10; handling of each band revised 12/10, see the Ba/Pb section below). **Before
using them on another histotype or slide, compare its Ba/Pb distribution with CHS (q99, q99.9, histogram) and
recalibrate if it differs markedly** (V.G. 10/10). For reference, over all pixels: Ba median 0, q90 1, q99 3, q99.9 23;
Pb median 0, q90 1, q99 4, q99.9 13. One threshold for both metals:
- 20 for `Artifacts_auto`;
- 10 for `Artifacts_auto_low`;
- 5 as the seed of candidate regions.

A region's band is set by **how many pixels** pass each threshold, never by its single brightest pixel (minimum
2 pixels, below):
- "> 20" = ≥ 2 pixels above 20;
- "10–20" = ≥ 2 pixels above 10 but < 2 above 20;
- "5–10" = ≥ 2 pixels above 5 but < 2 above 10, so a "5–10" speck can still hold one pixel above 10;
- "< 5" = < 2 pixels above 5.

**Display in QuPath:** Ba is shown at 0–10, so a pixel at ≥ 10 counts is full white and a pixel at 5 is
half-bright.

**Pixel and region rules**
- **'Multi' pixel:** ≥ 5 antibody channels 'high' at the same pixel. Any antibody counts; there is no lineage logic.
- **Region:** 8-connected pixels where at least one of the following holds:
  - Ba or Pb > 5;
  - ≥ 2 antibody channels are 'high';
  - the pixel is 'multi';
  - the pixel is 'single'.
- **Minimum size:** a rule fires only if **≥ 2 pixels** of the region satisfy it.
- **Polygon:** the region dilated by **1 px** (halo; V.G. 10/10, was 2 px up to v2). The measured signal tail is
  about 1 px (`auto_artifacts/halo_check/README.md`). Regions merged by the dilation take the highest class.

### Why these values
All three were set by Claude on 07/10, checked on V.G.'s row-A annotations, and confirmed by V.G. on 10/10 after the
checks below.

- **2 pixels, not 1.**
  - With 1 pixel, `Artifacts_auto` would rise from 6449 to 9838 (+53%).
  - The extra components peak just above the threshold (median Ba/Pb 24), and 62% have no 'high' antibody channel.
  - A real accumulation spans more than one pixel. Row-A agreement was 0.78 with 2 px and 0.65 with 3.
- **Ba/Pb 20 for both metals.**
  - The Ba/Pb histograms have no natural break, so the threshold is a choice. 20 is about the Ba q99.9 (23); the
    Pb q99.9 is 13.
  - Tested alternative: one threshold per metal at its own q99.9 (`auto_artifacts/bapb_variants/README.md`). It
    gives 7149 `Artifacts_auto` instead of 6449: +989 faint Pb specks (Pb 13–20), almost all already
    `Artifacts_auto_low`, and −250 Ba 20–23 accumulations.
  - Only 14% of the added polygons carry 'high' antibody signal, against 53% of the current ones. Ba/Pb matter only
    as markers of antibody contamination, so the alternative adds review work and excluded area without benefit.
    Kept at 20.
- **≥ 5 'high' channels, any antibody.**
  - Of the 13 945 pixels with ≥ 5 'high' channels, 81% have ≥ 2 lineage-incompatible markers 'high' at the same
    1-µm pixel. Markers counted: SOX9, S100, CD68/CD163, CD3, CD20, CD66b, CD31/ERG, aSMA, CD138.
  - The other 19% are mostly co-firing channels already judged not usable (CD10 + CD21 + CD72a + CD80 + GATA3
    ± Ki67). No coherent multi-marker phenotype appears among the frequent combinations.
  - The rule therefore captures aggregates, not cells.
  - It matters little in practice: only 157 `Artifacts_auto` (2.4%) come from it alone; 98% are found by Ba/Pb.

### What happens to single pixels (not captured by the 2-pixel rule)
Evidence: `auto_artifacts/cell_impact/README.md`, part B.
- **Isolated spikes > 50 counts above all 8 neighbors, any channel:** removed by the hot-pixel filter.
- **Isolated Ba/Pb pixels > 20:** about 12 per core, of which only 130 in cells and 71 with a 'high' antibody channel
  in the whole dataset. Ba/Pb are not analyzed channels, so these are irrelevant.
- **Antibody spikes 20–50 above all neighbors, left by the filter:**
  - They raise a cell mean by ≥ 1 count in 354 of 79 452 cells (0.45%).
  - 79% of those are in S100 and aSMA, where positive cells are in the hundreds; rare markers have ≤ 13 cells per
    channel in the whole dataset.
  - Censoring at ≥ 99.9th before phenotyping dampens the rest.
- **No extra rule is needed.**

## `Spot_auto` and `Spot_auto_large` – decided (V.G. 10/10/2026)
- **Spot:** a region that is not `Artifacts_auto`, has no pixel with Ba/Pb > 10, and has ≥ 2 'single' pixels.
- **Split:** n = number of 'single' pixels inside the polygon (QuPath measurement `n_px_single`).
  - **n ≤ 10 → `Spot_auto`;**
  - **n > 10 → `Spot_auto_large`.**
- In QuPath the polygon name lists the rule and the channels with 'single' pixels, e.g. `single (CD45RO)`.

### Why the split at 10 'single' pixels
Data: `auto_artifacts/hpf_check/README.md`. The median cell area in the current segmentation is 58 px (79 452
Cellpose cells).

| | `Spot_auto` (≤ 10) | `Spot_auto_large` (> 10) |
|---|---|---|
| Number (v2, 136 ROIs; v3: 3569 / 205) | 3475 (~26 per core) | 204 (median 1 per core, max 8; in 87 ROIs) |
| Median polygon area | 35 px: smaller than a cell | 72 px: cell-sized |
| What they are | bright foci with no DNA, mostly one channel (63% one channel only) | mostly 2–4-channel aggregates (CD45RO + PDL1, MHC_II + LAG3, …); a few could be real bright cells (GranzymeB in DNA-rich areas, e.g. ROI031_K10, ROI001_E10) |
| Risk of hiding biology | negligible (0.10% of the image area in total) | real: cell-sized, can be a cell |

The hot-pixel filter does not remove the spots: 3676/3684 survive it, because it only fixes isolated pixels.

### `Spot_auto` (≤ 10) – handling
- **Not reviewed by V.G.** Hidden in the QuPath viewer; accepted by rule.
- **Excluded area:** the polygons go to Rashid in the release like every other excluded area.
- **Why it matters.** Take a 58-px cell with a 3-px PDL1 spot at 1500 counts. Its mean PDL1 is about 78, a strong
  "positive", even though the cell's real value is typically < 1.

### `Spot_auto_large` (> 10) – handling
- **Reviewed by V.G. one by one** in the same pass as `Artifacts_auto_large`:
  - aggregate / not a cell → **leave it** (kept = accepted; no reclassification, V.G. 10/10);
  - real cell → **delete** the polygon (the area is not excluded).
- The pipelines use only the released polygons: a `Spot_auto_large` that V.G. deleted is not excluded.
- **Review aid:** the polygon name gives the channel to switch on (e.g. `single (GranzymeB)`). With that channel
  at its fixed display range and DNA on, look for DNA under the spot, a cell shape and a plausible intensity.

## `Artifacts_auto` and `Artifacts_auto_large` – decided (V.G. 10/10/2026)
- **Definition:** ≥ 2 pixels with Ba or Pb > 20, **or** ≥ 2 'multi' pixels. Polygon = region dilated by 1 px (2 px up to
  v2).
- **Numbers (v3, 1-px halo):** 6663 in all ROIs; 5931 in the 108 potentially evaluable cores, median 41.5 per core
  (IQR 26–73, max 210).
  - Composition: 81% Ba/Pb only, 17% Ba/Pb + multi, 2% multi only.
  - Median area 52 px; 467 polygons > 200 px and 193 > 300 px.
  - In total 0.42% of the image area.
- **Split by size** (QuPath output only): polygons > 200 px (about 3–4 cells) are written as
  `Artifacts_auto_large`. In the 108 evaluable cores that is 467 (median 3 per core), 32% of the class area.
- **Review (option 3, V.G. 10/10):**
  - `Artifacts_auto` (≤ 200 px): accepted by rule. In the single pass per core V.G. deletes only evident errors
    (review by exception). **Revised 12/10 (V.G.): no pass by exception; accepted by rule** (step 6 of the protocol).
    In the 15 sample cores of step 5 they were on screen and none was deleted as an error.
  - `Artifacts_auto_large`: reviewed one by one, because under rule B one large polygon excludes several cells.
  - Why not every polygon: the definition is objective (pixels with Ba/Pb ≥ 20 or ≥ 5 'high' channels are
    contaminated by definition). False positives are rare: 2% come from the multi rule alone, and 81% of 'multi'
    pixels are lineage-incompatible. On row A the polygons V.G. had not drawn were real accumulations.
- **Cells:** rule B (below).

## `Artifacts_auto_low` – decided (V.G. 10/10/2026, option 3) – **superseded 12/10/2026: option 2, every `_low` is a polygon**
See "Ba/Pb bands – revised" below. Until the next run (v5), QuPath still holds v4 (option 3). The 10/10 text is kept
as the record of that decision.

Evidence: `auto_artifacts/low_check/README.md`.
- **Candidate:** a region that is not `Artifacts_auto` and has ≥ 2 pixels with Ba or Pb > 10. In practice faint Ba/Pb
  specks between 10 and 20 (median peak 18). 4521 in all ROIs; 3688 in the 108 evaluable cores.
- **Written for QuPath only with antibody signal:** at least one antibody channel other than S100 and aSMA is 'high'
  somewhere inside the polygon. S100 and aSMA do not count because their 'high' level (654 / 210) is reached by
  bright real cells.
  - 906 polygons in all ROIs; **701 in the 108 evaluable cores** (19%), median 5 per core (IQR 3–8, max 27).
  - Small: median 26 px, 2 polygons > 200 px.
  - Top channels: PDL1, CD47, LAG3, CD31, CD138, Tbet, SOX9, GATA3, CD163, MHC_II, i.e. the usual sticky channels.
- **The others (81%) are not imported** and are not excluded areas. They stay in `components.csv` (column
  `exported` = False) for later checks.
- **Review:** as `Artifacts_auto`, by exception. Accepted by rule; in the single pass V.G. deletes only evident
  errors. Kept = accepted.
- **Why option 3.** It applies the same logic as keeping Ba/Pb 20 (`bapb_variants/`): Ba/Pb count only as markers of
  antibody contamination. Accepting every `_low` would amount to a Ba/Pb threshold of 10, while 81% of these specks
  carry no antibody signal.

| Option | Cells excluded in total (rule B, 108 cores) | Contaminated cells left near `_low` (lower bound) |
|---|---|---|
| 1. ignore `_low` | 3427 (6.1%) | 123 |
| 2. accept all `_low` | 4406 (7.8%) | 0 |
| **3. accept `_low` with antibody signal (chosen)** | **3694 (6.6%)** | **54** |

"Contaminated" here is counted in channels other than S100/aSMA. 44% of the cells touching a `_low` polygon cannot be
evaluated (no pixel farther than 4 px from a polygon), so the residual counts are lower bounds. The 54 residual
cells touch `_low` specks without antibody signal; at 13% contamination they cost less to keep than the 712 cells
that option 2 would add to the excluded ones.

## Ba/Pb bands – revised (V.G. 12/10/2026)
Evidence: `auto_artifacts/20261012_bapb10_test/README.md` (test, matrix check, speck checks, cell impact).
Literature: `Literature Review/20261012 BaPb_in_IMC_literature_review.md`.

**Why it was revised.**
- In QuPath, Ba accumulations looked unenclosed while Pb ones were enclosed. The Ba display (0–10) saturates below
  the old polygon threshold (20, or 10–20 only with a 'high' antibody channel).
- Ba has about 3× more pixels than Pb in the 10–20 range, and it forms clustered haze where Pb shows isolated noise
  pixels. In E10, v4 covered 51% of the Ba 10–20 pixels.

| Band (≥ 2 px) | Handling | Status |
|---|---|---|
| Ba/Pb > 20 | always a polygon (`Artifacts_auto` / `_large`) | unchanged (10/10) |
| Ba/Pb 10–20 | **always a polygon** (`Artifacts_auto_low`, all written: option 2) | **decided 12/10** |
| Ba/Pb 5–10 | **a polygon only with multi-channel antibody signal** (option B): inside the speck or its 1-px halo, ≥ 3 antibody channels have a pixel above their q99.9 ('lit'), **or** lit markers of ≥ 2 incompatible lineages. S100/aSMA are excluded. Lineages: T (CD3, CD4, CD8), myeloid (CD68, CD163, CD11c), B (CD20), granulocyte (CD66b, CD15), endothelial (CD31, ERG), tumor (SOX9); CD56 is left out (NK cells and CD56+ tumor cells) | **decided 12/10** (B; 'lit' = q99.9) |
| Ba/Pb < 5 | no polygon | **decided 12/10** |

**Evidence**
- **Not calcified matrix.** Pb and Ba can be endogenous in mineralized tissue (literature), and whether the blocks
  were decalcified is not known.
  - Ba/Pb 10–20 polygons fall on cells, median 3.9× chance (16/121 cores below 1), with no correlation with
    `matrix_pct`.
  - Ba/Pb > 20 polygons: median 1.45×. Where they fall off cells they are not Pb-dominant and stay dot-shaped.
- **The Ba/Pb 5–10 specks carry antibody signal** (V.G. saw it by eye).
  - In 6 ROIs, against controls matched for cell coverage: 1.70 lit channels vs 0.27; ≥ 3 channels in 21% vs 1.2%.
    Lineage-incompatible markers appear together.
  - Not a polyatomic interference from Ba: CD56 (169Tm) does not scale with Ba.
  - The signal is weak: only 1.0% of the cells touched by these specks are contaminated (≥ 1 count and ≥ 2× in a
    channel, as on 10/10).
- **Options compared for 5–10** (6 ROIs, 311 cells touched only by specks, 3 contaminated):

  | Option | Cells made phenotype-not-assessable | Contaminated removed / left |
  |---|---|---|
  | A: every speck | 311 | 3 / 0 |
  | B′: ≥ 1 lit channel | 221 | 3 / 0 |
  | **B: multi-channel (chosen)** | **85** | **2 / 1** |
  | C: a 'high' channel (first proposal) | 0 | 0 / 3 |

  - B removes about 2/3 of the excess antibody signal at about a quarter of A's cost: about 600 cells (about 1%) in
    the 121 included cores, against about 2300 for A.
  - B′ was rejected because one lit channel cannot tell a deposit from a genuinely positive cell. The specks it adds
    mostly light CD56, FoxP3, MHC-II, CD3 or CD8, so B′ would preferentially remove positive cells (the 10/10 principle:
    one channel alone never flags anything).
  - Specks that B flags through ≥ 3 channels of one lineage light mostly sticky channels, not coherent phenotypes.
    Myeloid-only specks are 1.4% (0.2% of the controls).
- **Below 5:** in the 3–5 band the excess signal is about a third of the 5–10 band's, with twice as many specks.
  Cells touched only by 3–5 specks: 265, 1 contaminated. The specks B would draw there touch 29 cells, none
  contaminated. Strong aggregates without Ba are already caught by the 'multi' and 'single' rules.

**Settled on 12/10 (V.G.), implemented in `auto_artifacts.py` v5 (`auto_artifacts/20261012_v5/`).** Totals in the
136 ROIs: `_low` 4516 (v4: 906 written), `Artifacts_auto_faint` 3185 (2784 in the included cores). The other classes
are as v4 apart from 219 polygons enlarged by merging; no v4 excluded area is lost (`auto_artifacts/README.md`).
- **Class:** the 5–10 polygons are written as **`Artifacts_auto_faint`** (light purple in QuPath, so it is not
  confused with the orange `Artifacts`). It stays distinct from `_low`, so the release always tells which rule made
  a polygon. The polygon name lists the lit channels, e.g. `faint (CD138+LAG3+CTLA4+…)`.
- **Review:** `Artifacts_auto_faint` is accepted by rule and **hidden** in the viewer, like `Spot_auto`.
  - Reasons: there are many (about 2500 in the included cores, estimated from the test); they are smaller than a
    cell (median about 14 px); and the criterion rests on pixels at the q99.9 level, which cannot be judged by eye at
    the current display.
  - `Artifacts_auto_low` (all written now) stays **visible**. It was to be reviewed by exception; **12/10 (V.G.):
    accepted by rule instead**, as `Artifacts_auto` (step 6 of the protocol).
- **Display:** 208Pb in QuPath goes from 0–8 to **0–10**, as 138Ba (script `01`, and
  `Pipeline Map/Marker_QC/QuPath_display_ranges.csv`). For both metals, full white (≥ 10 counts) now means "always a
  polygon", isolated single pixels aside.
- **Below 5:** nothing.
- **G10:** V.G.'s full-width horizontal band (y 640–650) is drawn as `Artifacts` (treated as a fold, V.G. 12/10).
  It looks more like an acquisition stripe. After the v5 import, the automatic polygons inside it reappear; this is
  harmless, because the excluded area is the union.

## `Artifacts` – content decided (V.G. 10/10/2026)
- **Only tissue folds** are drawn as `Artifacts`. A fold doubles the tissue thickness, so the signal is inflated in
  every channel, DNA included.
- **Not drawn:** damaged core edges (crush, bright rim), detached tissue fragments, areas that only look suspicious
  without a recognizable damage. The last ones are not objective; on row A, 60 of V.G.'s 274 polygons (22%) were of
  this kind (no chemical signature, median 34 px).
- Folds are judged on the IMC image. The H&E list (folds in A8, A11, C8, G8 among the evaluable cores; serial
  section, `core_review/`) is only a hint of where to look.
- Like every excluded area: subtracted from `Evaluable_area`; cells as in "Cells touching an excluded area".
- **Outcome of the single pass (V.G. 12/10/2026): no `Artifacts` drawn.**
  - A8, A11, C8, G8: no fold seen on IMC. A fold is made when each section is cut, so a fold on the H&E serial section
    does not imply one on the IMC section. Flag `fold_HE_only`, for information only.
  - J5: no fold. The core is fragmented, and all fragments are inside `Evaluable_area`. Its H&E entry was corrected
    from `fold` to `none`.
  - **The IMC images were not scanned for folds systematically** (V.G. 12/10): folds were looked for only in the cores
    with a fold on H&E. A fold present only on the IMC section of another core would not be drawn. This is a stated
    limitation.

## `Necrosis` – decided (V.G. 10/10/2026)
- **Drawn only in cores with necrosis on H&E**: in CHS these are A10 (ROI124) and B10 (ROI018) (`core_review/`). V.G.
  draws on the IMC image the area that corresponds to the necrosis on H&E, comparing the two.
- **Why not from the IMC alone:** the usual IMC sign of necrosis is the loss of DNA with nuclear debris. In CHS, 62% of
  the evaluable cores are DNA-negative because of the Ir staining anomaly, so an IMC-only call would confuse
  necrosis with that anomaly.
- Kept as its own class, not just left out of `Evaluable_area`, so that the location of necrosis stays available.
- Like every excluded area: subtracted from `Evaluable_area`; cells as in "Cells touching an excluded area".
- **Outcome of the single pass (V.G. 12/10/2026):**
  - **B10: `Necrosis` drawn**, recognized clearly on IMC: one polygon, 0.051 mm², 6.1% of `Evaluable_area`, with no
    segmented cell inside (current masks).
  - **A10: not drawn.** No necrosis is seen on IMC. Row A was acquired as a strip covering about half of the core, so
    the necrotic area may not have been acquired. Flag `necrosis_not_drawn`.

## `Hemorrhage` – decided (V.G. 10/10 and 11/10/2026)
- **Candidate cores:** those with red blood cells on H&E (`core_review/`, column `red_blood_cells`), 11 cores, all
  evaluable:
  - high: A12, B12, C12, E10, E12, F10, F12;
  - medium: C13, H12;
  - low: E7, B10 (B10 added 11/10 after the H&E–IMC audit; E14 checked: no red blood cells).
- **Drawn only where needed (V.G. 11/10).** V.G. looks at each of these cores with the H&E side by side and draws
  `Hemorrhage` on the IMC image only where V.G. judges it necessary. Scattered red blood cells and blood inside vessel
  lumina are not drawn.
- **The core-level information stays available** for downstream analyses: `red_blood_cells` in the core review
  sheet, plus the presence of `Hemorrhage` polygons in the export.
- **IMC cannot see red blood cells** (`rbc_check/README.md`, 11/10):
  - the panel has no erythroid marker (no CD235a); CD47 carries almost no signal;
  - red blood cells have no nucleus and none of the Cellpose input channels, so they are not segmented. The
    red-blood-cell cores show no excess of anucleate, marker-negative objects.
  - On IMC a hemorrhagic area therefore looks empty, like chondroid matrix. Its outline can only come from the H&E
    (serial section), transferred by eye.
- **Why exclude it where it matters:**
  - Mainly the area. An empty hemorrhagic area left in `Evaluable_area` dilutes the density in proportion to its size.
  - Circulating leukocytes matter little: blood holds about 1 leukocyte per 500–1000 red blood cells, so a 0.1 mm²
    hemorrhage holds only a few. (Correction of 11/10 to the first rationale.)
- **Why only with H&E:** as for necrosis, the IMC image alone cannot recognize it.
- **Own class, not merged into `Necrosis`,** so that necrosis and hemorrhage stay distinguishable.
- Like every excluded area: subtracted from `Evaluable_area`; cells as in "Cells touching an excluded area".
- **Outcome of the single pass (V.G. 12/10/2026): no `Hemorrhage` drawn.** In none of the 11 cores, B10 included, could
  the hemorrhage be recognized on IMC with enough confidence to draw it. All 11 carry the flag
  `hemorrhage_not_drawn`. The class stays defined (it may be used on other slides).

## H&E findings not drawn on IMC: core-level flags – decided (V.G. 12/10/2026)
**Why.** Folds, necrosis and hemorrhage are seen on the H&E serial section. V.G. drew a polygon on IMC only where the
finding was recognized clearly on the IMC image (B10, necrosis). Drawing the others by eye from the H&E would not be
reliable: the registration between H&E and IMC is approximate, row A was acquired as strips, and red blood cells are
invisible on IMC. **These cores are not excluded.** The flag lets the downstream analyses take their nature into
account.

**Where.** Core review sheet (`core_review/20261006 CHS_core_review.xlsx`), green columns:
- `fold_on_imc`, `necrosis_on_imc`, `hemorrhage_on_imc`: `drawn` / `not seen on IMC` / `not assessed (row K)`. Blank
  means there is no such finding on H&E.
- `special_area_flag`: codes separated by `; `.

| Flag | Cores | Meaning | Downstream handling |
|---|---|---|---|
| `hemorrhage_not_drawn` | A12, B12, C12, E10, E12, F10, F12 (high); C13, H12 (medium); E7, B10 (low) | the hemorrhagic area, empty on IMC, is still inside `Evaluable_area` | densities may be **underestimated**, in proportion to the hemorrhagic area: report the flag with the densities; sensitivity analysis of densities without these cores. Phenotyping is not affected, because red blood cells are not segmented |
| `necrosis_not_drawn` | A10 | necrosis on H&E, not seen on IMC, possibly not acquired | sensitivity analysis without A10 |
| `fold_HE_only` | A8, A11, C8, G8 | fold on the H&E section only | **information only**: folds are made when each section is cut, and none was seen on IMC |

- **All flagged cores are included** (12 cores with a flag that has analytic weight, 4 with `fold_HE_only`). The H&E-wins
  rule is unchanged: these are cores as expected on H&E.
- **The flagged cores are not random.** `hemorrhage_not_drawn` covers column 12 (patient 4: A12, B12, C12, E12, F12)
  and E10/F10 (patient 6), mostly rows E–F (high inflammatory infiltrate). Excluding them would remove most E–F cores
  of two patients. This is why they are flagged and tested in a sensitivity analysis rather than excluded.
- **K13** (row K, fold on H&E) was not assessed. It is excluded by design.
- In B10, the drawn `Necrosis` is an excluded area like any other. Only its hemorrhage is flagged.

## Kept = accepted, deleted = rejected – decided (V.G. 10/10/2026)
For every automatic class, a polygon still present in `CHS_IMC` at export is accepted and becomes an excluded area;
a polygon V.G. deleted is rejected. Accepted automatic polygons keep their class in the release, with no
reclassification into `Artifacts`. This keeps the automatic (chemical) artifacts distinct from V.G.'s drawn
(morphological) `Artifacts`: folds, edges, detached tissue.

## Cells touching an excluded area – decided: rule B, refined (V.G. 10/10/2026)
This rule applies to the cells that belong to the `Evaluable_area` (centroid inside, "Cells on the `Evaluable_area`
border" above, V.G. 12/10/2026); the others are already out of every analysis.

**A cell is excluded if at least one of its pixels is inside an excluded polygon** (any class kept in the release).
Chosen because it is the only area-only rule with no residual contamination: no parameter, no pixel masks, and no
change to the measurement code. Its cost is the highest cell loss, and it is sensitive to the polygon halo and to
the segmentation edges. Halo width: 1 px (V.G. 10/10; `auto_artifacts/halo_check/README.md`).
Rashid stores, for every cell, the fraction of its pixels inside excluded areas (required by the refinement below;
it also keeps sensitivity analyses such as rule A possible).

### Refinement: three groups of cells, and the density denominator – decided (V.G. 10/10/2026)
Evidence: `auto_artifacts/denominator_check/README.md`.

| Fraction of the segmented object inside excluded polygons | What it is | Cell counts and densities | Intensities and phenotyping |
|---|---|---|---|
| 0 | clean cell | counted | used |
| > 0 and ≤ 75% | real cell touched at the edge | **counted**, as "phenotype not assessable" | **excluded** (rule B) |
| > 75% | aggregate segmented as a cell | **removed from everything** | excluded |

- **Density denominator** = `Evaluable_area` minus the area of every excluded polygon (all classes kept in the
  release, `Artifacts`, `Necrosis` and `Hemorrhage` included). No extra margin around the polygons.
- **Phenotype densities** are computed on the assessable cells. For every core, the share of "not assessable" cells is
  reported as a QC value.
- For `Artifacts` (folds), `Necrosis` and `Hemorrhage` the same thresholds apply. A cell lying mostly inside one of
  these areas is in subtracted area, so it is not counted either.

**Why**
- **The polygons fall on cells.** In the 108 evaluable cores, rule B excludes 6.6% of the cells while the polygons
  cover 0.6% of the area, 3.4× more than chance.
  - The density loss is larger in DNA-negative cores (median −11.7%) than in valid ones (−2.9%).
  - Subtracting the polygons plus a cell radius does not fix it.
- **Objects > 75% inside are aggregates, not cells.**
  - In the 65 DNA-negative cores, 1196 such objects: small (58–60 px), S100 > 20 in 5–7% against 31% of the clean
    cells, Ba/Pb > 20 in 92%, often multi-channel with sticky SOX9 and CD68.
  - Gallery of 40 objects > 90% inside: V.G. judged 35 (88%) aggregates.
  - SOX9 is a nuclear channel of the Cellpose input, which plausibly explains why they are segmented as cells.
- **Objects ≤ 50% inside are real cells**, larger and more often S100+ than the clean cells (S100 > 20 in 49–62%).
  The 50–75% band already has a cell-like profile (S100 33%, 83 px).
- **Effect of counting the edge-touched cells.**
  - In DNA-negative cores, 772 of 16 412 real cells (4.7%) are touched at the edge.
  - Excluding them from the counts would lower densities by about 5% there, against about 3% in valid cores.
  - Their share of S100+ cells is higher, so phenotyping only the assessable cells shifts the tumor fraction by about
    1 percentage point (31.6% → 30.6% in DNA-negative cores). This bias is accepted.
- **Alternative rejected:** measuring edge-touched cells on their pixels outside the polygons. It would fix the
  composition too, but needs a change to the measurement code for about 1 point.
- **Scope of the evidence:** gallery and profile come from the DNA-negative cores, where the effect is largest.
  Re-check the 75% threshold on the final segmentation.

This rule acts **downstream** of the polygons. The polygons say where the signal is unreliable and are defined
independently of the segmentation. The rule says what the pipeline does with the segmented cells that overlap them,
so it can be changed without redrawing anything.

Numbers from Rashid's current Cellpose masks, union of `Spot_auto` + `Spot_auto_large` + `Artifacts_auto` (all
assumed kept), 108 evaluable cores, 56 175 cells (`auto_artifacts/cell_impact/README.md`). 6.6% of cells touch a
polygon. A cell is "contaminated" when the polygon pixels raise its mean by ≥ 1 count and ≥ 2× in at least one
antibody channel.

| Rule | Pixel masks? | Cells excluded | Per core (median / max) | Kept and still contaminated |
|---|---|---|---|---|
| A. centroid inside | no | 4.6% | 5.4% / 29% | 141 (0.25%); for `Spot_auto` 73 of the 136 kept |
| B. any pixel inside | no | 6.6% | 7.5% / 39% | 0 |
| C. > 10% of the cell inside | no | 5.9% | 6.6% / 31% | 10 (0.02%) |
| C. > 25% inside | no | 5.1% | 5.8% / 30% | 70 (0.12%) |
| C. > 50% inside | no | 4.3% | 4.6% / 28% | 229 (0.41%) |
| D. > 50% inside, pixels inside dropped from intensities | yes | 4.3% | 4.6% / 28% | 0 (1333 cells measured on fewer pixels) |
| E. pixels inside dropped; cell excluded only if fully inside | yes | 3.0% | 3.2% / 24% | 0 (2024 cells measured on fewer pixels) |
| F. no exclusion: per-cell flag (fraction inside), rule chosen per analysis | no | – | – | depends on the analysis |

## Open points for the pipelines
- The thresholds use quantiles computed on the unfiltered stack. Keep them fixed for reproducibility (the filter
  changes < 0.2% of the polygons).
- **Release format: GeoJSON only** (V.G. 10/10/2026; a per-ROI label raster was proposed and declined). Both
  pipelines must rasterize the same way:
  - **a pixel is inside a polygon if its center is inside** (rasterio `all_touched=False`);
  - a pixel is excluded if it is inside **any** excluded polygon (union of the classes kept in the release), so
    overlaps between classes need no priority;
  - the automatic polygons are traced along pixel edges, so this convention gives back exactly their original pixels.
    Checked on 20 ROIs: all vertices are integers, and 0 pixels differ from `area_px`. Only V.G.'s hand-drawn outlines
    (`Evaluable_area`, `Artifacts`, `Necrosis`) keep a ±1 px edge ambiguity, which is negligible for large areas.
- **Cells and `Evaluable_area`:** centroid inside the polygon (point-in-polygon on the GeoJSON, not on the raster),
  centroid in the same coordinates as the polygons (pixel center = column + 0.5, row + 0.5). Store
  `frac_in_evaluable` per cell for sensitivity analyses.
- The cell rule must be applied on Rashid's final segmentation (after the hot-pixel filter and any re-segmentation).
  The numbers above are an estimate on the current masks.

## History
- 10/10/2026 – `Spot_auto` split into `Spot_auto` (≤ 10 'single' px) and `Spot_auto_large` (> 10) (V.G.). Automatic
  classes recomputed after the hot-pixel filter (`auto_artifacts/20261010_v2/`). No pixel masks: accepted polygons
  become excluded areas (V.G.). Import into `CHS_IMC` (script `02`): **once, after all classes are defined** (V.G.).
- 10/10/2026 – Shared definitions decided (V.G.): 2-pixel minimum, Ba/Pb 20 for both metals (per-metal q99.9
  tested and rejected), 'multi' = ≥ 5 'high' channels of any antibody, 'high' = max(3 × q99.9, 10). Single-pixel
  handling documented. Cell rules compared.
- 10/10/2026 – Ba/Pb 20 re-examined against the per-metal q99.9 judged on cells (`bapb_variants/`): confirmed for CHS
  (V.G.), with a re-check of the Ba/Pb distribution before reuse on other histotypes.
- 10/10/2026 – Cell rule B decided (V.G.): a cell is excluded if ≥ 1 pixel is inside an excluded polygon. Halo
  width checked (`halo_check/`): the signal tail is ~1 px → halo 1 px (V.G.). Classes regenerated as
  `auto_artifacts/20261010_v3/` (script `02` now points to v3).
- 10/10/2026 – `Artifacts_auto` review: option 3 (V.G.). Accepted by rule, evident errors deleted; > 200 px written
  as `Artifacts_auto_large` and reviewed one by one. Kept = accepted, deleted = rejected, for all automatic classes;
  no reclassification into `Artifacts` (also for `Spot_auto_large`). v3 regenerated with the new class.
- 10/10/2026 – `Artifacts_auto_low`: option 3 (V.G.). Only polygons with a 'high' antibody channel other than
  S100/aSMA are written for QuPath and accepted by rule (review by exception); the others stay in `components.csv`.
  Classes regenerated as `auto_artifacts/20261010_v4/` (script `02` now points to v4).
- 10/10/2026 – `Artifacts` (manual) = tissue folds only (V.G.); edges, detached fragments and merely suspicious
  areas are not drawn.
- 10/10/2026 – `Necrosis` drawn only in cores with necrosis on H&E (A10, B10), matching the H&E area (V.G.).
- 10/10/2026 – Cell rule refined (V.G.): objects > 75% inside excluded polygons are aggregates and are removed from
  everything; cells > 0 and ≤ 75% inside are counted in densities as "phenotype not assessable" and excluded from
  phenotyping; denominator = `Evaluable_area` minus the excluded polygons (`auto_artifacts/denominator_check/`).
- 10/10/2026 – Release format: GeoJSON only (V.G.), with the pixel-center rasterization convention.
- 10/10/2026 – Detached tissue fragments are inside `Evaluable_area` (V.G.).
- 10/10/2026 – New class `Hemorrhage` (V.G.): drawn only in the 10 cores with red blood cells on H&E, matching the
  H&E areas (no scattered red blood cells); excluded and subtracted from `Evaluable_area` like `Necrosis`.
- 11/10/2026 – `Hemorrhage`: Rashid's masks do not segment red blood cells (`rbc_check/`). V.G. draws `Hemorrhage`
  only where needed, with the H&E side by side; the core-level information (`red_blood_cells`) is kept for
  downstream analyses. The circulating-leukocyte argument was downgraded: the area is what matters.
- 11/10/2026 – Scope rule (V.G.): G–J cores are in scope for TME profiling; only cores where the H&E contradicts the
  expected region (G–H without CHS, I–J with CHS; I5 corrected to CHS on H&E) and row K are excluded. Cores with
  partial or missing H&E stay in with a flag, unless both the visible H&E and the IMC S100 contradict the expected
  region (G11, excluded). Evaluable cores 108 → 121 (core review sheet;
  single-pass protocol).
- 11/10/2026 – Core inclusion rules written as three scenarios (V.G.): as expected → included; not as expected →
  excluded; partial/missing H&E → flag, IMC comparison, V.G. confirms. "As expected" checks only CHS presence (grade
  and infiltrate from the label). Row K excluded by design. The polygon review covers all 136 cores.
- 11/10/2026 – The H&E wins over the IMC for cores present on H&E (V.G.): J3 re-included (122 cores); the
  `Core_not_evaluable` marks of 05/10 no longer exclude a core (K3 and K9 stay out as row K).
- 11/10/2026 – H&E–IMC audit (`core_review/he_imc_check/`): J5 is CHS on H&E (V.G.) → region mismatch, excluded
  (121 cores).
- 11/10/2026 – `Evaluable_area` drawn by V.G. on all 136 cores (49 drafts kept, 55 edited, 32 redrawn; A13 redrawn as a
  polygon after a first attempt as an open line). Class `Evaluable_area_auto` removed from the `CHS_IMC` class list; the drafts stay in
  `auto_tissue/20261007_v2/`.
- 12/10/2026 – Steps 3–4 of the single pass (V.G.), with an H&E gallery of the flagged cores (temporary, deleted after
  use):
  - `Necrosis` drawn in B10 only;
  - no `Artifacts` (no fold seen on IMC in A8, A11, C8, G8; J5 has no fold, H&E entry corrected);
  - no `Hemorrhage` in any of the 11 cores;
  - no systematic scan of the IMC images for folds (stated limitation).

  The findings not drawn become core-level flags in the core review sheet (`special_area_flag`). The cores stay
  included, and the downstream analyses take the flags into account (new section "H&E findings not drawn on IMC").
  Export of script `03` (12/10 09:19) checked: automatic polygons identical to v4 in all 136 ROIs, nothing deleted yet.
- 12/10/2026 – Ba/Pb bands revised (V.G.), after Ba accumulations were seen unenclosed in E10 and after a literature
  review (`Literature Review/20261012 BaPb_in_IMC_literature_review.md`: no published fixed Ba/Pb threshold; Pb/Ba can
  be endogenous in calcified tissue):
  - Ba/Pb 10–20: always a polygon (option 2 instead of option 3);
  - Ba/Pb 5–10: a polygon only with multi-channel antibody signal (option B; ≥ 3 lit channels or ≥ 2 lineages);
    options A (every speck) and B′ (one lit channel) were rejected;
  - 'lit' = above the channel's q99.9, not the QuPath display maximum;
  - < 5: nothing (proposed);
  - checks: the polygons do not fall on matrix; the 5–10 specks carry weak multi-lineage antibody signal (1% of the
    touched cells contaminated).

  Units, the two kinds of thresholds and why q99.9 are now explained in "Shared definitions". Evidence:
  `auto_artifacts/20261012_bapb10_test/README.md`. v5 imported into `CHS_IMC` the same day (136/136 match).
- 12/10/2026 – Review of `Artifacts_auto_large` and `Spot_auto_large` (V.G.): a sample instead of one by one.
  - Sample: 15 included ROIs; 6 targeted (E10, J12, G10, D1, F13, G8) and 9 random (A4, B8, C7, D9, E12, F15, H10,
    I3, J9); 109 large polygons.
  - Result: 0 errors (random 0/49, targeted 0/60).
  - Decision rule fixed beforehand: the remaining 580 (528 in the included cores) are accepted by rule.
  - The only deletions are 18 automatic polygons in G10 lying inside V.G.'s `Artifacts` band.
  - Details: single-pass protocol, step 5.
- 12/10/2026 – Step 6 (V.G.): `Artifacts_auto` and `Artifacts_auto_low` are **accepted by rule**, without the pass by
  exception, as the large polygons. In the 15 sample cores they were on screen (922 and 650) and none was deleted as an
  error. Accepted in the 121 included cores: 5715 and 3971 (export of 16:04).
- 12/10/2026 – `Evaluable_area` border: **centroid rule** (V.G.). A cell belongs to the area if its centroid is inside
  the outline; then the rule for excluded areas applies. Measured against "any pixel" (+0.27%) and "fully inside"
  (−1.2%) (`annotations_check/20261012_evaluable_border/`). Rashid stores `frac_in_evaluable` per cell.
- 12/10/2026 – `Evaluable_area` edges corrected by V.G. in 15 included cores where tissue had been left out (C1, C3, C5,
  C14, D1, D7, F3, F6, F10, G10, H10, I4, J4, A10, A14): cells outside 677 → 430 (0.7%) (final export of 23:26). F6 had
  first been saved as an open line (Polyline tool); V.G. redrew it as a polygon.
