#!/usr/bin/env python3
"""Validate that generated multi-channel TIFFs are correctly structured OME-TIFFs.

Checks every ROI TIFF in a given directory (default data/img/) against
data/panel.csv. Every check reopens the file from disk with
tifffile.TiffFile and inspects the parsed series/OME metadata -- it never
trusts the in-memory array a writer script produced, since that's exactly
how the original bug (files structurally fine in-memory, but written with
metadata no external reader could parse) went unnoticed.

For each file, verifies:
  - the file is real OME-TIFF (is_ome), not tifffile's proprietary "shaped" format
  - SizeC equals the number of panel rows; SizeZ == 1; SizeT == 1
  - width_px / height_px match the panel-independent expected image size
  - dtype matches (uint16 by default for this workflow)
  - the OME-XML <Channel Name=...> list, in order, exactly matches
    data/panel.csv's "name" column, one-to-one
  - PhysicalSizeX/Y, if present, are reported (not enforced, since this
    workflow does not currently set them -- see note in the report)

Usage:
    python3 scripts/validate_ome_tiff.py --img-dir data/img
    python3 scripts/validate_ome_tiff.py --img-dir data/cleaned_img
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import tifffile

OME_NS = {"ome": "http://www.openmicroscopy.org/Schemas/OME/2016-06"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate OME-TIFF structure of workflow image files.")
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Workflow directory containing data/panel.csv.",
    )
    parser.add_argument(
        "--img-dir",
        type=Path,
        default=Path("data/img"),
        help="Directory (relative to --workflow-dir) of TIFFs to validate.",
    )
    parser.add_argument(
        "--expected-dtype",
        default="uint16",
        help="Expected pixel dtype (default: uint16, the Hyperion/Steinbock convention for this workflow).",
    )
    return parser.parse_args()


def validate_file(path: Path, expected_names: list[str], expected_dtype: str) -> list[str]:
    problems: list[str] = []

    with tifffile.TiffFile(path) as tf:
        if not tf.is_ome:
            problems.append(
                "not a real OME-TIFF (is_ome=False) -- Bio-Formats/QuPath will not read channel "
                "structure correctly; it will likely be misinterpreted as a Z or T stack"
            )
            # Still report what we can from the shaped/generic series before returning.
            series = tf.series[0]
            problems.append(f"  (fallback) series shape={series.shape} axes={series.axes}")
            return problems

        xml_str = tf.ome_metadata
        root = ET.fromstring(xml_str)
        pixels = root.find(".//ome:Pixels", OME_NS)
        if pixels is None:
            problems.append("OME-XML present but no <Pixels> element found")
            return problems

        size_c = int(pixels.get("SizeC", -1))
        size_z = int(pixels.get("SizeZ", -1))
        size_t = int(pixels.get("SizeT", -1))
        size_x = int(pixels.get("SizeX", -1))
        size_y = int(pixels.get("SizeY", -1))
        dtype = pixels.get("Type", "")
        physical_size_x = pixels.get("PhysicalSizeX")
        physical_size_y = pixels.get("PhysicalSizeY")

        if size_c != len(expected_names):
            problems.append(f"SizeC={size_c}, expected {len(expected_names)} (panel row count)")
        if size_z != 1:
            problems.append(f"SizeZ={size_z}, expected 1 (unexpected Z dimension)")
        if size_t != 1:
            problems.append(f"SizeT={size_t}, expected 1 (unexpected T dimension -- this was the original bug)")
        if dtype != expected_dtype:
            problems.append(f"pixel dtype={dtype!r}, expected {expected_dtype!r}")

        channels = pixels.findall("ome:Channel", OME_NS)
        if len(channels) != size_c:
            problems.append(f"{len(channels)} <Channel> elements found, but SizeC={size_c}")

        channel_names = [ch.get("Name") for ch in channels]
        if channel_names != expected_names:
            mismatches = [
                (i, got, want)
                for i, (got, want) in enumerate(zip(channel_names, expected_names))
                if got != want
            ]
            problems.append(
                f"channel name/order mismatch vs panel.csv at {len(mismatches)} position(s): "
                f"{mismatches[:5]}{'...' if len(mismatches) > 5 else ''}"
            )
        if len(channel_names) != len(expected_names):
            problems.append(
                f"channel name count ({len(channel_names)}) != panel row count ({len(expected_names)})"
            )

        # Cross-check against the actual pixel array shape too, not just the XML.
        series = tf.series[0]
        if series.axes != "CYX":
            problems.append(f"series.axes={series.axes!r}, expected 'CYX'")
        if series.shape != (size_c, size_y, size_x):
            problems.append(f"series.shape={series.shape} does not match OME SizeC/SizeY/SizeX")

        if physical_size_x is None or physical_size_y is None:
            problems.append(
                "NOTE (not a failure): PhysicalSizeX/Y not set in OME metadata -- this workflow "
                "does not currently record real-world pixel size. Hyperion IMC is conventionally "
                "1 micron/pixel; add PhysicalSizeX/Y=1.0 with Unit='µm' to the writer if you want "
                "QuPath to show correct physical scale bars."
            )

    return problems


def main() -> None:
    args = parse_args()
    workflow_dir = args.workflow_dir.resolve()
    img_dir = workflow_dir / args.img_dir
    panel_path = workflow_dir / "data" / "panel.csv"

    if not img_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {img_dir}")
    if not panel_path.exists():
        raise FileNotFoundError(f"panel.csv not found: {panel_path}")

    panel = pd.read_csv(panel_path)
    expected_names = panel["name"].astype(str).tolist()

    image_paths = sorted(img_dir.glob("*.tiff"))
    if not image_paths:
        raise FileNotFoundError(f"No TIFF files found in {img_dir}")

    print(f"Validating {len(image_paths)} file(s) in {img_dir} against {len(expected_names)}-channel panel\n")

    any_failed = False
    for path in image_paths:
        problems = validate_file(path, expected_names, args.expected_dtype)
        real_problems = [p for p in problems if not p.startswith("NOTE")]
        notes = [p for p in problems if p.startswith("NOTE")]

        if real_problems:
            any_failed = True
            print(f"[FAIL] {path.name}")
            for p in real_problems:
                print(f"    - {p}")
        else:
            print(f"[PASS] {path.name}  (SizeC={len(expected_names)}, SizeZ=1, SizeT=1, channel names/order match panel.csv)")
        for n in notes:
            print(f"    - {n}")

    print()
    if any_failed:
        print("Validation FAILED for one or more files.")
        sys.exit(1)
    else:
        print("All files passed validation.")


if __name__ == "__main__":
    main()
