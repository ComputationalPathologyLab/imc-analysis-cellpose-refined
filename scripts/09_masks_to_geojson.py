"""Write the cell outlines of every ROI as a QuPath GeoJSON, classified by the manual review `cell_status`.

For visual review only: the files can be dragged onto the matching image in QuPath, on top of the manual review
GeoJSON (`Evaluable_area` + excluded polygons), to see which cells the review keeps or removes. Nothing downstream
reads them.

Per ROI, one feature per mask label:
- geometry: outer boundary of the label (marching squares at level 0.5), in pixel coordinates with the QuPath
  convention (x = column, y = row, pixel (r, c) covers [c, c + 1] x [r, r + 1]);
- `objectType` detection (drawn as outlines), `name` "cell <Object>";
- `classification`: `cell_status` from `data/manual_review/cell_flags.csv` (script 10), with a fixed colour:
  clean = light blue, phenotype_not_assessable = orange, aggregate_removed = red, outside_evaluable_area = grey;
- `measurements`: area_px, frac_in_excluded (from cell_flags.csv).

Requires script 10 to have been run (it reads its cell_flags.csv).

Usage (from the workflow directory):
    python scripts/09_masks_to_geojson.py --workflow-dir .
    python scripts/09_masks_to_geojson.py --workflow-dir . --rois ROI001_E10 ROI003_C4
"""
import argparse
import datetime as dt
import json
import platform
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import skimage
import tifffile
from skimage.measure import find_contours, regionprops

COLORS = {"clean": [0, 200, 255], "phenotype_not_assessable": [255, 165, 0],
          "aggregate_removed": [255, 0, 0], "outside_evaluable_area": [160, 160, 160]}


def outline(region) -> list:
    """Outer boundary of one label as a closed ring of [x, y] in image pixel coordinates."""
    sub = np.pad(region.image, 1).astype(float)
    contour = max(find_contours(sub, 0.5), key=len)
    r0, c0 = region.bbox[0] - 1, region.bbox[1] - 1  # offset of the padded crop
    ring = [[float(c + c0 + 0.5), float(r + r0 + 0.5)] for r, c in contour]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def roi_to_geojson(mask: np.ndarray, flags: pd.DataFrame) -> tuple[dict, int]:
    flags = flags.set_index("Object")
    features, missing = [], 0
    for region in regionprops(mask):
        if region.label not in flags.index:
            missing += 1
            continue
        f = flags.loc[region.label]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [outline(region)]},
            "properties": {"objectType": "detection", "name": f"cell {region.label}",
                           "classification": {"name": f.cell_status, "color": COLORS[f.cell_status]},
                           "measurements": {"area_px": int(f.area_px),
                                            "frac_in_excluded": float(f.frac_in_excluded)}},
        })
    return {"type": "FeatureCollection", "features": features}, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow-dir", default=".")
    ap.add_argument("--masks-dir", default="data/masks")
    ap.add_argument("--cell-flags", default="data/manual_review/cell_flags.csv")
    ap.add_argument("--output-dir", default="data/masksToGeojson")
    ap.add_argument("--rois", nargs="*", default=None, help="subset of ROIs (default: all in cell_flags.csv)")
    ap.add_argument("--log-file", default="logs/09_masks_to_geojson.log")
    args = ap.parse_args()

    wd = Path(args.workflow_dir).resolve()
    resolve = lambda p: (wd / p) if not Path(p).is_absolute() else Path(p)
    out_dir, log_path = resolve(args.output_dir), resolve(args.log_file)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a")

    def log(line=""):
        print(line)
        handle.write(line + "\n")

    log("MASKS TO GEOJSON (cells classified by cell_status)")
    log(f"run_started: {dt.datetime.now().isoformat(timespec='seconds')}")
    log(f"host: {socket.gethostname()}; python: {platform.python_version()}; numpy: {np.__version__}; "
        f"pandas: {pd.__version__}; scikit-image: {skimage.__version__}")

    flags = pd.read_csv(resolve(args.cell_flags))
    rois = args.rois or sorted(flags["Image"].unique())
    failed = []
    for i, roi in enumerate(rois, start=1):
        try:
            roi_flags = flags[flags["Image"] == roi]
            mask = tifffile.imread(resolve(args.masks_dir) / roi_flags["mask_file"].iloc[0])
            geojson, missing = roi_to_geojson(mask, roi_flags)
            (out_dir / f"{roi}_cells_by_status.geojson").write_text(json.dumps(geojson))
            counts = roi_flags["cell_status"].value_counts().to_dict()
            log(f"[{i}/{len(rois)}] {roi}: {len(geojson['features'])}/{len(roi_flags)} cells written; "
                f"labels not in cell_flags: {missing}; {counts}")
            if len(geojson["features"]) != len(roi_flags) or missing:
                failed.append(roi)
        except Exception as e:
            failed.append(roi)
            log(f"[{i}/{len(rois)}] {roi}: FAILED - {e}")

    log(f"rois: {len(rois)}; failed or incomplete: {len(failed)} {failed if failed else ''}")
    log(f"run_finished: {dt.datetime.now().isoformat(timespec='seconds')}")
    log("")
    handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
