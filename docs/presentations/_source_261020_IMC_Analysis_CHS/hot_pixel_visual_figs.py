import sys
from pathlib import Path
import numpy as np, pandas as pd, tifffile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from scipy.ndimage import maximum_filter
from skimage.segmentation import find_boundaries
OUT = Path(sys.argv[1])
R = Path("/Users/rashid/1_IMC_Analysis/11_Vincenzo/261007_imcAnalysis_cellpose_Refined")
plt.rcParams.update({"font.family": "Arial", "font.size": 13, "axes.titlesize": 14})
PINK, TEAL, GREY, DARK = "#B5446E", "#2F6F73", "#9AA5B1", "#222222"
heat = LinearSegmentedColormap.from_list("h", ["#F4F5F7", "#F3D9B1", "#E9965A", "#C0392B"])
roi = "ROI018_B10"; raw = lambda f: tifffile.imread(R / f"data/raw/{roi}/{f}.ome.tiff").astype(float)
cd31_old = raw("144Nd_CD31"); names = pd.read_csv(R / "data/panel.csv").name.tolist()
cd31_new = tifffile.imread(R / f"data/img/{roi}.tiff")[names.index("CD31")].astype(float)
s100 = raw("164Dy_S100"); dna = raw("191Ir_DNA1"); mask = tifffile.imread(R / f"data/masks/{roi}.tiff")
Y, X = 665, 736
def save(fig, n): fig.savefig(OUT / n, dpi=200, bbox_inches="tight", facecolor="white"); plt.close(fig); print(n)

def numgrid(ax, a, vmax, centre=None, ring=False, star=None, fs=15, title=None):
    n = a.shape[0]
    ax.imshow(a, cmap=heat, norm=PowerNorm(0.45, vmin=0, vmax=vmax), interpolation="nearest")
    for i in range(n):
        for j in range(a.shape[1]):
            ax.text(j, i, f"{int(a[i, j])}", ha="center", va="center", fontsize=fs, color=DARK,
                    fontweight="bold" if centre == (i, j) else "normal")
    for k in range(n + 1): ax.axhline(k - .5, color="white", lw=2); ax.axvline(k - .5, color="white", lw=2)
    if centre: ax.add_patch(Rectangle((centre[1] - .5, centre[0] - .5), 1, 1, fill=False, ec=PINK, lw=3))
    if ring: ax.add_patch(Rectangle((centre[1] - 1.5, centre[0] - 1.5), 3, 3, fill=False, ec=TEAL, lw=2.5, ls="--"))
    if star: ax.add_patch(Circle((star[1], star[0]), .42, fill=False, ec=TEAL, lw=3))
    ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
    if title: ax.set_title(title, pad=8)

# 1 what a pixel holds: real image + histogram
fig, axes = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1, 1.25]})
c = cd31_old[Y - 40:Y + 40, X - 40:X + 40]
axes[0].imshow(np.clip(c / 8, 0, 1), cmap="magma", interpolation="nearest")
axes[0].add_patch(Circle((40, 40), 4, fill=False, ec="white", lw=1.8))
axes[0].annotate("816 ions", (43, 37), (55, 12), color="white", fontsize=14, arrowprops=dict(arrowstyle="-", color="white", lw=1.2))
axes[0].set_title("CD31, 80 × 80 µm of ROI018_B10"); axes[0].axis("off")
v = cd31_old.ravel(); lab = ["0", "1", "2", "3", "4", "5–9", "10–49", "≥ 50"]
cnt = [(v == 0).sum(), (v == 1).sum(), (v == 2).sum(), (v == 3).sum(), (v == 4).sum(), ((v >= 5) & (v < 10)).sum(), ((v >= 10) & (v < 50)).sum(), (v >= 50).sum()]
b = axes[1].bar(lab, cnt, color=[TEAL] * 7 + [PINK]); axes[1].set_yscale("log")
for r, n in zip(b, cnt): axes[1].text(r.get_x() + r.get_width() / 2, n * 1.2, f"{n:,}", ha="center", fontsize=11)
axes[1].set_xlabel("ions in one pixel"); axes[1].set_ylabel("pixels (of 1 million)")
axes[1].set_title("91% of pixels hold 0 ions")
for s in ["top", "right"]: axes[1].spines[s].set_visible(False)
plt.tight_layout(w_pad=3); save(fig, "v1.png")

# 2 the spike, before and after (7x7)
fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
numgrid(axes[0], cd31_old[Y - 3:Y + 4, X - 3:X + 4], 816, centre=(3, 3), fs=14, title="before the filter")
numgrid(axes[1], cd31_new[Y - 3:Y + 4, X - 3:X + 4], 816, centre=(3, 3), fs=14, title="after the filter")
fig.text(0.5, 0.5, "→", ha="center", va="center", fontsize=40, color=GREY)
save(fig, "v2.png")

