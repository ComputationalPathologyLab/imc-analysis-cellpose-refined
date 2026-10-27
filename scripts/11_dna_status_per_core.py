"""Recompute the per-core DNA status on the current segmentation (review item 2.1; manual review guide, section 5).

Rule (identical to the one used for the core review sheet):
1. per object, dna_sum = arcsinh(DNA1) + arcsinh(DNA2), on the per-object mean counts (cofactor 1);
2. an object is DNA-negative if dna_sum < 1;
3. per core, fraction of DNA-negative objects: < 0.20 -> valid; 0.20-0.50 -> intermediate; > 0.50 -> dna_negative.

The class in the core review sheet was computed on all objects of the predecessor segmentation. It is recomputed here
in two ways and compared with the sheet; the sheet value is not overwritten:
- `all objects`: every object of the core, as in the original computation (the rule as defined);
- `retained cells`: only objects kept by the manual review (`cell_status` clean or phenotype_not_assessable), i.e.
  without objects outside the Evaluable_area and without aggregates segmented as cells.

With `--reference-cells` the rule is first applied to the predecessor single-cell table and compared with the per-core
values of the TMA core map (fraction and class must be identical), which validates the implementation.

Usage (from the workflow directory):
    python scripts/11_dna_status_per_core.py --workflow-dir .
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

OLD_NAMES = {f"ROI{k:03d}_ROI_{k:03d}": new for k, new in zip(
    range(32, 42), ["ROI032_I13", "ROI033_G12", "ROI034_G13", "ROI035_C1", "ROI036_K6",
                    "ROI037_F10", "ROI038_E15", "ROI039_F14", "ROI040_D7", "ROI041_D5"])}
RETAINED = ["clean", "phenotype_not_assessable"]


def classify(fraction):
    return np.where(fraction > 0.5, "dna_negative", np.where(fraction >= 0.2, "intermediate", "valid"))


def per_object(cells: pd.DataFrame) -> pd.DataFrame:
    out = cells[["roi", "Object", "DNA1", "DNA2"]].copy()
    out["dna_sum"] = np.arcsinh(out["DNA1"]) + np.arcsinh(out["DNA2"])
    out["dna_negative_object"] = out["dna_sum"] < 1
    return out


def per_core(objects: pd.DataFrame, prefix: str) -> pd.DataFrame:
    g = objects.groupby("roi").agg(objects=("dna_negative_object", "size"),
                                   dna_negative_objects=("dna_negative_object", "sum"),
                                   fraction_dna_negative=("dna_negative_object", "mean"),
                                   DNA1_median=("DNA1", "median"), DNA2_median=("DNA2", "median"))
    g["dna_status"] = classify(g["fraction_dna_negative"])
    return g.add_prefix(prefix)


def read_cells(path: Path) -> pd.DataFrame:
    cells = pd.read_csv(path, usecols=["Image", "Object", "DNA1", "DNA2"])
    cells["roi"] = cells["Image"].str.replace(r"\.tiff?$", "", regex=True).replace(OLD_NAMES)
    return cells


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow-dir", default=".")
    ap.add_argument("--cells", default="data/cells.csv")
    ap.add_argument("--cell-flags", default="data/manual_review/cell_flags.csv")
    ap.add_argument("--release", default="data/reference/manual_review/20261012_v1")
    ap.add_argument("--core-map", default="data/reference/20261005 TMA_core_map.csv")
    ap.add_argument("--reference-cells", default="", help="predecessor single-cell table, to validate the rule")
    ap.add_argument("--output-dir", default="data/dna_status")
    ap.add_argument("--numbered-copy", default="results/12_dna_status_per_core.csv", help="'' to skip")
    ap.add_argument("--log-file", default="logs/11_dna_status_per_core.log")
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

    log("DNA STATUS PER CORE")
    log(f"run_started: {dt.datetime.now().isoformat(timespec='seconds')}")
    log(f"host: {socket.gethostname()}; python: {platform.python_version()}; numpy: {np.__version__}; pandas: {pd.__version__}")
    log("rule: dna_sum = arcsinh(DNA1) + arcsinh(DNA2) per object; DNA-negative if < 1; "
        "core: < 0.20 valid, 0.20-0.50 intermediate, > 0.50 dna_negative")

    core_map = pd.read_csv(resolve(args.core_map)).set_index("roi")
    failed = False

    if args.reference_cells:
        ref = per_core(per_object(read_cells(resolve(args.reference_cells))), "")
        joined = ref.join(core_map[["cells", "fraction_dna_negative_cells", "DNA1_median_per_cell",
                                    "DNA2_median_per_cell", "dna_status"]], rsuffix="_map")
        checks = {
            "rois": len(joined),
            "object_count_differences": int((joined["objects"] != joined["cells"]).sum()),
            "fraction_max_abs_difference": float((joined["fraction_dna_negative"].round(3)
                                                  - joined["fraction_dna_negative_cells"]).abs().max()),
            "DNA1_median_max_abs_difference": float((joined["DNA1_median"].round(3) - joined["DNA1_median_per_cell"]).abs().max()),
            "class_differences": int((joined["dna_status"] != joined["dna_status_map"]).sum()),
        }
        log("validation on the reference cells vs TMA core map: " + "; ".join(f"{k}={v}" for k, v in checks.items()))
        failed |= bool(checks["object_count_differences"] or checks["class_differences"]
                       or checks["fraction_max_abs_difference"] > 0)

    cells = read_cells(resolve(args.cells))
    flags = pd.read_csv(resolve(args.cell_flags)).rename(columns={"Image": "roi"})[["roi", "Object", "cell_status"]]
    objects = per_object(cells).merge(flags, on=["roi", "Object"], how="left", validate="one_to_one")
    if objects["cell_status"].isna().any():
        log(f"STOP: {int(objects['cell_status'].isna().sum())} objects without cell_status")
        sys.exit(1)

    sheet_path = glob.glob(str(resolve(args.release) / "core_review" / "*.xlsx"))[0]
    sheet = (pd.read_excel(sheet_path, sheet_name="Core review").dropna(subset=["roi"]).set_index("roi")
             [["dna_status", "evaluable_for_IMC"]].rename(columns={"dna_status": "dna_status_sheet"}))

    table = (per_core(objects, "all_")
             .join(per_core(objects[objects["cell_status"].isin(RETAINED)], "retained_"))
             .join(sheet, how="left"))
    table["fraction_dna_negative_sheet"] = core_map["fraction_dna_negative_cells"].reindex(table.index)
    table["changed_all_objects"] = table["all_dna_status"] != table["dna_status_sheet"]
    table["changed_retained_cells"] = table["retained_dna_status"] != table["dna_status_sheet"]
    table = table.reset_index()

    objects[["roi", "Object", "dna_sum", "dna_negative_object"]].rename(columns={"roi": "Image"}).to_csv(
        out_dir / "object_dna.csv", index=False)
    table.to_csv(out_dir / "dna_status_per_core.csv", index=False)
    if args.numbered_copy:
        resolve(args.numbered_copy).parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(resolve(args.numbered_copy), index=False)

    log(f"objects: {len(objects)}; DNA-negative objects: {int(objects['dna_negative_object'].sum())} "
        f"({100 * objects['dna_negative_object'].mean():.1f}%)")
    for label, column in [("sheet", "dna_status_sheet"), ("all objects", "all_dna_status"),
                          ("retained cells", "retained_dna_status")]:
        counts = table[column].value_counts().reindex(["valid", "intermediate", "dna_negative"], fill_value=0).to_dict()
        counts_included = (table.loc[table["evaluable_for_IMC"] == "yes", column].value_counts()
                           .reindex(["valid", "intermediate", "dna_negative"], fill_value=0).to_dict())
        log(f"classes ({label}): 136 cores {counts}; evaluable cores {counts_included}")
    for flag, label in [("changed_all_objects", "all objects"), ("changed_retained_cells", "retained cells")]:
        changed = table[table[flag]]
        log(f"class changes vs sheet ({label}): {len(changed)}")
        prefix = "all_" if flag == "changed_all_objects" else "retained_"
        for _, r in changed.iterrows():
            log(f"  {r.roi}: {r.dna_status_sheet} ({r.fraction_dna_negative_sheet:.3f}) -> {r[prefix + 'dna_status']} "
                f"({r[prefix + 'fraction_dna_negative']:.3f}); objects {int(r[prefix + 'objects'])}; "
                f"evaluable_for_IMC={r.evaluable_for_IMC}")
    log(f"run_finished: {dt.datetime.now().isoformat(timespec='seconds')}; checks_failed={failed}")
    log("")
    handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
