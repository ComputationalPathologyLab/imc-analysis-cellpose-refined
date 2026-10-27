import json
import time
from pathlib import Path

import numpy as np
import tifffile
from skimage.measure import find_contours

MASKS_DIR = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/260812_imcAnalysis_cellpose_AllImages/data/masks")
OUT_DIR = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/260812_imcAnalysis_cellpose_AllImages/data/GeoJSON")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def mask_to_geojson(mask_path: Path) -> tuple[int, int]:
    mask = tifffile.imread(mask_path)
    labels = np.unique(mask)
    labels = labels[labels != 0]  # 0 = background

    features = []
    for lab in labels:
        ys, xs = np.where(mask == lab)
        y0, y1 = ys.min() - 1, ys.max() + 2
        x0, x1 = xs.min() - 1, xs.max() + 2
        sub = (mask[y0:y1, x0:x1] == lab)
        if sub.shape[0] < 2 or sub.shape[1] < 2:
            continue  # too small to trace an outline

        contours = find_contours(sub.astype(float), level=0.5)
        if not contours:
            continue
        contour = max(contours, key=len)  # outer boundary
        coords = [[float(x0 + c[1]), float(y0 + c[0])] for c in contour]
        if coords[0] != coords[-1]:
            coords.append(coords[0])  # GeoJSON polygons must close

        features.append({
            "type": "Feature",
            "properties": {"objectType": "detection", "cell_label": int(lab)},
            "geometry": {"type": "Polygon", "coordinates": [coords]},
        })

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = OUT_DIR / (mask_path.stem + ".geojson")
    with open(out_path, "w") as f:
        json.dump(geojson, f)

    return len(features), len(labels)


def main():
    mask_files = sorted(MASKS_DIR.glob("*.tiff"))
    print(f"Found {len(mask_files)} mask files in {MASKS_DIR}")

    t0 = time.time()
    ok, failed = 0, []
    for i, mask_path in enumerate(mask_files, start=1):
        try:
            n_features, n_labels = mask_to_geojson(mask_path)
            ok += 1
            print(f"[{i}/{len(mask_files)}] {mask_path.name}: {n_features}/{n_labels} cells "
                  f"({time.time()-t0:.0f}s elapsed)")
        except Exception as e:
            failed.append((mask_path.name, str(e)))
            print(f"[{i}/{len(mask_files)}] {mask_path.name}: FAILED - {e}")

    print(f"\nDone in {time.time()-t0:.0f}s. {ok} converted, {len(failed)} failed.")
    if failed:
        print("Failed files:")
        for name, err in failed:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
