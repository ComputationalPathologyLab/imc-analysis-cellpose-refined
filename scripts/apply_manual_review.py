"""Apply the manual review release (Manual_Review/releases/<name>/) to a cell segmentation.

For every segmented object it decides whether it belongs to the core and whether it can be phenotyped; for every ROI
it computes the density denominator. The rules are those of the release README and of the rules document
(rules/20261010 Annotation_class_rules.md):
1. a cell belongs to the core if its centroid is inside the Evaluable_area polygon;
2. for the cells that belong to the core, the fraction of their pixels inside the excluded areas (union of all the
   other classes) decides: 0 -> clean; > 0 and <= 0.75 -> counted, phenotype not assessable; > 0.75 -> aggregate,
   removed from everything;
3. denominator = Evaluable_area minus the excluded areas, in pixels (1 px = 1 um^2).
Polygons are rasterized with the pixel-center convention (rasterio all_touched=False).

Usage:
    python apply_manual_review.py <release dir> <masks dir> <out dir>

<masks dir>: one label image per ROI (TIFF; 0 = background, k = object k = column 'Object' of cells.csv), named
<ROI>.tiff. The old names ROI032_ROI_032 ... ROI041_ROI_041 are mapped to the TMA names used by the release.

Outputs in <out dir>:
- cell_flags.csv: Image (release ROI name), mask_file, Object, area_px, centroid_x, centroid_y (QuPath/GeoJSON
  coordinates: column + 0.5, row + 0.5), in_evaluable_area, frac_in_evaluable, frac_in_excluded, cell_status;
- core_areas.csv: one row per ROI: areas in px and mm^2, number of objects per cell_status, the key columns of the
  core review sheet, and the check of the denominator against the release (must be identical).

Needs: numpy, pandas, tifffile, shapely >= 2, rasterio, openpyxl.
"""
import glob, json, os, sys
import numpy as np, pandas as pd, tifffile
import shapely
from shapely.geometry import shape, mapping
from rasterio import features
from rasterio.transform import Affine

EXCLUDED = {"Artifacts_auto", "Artifacts_auto_large", "Artifacts_auto_low", "Artifacts_auto_faint", "Spot_auto",
            "Spot_auto_large", "Artifacts", "Necrosis", "Hemorrhage"}
OLD_NAMES = {f"ROI{k:03d}_ROI_{k:03d}": new for k, new in zip(
    range(32, 42), ["ROI032_I13", "ROI033_G12", "ROI034_G13", "ROI035_C1", "ROI036_K6",
                    "ROI037_F10", "ROI038_E15", "ROI039_F14", "ROI040_D7", "ROI041_D5"])}
STATUS = ["clean", "phenotype_not_assessable", "aggregate_removed", "outside_evaluable_area"]
SHEET_COLUMNS = ["facility_position", "patient_id", "region", "dna_status", "he_core", "evaluable_for_IMC",
                 "exclusion_reason", "matrix_pct", "special_area_flag"]


def class_name(feature):
    return (feature["properties"].get("classification") or {}).get("name")


def load_polygons(geojson_path):
    """Return (Evaluable_area polygon, list of excluded polygons) of one ROI."""
    feats = json.load(open(geojson_path))["features"]
    unknown = {class_name(f) for f in feats} - EXCLUDED - {"Evaluable_area"}
    if unknown:
        raise ValueError(f"{geojson_path}: unknown classes {unknown}")
    evaluable = [shape(f["geometry"]) for f in feats if class_name(f) == "Evaluable_area"]
    if len(evaluable) != 1:
        raise ValueError(f"{geojson_path}: {len(evaluable)} Evaluable_area polygons, expected 1")
    return evaluable[0], [shape(f["geometry"]) for f in feats if class_name(f) in EXCLUDED]


def rasterize(geoms, shape_yx):
    """Boolean image: True where the pixel center is inside at least one polygon."""
    if not geoms:
        return np.zeros(shape_yx, bool)
    return features.rasterize(((mapping(g), 1) for g in geoms), out_shape=shape_yx, transform=Affine.identity(),
                              all_touched=False, dtype="uint8").astype(bool)