# 3 hill vs needle
fig, axes = plt.subplots(2, 2, figsize=(12, 7.2), gridspec_kw={"height_ratios": [1.15, 1]})
sy, sx = 48, 749
numgrid(axes[0, 0], s100[sy - 2:sy + 3, sx - 2:sx + 3], s100[sy - 2:sy + 3, sx - 2:sx + 3].max(), centre=(2, 2), fs=14, title="S100: a stained cell")
numgrid(axes[0, 1], cd31_old[Y - 2:Y + 3, X - 2:X + 3], 816, centre=(2, 2), fs=14, title="CD31: a hot pixel")
for ax, a, cx, col, t in [(axes[1, 0], s100[sy, sx - 6:sx + 7], 6, TEAL, "a hill: bright over several pixels"), (axes[1, 1], cd31_old[Y, X - 6:X + 7], 6, PINK, "a needle: one pixel")]:
    ax.bar(range(len(a)), a, color=[col if i == cx else GREY for i in range(len(a))], width=0.85)
    ax.set_xticks([]); ax.set_ylabel("ions"); ax.set_title(t); [ax.spines[s].set_visible(False) for s in ["top", "right"]]
    ax.set_xlabel("pixels along one line through the centre")
plt.tight_layout(h_pad=2, w_pad=4); save(fig, "v3.png")

# 4 the rule, as a strip, two cases
fig, axes = plt.subplots(2, 4, figsize=(15, 7.4))
cases = [(cd31_old[Y - 1:Y + 2, X - 1:X + 2], "816 − 3 = 813, more than 50", "replaced by 3", cd31_new[Y - 1:Y + 2, X - 1:X + 2]),
         (s100[sy - 1:sy + 2, sx - 1:sx + 2], "158 − 110 = 48, not more than 50", "kept", s100[sy - 1:sy + 2, sx - 1:sx + 2])]
for row, (a, eq, verdict, after) in enumerate(cases):
    nb = a.copy(); nb[1, 1] = -1; by, bx = np.unravel_index(np.argmax(nb), nb.shape)
    vm = a.max()
    numgrid(axes[row, 0], a, vm, centre=(1, 1), fs=18, title="1. the pixel")
    numgrid(axes[row, 1], a, vm, centre=(1, 1), ring=True, fs=18, title="2. its 8 neighbours")
    numgrid(axes[row, 2], a, vm, centre=(1, 1), star=(by, bx), fs=18, title="3. the brightest one")
    numgrid(axes[row, 3], after, vm, centre=(1, 1), fs=18, title=f"4. {verdict}")
    axes[row, 3].text(1, 2.95, eq, ha="center", va="top", fontsize=13, color=PINK if row == 0 else TEAL)
fig.text(0.005, 0.73, "hot pixel\n(CD31)", fontsize=13, ha="left", va="center", color=PINK)
fig.text(0.005, 0.27, "real signal\n(S100)", fontsize=13, ha="left", va="center", color=TEAL)
plt.tight_layout(rect=(0.06, 0, 1, 1), h_pad=4); save(fig, "v4.png")

# 5 nucleus
ny, nx = 359, 471
fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"width_ratios": [1, 1.1]})
crop = dna[ny - 15:ny + 16, nx - 15:nx + 16]
axes[0].imshow(np.clip(crop / np.percentile(dna, 99.8), 0, 1), cmap="magma", interpolation="nearest")
axes[0].add_patch(Rectangle((15 - 2.5, 15 - 2.5), 5, 5, fill=False, ec="white", lw=1.6)); axes[0].axis("off")
axes[0].set_title("DNA1: a nucleus, 30 × 30 µm")
w = dna[ny - 2:ny + 3, nx - 2:nx + 3]; nb = w[1:4, 1:4].copy(); nb[1, 1] = -1; by, bx = np.unravel_index(np.argmax(nb), nb.shape)
numgrid(axes[1], w, w.max(), centre=(2, 2), star=(by + 1, bx + 1), fs=15, title="49 − 32 = 17  →  kept")
save(fig, "v5.png")

# 6 cell 606 before/after
ys, xs = np.nonzero(mask == 606); cy, cx = int(ys.mean()), int(xs.mean())
y0, x0 = cy - 6, cx - 6; m = (mask[y0:y0 + 13, x0:x0 + 13] == 606)
fig, axes = plt.subplots(1, 2, figsize=(13, 6.6))
for ax, img, t in [(axes[0], cd31_old, "before"), (axes[1], cd31_new, "after")]:
    a = img[y0:y0 + 13, x0:x0 + 13]
    ax.imshow(np.where(m, 1, 0), cmap=LinearSegmentedColormap.from_list("m", ["#FFFFFF", "#D7E8EA"]), interpolation="nearest")
    for i in range(13):
        for j in range(13):
            v_ = int(a[i, j]); big = v_ > 50
            ax.text(j, i, str(v_), ha="center", va="center", fontsize=13 if big else 10,
                    color=PINK if big else (DARK if m[i, j] else "#B8BEC6"), fontweight="bold" if big else "normal")
    for i in range(13):
        for j in range(13):
            if not m[i, j]: continue
            if i == 0 or not m[i - 1, j]: ax.plot([j - .5, j + .5], [i - .5, i - .5], color=TEAL, lw=2.2)
            if i == 12 or not m[i + 1, j]: ax.plot([j - .5, j + .5], [i + .5, i + .5], color=TEAL, lw=2.2)
            if j == 0 or not m[i, j - 1]: ax.plot([j - .5, j - .5], [i - .5, i + .5], color=TEAL, lw=2.2)
            if j == 12 or not m[i, j + 1]: ax.plot([j + .5, j + .5], [i - .5, i + .5], color=TEAL, lw=2.2)
    ax.set_xlim(-.5, 12.5); ax.set_ylim(12.5, -.5)
    tot = int(a[m].sum()); ax.set_title(f"{t}:  {tot} ions ÷ {int(m.sum())} pixels = {tot / m.sum():.2f}", fontsize=15, color=PINK if t == "before" else TEAL)
    ax.set_xticks([]); ax.set_yticks([]); [s.set_visible(False) for s in ax.spines.values()]
