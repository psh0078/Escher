from __future__ import annotations

import csv
import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComparisonMismatch:
    file_name: str
    reason: str


@dataclass(frozen=True)
class ComparisonReport:
    compared_files: int
    matched_files: int
    mismatches: tuple[ComparisonMismatch, ...]

    @property
    def ok(self) -> bool:
        return not self.mismatches


def compare_misim_csv_dirs(
    escher_dir: Path,
    misim_dir: Path,
    *,
    tolerance: float = 1e-9,
) -> ComparisonReport:
    """Compares MiSim-style CSV outputs by file, time, and numeric values.

    Time complexity is O(F + R), where F is file count and R is total rows.
    """
    escher_files = sorted(p.name for p in escher_dir.glob("*.csv"))
    misim_files = sorted(p.name for p in misim_dir.glob("*.csv"))

    mismatches: list[ComparisonMismatch] = []

    escher_set = set(escher_files)
    misim_set = set(misim_files)
    missing_in_escher = sorted(misim_set - escher_set)
    missing_in_misim = sorted(escher_set - misim_set)

    for name in missing_in_escher:
        mismatches.append(
            ComparisonMismatch(file_name=name, reason="missing_in_escher")
        )
    for name in missing_in_misim:
        mismatches.append(ComparisonMismatch(file_name=name, reason="missing_in_misim"))

    shared_files = sorted(escher_set & misim_set)
    matched_files = 0
    for file_name in shared_files:
        escher_rows = _read_rows(escher_dir / file_name)
        misim_rows = _read_rows(misim_dir / file_name)
        mismatch_reason = _compare_rows(escher_rows, misim_rows, tolerance=tolerance)
        if mismatch_reason is None:
            matched_files += 1
            continue
        mismatches.append(
            ComparisonMismatch(file_name=file_name, reason=mismatch_reason)
        )

    return ComparisonReport(
        compared_files=len(shared_files),
        matched_files=matched_files,
        mismatches=tuple(mismatches),
    )


def _read_rows(path: Path) -> list[tuple[float, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader, None)
        if header != ["SimulationTime", "Value"]:
            raise ValueError(f"Unexpected CSV header in {path}: {header}")

        rows: list[tuple[float, str]] = []
        for raw_time, raw_value in reader:
            rows.append((float(raw_time), raw_value))
        return rows


def _compare_rows(
    escher_rows: list[tuple[float, str]],
    misim_rows: list[tuple[float, str]],
    *,
    tolerance: float,
) -> str | None:
    if len(escher_rows) != len(misim_rows):
        return f"row_count_mismatch:{len(escher_rows)}!={len(misim_rows)}"

    for idx, ((escher_time, escher_value), (misim_time, misim_value)) in enumerate(
        zip(escher_rows, misim_rows)
    ):
        if abs(escher_time - misim_time) > tolerance:
            return f"time_mismatch_at_row:{idx}"

        if _is_float(escher_value) and _is_float(misim_value):
            if abs(float(escher_value) - float(misim_value)) > tolerance:
                return f"value_mismatch_at_row:{idx}"
            continue

        if escher_value != misim_value:
            return f"value_mismatch_at_row:{idx}"

    return None


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Escher and MiSim CSV metric directories."
    )
    parser.add_argument("escher_dir", type=Path)
    parser.add_argument("misim_dir", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()

    report = compare_misim_csv_dirs(
        args.escher_dir,
        args.misim_dir,
        tolerance=args.tolerance,
    )
    print(f"Compared files: {report.compared_files}")
    print(f"Matched files: {report.matched_files}")
    if report.ok:
        print("Result: MATCH")
        return 0

    print("Result: MISMATCH")
    for mismatch in report.mismatches:
        print(f"- {mismatch.file_name}: {mismatch.reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