def classify_cells(mask, geojson_path):
    """Per-object flags and the denominator for one ROI. mask: 2-D label image (rows x columns)."""
    evaluable, excluded = load_polygons(geojson_path)
    ev = rasterize([evaluable], mask.shape)
    ex = rasterize(excluded, mask.shape)
    lab = mask.ravel().astype(np.int64)
    n = int(lab.max()) + 1
    area = np.bincount(lab, minlength=n)
    rows, cols = np.indices(mask.shape)
    with np.errstate(invalid="ignore", divide="ignore"):
        cy = np.bincount(lab, weights=rows.ravel(), minlength=n) / area     # mean row index = regionprops centroid-0
        cx = np.bincount(lab, weights=cols.ravel(), minlength=n) / area     # mean column index = centroid-1
        f_ev = np.bincount(lab, weights=ev.ravel(), minlength=n) / area
        f_ex = np.bincount(lab, weights=ex.ravel(), minlength=n) / area
    ids = np.nonzero(area)[0]
    ids = ids[ids > 0]
    x, y = cx[ids] + 0.5, cy[ids] + 0.5                                       # pixel center convention
    inside = shapely.contains_xy(evaluable, x, y)
    status = np.select([~inside, f_ex[ids] > 0.75, f_ex[ids] > 0], STATUS[:0:-1], "clean")
    cells = pd.DataFrame(dict(Object=ids, area_px=area[ids], centroid_x=x.round(2), centroid_y=y.round(2),
                              in_evaluable_area=inside, frac_in_evaluable=f_ev[ids].round(4),
                              frac_in_excluded=f_ex[ids].round(4), cell_status=status))
    areas = dict(height_px=mask.shape[0], width_px=mask.shape[1], evaluable_area_px=int(ev.sum()),
                 excluded_in_evaluable_px=int((ev & ex).sum()), denominator_px=int((ev & ~ex).sum()))
    return cells, areas


if __name__ == "__main__":
    release, masks_dir, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    ref = pd.read_csv(os.path.join(release, "summary", "areas_per_core.csv")).set_index("roi")
    sheet = glob.glob(os.path.join(release, "core_review", "*.xlsx"))[0]
    core = pd.read_excel(sheet, sheet_name="Core review").dropna(subset=["roi"]).set_index("roi")[SHEET_COLUMNS]
    all_cells, all_cores = [], []
    for path in sorted(glob.glob(os.path.join(masks_dir, "*.tif*"))):
        stem = os.path.basename(path).split(".")[0]
        roi = OLD_NAMES.get(stem, stem)
        geojson = os.path.join(release, "geojson", f"{roi}.geojson")
        if not os.path.exists(geojson):
            print(f"skipped {path}: no release GeoJSON for {roi}")
            continue
        mask = tifffile.imread(path)
        if (mask.shape[0], mask.shape[1]) != (ref.loc[roi, "height_px"], ref.loc[roi, "width_px"]):
            raise ValueError(f"{roi}: mask {mask.shape} differs from the image size in the release")
        cells, areas = classify_cells(mask, geojson)
        cells.insert(0, "mask_file", os.path.basename(path))
        cells.insert(0, "Image", roi)
        all_cells.append(cells)
        counts = cells.cell_status.value_counts().reindex(STATUS, fill_value=0).to_dict()
        all_cores.append(dict(roi=roi, **areas, denominator_mm2=areas["denominator_px"] / 1e6,
                              denominator_matches_release=areas["denominator_px"] == ref.loc[roi, "denominator_px"],
                              **counts))
    cells = pd.concat(all_cells, ignore_index=True)
    cores = pd.DataFrame(all_cores).set_index("roi").join(core).reset_index()
    cells.to_csv(os.path.join(out, "cell_flags.csv"), index=False)
    cores.to_csv(os.path.join(out, "core_areas.csv"), index=False)
    bad = cores.loc[~cores.denominator_matches_release, "roi"].tolist()
    print(f"{len(cores)} ROIs, {len(cells)} objects;", cells.cell_status.value_counts().to_dict())
    print("denominator identical to the release in every ROI" if not bad else f"DENOMINATOR MISMATCH: {bad}")
