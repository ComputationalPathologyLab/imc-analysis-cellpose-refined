"""Before/after hot-pixel filter: pixel window and per-cell comparison for one ROI and marker."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, tifffile
OLD = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/260812_imcAnalysis_cellpose_AllImages/data")
NEW = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/261007_imcAnalysis_cellpose_Refined/data")
OUT = Path(sys.argv[1]); ROI = sys.argv[2]; MARKER = sys.argv[3]
names = pd.read_csv(NEW / "panel.csv").name.tolist(); k = names.index(MARKER)
old_img = tifffile.imread(OLD / f"img/{ROI}.tiff")[k].astype(int)
new_img = tifffile.imread(NEW / f"img/{ROI}.tiff")[k].astype(int)
# 1 every pixel the filter changed
ys, xs = np.nonzero(old_img != new_img)
px = pd.DataFrame({"row": ys, "column": xs, "before": old_img[ys, xs], "after": new_img[ys, xs]})
px["removed"] = px.before - px.after
px.sort_values("removed", ascending=False).to_csv(OUT / f"{ROI}_{MARKER}_changed_pixels.csv", index=False)
# 2 the 5x5 window around the biggest spike, before and after
y, x = px.sort_values("removed", ascending=False).iloc[0][["row", "column"]].astype(int)
win = lambda a: pd.DataFrame(a[y - 2:y + 3, x - 2:x + 3], index=[f"row {r}" for r in range(y - 2, y + 3)], columns=[f"col {c}" for c in range(x - 2, x + 3)])
with open(OUT / f"{ROI}_{MARKER}_spike_window.csv", "w") as f:
    f.write(f"BEFORE (old stack, no filter)\n"); win(old_img).to_csv(f)
    f.write(f"\nAFTER (new stack, hot-pixel filter)\n"); win(new_img).to_csv(f)
# 3 per cell: match old and new objects by largest pixel overlap
om = tifffile.imread(OLD / f"masks/{ROI}.tiff"); nm = tifffile.imread(NEW / f"masks/{ROI}.tiff")
both = (om > 0) & (nm > 0)
pairs = pd.DataFrame({"old_object": om[both], "new_object": nm[both]}).value_counts().rename("shared_px").reset_index()
pairs = pairs.sort_values("shared_px", ascending=False).drop_duplicates("new_object").drop_duplicates("old_object")
oi = pd.read_csv(OLD / f"intensities/{ROI}.csv").set_index("Object"); ni = pd.read_csv(NEW / f"intensities/{ROI}.csv").set_index("Object")
oa = pd.Series(om[om > 0]).value_counts(); na = pd.Series(nm[nm > 0]).value_counts()
pairs["old_area"] = pairs.old_object.map(oa); pairs["new_area"] = pairs.new_object.map(na)
pairs[f"{MARKER}_before"] = pairs.old_object.map(oi[MARKER]).round(3)
pairs[f"{MARKER}_after"] = pairs.new_object.map(ni[MARKER]).round(3)
pairs["change"] = (pairs[f"{MARKER}_after"] - pairs[f"{MARKER}_before"]).round(3)
pairs = pairs[pairs.shared_px >= 0.8 * pairs[["old_area", "new_area"]].max(axis=1)]   # same cell in both runs
pairs.sort_values("change").to_csv(OUT / f"{ROI}_{MARKER}_cells_before_after.csv", index=False)
print(f"{len(px)} pixels changed; biggest spike at row {y}, col {x}: {old_img[y, x]} -> {new_img[y, x]}")
print(f"{len(pairs)} cells matched between runs; cells whose {MARKER} dropped by more than 1:", int((pairs.change < -1).sum()))
print(pairs.sort_values("change").head(5).to_string(index=False))
