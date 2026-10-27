# Single-pass review protocol – `CHS_IMC`

V.G. reviews each core **once**. The definitions are in `20261010 Annotation_class_rules.md`; this document only
gives the order of the work. Status: **approved by V.G. 11/10/2026**.

## Scope (updated 11/10/2026)
- **All 136 cores are reviewed** (V.G. 11/10), including the 15 excluded from the downstream analyses. An excluded core
  may be used later for other purposes, so its polygons must be clean too.
- **Inclusion in the downstream analyses** follows "Core inclusion in the downstream analyses" in the rules document:
  121 cores (`evaluable_for_IMC` = `yes`). Excluded:
  - region mismatch on H&E: G9, G11, H9, H11, I5, J2, J5, J11 (J5: CHS on H&E, found by the H&E–IMC audit, V.G. 11/10);
  - row K by design.
- **Suggested order:** the 121 included cores first, then the 15 excluded ones.
- **J3** is included (H&E wins over IMC, V.G. 11/10). Its 26 large objects are all skeletal muscle fibers (V.G.
  11/10): kept as cells (equivalent to `LO_cell`), with no object-by-object classification.
- **Workload** in all 136 cores (v5, 12/10; v4 in brackets):

| Class | Total | Per core, median (max) | Action |
|---|---|---|---|
| `Artifacts_auto_large` | 484 (478) | 1 (17) | one by one → sample (V.G. 12/10, step 5) |
| `Spot_auto_large` | 205 (205) | 1 (8) | one by one → sample (V.G. 12/10, step 5) |
| `Artifacts_auto` | 6178 (6185) | 32.5 (197) | by exception → accepted by rule (V.G. 12/10, step 6) |
| `Artifacts_auto_low` | 4516 (906) | 29 (100) | by exception → accepted by rule (V.G. 12/10, step 6) |
| `Artifacts_auto_faint` | 3185 (–) | 16 (120) | none (hidden) |
| `Spot_auto` | 3561 (3569) | 23 (82) | none (hidden) |

  One-by-one checks: 683 in total, median 3 per core (max 22). In the 121 included cores: 631.

## Before starting (once)
1. **Close QuPath.** Replace the class list of `CHS_IMC` with the final classes (Claude can write `classes.json` while
   QuPath is closed; a backup is kept):
   - `Evaluable_area_auto` (removed 11/10 after step 2 was done on every core), `Evaluable_area`, `Artifacts`,
     `Necrosis`, `Hemorrhage`;
   - `Artifacts_auto`, `Artifacts_auto_large`, `Artifacts_auto_low`, `Spot_auto`, `Spot_auto_large`.

   The old classes (Tumor, Stroma, Immune cells, Other, Positive, Negative, mArtifacts, LO_*) are removed from the list.
   **Done 11/10** (backup `classifiers/classes.json.20261011_backup`).
2. **Run script `02` once** (*Run for project*, all images). Workaround if the script editor misbehaves: `pbcopy` the
   script, *File → New*, paste, *Run for project*. It replaces the old automatic classes with `auto_artifacts/20261010_v4`
   and **locks** them: they cannot be moved or reshaped by mistake, but they can still be deleted. Locked polygons can be
   deleted (checked by V.G. 11/10).
3. **Check the counts** against `auto_artifacts/20261010_v4/components.csv` (`exported` = True). Claude does this from
   `CHS_IMC/data/*/summary.json`. **Done 11/10:** script `02` run by V.G.; all 136 ROIs match v4 class by class
   (6185 / 478 / 906 / 3569 / 205; `Evaluable_area_auto` 1 per image); the class list is unchanged after closing QuPath.
4. **Hide `Spot_auto`** in the viewer (class list, right-click on the class). It is accepted by rule and is not
   reviewed.
5. Display ranges are already fixed per channel (script `01`). Do not auto-adjust brightness: the same scale in every
   core is what makes cores comparable.

## Re-import of the automatic classes, v5 (12/10/2026)
The Ba/Pb bands were revised (rules document, "Ba/Pb bands – revised"):
- every `Artifacts_auto_low` is now written;
- new class `Artifacts_auto_faint` (Ba/Pb 5–10 with multi-channel antibody signal), accepted by rule and hidden;
- 208Pb display 0–10.

Steps:
1. **Close QuPath.** `classes.json` already holds `Artifacts_auto_faint` (light purple; written by Claude 12/10,
   backup `classifiers/classes.json.20261012_before_faint`).
