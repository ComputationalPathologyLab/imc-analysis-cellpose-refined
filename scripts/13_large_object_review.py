"""Apply the pathologist's large-object review to the current masks (review item 4.2; guide section 6.4, step 3).

The pathologist (V.G., 05/10/2026) reviewed in QuPath every object larger than 400 px of the predecessor segmentation
and classified it as `LO_cell` (real large cell), `LO_non_cell` (not a cell, e.g. vessel wall), `LO_uncertain` or
`LO_merged` (none). Handling (guide, sections 4.2 and 6.4):
- `LO_cell`: kept;
- `LO_non_cell`: removed from every analysis (`lo_non_cell`);
- `LO_uncertain`: kept, flagged for sensitivity analysis S4 (`s4_lo_uncertain`);
- the `Core_not_evaluable` marks of that review are superseded by the core review sheet (core selection, script 12);
  the unclassified large objects of ROI046_J3 are skeletal muscle fibres and are treated as `LO_cell`
  (`--superseded-cores-as-lo-cell`).

Because the masks were regenerated, every reviewed polygon is matched again to the current mask label by position:
the label covering most of the polygon, accepted if IoU > 0.5. A polygon moved in QuPath (no match) is matched through
the original, unedited polygon of the same name, if that name is unique and the areas agree within 5%. This is the
matching rule of the reviewer's script `check_large_objects_review.py`.

Objects larger than --min-area px in the current masks that no reviewed polygon matches are listed (and written as
GeoJSON for QuPath); they are kept as cells until classified.

With `--reference-classes` the matching is first checked against the reviewer's own table on the predecessor masks
(use `--masks-dir` with the predecessor masks).

With `--annotations` the cell annotation table of script 12 is extended in place with `large_object_class`,
`lo_non_cell`, `s4_lo_uncertain`, and `counted` / `phenotypable` are recomputed (LO_non_cell excluded from both); the
per-core table (`--core-table`) is updated accordingly. The update is idempotent.

Usage (from the workflow directory):
    python scripts/13_large_object_review.py --workflow-dir .
"""
import argparse
import collections
import datetime as dt
import json
import platform
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage as ndi
from skimage.draw import polygon as skpoly
from skimage.measure import find_contours

LEGACY = {"LO_cellula": "LO_cell", "LO_fuse": "LO_merged", "LO_non_cellula": "LO_non_cell",
          "LO_incerto": "LO_uncertain", "Core_non_valutabile": "Core_not_evaluable"}
LO_CLASSES = {"LO_cell", "LO_merged", "LO_non_cell", "LO_uncertain"}
OLD_NAMES = {f"ROI{k:03d}_ROI_{k:03d}": new for k, new in zip(
    range(32, 42), ["ROI032_I13", "ROI033_G12", "ROI034_G13", "ROI035_C1", "ROI036_K6",
                    "ROI037_F10", "ROI038_E15", "ROI039_F14", "ROI040_D7", "ROI041_D5"])}
COUNTED = ["clean", "phenotype_not_assessable"]


def cls(feature):
    c = feature.get("properties", {}).get("classification")
    name = c.get("name") if isinstance(c, dict) else c
    return LEGACY.get(name, name)


