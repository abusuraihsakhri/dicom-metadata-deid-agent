"""Conservative, local DICOM metadata inspection and allowlisted JSON export.

This does NOT rewrite a DICOM instance or implement the full DICOM PS3.15
Basic Application Level Confidentiality Profile. No pixel data is read or
exported. Pixel-burned identifiers, overlays and waveform content are not
assessed; the resulting JSON must still be reviewed before sharing.
"""
import argparse
import json
from pathlib import Path
from typing import Dict, Union

from pydicom import dcmread
from pydicom.errors import InvalidDicomError

# Only enumerated image-encoding properties, not identifiers, sequences,
# acquisition timestamps, free text, or private elements.
_NUMERIC_FIELDS = {
    (0x0028, 0x0002): "SamplesPerPixel",
    (0x0028, 0x0008): "NumberOfFrames",
    (0x0028, 0x0010): "Rows",
    (0x0028, 0x0011): "Columns",
    (0x0028, 0x0100): "BitsAllocated",
    (0x0028, 0x0101): "BitsStored",
    (0x0028, 0x0102): "HighBit",
    (0x0028, 0x0103): "PixelRepresentation",
}
_CODE_FIELDS = {
    (0x0008, 0x0060): ("Modality", frozenset({
        "CT", "MR", "US", "DX", "CR", "MG", "NM", "PT", "PET", "XA",
        "RF", "SC", "OT", "XC", "IO", "ECG", "SM", "SEG", "RTIMAGE",
    })),
    (0x0028, 0x0004): ("PhotometricInterpretation", frozenset({
        "MONOCHROME1", "MONOCHROME2", "RGB", "PALETTE COLOR",
        "YBR_FULL", "YBR_FULL_422", "YBR_PARTIAL_422",
        "YBR_RCT", "YBR_ICT",
    })),
}

class MetadataInspectionError(ValueError):
    """Invalid or unsupported DICOM input; never include source identifiers."""


def inspect_dicom_file(path: Union[str, Path]) -> Dict[str, object]:
    """Return technical metadata without PHI-bearing tags or source path.

    Uses strict DICOM parsing and stops before Pixel Data. The list is
    intentionally minimal: absence of identifiers in this report does not
    prove that the original image or other content was anonymized.
    """
    try:
        dataset = dcmread(str(path), stop_before_pixels=True, force=False,
                         defer_size="1 MB")
    except (InvalidDicomError, OSError, ValueError, TypeError) as exc:
        raise MetadataInspectionError(
            "Cannot inspect input: supply a readable DICOM Part 10 file."
        ) from None

    technical: Dict[str, object] = {}
    for tag, name in _NUMERIC_FIELDS.items():
        element = dataset.get(tag)
        if element is not None:
            try:
                value = str(element.value)
                if not value.isascii() or not value.isdecimal():
                    continue
                number = int(value)
                if 0 <= number <= 1000000:
                    technical[name] = number
            except (ValueError, TypeError, OverflowError):
                continue
    for tag, (name, allowed) in _CODE_FIELDS.items():
        element = dataset.get(tag)
        if element is not None:
            value = str(element.value).strip().upper()
            if value in allowed:
                technical[name] = value

    # Avoid echoing any tag values or private element names, including names
    # buried in sequences. A private tag count is not a privacy guarantee.
    elements = list(dataset.iterall())
    private_count = sum(1 for item in elements if item.tag.is_private)
    burned_in = dataset.get((0x0028, 0x0301))
    burned_in_flag = (
        str(burned_in.value).upper() if burned_in is not None else "UNKNOWN"
    )
    if burned_in_flag not in ("YES", "NO"):
        burned_in_flag = "UNKNOWN"

    return {
        "technical_metadata": technical,
        "suppressed_element_count": len(elements) - len(technical),
        "private_element_count": private_count,
        "source_pixel_data_read": False,
        "source_pixel_data_examined": False,
        "burned_in_annotation_flag": burned_in_flag,
        "warning": (
            "Technical metadata extract only. Original DICOM and pixel data "
            "have NOT been de-identified. A NO burned-in flag does not "
            "exclude visible patient identifiers; review before disclosure."
        ),
    }


def export_sanitized_metadata(input_path: Union[str, Path],
                              output_path: Union[str, Path]) -> Dict[str, object]:
    """Write a new JSON extract; never overwrite an existing output or input."""
    source, destination = Path(input_path), Path(output_path)
    if source.resolve() == destination.resolve():
        raise MetadataInspectionError("Input and output must be different files.")
    report = inspect_dicom_file(source)
    try:
        with destination.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, sort_keys=True)
            output.write("\n")
    except FileExistsError:
        raise MetadataInspectionError("Output already exists; choose a new path.") from None
    except OSError:
        raise MetadataInspectionError("Cannot write output file.") from None
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="dicom-metadata-inspect",
        description="Local metadata inspection (not DICOM de-identification).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="Print a technical metadata-only JSON report")
    scan.add_argument("input", help="DICOM Part 10 file")
    export = subparsers.add_parser("export", help="Write a technical metadata-only JSON report")
    export.add_argument("input", help="DICOM Part 10 file")
    export.add_argument("output", help="New JSON output path (must not exist)")
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            print(json.dumps(inspect_dicom_file(args.input), indent=2, sort_keys=True))
        else:
            export_sanitized_metadata(args.input, args.output)
            print("Technical metadata report exported locally.")
    except MetadataInspectionError as exc:
        parser.exit(1, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
