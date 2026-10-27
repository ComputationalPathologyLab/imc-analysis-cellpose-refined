"""Apply the pathologist's manual review release to the Cellpose masks (review items 4.5 and 1.4).

For every segmented object the release decides whether it belongs to the core and whether it can be phenotyped; for
every ROI it gives the density denominator. The per-cell rules are those of the release README and are computed by
the reviewer's reference implementation `scripts/apply_manual_review.py`, imported unchanged:

1. a cell belongs to the core if its centroid (column + 0.5, row + 0.5) is inside the `Evaluable_area` polygon;
   otherwise `outside_evaluable_area`;
2. for the cells inside, the fraction of their pixels in the excluded areas (union of all other classes) decides:
   0 -> `clean`; > 0 and <= 0.75 -> `phenotype_not_assessable`; > 0.75 -> `aggregate_removed`;
3. denominator = `Evaluable_area` minus the excluded areas, in pixels (1 px = 1 um^2).
Polygons are rasterized with the pixel-centre convention (rasterio `all_touched=False`).

This script adds the workflow layer around those rules:
- integrity check of every release file against `MANIFEST.sha256` (the run stops on a mismatch);
- per-ROI processing of a masks folder, joined with the core review sheet;
- consistency check against the exported single-cell table (`--cells`): every object present once, same area;
- check of the denominators against the release (`summary/areas_per_core.csv`);
- optional comparison with a reference result produced by the reviewer on the same masks (`--reference-dir`);
- working outputs, numbered research copies and a log.

Usage (from the workflow directory):
    python scripts/10_apply_manual_review.py --workflow-dir .
"""
import argparse
import datetime as dt
import glob
import hashlib
import importlib.util
import os
import platform
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile

STATUS = ["clean", "phenotype_not_assessable", "aggregate_removed", "outside_evaluable_area"]


