#!/usr/bin/env python3
"""Export draw.io XML to an opaque, white-background PNG."""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


MACOS_DRAWIO = Path("/Applications/draw.io.app/Contents/MacOS/draw.io")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def drawio_executable() -> str:
    executable = shutil.which("drawio")
    if executable:
        return executable
    if MACOS_DRAWIO.is_file():
        return str(MACOS_DRAWIO)
    raise FileNotFoundError("draw.io Desktop CLI was not found on PATH or in /Applications")


def white_source(source: Path, destination: Path) -> None:
    tree = ET.parse(source)
    models = tree.getroot().findall(".//mxGraphModel")
    if not models:
        raise ValueError("No mxGraphModel found; expected uncompressed draw.io XML")
    for model in models:
        model.set("background", "#FFFFFF")
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def png_has_transparency(path: Path) -> bool:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE) or len(data) < 33:
        raise ValueError("draw.io did not produce a valid PNG")
    length = struct.unpack(">I", data[8:12])[0]
    if data[12:16] != b"IHDR" or length != 13:
        raise ValueError("PNG has an invalid IHDR chunk")
    color_type = data[25]
    return color_type in (4, 6) or b"tRNS" in data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export uncompressed draw.io XML to an opaque white PNG."
    )
    parser.add_argument("source", type=Path, help="Input .drawio or .xml file")
    parser.add_argument("--output", type=Path, help="Output PNG; defaults beside source")
    parser.add_argument("--scale", type=float, default=1.5)
    args = parser.parse_args()

    source = args.source.resolve()
    if source.suffix.lower() not in {".drawio", ".xml"}:
        parser.error("source must use the .drawio or .xml extension")
    if not source.is_file():
        parser.error(f"source does not exist: {source}")
    if args.scale <= 0:
        parser.error("--scale must be greater than zero")

    output = (args.output or source.with_suffix(".png")).resolve()
    if output.suffix.lower() != ".png":
        parser.error("--output must use the .png extension")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="drawio-white-export-") as temp_dir:
        render_source = Path(temp_dir) / source.name
        white_source(source, render_source)
        subprocess.run(
            [
                drawio_executable(),
                "--export",
                "--format",
                "png",
                "--scale",
                str(args.scale),
                "--output",
                str(output),
                str(render_source),
            ],
            check=True,
        )

    if not output.is_file():
        raise RuntimeError(f"draw.io reported success but did not create {output}")
    if png_has_transparency(output):
        output.unlink()
        raise RuntimeError("exported PNG contains transparency; removed invalid output")

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
