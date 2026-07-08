#!/usr/bin/env python3
"""
json_to_csv.py - Converts a JSON file to a flattened CSV file.

Usage:
    python3 json_to_csv.py input.json output.csv [--sep '.'] [--array-delimiter '|']
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def flatten_record(record: dict, sep: str = ".", prefix: str = "") -> dict:
    """
    Recursively flatten a nested dict/list into a single-level dict.

    - Nested dicts -> key.subkey
    - Arrays of dicts -> key_0.subkey, key_1.subkey
    - Arrays of scalars -> joined later with array_delimiter
    """
    flat = {}
    for key, value in record.items():
        full_key = f"{prefix}{sep}{key}" if prefix else key

        if isinstance(value, dict):
            flat.update(flatten_record(value, sep=sep, prefix=full_key))

        elif isinstance(value, list):
            if not value:
                flat[full_key] = ""
            elif all(isinstance(v, dict) for v in value):
                # Array of objects -> flatten each element with indexed key
                for idx, item in enumerate(value):
                    flat.update(flatten_record(item, sep=sep, prefix=f"{full_key}_{idx}"))
            else:
                # Mixed or scalar array -> keep list for post-processing
                flat[full_key] = value

        else:
            flat[full_key] = value

    return flat


def join_list_values(df: pd.DataFrame, array_delimiter: str) -> pd.DataFrame:
    """Replace any remaining list cells with a delimited string."""
    for col in df.columns:
        mask = df[col].apply(lambda v: isinstance(v, list))
        if mask.any():
            df.loc[mask, col] = df.loc[mask, col].apply(
                lambda lst: array_delimiter.join(str(v) for v in lst)
            )
    return df


def load_json(path: Path) -> list[dict]:
    """Read and validate the JSON file; always return a list of records."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"Error: Input file not found: {path}")
    except PermissionError:
        sys.exit(f"Error: Permission denied reading: {path}")

    if not text.strip():
        sys.exit(f"Error: Input file is empty: {path}")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        sys.exit(f"Error: Invalid JSON - {exc}")

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        if not data:
            sys.exit("Error: JSON array is empty - nothing to convert.")
        if not all(isinstance(item, dict) for item in data):
            # Array of scalars -> wrap each element so it has a column
            return [{"value": item} for item in data]
        return data

    sys.exit(f"Error: Unexpected top-level JSON type: {type(data).__name__}")


def convert(
    input_path: Path,
    output_path: Path,
    sep: str = ".",
    array_delimiter: str = "|",
) -> None:
    records = load_json(input_path)

    flat_records = [flatten_record(r, sep=sep) for r in records]
    df = pd.DataFrame(flat_records)
    df = join_list_values(df, array_delimiter)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8")
    except PermissionError:
        sys.exit(f"Error: Permission denied writing: {output_path}")

    print(f"Converted {len(df)} record(s), {len(df.columns)} column(s)")
    print(f"Input : {input_path}")
    print(f"Output: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flatten a JSON file and write it as a CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Path to the input JSON file")
    parser.add_argument("output", type=Path, help="Path for the output CSV file")
    parser.add_argument(
        "--sep",
        default=".",
        help="Separator used when flattening nested object keys (e.g. user.name)",
    )
    parser.add_argument(
        "--array-delimiter",
        default="|",
        dest="array_delimiter",
        help="Delimiter used to join scalar array values into a single cell",
    )

    args = parser.parse_args()
    convert(args.input, args.output, sep=args.sep, array_delimiter=args.array_delimiter)


if __name__ == "__main__":
    main()