def load_reference_implementation(scripts_dir: Path):
    spec = importlib.util.spec_from_file_location("apply_manual_review", scripts_dir / "apply_manual_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_manifest(release: Path):
    """Return (n_checked, mismatched, unlisted) for the release folder."""
    entries = [line.split(maxsplit=1) for line in (release / "MANIFEST.sha256").read_text().splitlines() if line.strip()]
    mismatched = [name for digest, name in entries
                  if hashlib.sha256((release / name).read_bytes()).hexdigest() != digest]
    listed = {name for _, name in entries}
    unlisted = sorted(str(p.relative_to(release)) for p in release.rglob("*")
                      if p.is_file() and p.name != "MANIFEST.sha256" and str(p.relative_to(release)) not in listed)
    return len(entries), mismatched, unlisted


def apply_release(ref_impl, release: Path, masks_dir: Path, log):
    """Per-object flags and per-ROI areas for every mask that has a release GeoJSON."""
    ref_areas = pd.read_csv(release / "summary" / "areas_per_core.csv").set_index("roi")
    sheet = glob.glob(str(release / "core_review" / "*.xlsx"))[0]
    core = (pd.read_excel(sheet, sheet_name="Core review").dropna(subset=["roi"]).set_index("roi")
            [ref_impl.SHEET_COLUMNS])
    all_cells, all_cores, skipped = [], [], []
    for path in sorted(glob.glob(str(masks_dir / "*.tif*"))):
        stem = os.path.basename(path).split(".")[0]
        roi = ref_impl.OLD_NAMES.get(stem, stem)
        geojson = release / "geojson" / f"{roi}.geojson"
        if not geojson.exists():
            skipped.append(os.path.basename(path))
            continue
        mask = tifffile.imread(path)
        if (mask.shape[0], mask.shape[1]) != (ref_areas.loc[roi, "height_px"], ref_areas.loc[roi, "width_px"]):
            raise ValueError(f"{roi}: mask {mask.shape} differs from the image size in the release")
        cells, areas = ref_impl.classify_cells(mask, str(geojson))
        cells.insert(0, "mask_file", os.path.basename(path))
        cells.insert(0, "Image", roi)
        all_cells.append(cells)
        counts = cells.cell_status.value_counts().reindex(STATUS, fill_value=0).to_dict()
        all_cores.append(dict(roi=roi, **areas, denominator_mm2=areas["denominator_px"] / 1e6,
                              denominator_matches_release=areas["denominator_px"] == ref_areas.loc[roi, "denominator_px"],
                              **counts))
        log(f"{roi}\tobjects={len(cells)}\t" + "\t".join(f"{k}={v}" for k, v in counts.items())
            + f"\tdenominator_px={areas['denominator_px']}")
    cells = pd.concat(all_cells, ignore_index=True)
    cores = pd.DataFrame(all_cores).set_index("roi").join(core).reset_index()
    return cells, cores, skipped


def check_cells_table(cells_csv: Path, flags: pd.DataFrame):
    table = pd.read_csv(cells_csv, usecols=["Image", "Object", "area"])
    table["Image"] = table["Image"].str.replace(r"\.tiff?$", "", regex=True)
    merged = table.merge(flags[["Image", "Object", "area_px"]], on=["Image", "Object"], how="outer", indicator=True)
    unmatched = int((merged["_merge"] != "both").sum())
    area_diff = int((merged.loc[merged["_merge"] == "both", "area"]
                     != merged.loc[merged["_merge"] == "both", "area_px"]).sum())
    return len(table), unmatched, area_diff


def compare_reference(reference_dir: Path, flags: pd.DataFrame, cores: pd.DataFrame):
    ref_flags = pd.read_csv(reference_dir / "cell_flags.csv")
    ref_cores = pd.read_csv(reference_dir / "core_areas.csv")
    merged = flags.merge(ref_flags, on=["Image", "Object"], how="outer", suffixes=("", "_ref"), indicator=True)
    both = merged["_merge"] == "both"
    result = {"objects": len(flags), "reference_objects": len(ref_flags), "unmatched": int((~both).sum())}
    for column in ["area_px", "in_evaluable_area", "cell_status"]:
        result[f"{column}_differences"] = int((merged.loc[both, column] != merged.loc[both, column + "_ref"]).sum())
    for column in ["centroid_x", "centroid_y", "frac_in_evaluable", "frac_in_excluded"]:
        result[f"{column}_max_abs_difference"] = float((merged.loc[both, column] - merged.loc[both, column + "_ref"]).abs().max())
    result["core_table_identical"] = bool(cores.equals(ref_cores))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow-dir", default=".")
    ap.add_argument("--release", default="data/reference/manual_review/20261012_v1")
    ap.add_argument("--masks-dir", default="data/masks")
    ap.add_argument("--cells", default="data/cells.csv", help="exported single-cell table to check against ('' to skip)")
    ap.add_argument("--output-dir", default="data/manual_review")
    ap.add_argument("--numbered-cell-flags", default="results/11_cell_flags.csv", help="'' to skip")
    ap.add_argument("--numbered-core-areas", default="results/11_core_areas.csv", help="'' to skip")
    ap.add_argument("--reference-dir", default="", help="reviewer's result on the same masks, for comparison")
    ap.add_argument("--log-file", default="logs/10_apply_manual_review.log")
    args = ap.parse_args()

    wd = Path(args.workflow_dir).resolve()
    resolve = lambda p: (wd / p) if p and not Path(p).is_absolute() else (Path(p) if p else None)
    release, masks_dir, out_dir = resolve(args.release), resolve(args.masks_dir), resolve(args.output_dir)
    log_path = resolve(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a")

    def log(line=""):
        print(line)
        log_handle.write(line + "\n")

    import rasterio
    import shapely
    log("MANUAL REVIEW APPLICATION")
    log(f"run_started: {dt.datetime.now().isoformat(timespec='seconds')}")
    log(f"host: {socket.gethostname()}")
    log(f"python: {platform.python_version()}; numpy: {np.__version__}; pandas: {pd.__version__}; "
        f"shapely: {shapely.__version__}; rasterio: {rasterio.__version__}")
    log(f"release: {release}")
    log(f"masks_dir: {masks_dir}")
    log(f"output_dir: {out_dir}")

    n_checked, mismatched, unlisted = verify_manifest(release)
    log(f"manifest: {n_checked} files checked; mismatches: {mismatched or 'none'}; unlisted files: {unlisted or 'none'}")
    if mismatched or unlisted:
        log("STOP: the release differs from its manifest")
        sys.exit(1)

    ref_impl = load_reference_implementation(Path(__file__).resolve().parent)
    log("rules: scripts/apply_manual_review.py (reviewer's reference implementation, unchanged)")
    log("")
    flags, cores, skipped = apply_release(ref_impl, release, masks_dir, log)
    log("")
    log(f"skipped (no release GeoJSON): {skipped or 'none'}")

    flags.to_csv(out_dir / "cell_flags.csv", index=False)
    cores.to_csv(out_dir / "core_areas.csv", index=False)
    for numbered, frame in [(args.numbered_cell_flags, flags), (args.numbered_core_areas, cores)]:
        if numbered:
            resolve(numbered).parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(resolve(numbered), index=False)

    log(f"ROIs: {len(cores)}; objects: {len(flags)}; " + str(flags.cell_status.value_counts().reindex(STATUS).to_dict()))
    bad = cores.loc[~cores.denominator_matches_release, "roi"].tolist()
    log("denominator identical to the release in every ROI" if not bad else f"DENOMINATOR MISMATCH: {bad}")

    included = cores["evaluable_for_IMC"] == "yes"
    totals = cores.loc[included, STATUS].sum()
    log(f"included cores (evaluable_for_IMC = yes): {int(included.sum())}; objects: {int(totals.sum())}; "
        f"denominator_mm2: {cores.loc[included, 'denominator_mm2'].sum():.2f}")
    log("  " + "; ".join(f"{k}={v} ({100 * v / totals.sum():.2f}%)" for k, v in totals.items()))

    failed = bool(bad)
    if args.cells:
        n_table, unmatched, area_diff = check_cells_table(resolve(args.cells), flags)
        log(f"cells table check: {n_table} objects in {args.cells}; unmatched: {unmatched}; area differences: {area_diff}")
        failed |= bool(unmatched or area_diff)
    if args.reference_dir:
        comparison = compare_reference(resolve(args.reference_dir), flags, cores)
        log("reference comparison: " + "; ".join(f"{k}={v}" for k, v in comparison.items()))
        failed |= bool(comparison["unmatched"] or comparison["cell_status_differences"]
                       or comparison["area_px_differences"] or not comparison["core_table_identical"])
    log(f"run_finished: {dt.datetime.now().isoformat(timespec='seconds')}; checks_failed={failed}")
    log("")
    log_handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
