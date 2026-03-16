#!/usr/bin/env python3
"""Import PhysioNet RR interval records into RecordRepository.
https://physionet.org/content/rr-interval-healthy-subjects

Loads data from rr-interval-healthy-subjects/ (PhysioNet dataset)
and populates the repository with tags and descriptions from patient-info.csv.
"""

import csv
from pathlib import Path

from rr_repository import RecordRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "rr-interval-healthy-subjects"
PATIENT_INFO_CSV = DATA_DIR / "patient-info.csv"


def is_digit_only_filename(path: Path) -> bool:
    """True if the stem (filename without extension) contains only digits."""
    return path.stem.isdigit()


def load_patient_info() -> dict[str, dict]:
    """Load patient-info.csv into a dict keyed by file ID (string)."""
    info: dict[str, dict] = {}
    with open(PATIENT_INFO_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            file_id = row["File"].strip()
            age = row.get("Age (years)", "").strip()
            gender = row.get("Gender", "").strip().upper()
            info[file_id] = {"age": age, "gender": gender}
    return info


def build_description(record_id: str, info: dict | None) -> str:
    """Build a human-readable description from patient info."""
    if not info or (not info.get("age") and not info.get("gender")):
        return f"PhysioNet RR record {record_id}"

    parts = []
    if info.get("age"):
        parts.append(f"Age {info['age']}y")
    if info.get("gender"):
        parts.append(info["gender"])
    return ", ".join(parts)


def patient_lookup(patient_info: dict[str, dict], stem: str) -> dict | None:
    """Lookup patient info by file stem (handles leading zeros, e.g. 000 -> 0)."""
    if stem in patient_info:
        return patient_info[stem]
    # Try normalizing numeric IDs (000 -> 0)
    if stem.isdigit():
        normalized = str(int(stem))
        return patient_info.get(normalized)
    return None


def parse_rr_intervals(path: Path) -> list[int]:
    """Parse RR intervals from file, skipping non-numeric lines (artifacts)."""
    rr_intervals: list[int] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rr_intervals.append(int(line))
        except ValueError:
            # Skip artifact lines (e.g. occasional '@' in PhysioNet data)
            continue
    return rr_intervals


def main() -> None:
    patient_info = load_patient_info()

    # Use the default repository, which writes to the configured DB path.
    repo = RecordRepository()
    data_files = sorted(p for p in DATA_DIR.glob("*.txt") if is_digit_only_filename(p))

    for path in data_files:
        record_id = path.stem
        tag = f"physionet-rr-{record_id}"
        info = patient_lookup(patient_info, record_id)
        description = build_description(record_id, info)

        rr_intervals = parse_rr_intervals(path)

        repo.add_record(tag=tag, description=description, rr_intervals=rr_intervals)
        print(f"Added {tag}: {description} ({len(rr_intervals)} intervals)")

    print(f"\nImported {len(data_files)} records.")


if __name__ == "__main__":
    main()