2. **Run script `02`** (*Run for project*). It replaces every automatic class with `auto_artifacts/20261012_v5` and
   locks it. It removes the temporary test classes if present. It never touches `Evaluable_area`, `Artifacts`,
   `Necrosis` or `Hemorrhage`. No automatic polygon had been deleted before the re-import (checked 12/10), so no review
   work is lost. In G10, the automatic polygons inside V.G.'s `Artifacts` band reappear, which is harmless.
3. **Run script `01`** (*Run for project*): applies the new 208Pb display range (0–10).
4. **Save, quit QuPath (⌘Q)**; Claude checks the counts against `auto_artifacts/20261012_v5/components.csv`.
5. **Hide `Artifacts_auto_faint`** in the viewer, as `Spot_auto` (class list, right-click on the class).

**What happened (12/10).**
- The first v5 run of script `02` (QuPath 0.7.0, after script `01`) removed v4 from all 136 images and imported
  nothing, with no output line. Only the manual annotations were left; no review work was lost.
- The read-only diagnosis (script `02b`) showed that QuPath finds and reads the v5 files.
- Script `02` was rewritten: it reads first, locks with a fallback, removes the old annotations only after a
  successful read, and always prints a result line.
- Tested on E10 with Run: 281 added and locked (saved 15:31).
- **Then Run for project (12/10, 15:36): all 136 images match `20261012_v5` class by class** (6178 / 484 / 4516 /
  3185 / 3561 / 205; checked by Claude from `summary.json`). The manual annotations are intact (136
  `Evaluable_area`, G10 `Artifacts`, B10 `Necrosis`). The cause of the first failure is unknown.

## Per core, in this order
**1. Overview** (low magnification, all non-gas channels on)
- **Done 11/10** for the 10 `to assess on IMC` cores (E4, G5, G11, G15, H8, I2, I8, I10, I15, J10): `Evaluable_area`
  drawn; G11 then excluded from the downstream analyses, but still reviewed. Steps 3–6 are still to do on all 10.
- Excluded cores get the same review. If something during the pass changes a core's inclusion, tell Claude, who
  updates the sheet.

**2. `Evaluable_area`** – **done on all 136 cores (V.G. 11/10)**: 49 drafts kept, 55 edited, 32 redrawn (A13 redrawn
as a polygon after a first attempt as an open line). Trace: `annotations_check/20261011_evaluable_area/`.
- **12/10: edges corrected** in 15 included cores where tissue had been left out (cells outside 677 → 430, 0.7%;
  `annotations_check/20261012_evaluable_outside_groups_after/`). Cells on the outline: centroid rule (rules document).
- **Draw with the Polygon tool, never Polyline:** a polyline encloses no area (A13 on 11/10, F6 on 12/10). Script `03`
  warns about it; script `04` closes an open line into a polygon with the same vertices (open the image, *Run*, *Save*).
- Start from `Evaluable_area_auto`: a circle in 78 cores, the whole image in 30. About 70% of the circles are right or
  nearly right; the wrong ones are mostly in rows I/J/K (see `auto_tissue/README.md`).
- Draw or correct the outline as `Evaluable_area`. Deleting the `_auto` draft is optional: the release ignores
  `Evaluable_area_auto` (11/10).
- No need to snap the outline to pixel edges: at release every hand-drawn polygon is rasterized with the pixel-center
  convention (rules document, "Open points for the pipelines").
- Include the chondroid matrix and **detached tissue fragments** (V.G. 10/10: they are evaluable tissue, not
  `Artifacts`). Leave out glass and holes.

**3. `Artifacts` (folds only)** – **done 12/10 (V.G.), only in the cores with a fold on H&E: none drawn.**
- Draw every tissue fold as `Artifacts`: a band of doubled intensity in all channels, DNA included.
- Judge on the IMC image. The H&E hints are folds in A8, A11, C8 and G8.
- Outcome: no fold on IMC in A8, A11, C8, G8 (flag `fold_HE_only`). J5 has no fold: the core is fragmented, and its H&E
  entry was corrected.
- **No systematic fold scan of the other IMC images** (V.G. 12/10; stated limitation in the rules document). Step 3 is
  closed: skip it in the rest of the pass.

**4. `Necrosis` and `Hemorrhage`** (only cores flagged on H&E), with `CHS_HE` open side by side – **done 12/10 (V.G.)**
- Outcome:
  - `Necrosis` drawn in B10;
  - A10 not drawn (not seen on IMC, possibly not acquired);
  - no `Hemorrhage` drawn in any of the 11 cores.
- The findings not drawn are core-level flags (`special_area_flag` in the core review sheet). The cores stay included
  (rules document, "H&E findings not drawn on IMC").
