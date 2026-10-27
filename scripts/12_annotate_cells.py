"""Join the core information to every cell and select the evaluable cores (review item 1.5; guide sections 4 and 7).

Every object of the exported single-cell table receives:
- the core information of the core review sheet (manual review release): facility position, patient, sampling region,
  DNA status, inclusion (`evaluable_for_IMC`, `exclusion_reason`), H&E flags (`he_core`, `special_area_flag`) and
  `matrix_pct`; plus `tumor_region` from the TMA core map;
- its manual review flags (`cell_status`, fractions; script 10) and its DNA value (`dna_sum`; script 11);
- derived selections:
    core_included  = evaluable_for_IMC == "yes"                         (core selection, guide section 4.2)
    counted        = core_included and cell_status in {clean, phenotype_not_assessable}   (densities)
    phenotypable   = core_included and cell_status == clean            (intensities, phenotyping)
  (later steps - large-object review, anucleate rule - will refine `phenotypable`);
- sensitivity-analysis flags (guide section 7): s1_he_core_partial, s2_hemorrhage_not_drawn, s3_necrosis_not_drawn.

`dna_status` is taken from the source chosen with `--dna-status-source` (default: the sheet); the sheet value and both
recomputed values (script 11) are always kept as separate columns.

A per-core table gathers the core information, the areas and density denominator (script 10), the object counts and
the densities of counted cells (cells per mm^2 of evaluable tissue minus excluded areas).

Usage (from the workflow directory):
    python scripts/12_annotate_cells.py --workflow-dir .
"""
import argparse
import datetime as dt
import glob
import platform
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd

STATUS = ["clean", "phenotype_not_assessable", "aggregate_removed", "outside_evaluable_area"]
COUNTED = ["clean", "phenotype_not_assessable"]
SHEET_COLUMNS = ["facility_position", "patient_id", "region", "dna_status", "evaluable_for_IMC", "exclusion_reason",
                 "he_core", "special_area_flag", "matrix_pct"]
