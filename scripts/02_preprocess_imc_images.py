#!/usr/bin/env python3
"""Prepare IMC images for a workflow data directory.

For marker-channel OME-TIFF folder inputs, this script stacks each ROI folder
into a Steinbock-style multi-channel TIFF in `data/img/` and writes an
`images.csv` table with the expected Steinbock-compatible structure. The channel
order follows `data/panel.csv`. If a marker from the union panel is absent from
one ROI, the missing channel is represented by a zero-filled image for that ROI
and recorded in the preprocessing log.

Before writing, every channel is hot-pixel filtered with the Steinbock rule
(review item 1.1): a pixel brighter than all 8 neighbours by more than `--hpf`
counts is replaced by its brightest neighbour. Stacks keep the source dtype:
the pre-exported channels are integer counts, and the filter only ever
substitutes a neighbouring integer value, so a float32 container would add
disk without adding information (fractional counts need the original .mcd,
review item 1.2).

Output image names follow the TMA core map (review item 1.3): a raw ROI folder
whose name differs from the core-map name for the same ROI number (e.g.
`ROI032_ROI_032` -> `ROI032_I13`) is written under the core-map name. Raw
folders are never renamed; the original folder name is kept in images.csv.

For legacy MCD/raw text inputs, when no OME-TIFF ROI folders are present, the
script follows the Steinbock hands-on preprocessing command:

    steinbock preprocess imc images --hpf 50

The script uses the official Steinbock Docker image by default. Steinbock
working outputs keep the required names inside `data/`, while numbered research
copies and logs are written to `results/` and `logs/`.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess raw IMC data with Steinbock.")
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Workflow directory containing data/raw and data/panel.csv.",
    )
    parser.add_argument(
        "--steinbock-image",
        default="ghcr.io/bodenmillergroup/steinbock:0.16.1",
        help="Steinbock Docker image.",
    )
    parser.add_argument(
        "--hpf",
        default="50",
        help=(
            "Hot-pixel filtering threshold in counts, applied to OME-TIFF channel "
            "stacks and passed to Steinbock for legacy MCD/raw text inputs. "
            "Use 0 to disable."
        ),
    )
    parser.add_argument(
        "--roi-name-map",
        type=Path,
        default=Path("data/reference/20261005 TMA_core_map.csv"),
        help=(
            "Core map CSV with a 'roi' column; output images are named after it. "
            "Use 'none' to keep raw folder names."
        ),
    )
    parser.add_argument(
        "--numbered-images-copy",
        type=Path,
        default=Path("results/02_images.csv"),
        help="Numbered copy of Steinbock data/images.csv.",
    )
    parser.add_argument(
        "--numbered-inventory",
        type=Path,
        default=Path("results/03_preprocessed_tiff_inventory.csv"),
        help="Numbered inventory of generated TIFF image files.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("logs/02_preprocess_imc_images.log"),
        help="Numbered preprocessing command log.",
    )
    parser.add_argument(
        "--keep-source",
        choices=["mcd", "all"],
        default="mcd",
        help=(
            "Legacy Steinbock filter only. Ignored when ROI folders containing "
            "per-channel .ome.tiff files are present."
        ),
    )
    # Defaults are 0 (review item 1.4): 27 of 136 ROIs are not 1000 x 1000 px,
    # and a non-zero minimum silently deletes them on the legacy .mcd path.
    parser.add_argument(
        "--min-width",
        type=int,
        default=0,
        help="Legacy .mcd path only: minimum retained image width in pixels (0 = keep all).",
    )
    parser.add_argument(
        "--min-height",
        type=int,
        default=0,
        help="Legacy .mcd path only: minimum retained image height in pixels (0 = keep all).",
    )
    return parser.parse_args()


def require_input(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required {description} not found: {path}")


def read_panel_rows(panel_path: Path) -> list[dict[str, str]]:
    with panel_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No marker rows were found in panel file: {panel_path}")
    return rows


def infer_roi_shape(roi_dir: Path):
    try:
        import tifffile
    except ImportError as error:
        raise RuntimeError(
            "Marker-folder preprocessing requires tifffile. "
            "Install it with: python3 -m pip install tifffile"
        ) from error

    for path in sorted(roi_dir.glob("*.ome.tiff")):
        array = tifffile.imread(path)
        return array.shape, array.dtype
    raise FileNotFoundError(f"No OME-TIFF files found in ROI folder: {roi_dir}")


def filter_hot_pixels(channel, thres: float):
    """Steinbock hot-pixel rule on one 2-D channel; returns (filtered, n_replaced).

    Equivalent to steinbock.preprocessing.imc.filter_hot_pixels, computed in
    float64 so unsigned integer inputs cannot wrap around on subtraction.
    """
    import numpy as np
    from scipy.ndimage import maximum_filter

    footprint = np.ones((3, 3), dtype=bool)
    footprint[1, 1] = False
    values = channel.astype(np.float64)
    max_neighbor = maximum_filter(values, footprint=footprint, mode="mirror")
    hot = values - max_neighbor > thres
    filtered = np.where(hot, max_neighbor, values).astype(channel.dtype)
    return filtered, int(hot.sum())


def load_roi_name_map(map_path: Path | None) -> dict[str, str]:
    """Map ROI number prefix (e.g. 'ROI032') to its core-map name ('ROI032_I13')."""
    if map_path is None:
        return {}
    require_input(map_path, "ROI name map (TMA core map)")
    with map_path.open(newline="", encoding="utf-8") as handle:
        names = [row["roi"] for row in csv.DictReader(handle)]
    mapping = {}
    for name in names:
        prefix = name.split("_", 1)[0]
        if prefix in mapping:
            raise ValueError(f"ROI number {prefix} appears twice in {map_path}")
        mapping[prefix] = name
    return mapping


def marker_folder_inputs(raw_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in raw_dir.iterdir()
        if path.is_dir() and any(path.glob("*.ome.tiff"))
    )


def write_marker_folder_images(
    workflow_dir: Path,
    numbered_images_copy: Path,
    numbered_inventory: Path,
    log_file: Path,
    hpf: float,
    roi_name_map: dict[str, str],
) -> None:
    try:
        import numpy as np
        import tifffile
    except ImportError as error:
        raise RuntimeError(
            "Marker-folder preprocessing requires numpy and tifffile. "
            "Install them with: python3 -m pip install numpy tifffile"
        ) from error

    raw_dir = workflow_dir / "data" / "raw"
    img_dir = workflow_dir / "data" / "img"
    images_csv = workflow_dir / "data" / "images.csv"
    panel_rows = read_panel_rows(workflow_dir / "data" / "panel.csv")
    roi_dirs = marker_folder_inputs(raw_dir)

    if not roi_dirs:
        raise FileNotFoundError(f"No ROI folders containing .ome.tiff files were found in {raw_dir}")

    img_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    output_names = {}
    for roi_dir in roi_dirs:
        mapped = roi_name_map.get(roi_dir.name.split("_", 1)[0], roi_dir.name)
        output_names[roi_dir] = mapped
    duplicated = {n for n in output_names.values() if list(output_names.values()).count(n) > 1}
    if duplicated:
        raise ValueError(f"Several raw ROI folders map to the same image name: {sorted(duplicated)}")

    images_rows = []
    log_lines = [
        "MARKER_FOLDER_PREPROCESSING",
        f"raw_dir={raw_dir}",
        f"roi_folders={len(roi_dirs)}",
        f"panel_rows={len(panel_rows)}",
        (
            f"hot_pixel_filter=applied;hpf={hpf:g};rule=steinbock_8_neighbour_max"
            if hpf > 0
            else "hot_pixel_filter=disabled"
        ),
        f"roi_name_map_entries={len(roi_name_map)}",
    ]
    total_hot = {row["name"]: 0 for row in panel_rows}

    for roi_index, roi_dir in enumerate(roi_dirs, start=1):
        channel_arrays = []
        missing_files = []
        reference_shape = None
        reference_dtype = None

        for row in panel_rows:
            channel = row["channel"]
            marker = row["name"]
            channel_path = roi_dir / f"{channel}_{marker}.ome.tiff"
            if not channel_path.exists():
                missing_files.append(channel_path.name)
                if reference_shape is None or reference_dtype is None:
                    reference_shape, reference_dtype = infer_roi_shape(roi_dir)
                channel_arrays.append(np.zeros(reference_shape, dtype=reference_dtype))
                continue
            array = tifffile.imread(channel_path)
            if reference_shape is None:
                reference_shape = array.shape
                reference_dtype = array.dtype
            channel_arrays.append(array)

        shapes = {array.shape for array in channel_arrays}
        if len(shapes) != 1:
            raise ValueError(f"Channel images in {roi_dir} do not share one shape: {sorted(shapes)}")

        hot_counts = []
        if hpf > 0:
            filtered_arrays = []
            for array in channel_arrays:
                filtered, n_hot = filter_hot_pixels(array, hpf)
                filtered_arrays.append(filtered)
                hot_counts.append(n_hot)
            channel_arrays = filtered_arrays
            for row, n_hot in zip(panel_rows, hot_counts):
                total_hot[row["name"]] += n_hot

        stack = np.stack(channel_arrays, axis=0)
        image_name = f"{output_names[roi_dir]}.tiff"
        output_path = img_dir / image_name
        channel_names = [row["name"] for row in panel_rows]
        # ome=True + a Channel/Name list writes real OME-XML (SizeC/SizeZ/SizeT
        # and named channels) that Bio-Formats/QuPath can read correctly. The
        # previous plain metadata={"axes": "CYX"} call only wrote tifffile's own
        # proprietary "shaped" JSON into ImageDescription, which nothing but
        # tifffile itself understands -- Bio-Formats fell back to treating the
        # 43 unlabeled planes as a time series (T=43) instead of channels
        # (C=43). Pixel values are unaffected either way; only the container
        # metadata changes. See scripts/validate_ome_tiff.py.
        tifffile.imwrite(
            output_path,
            stack,
            photometric="minisblack",
            ome=True,
            metadata={"axes": "CYX", "Channel": {"Name": channel_names}},
        )

        height, width = stack.shape[1:]
        images_rows.append(
            {
                "image": image_name,
                "width_px": width,
                "height_px": height,
                "num_channels": stack.shape[0],
                "source_file": str(roi_dir.relative_to(raw_dir)),
                "recovery_file": "",
                "recovered": "False",
                "acquisition_id": roi_index,
                "acquisition_description": roi_dir.name,
                "acquisition_start_x_um": "",
                "acquisition_start_y_um": "",
                "acquisition_end_x_um": "",
                "acquisition_end_y_um": "",
                "acquisition_width_um": width,
                "acquisition_height_um": height,
            }
        )
        missing_note = "none" if not missing_files else ",".join(missing_files)
        hot_note = ",".join(
            f"{row['name']}:{n}" for row, n in zip(panel_rows, hot_counts) if n
        ) or "none"
        rename_note = (
            f"; renamed_from={roi_dir.name}" if output_names[roi_dir] != roi_dir.name else ""
        )
        log_lines.append(
            f"wrote={output_path.name}; shape={stack.shape}; dtype={stack.dtype}; "
            f"zero_filled_missing_channels={missing_note}; hot_pixels_replaced={hot_note}"
            f"{rename_note}"
        )

    fieldnames = [
        "image",
        "width_px",
        "height_px",
        "num_channels",
        "source_file",
        "recovery_file",
        "recovered",
        "acquisition_id",
        "acquisition_description",
        "acquisition_start_x_um",
        "acquisition_start_y_um",
        "acquisition_end_x_um",
        "acquisition_end_y_um",
        "acquisition_width_um",
        "acquisition_height_um",
    ]
    with images_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(images_rows)

    log_lines.append("")
    log_lines.append("HOT_PIXELS_REPLACED_TOTAL_PER_CHANNEL")
    log_lines.extend(f"{name}={count}" for name, count in total_hot.items())
    log_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    copy_images_csv(workflow_dir, numbered_images_copy)
    write_tiff_inventory(workflow_dir, numbered_inventory)


def run_steinbock(workflow_dir: Path, image: str, hpf: str, log_file: Path) -> None:
    data_dir = workflow_dir / "data"
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{data_dir.resolve()}:/data",
        "-u",
        f"{subprocess.check_output(['id', '-u'], text=True).strip()}:"
        f"{subprocess.check_output(['id', '-g'], text=True).strip()}",
        image,
        "preprocess",
        "imc",
        "images",
        "--hpf",
        hpf,
    ]

    log_file.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=workflow_dir, text=True, capture_output=True)

    log_file.write_text(
        "COMMAND\n"
        + " ".join(command)
        + "\n\nSTDOUT\n"
        + completed.stdout
        + "\n\nSTDERR\n"
        + completed.stderr
        + f"\n\nRETURN_CODE\n{completed.returncode}\n",
        encoding="utf-8",
    )

    if completed.returncode != 0:
        raise RuntimeError(f"Steinbock preprocessing failed. See log: {log_file}")


def copy_images_csv(workflow_dir: Path, numbered_images_copy: Path) -> None:
    source = workflow_dir / "data" / "images.csv"
    destination = workflow_dir / numbered_images_copy
    require_input(source, "Steinbock images.csv output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def filter_preprocessed_images(
    workflow_dir: Path,
    keep_source: str,
    min_width: int,
    min_height: int,
    log_file: Path,
) -> None:
    images_csv = workflow_dir / "data" / "images.csv"
    img_dir = workflow_dir / "data" / "img"
    require_input(images_csv, "Steinbock images.csv output")
    require_input(img_dir, "Steinbock image output directory")

    with images_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if fieldnames is None:
        raise ValueError(f"Could not read header from {images_csv}")

    kept_rows = []
    removed_rows = []

    for row in rows:
        remove_reasons = []
        source_file = row.get("source_file", "")
        image_name = row.get("image", "")
        width = int(float(row.get("width_px") or 0))
        height = int(float(row.get("height_px") or 0))

        if keep_source == "mcd" and not source_file.endswith(".mcd"):
            remove_reasons.append("source_not_mcd")
        if min_width and width < min_width:
            remove_reasons.append(f"width_lt_{min_width}")
        if min_height and height < min_height:
            remove_reasons.append(f"height_lt_{min_height}")

        if remove_reasons:
            removed_rows.append((row, remove_reasons))
            image_path = img_dir / image_name
            if image_path.exists():
                image_path.unlink()
        else:
            kept_rows.append(row)

    with images_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    summary_lines = [
        "",
        "POSTPROCESSING_FILTER",
        f"keep_source={keep_source}",
        f"min_width={min_width}",
        f"min_height={min_height}",
        f"images_kept={len(kept_rows)}",
        f"images_removed={len(removed_rows)}",
    ]
    for row, reasons in removed_rows:
        summary_lines.append(
            f"removed={row.get('image', '')}; source={row.get('source_file', '')}; "
            f"size={row.get('width_px', '')}x{row.get('height_px', '')}; "
            f"reason={'+'.join(reasons)}"
        )

    with log_file.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines) + "\n")


def write_tiff_inventory(workflow_dir: Path, numbered_inventory: Path) -> None:
    img_dir = workflow_dir / "data" / "img"
    require_input(img_dir, "Steinbock image output directory")

    rows = []
    for index, path in enumerate(sorted(img_dir.glob("*.tiff")), start=1):
        rows.append(
            {
                "index": index,
                "file_name": path.name,
                "relative_path": str(path.relative_to(workflow_dir)),
                "size_bytes": path.stat().st_size,
            }
        )

    destination = workflow_dir / numbered_inventory
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["index", "file_name", "relative_path", "size_bytes"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    workflow_dir = args.workflow_dir.resolve()

    require_input(workflow_dir / "data" / "raw", "raw data directory")
    require_input(workflow_dir / "data" / "panel.csv", "Steinbock panel file")

    raw_dir = workflow_dir / "data" / "raw"
    if marker_folder_inputs(raw_dir):
        name_map_path = (
            None
            if str(args.roi_name_map).casefold() == "none"
            else (args.roi_name_map if args.roi_name_map.is_absolute() else workflow_dir / args.roi_name_map)
        )
        write_marker_folder_images(
            workflow_dir,
            args.numbered_images_copy,
            args.numbered_inventory,
            workflow_dir / args.log_file,
            hpf=float(args.hpf),
            roi_name_map=load_roi_name_map(name_map_path),
        )
    else:
        run_steinbock(workflow_dir, args.steinbock_image, args.hpf, workflow_dir / args.log_file)
        filter_preprocessed_images(
            workflow_dir,
            args.keep_source,
            args.min_width,
            args.min_height,
            workflow_dir / args.log_file,
        )
        copy_images_csv(workflow_dir, args.numbered_images_copy)
        write_tiff_inventory(workflow_dir, args.numbered_inventory)

    print(f"Steinbock preprocessing complete: {workflow_dir / 'data' / 'img'}")
    print(f"Numbered images metadata: {workflow_dir / args.numbered_images_copy}")
    print(f"Numbered TIFF inventory: {workflow_dir / args.numbered_inventory}")
    print(f"Command log: {workflow_dir / args.log_file}")


if __name__ == "__main__":
    main()
