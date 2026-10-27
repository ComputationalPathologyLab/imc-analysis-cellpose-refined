#!/usr/bin/env python3
"""Apply conservative TMA-core masking to IMC stacks.

This script replaces the earlier corner-subtraction idea with a safer strategy:
derive a tissue/core mask from the marker stack, dilate it slightly, and set
pixels outside the core to zero. This removes obvious background around the TMA
core without altering intensities inside the retained tissue region.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path.cwd() / ".cache"))

import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops
from skimage.morphology import (
    binary_closing,
    binary_dilation,
    binary_opening,
    disk,
    remove_small_holes,
    remove_small_objects,
)

warnings.filterwarnings("ignore", category=FutureWarning, module=r"skimage\..*")


TECHNICAL_CHANNELS = {
    "80ARAR",
    "127I",
    "131XE",
    "134XE",
    "138BA",
    "208PB",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mask pixels outside the inferred TMA core in IMC image stacks."
    )
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Workflow directory containing data/img and data/panel.csv.",
    )
    parser.add_argument(
        "--image-name",
        default=None,
        help="Optional single image name inside data/img/. If omitted, process all TIFF stacks.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/13_core_mask_cleanup"),
        help="Directory for masks, QC figures, and summary tables.",
    )
    parser.add_argument(
        "--replace-data-img",
        action="store_true",
        help="Write cleaned stacks back into data/img/ for downstream reruns.",
    )
    parser.add_argument(
        "--write-cleaned-copies",
        action="store_true",
        help="Also write cleaned image stacks into the output directory.",
    )
    parser.add_argument(
        "--dilation-radius",
        type=int,
        default=12,
        help="Safety margin in pixels added around the inferred core.",
    )
    parser.add_argument(
        "--min-object-size",
        type=int,
        default=50_000,
        help="Minimum retained core object size in pixels.",
    )
    parser.add_argument(
        "--min-hole-size",
        type=int,
        default=80_000,
        help="Minimum hole size to fill inside the inferred core.",
    )
    parser.add_argument(
        "--skip-qc-figures",
        action="store_true",
        help="Skip QC figure generation.",
    )
    return parser.parse_args()


def robust_normalize(array: np.ndarray) -> np.ndarray:
    array = array.astype(np.float32, copy=False)
    low = np.percentile(array, 1)
    high = np.percentile(array, 99.5)
    if high <= low:
        return np.zeros_like(array, dtype=np.float32)
    return np.clip((array - low) / (high - low), 0.0, 1.0)


def load_panel(panel_path: Path) -> pd.DataFrame:
    panel = pd.read_csv(panel_path)
    required = {"channel", "name"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Panel file is missing required columns: {sorted(missing)}")
    return panel


def infer_broad_tissue_indices(panel: pd.DataFrame) -> list[int]:
    indices: list[int] = []
    for idx, marker_name in enumerate(panel["name"].astype(str).tolist()):
        upper = marker_name.upper()
        if upper in TECHNICAL_CHANNELS:
            continue
        if upper.startswith("DNA"):
            continue
        indices.append(idx)
    return indices


def build_core_mask(
    stack: np.ndarray,
    panel: pd.DataFrame,
    dilation_radius: int,
    min_object_size: int,
    min_hole_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    tissue_indices = infer_broad_tissue_indices(panel)
    if not tissue_indices:
        raise ValueError("No eligible biological channels were found for tissue masking.")

    composite = np.zeros(stack.shape[1:], dtype=np.float32)
    for index in tissue_indices:
        composite += robust_normalize(stack[index])
    composite /= max(len(tissue_indices), 1)
    composite = ndi.gaussian_filter(composite, sigma=24)

    positive_pixels = composite[composite > 0]
    if positive_pixels.size == 0:
        raise ValueError("Broad tissue composite contains no positive pixels.")

    threshold = max(
        threshold_otsu(composite),
        float(np.percentile(positive_pixels, 70)),
    )
    mask = composite > threshold
    mask = binary_closing(mask, disk(15))
    mask = binary_opening(mask, disk(9))
    mask = remove_small_objects(mask, min_size=min_object_size)
    mask = remove_small_holes(mask, area_threshold=min_hole_size)

    labeled = label(mask)
    if labeled.max() > 0:
        largest = max(regionprops(labeled), key=lambda region: region.area)
        mask = labeled == largest.label

    mask = ndi.binary_fill_holes(mask)
    if dilation_radius > 0:
        mask = binary_dilation(mask, disk(dilation_radius))
    return composite, mask.astype(bool)


def save_mask_artifacts(output_dir: Path, image_name: str, core_mask: np.ndarray) -> None:
    mask_dir = output_dir / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(
        mask_dir / image_name,
        (core_mask.astype(np.uint8) * 255),
        photometric="minisblack",
    )


def write_qc_figure(
    output_dir: Path,
    image_name: str,
    panel: pd.DataFrame,
    original_stack: np.ndarray,
    cleaned_stack: np.ndarray,
    composite: np.ndarray,
    core_mask: np.ndarray,
) -> None:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
    axes[0, 0].imshow(composite, cmap="magma")
    axes[0, 0].set_title("Broad tissue composite")
    axes[0, 1].imshow(core_mask, cmap="gray")
    axes[0, 1].set_title("Dilated core mask")
    overlay = np.dstack(
        [
            robust_normalize(composite),
            robust_normalize(composite),
            robust_normalize(composite),
        ]
    )
    overlay[~core_mask] *= 0.25
    axes[0, 2].imshow(overlay)
    axes[0, 2].set_title("Retained area overlay")

    for axis, marker in zip(axes[1], ["DNA1", "CD3", "aSMA"]):
        idx_matches = panel.index[panel["name"].astype(str).str.upper() == marker.upper()].tolist()
        if not idx_matches:
            axis.axis("off")
            continue
        idx = idx_matches[0]
        before = robust_normalize(original_stack[idx])
        after = robust_normalize(cleaned_stack[idx])
        rgb = np.dstack([before, after, np.zeros_like(before)])
        axis.imshow(rgb)
        axis.set_title(f"{marker}: red=before, green=after")

    for axis in axes.ravel():
        axis.set_xticks([])
        axis.set_yticks([])

    fig.suptitle(f"Core-masking QC: {image_name}", fontsize=14)
    fig.savefig(figure_dir / image_name.replace(".tiff", "_qc.png"), dpi=200)
    plt.close(fig)


def process_image(
    image_path: Path,
    panel: pd.DataFrame,
    output_dir: Path,
    replace_data_img: bool,
    write_cleaned_copies: bool,
    dilation_radius: int,
    min_object_size: int,
    min_hole_size: int,
    skip_qc_figures: bool,
) -> dict[str, object]:
    stack = tifffile.imread(image_path)
    if stack.ndim != 3:
        raise ValueError(f"Expected C x H x W stack, got {stack.shape} for {image_path.name}")

    composite, core_mask = build_core_mask(
        stack,
        panel,
        dilation_radius=dilation_radius,
        min_object_size=min_object_size,
        min_hole_size=min_hole_size,
    )

    cleaned_stack = stack.copy()
    cleaned_stack[:, ~core_mask] = 0

    save_mask_artifacts(output_dir, image_path.name, core_mask)

    outside_fraction_before = float(np.mean(np.any(stack > 0, axis=0)[~core_mask]))
    outside_fraction_after = float(np.mean(np.any(cleaned_stack > 0, axis=0)[~core_mask]))
    retained_fraction = float(core_mask.mean())

    if replace_data_img:
        temp_output_path = image_path.with_suffix(image_path.suffix + ".tmp")
        tifffile.imwrite(
            temp_output_path,
            cleaned_stack,
            photometric="minisblack",
            metadata={"axes": "CYX"},
        )
        temp_output_path.replace(image_path)

    cleaned_copy_path = None
    if write_cleaned_copies:
        cleaned_dir = output_dir / "cleaned_img"
        cleaned_dir.mkdir(parents=True, exist_ok=True)
        cleaned_copy_path = cleaned_dir / image_path.name
        tifffile.imwrite(
            cleaned_copy_path,
            cleaned_stack,
            photometric="minisblack",
            metadata={"axes": "CYX"},
        )

    if not skip_qc_figures:
        write_qc_figure(
            output_dir=output_dir,
            image_name=image_path.name,
            panel=panel,
            original_stack=stack,
            cleaned_stack=cleaned_stack,
            composite=composite,
            core_mask=core_mask,
        )

    return {
        "image": image_path.name,
        "height_px": int(stack.shape[1]),
        "width_px": int(stack.shape[2]),
        "channels": int(stack.shape[0]),
        "core_fraction": retained_fraction,
        "outside_pixel_fraction_before": outside_fraction_before,
        "outside_pixel_fraction_after": outside_fraction_after,
        "pixels_removed": int((~core_mask).sum()),
        "pixels_retained": int(core_mask.sum()),
        "cleaned_copy_path": str(cleaned_copy_path) if cleaned_copy_path else "",
    }


def main() -> None:
    args = parse_args()
    workflow_dir = args.workflow_dir.resolve()
    img_dir = workflow_dir / "data" / "img"
    panel = load_panel(workflow_dir / "data" / "panel.csv")
    output_dir = workflow_dir / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.image_name:
        image_paths = [img_dir / args.image_name]
    else:
        image_paths = sorted(img_dir.glob("*.tiff"))

    if not image_paths:
        raise FileNotFoundError(f"No TIFF stacks were found in {img_dir}")

    summary_rows = []
    for image_path in image_paths:
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        print(f"Processing {image_path.name}")
        summary_rows.append(
            process_image(
                image_path=image_path,
                panel=panel,
                output_dir=output_dir,
                replace_data_img=args.replace_data_img,
                write_cleaned_copies=args.write_cleaned_copies,
                dilation_radius=args.dilation_radius,
                min_object_size=args.min_object_size,
                min_hole_size=args.min_hole_size,
                skip_qc_figures=args.skip_qc_figures,
            )
        )

    summary_path = output_dir / "13_core_mask_cleanup_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "image",
                "height_px",
                "width_px",
                "channels",
                "core_fraction",
                "outside_pixel_fraction_before",
                "outside_pixel_fraction_after",
                "pixels_removed",
                "pixels_retained",
                "cleaned_copy_path",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    metadata = {
        "workflow_dir": str(workflow_dir),
        "processed_images": len(summary_rows),
        "replace_data_img": args.replace_data_img,
        "write_cleaned_copies": args.write_cleaned_copies,
        "dilation_radius": args.dilation_radius,
        "min_object_size": args.min_object_size,
        "min_hole_size": args.min_hole_size,
        "technical_channels_excluded_from_mask_building": sorted(TECHNICAL_CHANNELS),
    }
    (output_dir / "13_core_mask_cleanup_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Core-mask cleanup complete for {len(summary_rows)} image(s)")
    print(f"Summary: {summary_path}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