print("cell 606 sums", int(cd31_old[mask == 606].sum()), int(cd31_new[mask == 606].sum()), int(m.sum()), int((mask == 606).sum()))
save(fig, "v6.png")

# 7 where: whole core + per-channel bars
fp = np.ones((3, 3), bool); fp[1, 1] = False
hot = (cd31_old - maximum_filter(cd31_old, footprint=fp, mode="mirror")) > 50
hy, hx = np.nonzero(hot); inside = mask[hy, hx] > 0
fig, axes = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1, 1.05]})
axes[0].imshow(np.clip(cd31_old / 6, 0, 1), cmap="gray", interpolation="nearest", alpha=0.85)
axes[0].contour((mask > 0).astype(float), levels=[.5], colors="#4A5560", linewidths=0.3)
axes[0].scatter(hx[~inside], hy[~inside], s=110, facecolors="none", edgecolors="#F3D9B1", linewidths=1.6, label=f"outside cells ({(~inside).sum()})")
axes[0].scatter(hx[inside], hy[inside], s=150, facecolors="none", edgecolors=PINK, linewidths=2.4, label=f"inside a cell ({inside.sum()})")
axes[0].legend(loc="lower left", fontsize=11, framealpha=0.9); axes[0].axis("off")
axes[0].set_title(f"CD31 hot pixels in ROI018_B10: {hot.sum()}")
t = {}; on = False
for line in open(R / "logs/02_preprocess_imc_images.log"):
    if line.startswith("HOT_PIXELS_REPLACED_TOTAL_PER_CHANNEL"): on = True; continue
    if on and "=" in line: k, v_ = line.strip().split("="); t[k] = int(v_)
tech = {"127I", "131Xe", "134Xe", "138Ba", "208Pb", "80ArAr"}
ab = pd.Series({k: v_ for k, v_ in t.items() if k not in tech}).sort_values().tail(10)
axes[1].barh(ab.index, ab.values, color=PINK)
for i, v_ in enumerate(ab.values): axes[1].text(v_ + 80, i, f"{v_:,}", va="center", fontsize=11)
axes[1].set_title(f"all 136 ROIs: {sum(v_ for k, v_ in t.items() if k not in tech):,} hot pixels")
axes[1].set_xlabel("pixels replaced"); [axes[1].spines[s].set_visible(False) for s in ["top", "right"]]
plt.tight_layout(w_pad=3); save(fig, "v7.png")

# 8 routes
fig, ax = plt.subplots(figsize=(14, 5.2)); ax.set_xlim(0, 14); ax.set_ylim(0, 6); ax.axis("off")
def box(x, y, w, t, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, 1.0, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.5)); ax.text(x + w / 2, y + .5, t, ha="center", va="center", fontsize=13)
def arrow(x0, x1, y): ax.annotate("", (x1, y + .5), (x0, y + .5), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.6))
rows = [(4.6, "usual steinbock", ".mcd file", "steinbock reads it\n+ hot-pixel filter", "43-channel image", "#EAF2F2", TEAL),
        (2.6, "our first run", "43 TIFFs\nfrom the facility", "our stacking script\n(no filter)", "43-channel image\nwith hot pixels", "#F6E9EF", PINK),
        (0.6, "now", "43 TIFFs\nfrom the facility", "our stacking script\n+ the same filter", "43-channel image", "#EAF2F2", TEAL)]
for y, lab_, a, b_, c_, fc, ec in rows:
    ax.text(0.1, y + .5, lab_, va="center", fontsize=14, color=ec, fontweight="bold")
    box(2.6, y, 2.8, a, "#F2F3F5", "#D9DDE3"); arrow(5.5, 6.3, y); box(6.4, y, 3.4, b_, fc, ec); arrow(9.9, 10.7, y); box(10.8, y, 3.0, c_, fc if ec == PINK else "#F2F3F5", ec if ec == PINK else "#D9DDE3")
save(fig, "v8.png")