def ring_of(feature):
    g = feature["geometry"]
    return np.array(g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"][0][0])


def match_label(feature, mask, areas, iou_min):
    """Mask label covered by the polygon with IoU > iou_min, otherwise 0. Coordinates are (x, y) = (column, row)."""
    ring = ring_of(feature)
    rr, cc = skpoly(ring[:, 1], ring[:, 0], shape=mask.shape)
    labels, counts = np.unique(mask[rr, cc], return_counts=True)
    ok = labels > 0
    if not ok.any():
        return 0, 0.0, len(rr)
    lab, inter = int(labels[ok][counts[ok].argmax()]), int(counts[ok].max())
    iou = inter / (len(rr) + areas[lab] - inter)
    return (lab if iou > iou_min else 0), float(iou), len(rr)


def label_polygon(mask, lab):
    ys, xs = np.nonzero(mask == lab)
    y0, x0 = ys.min(), xs.min()
    sub = np.pad(mask[y0:ys.max() + 1, x0:xs.max() + 1] == lab, 1)
    contour = max(find_contours(sub.astype(float), 0.5), key=len)
    ring = [[float(c + x0 - 1), float(r + y0 - 1)] for r, c in contour]
    return ring + [ring[0]]


def find_mask(masks_dir: Path, roi: str):
    for name in [roi] + [old for old, new in OLD_NAMES.items() if new == roi]:
        path = masks_dir / f"{name}.tiff"
        if path.exists():
            return path
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow-dir", default=".")
    ap.add_argument("--review-dir", default="data/reference/large_objects")
    ap.add_argument("--masks-dir", default="data/masks")
    ap.add_argument("--img-dir", default="data/img", help="for descriptive S100/aSMA/nuclei per object ('' to skip)")
    ap.add_argument("--panel", default="data/panel.csv")
    ap.add_argument("--superseded-cores-as-lo-cell", nargs="*", default=["ROI046_J3"])
    ap.add_argument("--min-area", type=int, default=400)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--reference-classes", default="", help="reviewer's table on the same masks, for validation")
    ap.add_argument("--annotations", default="data/cell_annotations/cell_annotations.csv", help="'' to skip")
    ap.add_argument("--core-table", default="data/cell_annotations/core_table.csv", help="'' to skip")
    ap.add_argument("--output-dir", default="data/large_objects")
    ap.add_argument("--numbered-copy", default="results/14_large_object_classes.csv", help="'' to skip")
    ap.add_argument("--unreviewed-geojson-dir", default="results/14_unreviewed_large_objects", help="'' to skip")
    ap.add_argument("--log-file", default="logs/13_large_object_review.log")
    args = ap.parse_args()

    wd = Path(args.workflow_dir).resolve()
    resolve = lambda p: (wd / p) if p and not Path(p).is_absolute() else (Path(p) if p else None)
    review_dir, masks_dir, out_dir = resolve(args.review_dir), resolve(args.masks_dir), resolve(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = resolve(args.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a")

    def log(line=""):
        print(line)
        handle.write(line + "\n")

    log("LARGE-OBJECT REVIEW")
    log(f"run_started: {dt.datetime.now().isoformat(timespec='seconds')}")
    log(f"host: {socket.gethostname()}; python: {platform.python_version()}; numpy: {np.__version__}; pandas: {pd.__version__}")
    log(f"masks_dir: {masks_dir}; min_area: > {args.min_area} px; IoU > {args.iou}; "
        f"superseded cores treated as LO_cell: {args.superseded_cores_as_lo_cell}")
    failed = False

    img_dir = resolve(args.img_dir) if args.img_dir else None
    ix = {n: i for i, n in enumerate(pd.read_csv(resolve(args.panel))["name"])}

    rows, unmatched_rows, moved, unreviewed_rows = [], [], [], []
    reviewed_rois = set()
    for path in sorted((review_dir / "large_objects_reviewed").glob("*.geojson")):
        roi = path.name.split(".")[0]
        reviewed_rois.add(roi)
        feats = json.loads(path.read_text()).get("features", [])
        original_path = review_dir / "large_objects_geojson" / f"{roi}.geojson"
        originals = json.loads(original_path.read_text())["features"] if original_path.exists() else []
        mask_path = find_mask(masks_dir, roi)
        mask = tifffile.imread(mask_path)
        areas = np.bincount(mask.ravel())
        superseded = "Core_not_evaluable" in [cls(f) for f in feats]
        by_name = {f["properties"].get("name"): f for f in originals}
        name_count = collections.Counter(f["properties"].get("name") for f in feats)
        for f in feats:
            c = cls(f)
            if c == "Core_not_evaluable":
                continue
            source = "review"
            if c not in LO_CLASSES:
                if superseded and roi in args.superseded_cores_as_lo_cell:
                    c, source = "LO_cell", "guide 4.2 (muscle fibres; Core_not_evaluable superseded)"
                else:
                    continue          # unclassified objects of the other superseded cores (row K, excluded cores)
            lab, iou, n_px = match_label(f, mask, areas, args.iou)
            name = f["properties"].get("name")
            if lab == 0 and name_count[name] == 1 and name in by_name:
                lab_o, iou_o, n_o = match_label(by_name[name], mask, areas, args.iou)
                if lab_o and abs(n_o - n_px) <= 0.05 * n_o:
                    moved.append(f"{roi}: '{name}' moved in QuPath -> matched through the original polygon to object {lab_o}")
                    lab, iou = lab_o, iou_o
            if lab == 0:
                unmatched_rows.append(dict(roi=roi, polygon_name=name, review_class=c, polygon_area=n_px,
                                           best_iou=round(iou, 3)))
                continue
            rows.append(dict(roi=roi, Object=lab, review_class=c, class_source=source, iou=round(iou, 3),
                             area=int(areas[lab])))

    classes = pd.DataFrame(rows, columns=["roi", "Object", "review_class", "class_source", "iou", "area"])
    conflicts = classes.groupby(["roi", "Object"])["review_class"].nunique()
    conflicts = conflicts[conflicts > 1]
    classes = classes.drop_duplicates(["roi", "Object"], keep="first")
    if img_dir:
        extra = []
        for roi, sub in classes.groupby("roi"):
            mask = tifffile.imread(find_mask(masks_dir, roi))
            with tifffile.TiffFile(img_dir / f"{roi}.tiff") as t:
                dna = np.maximum(t.pages[ix["DNA1"]].asarray(), t.pages[ix["DNA2"]].asarray()).astype(np.float32)
                asma = t.pages[ix["aSMA"]].asarray().astype(np.float32)
                s100 = t.pages[ix["S100"]].asarray().astype(np.float32)
            nuc = ndi.uniform_filter(dna, 3) > 8
            for obj in sub["Object"]:
                m = mask == obj
                extra.append(dict(roi=roi, Object=obj, nuclei=ndi.label(nuc & m)[1],
                                  S100=round(float(s100[m].mean()), 2), aSMA=round(float(asma[m].mean()), 2)))
        classes = classes.merge(pd.DataFrame(extra), on=["roi", "Object"], how="left")

    # objects above the size limit that the review does not cover (all cores)
    matched = set(zip(classes["roi"], classes["Object"]))
    geo_dir = resolve(args.unreviewed_geojson_dir) if args.unreviewed_geojson_dir else None
    if geo_dir:
        geo_dir.mkdir(parents=True, exist_ok=True)
        for old in geo_dir.glob("*.geojson"):
            old.unlink()
    for mask_path in sorted(masks_dir.glob("*.tiff")):
        roi = OLD_NAMES.get(mask_path.stem, mask_path.stem)
        if roi.endswith("_masks"):
            continue
        mask = tifffile.imread(mask_path)
        areas = np.bincount(mask.ravel())
        large = [int(l) for l in np.nonzero(areas > args.min_area)[0] if l > 0 and (roi, int(l)) not in matched]
        for l in large:
            unreviewed_rows.append(dict(roi=roi, Object=l, area=int(areas[l]), core_reviewed=roi in reviewed_rois))
        if geo_dir and large:
            fc = {"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"objectType": "annotation", "name": f"object {l} - {int(areas[l])} px",
                                                   "classification": {"name": "Large_object", "color": [255, 160, 0]}},
                 "geometry": {"type": "Polygon", "coordinates": [label_polygon(mask, l)]}} for l in large]}
            (geo_dir / f"{roi}.geojson").write_text(json.dumps(fc))
    unmatched = pd.DataFrame(unmatched_rows, columns=["roi", "polygon_name", "review_class", "polygon_area", "best_iou"])
    unreviewed = pd.DataFrame(unreviewed_rows, columns=["roi", "Object", "area", "core_reviewed"])

    classes.to_csv(out_dir / "large_object_classes.csv", index=False)
    unmatched.to_csv(out_dir / "unmatched_polygons.csv", index=False)
    unreviewed.to_csv(out_dir / "unreviewed_large_objects.csv", index=False)
    if args.numbered_copy:
        classes.to_csv(resolve(args.numbered_copy), index=False)

    log(f"reviewed cores: {len(reviewed_rois)}; matched objects: {len(classes)} "
        f"{classes['review_class'].value_counts().to_dict()}; from the guide rule: "
        f"{int((classes['class_source'] != 'review').sum())}")
    log(f"unmatched polygons: {len(unmatched)}; conflicting classes on one object: {len(conflicts)}")
    for _, r in unmatched.iterrows():
        log(f"  unmatched: {r.roi} '{r.polygon_name}' {r.review_class} ({r.polygon_area} px, best IoU {r.best_iou})")
    for line in moved:
        log("  " + line)
    if len(classes):
        log(f"IoU of matched objects: median {classes['iou'].median():.3f}; minimum {classes['iou'].min():.3f}")
    log(f"objects > {args.min_area} px not covered by the review: {len(unreviewed)} in {unreviewed['roi'].nunique()} cores")

    if args.reference_classes:
        ref = pd.read_csv(resolve(args.reference_classes)).rename(columns={"cell": "Object"})
        mine = classes[classes["class_source"] == "review"]
        merged = mine.merge(ref[["roi", "Object", "review_class"]], on=["roi", "Object"], how="outer",
                            suffixes=("", "_ref"), indicator=True)
        diff = int((merged["_merge"] != "both").sum() + (merged["review_class"] != merged["review_class_ref"]).sum())
        log(f"validation vs reference classes: reference {len(ref)}; reproduced {int((merged['_merge'] == 'both').sum())}; "
            f"differences {diff}")
        failed |= bool(diff)

    if args.annotations:
        ann_path = resolve(args.annotations)
        ann = pd.read_csv(ann_path).drop(columns=["large_object_class", "lo_non_cell", "s4_lo_uncertain"], errors="ignore")
        lo = classes[["roi", "Object", "review_class"]].rename(columns={"roi": "Image", "review_class": "large_object_class"})
        ann = ann.merge(lo, on=["Image", "Object"], how="left", validate="one_to_one")
        ann["large_object_class"] = ann["large_object_class"].fillna("")
        ann["lo_non_cell"] = ann["large_object_class"] == "LO_non_cell"
        ann["s4_lo_uncertain"] = ann["large_object_class"] == "LO_uncertain"
        ann["counted"] = ann["core_included"] & ann["cell_status"].isin(COUNTED) & ~ann["lo_non_cell"]
        ann["phenotypable"] = ann["core_included"] & (ann["cell_status"] == "clean") & ~ann["lo_non_cell"]
        ann.to_csv(ann_path, index=False)
        log(f"annotations updated: {ann_path.relative_to(wd) if ann_path.is_relative_to(wd) else ann_path}; "
            f"LO_non_cell objects {int(ann['lo_non_cell'].sum())} (in included cores, counted before this step: "
            f"{int((ann['lo_non_cell'] & ann['core_included'] & ann['cell_status'].isin(COUNTED)).sum())}); "
            f"LO_uncertain {int(ann['s4_lo_uncertain'].sum())}")
        log(f"included cores: counted {int(ann['counted'].sum())}; phenotypable {int(ann['phenotypable'].sum())}")
        if args.core_table:
            ct_path = resolve(args.core_table)
            ct = pd.read_csv(ct_path).drop(columns=["lo_non_cell_objects", "lo_uncertain_objects"], errors="ignore")
            # per core, independent of core inclusion: counted = clean or not assessable, and not LO_non_cell
            ann["_counted_core"] = ann["cell_status"].isin(COUNTED) & ~ann["lo_non_cell"]
            ann["_phenotypable_core"] = (ann["cell_status"] == "clean") & ~ann["lo_non_cell"]
            per = ann.groupby("Image").agg(lo_non_cell_objects=("lo_non_cell", "sum"),
                                           lo_uncertain_objects=("s4_lo_uncertain", "sum"),
                                           counted_cells_new=("_counted_core", "sum"),
                                           phenotypable_cells_new=("_phenotypable_core", "sum"))
            ct = ct.merge(per, left_on="roi", right_index=True, how="left")
            ct["counted_cells"] = ct.pop("counted_cells_new")
            ct["phenotypable_cells"] = ct.pop("phenotypable_cells_new")
            ct["counted_cells_per_mm2"] = ct["counted_cells"] / ct["denominator_mm2"]
            ct.to_csv(ct_path, index=False)
            log(f"core table updated: {ct_path.relative_to(wd) if ct_path.is_relative_to(wd) else ct_path}")

    log(f"run_finished: {dt.datetime.now().isoformat(timespec='seconds')}; checks_failed={failed}")
    log("")
    handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