- `Necrosis`: A10 (ROI124) and B10 (ROI018). Draw the area that corresponds to the necrosis on H&E.
- `Hemorrhage`: A12, B12, C12, E10, E12, F10, F12 (high), C13, H12 (medium), E7, B10 (low). Look at the H&E and draw only
  where needed (V.G. 11/10). Red blood cells are invisible on IMC, where a hemorrhage looks empty, so the outline comes
  from the H&E. Do not draw scattered red blood cells or blood inside vessel lumina.

**5. `Artifacts_auto_large` and `Spot_auto_large`, one by one** – **12/10: replaced by a sample; done, 0 errors → the rest accepted by rule**
- **Sample, not one by one** (V.G. 12/10): 15 included ROIs, 109 large polygons.
  - 6 targeted ROIs: E10, J12, G10, D1, F13, G8.
  - 9 random ROIs, with fixed seed, quotas by DNA status and at most one per facility row: A4, B8, C7, D9, E12, F15,
    H10, I3, J9.
  - Seen so far: E10, J12, G10, D1, F13, A4, B8, with 0 polygons deleted; G10 got V.G.'s `Artifacts` band.
  - Proposed decision rule: 0–1 errors among the 49 random polygons and no pattern in the targeted ones → the rest is
    accepted by rule; errors concentrated in one type → that type is reviewed in every core; scattered errors → back
    to one by one.
  - **Outcome (12/10/2026, v5, export of script `03` at 16:04).**
    - The whole sample was seen; E10, J12, G10, D1, F13, A4 and B8 were seen again on v5.
    - **0 errors**: random 0/49 (39 `_large`, 10 `Spot_auto_large`); targeted 0/60 (37 + 23).
    - The only deletions in the whole project are 18 automatic polygons in G10 (15 `_low`, 2 `_large`, 1 `_faint`),
      all 97–100% inside V.G.'s `Artifacts` band. They are redundant with the band, not errors of the rules.
    - With 0/49 errors, the upper 95% bound of the error rate is about 6%.
    - **Decision: the remaining 580 large polygons (528 in the included cores) are accepted by rule.**
- Switch on Ba and Pb, plus the channel named in the polygon (e.g. `single (GranzymeB)`), with DNA.
- Accumulation or aggregate → **leave** it (kept = accepted).
- Real cell, or nothing there → **delete** it.

**Notes from the H&E–IMC audit (11/10)**
- Uniform gray "sheets" with sharp borders (G11, I15 and other muscle-rich cores) are **skeletal muscle fibers**, not
  contamination (confirmed by V.G. 11/10): do not draw them.
- **B10** has some red blood cells (V.G. 11/10; sheet corrected to `low`): `Hemorrhage` candidate, drawn only if
  needed. **E14**: no red blood cells.

**6. `Artifacts_auto` and `Artifacts_auto_low`, by exception** – **12/10: not done; accepted by rule (V.G.), as the
large polygons**
- **Decision (V.G. 12/10/2026):** no pass by exception. Every `Artifacts_auto` and `Artifacts_auto_low` still in
  `CHS_IMC` is accepted by rule (kept = accepted).
- Why:
  - in the 15 cores of the step-5 sample these classes were on screen (922 `Artifacts_auto`, 650 `_low`), and none
    was deleted as an error (the 15 `_low` deleted in G10 lie inside V.G.'s `Artifacts` band, so they are redundant,
    not wrong);
  - the large polygons, which exclude the most cells each, had 0 errors in the sample;
  - the definitions are objective (Ba/Pb counts, 'multi' pixels), and a small polygon can hardly be judged wrong by
    eye at the fixed display.
- Accepted in the 121 included cores (export of 16:04): 5715 `Artifacts_auto`, 3971 `_low`.
- The original instruction, kept for other slides: scan at medium magnification and delete only evident errors; do not
  reclassify anything. From v5, `Artifacts_auto_low` holds every Ba/Pb 10–20 speck (about 4500 in all ROIs instead of
  906). `Artifacts_auto_faint` stays hidden and is not reviewed.

**7. Save** (*File → Save*) and go to the next core.

## After the pass
1. Script `03`: export the annotations to `annotations_export/`.
2. Claude builds `releases/YYYYMMDD_v1/` with `Scripts/build_release.py` (checks first; refuses open-line outlines and
   automatic polygons not in v5; read-only files, SHA-256 manifest):
   - the GeoJSON of the kept polygons + `Evaluable_area`;
   - `params.json` and `components.csv` of v5 (`auto_artifacts/20261012_v5/`);
   - the core review sheet, with the `special_area_flag` column;
   - the rules document;
   - a count summary (kept/deleted per class and core).
3. Rashid email + package, with the rules document.
