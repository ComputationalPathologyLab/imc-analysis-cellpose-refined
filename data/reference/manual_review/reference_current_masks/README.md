# Reference output of `apply_manual_review.py` on the current masks

Produced on 13/10/2026 by `scripts/apply_manual_review.py` with:
- the release `manual_review/20261012_v1/`;
- the current Cellpose masks of the project (`data/masks`, 136 files, 79 452 objects; the ten old names ROI032_ROI_032 … ROI041_ROI_041 mapped to the TMA names).

Files:
- `cell_flags.csv`: one row per object. Columns: `Image`, `mask_file`, `Object`, `area_px`, `centroid_x`, `centroid_y`, `in_evaluable_area`, `frac_in_evaluable`, `frac_in_excluded`, `cell_status`.
- `core_areas.csv`: one row per ROI. It has the areas, the denominator, the number of objects per `cell_status`, `denominator_matches_release` (True in all 136) and the key columns of the core review sheet.

**Use:** run your own implementation on the same masks and compare by (`Image`, `Object`). `cell_status` and the denominators must be identical; the fractions may differ only in rounding. Explanation: `20261012 Manual_Review_Guide_for_Rashid`, §6 and §8.