DNA_SOURCES = {"sheet": "dna_status_sheet", "all_objects": "dna_status_all_objects",
               "retained_cells": "dna_status_retained_cells"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow-dir", default=".")
    ap.add_argument("--cells", default="data/cells.csv")
    ap.add_argument("--cell-flags", default="data/manual_review/cell_flags.csv")
    ap.add_argument("--core-areas", default="data/manual_review/core_areas.csv")
    ap.add_argument("--object-dna", default="data/dna_status/object_dna.csv")
    ap.add_argument("--dna-status", default="data/dna_status/dna_status_per_core.csv")
    ap.add_argument("--release", default="data/reference/manual_review/20261012_v1")
    ap.add_argument("--core-map", default="data/reference/20261005 TMA_core_map.csv")
    ap.add_argument("--dna-status-source", choices=list(DNA_SOURCES), default="sheet")
    ap.add_argument("--output-dir", default="data/cell_annotations")
    ap.add_argument("--numbered-cells", default="results/13_cell_annotations.csv", help="'' to skip")
    ap.add_argument("--numbered-cores", default="results/13_core_table.csv", help="'' to skip")
    ap.add_argument("--log-file", default="logs/12_annotate_cells.log")
    args = ap.parse_args()

    wd = Path(args.workflow_dir).resolve()
    resolve = lambda p: (wd / p) if p and not Path(p).is_absolute() else (Path(p) if p else None)
    out_dir, log_path = resolve(args.output_dir), resolve(args.log_file)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a")

    def log(line=""):
        print(line)
        handle.write(line + "\n")

    log("CELL ANNOTATION AND CORE SELECTION")
    log(f"run_started: {dt.datetime.now().isoformat(timespec='seconds')}")
    log(f"host: {socket.gethostname()}; python: {platform.python_version()}; pandas: {pd.__version__}")
    log(f"dna_status_source: {args.dna_status_source}")
    failed = False

    # ---- inputs -------------------------------------------------------------------------------------------------
    cells = pd.read_csv(resolve(args.cells), usecols=["Image", "Object"])
    cells["Image"] = cells["Image"].str.replace(r"\.tiff?$", "", regex=True)
    flags = pd.read_csv(resolve(args.cell_flags)).drop(columns=["mask_file", "area_px", "centroid_x", "centroid_y"])
    object_dna = pd.read_csv(resolve(args.object_dna))
    core_areas = pd.read_csv(resolve(args.core_areas)).set_index("roi")
    dna = pd.read_csv(resolve(args.dna_status)).set_index("roi")
    sheet_path = glob.glob(str(resolve(args.release) / "core_review" / "*.xlsx"))[0]
    sheet = pd.read_excel(sheet_path, sheet_name="Core review").dropna(subset=["roi"]).set_index("roi")[SHEET_COLUMNS]
    core_map = pd.read_csv(resolve(args.core_map)).set_index("roi")

    # ---- consistency of the core information -------------------------------------------------------------------
    rois = sorted(cells["Image"].unique())
    missing_in_sheet = sorted(set(rois) - set(sheet.index))
    mismatch = {col: sorted(sheet.index[(sheet[col].reindex(core_map.index).astype(str)
                                         != core_map[col].astype(str)).reindex(sheet.index, fill_value=False)])
                for col in ["facility_position", "patient_id", "region"]}
    log(f"ROIs in cells table: {len(rois)}; missing in the core review sheet: {missing_in_sheet or 'none'}")
    log("sheet vs TMA core map: " + "; ".join(f"{c} mismatches={v or 'none'}" for c, v in mismatch.items()))
    failed |= bool(missing_in_sheet or any(mismatch.values()))

    # ---- core table -------------------------------------------------------------------------------------------
    cores = sheet.loc[rois].rename(columns={"dna_status": "dna_status_sheet"})
    cores["tumor_region"] = core_map["tumor_region"].reindex(cores.index)
    cores["dna_status_all_objects"] = dna["all_dna_status"].reindex(cores.index)
    cores["dna_status_retained_cells"] = dna["retained_dna_status"].reindex(cores.index)
    cores["dna_status"] = cores[DNA_SOURCES[args.dna_status_source]]
    cores["core_included"] = cores["evaluable_for_IMC"] == "yes"
    cores["s1_he_core_partial"] = cores["he_core"] == "partial"
    cores["s2_hemorrhage_not_drawn"] = cores["special_area_flag"] == "hemorrhage_not_drawn"
    cores["s3_necrosis_not_drawn"] = cores["special_area_flag"] == "necrosis_not_drawn"
    area_cols = ["height_px", "width_px", "evaluable_area_px", "excluded_in_evaluable_px", "denominator_px",
                 "denominator_mm2"]
    cores = cores.join(core_areas[area_cols + STATUS].add_prefix(""))
    cores["objects"] = cores[STATUS].sum(axis=1)
    cores["counted_cells"] = cores[COUNTED].sum(axis=1)
    cores["phenotypable_cells"] = cores["clean"]
    cores["counted_cells_per_mm2"] = cores["counted_cells"] / cores["denominator_mm2"]
    cores.index.name = "roi"

    # ---- cell table -------------------------------------------------------------------------------------------
    annotated = (cells.merge(flags, on=["Image", "Object"], how="left", validate="one_to_one")
                 .merge(object_dna, on=["Image", "Object"], how="left", validate="one_to_one"))
    missing_flags = int(annotated["cell_status"].isna().sum())
    missing_dna = int(annotated["dna_sum"].isna().sum())
    core_cols = ["facility_position", "patient_id", "region", "tumor_region", "dna_status", "dna_status_sheet",
                 "dna_status_all_objects", "dna_status_retained_cells", "evaluable_for_IMC", "exclusion_reason",
                 "he_core", "special_area_flag", "matrix_pct", "core_included", "s1_he_core_partial",
                 "s2_hemorrhage_not_drawn", "s3_necrosis_not_drawn"]
    annotated = annotated.merge(cores[core_cols], left_on="Image", right_index=True, how="left", validate="many_to_one")
    annotated["counted"] = annotated["core_included"] & annotated["cell_status"].isin(COUNTED)
    annotated["phenotypable"] = annotated["core_included"] & (annotated["cell_status"] == "clean")
    log(f"objects: {len(annotated)}; without cell_status: {missing_flags}; without dna_sum: {missing_dna}; "
        f"without core information: {int(annotated['patient_id'].isna().sum())}")
    failed |= bool(missing_flags or missing_dna or annotated["patient_id"].isna().any())

    annotated.to_csv(out_dir / "cell_annotations.csv", index=False)
    cores.reset_index().to_csv(out_dir / "core_table.csv", index=False)
    for numbered, frame in [(args.numbered_cells, annotated), (args.numbered_cores, cores.reset_index())]:
        if numbered:
            resolve(numbered).parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(resolve(numbered), index=False)

    # ---- summary ----------------------------------------------------------------------------------------------
    inc = cores[cores["core_included"]]
    log(f"cores: {len(cores)}; included (evaluable_for_IMC = yes): {len(inc)}; excluded: "
        + str(cores.loc[~cores["core_included"], "exclusion_reason"].value_counts().to_dict()))
    log(f"included cores: patients {inc['patient_id'].nunique()}; denominator {inc['denominator_mm2'].sum():.2f} mm2")
    log(f"objects in included cores: {int(annotated['core_included'].sum())}; counted: {int(annotated['counted'].sum())}; "
        f"phenotypable: {int(annotated['phenotypable'].sum())}")
    table = pd.crosstab(inc["region"], inc["dna_status"]).reindex(columns=["dna_negative", "intermediate", "valid"],
                                                                  fill_value=0)
    log("included cores by region and dna_status:")
    for region, row in table.iterrows():
        log(f"  {region}: " + ", ".join(f"{k}={v}" for k, v in row.items()) + f", total={row.sum()}")
    log("sensitivity flags among included cores: "
        f"S1 he_core partial={int(inc['s1_he_core_partial'].sum())} {sorted(inc.loc[inc['s1_he_core_partial'], 'facility_position'])}; "
        f"S2 hemorrhage_not_drawn={int(inc['s2_hemorrhage_not_drawn'].sum())}; "
        f"S3 necrosis_not_drawn={int(inc['s3_necrosis_not_drawn'].sum())} {sorted(inc.loc[inc['s3_necrosis_not_drawn'], 'facility_position'])}")
    log(f"run_finished: {dt.datetime.now().isoformat(timespec='seconds')}; checks_failed={failed}")
    log("")
    handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
