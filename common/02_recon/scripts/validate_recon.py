#!/usr/bin/env python3
"""Independent validator for A-2 Structural Recon outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
A1_DIR = ROOT / "A_route" / "common" / "01_preprocessing"
A2_DIR = ROOT / "A_route" / "common" / "02_recon"
PROCESSED = A1_DIR / "processed"
A1_TABLES = A1_DIR / "tables"
TABLES = A2_DIR / "tables"
REPORTS = A2_DIR / "reports"
CHECK_FIELDS = ["runner", "check_id", "scope", "check_name", "status", "blocking", "expected", "actual", "detail"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Validator:
    def __init__(self) -> None:
        self.rows: list[dict[str, str]] = []
        self.blocking_failures: list[str] = []

    def check(self, scope: str, name: str, expected: Any, actual: Any, passed: bool, blocking: bool = True, detail: str = "") -> None:
        self.rows.append({
            "runner": "validator", "check_id": f"RECON-VALIDATOR-{len(self.rows) + 1:03d}",
            "scope": scope, "check_name": name, "status": "PASS" if passed else "FAIL",
            "blocking": str(blocking).lower(), "expected": str(expected), "actual": str(actual), "detail": detail,
        })
        if blocking and not passed:
            self.blocking_failures.append(f"{scope}: {name}")


def append_checks(rows: list[dict[str, str]]) -> None:
    path = TABLES / "recon_checks.csv"
    existing = read_csv(path)
    main_rows = [row for row in existing if row.get("runner") != "validator"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CHECK_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(main_rows + rows)


def validate(quiet: bool = False) -> int:
    v = Validator()
    gate_path = REPORTS / "RECON_GATE.md"
    v.check("pipeline", "gate absent before independent validator", False, gate_path.exists(), not gate_path.exists())

    frozen = read_csv(TABLES / "a1_frozen_hashes.csv")
    missing = []
    changed = []
    for row in frozen:
        path = ROOT / row["relative_path"]
        if not path.is_file():
            missing.append(row["relative_path"])
        elif sha256(path) != row["sha256"]:
            changed.append(row["relative_path"])
    current_paths = {
        path.relative_to(ROOT).as_posix()
        for path in A1_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    frozen_paths = {row["relative_path"] for row in frozen}
    added = sorted(current_paths - frozen_paths)
    v.check("a1_freeze", "no A-1 file removed", 0, len(missing), not missing, detail=" | ".join(missing[:5]))
    v.check("a1_freeze", "no A-1 file content changed", 0, len(changed), not changed, detail=" | ".join(changed[:5]))
    v.check("a1_freeze", "no A-1 file added", 0, len(added), not added, detail=" | ".join(added[:5]))

    cross = read_csv(TABLES / "cross_source_join_checks.csv")
    v.check("cross_source", "all exact key and marker checks pass", len(cross), sum(row["status"] == "PASS" for row in cross), bool(cross) and all(row["status"] == "PASS" for row in cross))
    crosswalk = read_csv(A1_TABLES / "time_marker_crosswalk.csv")
    v.check("cross_source", "144-marker sequence stable", "144 equal markers; 0:10..0:00+1", f"rows={len(crosswalk)}; first={crosswalk[0]['attachment1_time_marker']}; last={crosswalk[-1]['attachment1_time_marker']}", len(crosswalk) == 144 and all(row["all_sources_same_marker"] == "true" for row in crosswalk) and crosswalk[0]["attachment1_time_marker"] == "0:10" and crosswalk[-1]["attachment1_time_marker"] == "0:00+1")

    hypotheses = read_csv(TABLES / "time_semantics_hypotheses.csv")
    hypothesis_counts = Counter(row["hypothesis"] for row in hypotheses)
    v.check("time_semantics", "both hypotheses generated for 144 slots", {"H-END": 144, "H-START": 144}, dict(hypothesis_counts), hypothesis_counts == {"H-END": 144, "H-START": 144})
    selected = sum(row["final_convention_selected"] == "true" for row in hypotheses)
    v.check("time_semantics", "no hypothesis silently selected", 0, selected, selected == 0)
    time_report = (REPORTS / "TIME_ALIGNMENT_RECON.md").read_text(encoding="utf-8").strip()
    v.check("time_semantics", "OI-01 conclusion explicit", "OI01_STRUCTURAL_CONFLICT_CONFIRMED", time_report.splitlines()[-1], time_report.endswith("OI01_STRUCTURAL_CONFLICT_CONFIRMED"))

    forecast = read_csv(PROCESSED / "pv_forecast_hourly_long.csv")
    issue_counts = Counter(row["issue_datetime"] for row in forecast)
    horizons: dict[str, set[int]] = defaultdict(set)
    formula_ok = 0
    for row in forecast:
        horizons[row["issue_datetime"]].add(int(row["horizon_hour"]))
        formula_ok += int(datetime.fromisoformat(row["nominal_target_datetime"]) == datetime.fromisoformat(row["issue_datetime"]) + timedelta(hours=int(row["horizon_hour"])))
    complete = sum(count == 24 and horizons[key] == set(range(1, 25)) for key, count in issue_counts.items())
    v.check("forecast_grid", "1460 issue rows intact", 1460, len(issue_counts), len(issue_counts) == 1460)
    v.check("forecast_grid", "35040 forecast rows intact", 35040, len(forecast), len(forecast) == 35040)
    v.check("forecast_grid", "24 horizons intact per issue", 1460, complete, complete == 1460)
    v.check("forecast_grid", "target formula intact", 35040, formula_ok, formula_ok == 35040)
    coverage = read_csv(TABLES / "forecast_grid_coverage.csv")
    v.check("forecast_grid", "coverage row per issue clock", {"0:00", "6:00", "12:00", "18:00"}, {row["issue_clock"] for row in coverage}, len(coverage) == 4 and {row["issue_clock"] for row in coverage} == {"0:00", "6:00", "12:00", "18:00"})
    candidate = read_csv(TABLES / "forecast_actual_candidate_alignment.csv")
    v.check("forecast_grid", "candidate alignment rows", 35040, len(candidate), len(candidate) == 35040)
    v.check("forecast_grid", "candidate matches do not authorize semantic equality", 0, sum(row["semantic_alignment_authorized"] == "true" for row in candidate), all(row["semantic_alignment_authorized"] == "false" for row in candidate))
    forecast_report = (REPORTS / "FORECAST_GRID_RECON.md").read_text(encoding="utf-8").strip()
    v.check("forecast_grid", "OI-13 conclusion explicit", "OI13_REMAINS_OPEN", forecast_report.splitlines()[-1], forecast_report.endswith("OI13_REMAINS_OPEN"))

    info = read_csv(TABLES / "information_availability_matrix.csv")
    contexts = Counter((row["problem"], row["decision_time"]) for row in info)
    required = {("P1", "0:00"), ("P2", "daily 0:00"), ("P3", "0:00"), ("P3", "6:00"), ("P3", "12:00"), ("P3", "18:00"), ("P4-2", "0:00"), ("P4-3", "0:00"), ("P4-3", "6:00"), ("P4-3", "12:00"), ("P4-3", "18:00")}
    allowed = {"KNOWN_BY_PROBLEM_ASSUMPTION", "AVAILABLE_FROM_PUBLISHED_FORECAST", "REALIZED_HISTORY_ONLY", "CURRENT_STATE_IF_OBSERVED", "EX_POST_ONLY", "AMBIGUOUS_FROM_STATEMENT"}
    v.check("information_set", "all required decision contexts", 11, len(contexts), set(contexts) == required and set(contexts.values()) == {10})
    v.check("information_set", "classification vocabulary", allowed, sorted({row["classification"] for row in info}), all(row["classification"] in allowed for row in info))
    future_actual_rows = [row for row in info if row["quantity"] in {"future actual load", "future PV actual"} and row["problem"] != "P1"]
    v.check("information_set", "future actuals are ex-post outside deterministic P1 load", "EX_POST_ONLY", sorted({row["classification"] for row in future_actual_rows}), all(row["classification"] == "EX_POST_ONLY" for row in future_actual_rows))

    required_tables = {
        "cross_source_join_checks.csv", "time_semantics_hypotheses.csv", "source_template_slot_alignment.csv",
        "forecast_grid_coverage.csv", "forecast_actual_candidate_alignment.csv", "information_availability_matrix.csv",
        "state_unit_contract.csv", "output_contract_recon.csv", "recon_checks.csv",
    }
    required_reports = {
        "CROSS_SOURCE_CONTRACT.md", "TIME_ALIGNMENT_RECON.md", "FORECAST_GRID_RECON.md",
        "INFORMATION_SET_RECON.md", "STATE_UNIT_RECON.md", "OUTPUT_CONTRACT_RECON.md",
        "RECON_SUMMARY.md", "RUN_INFO.md",
    }
    actual_tables = {path.name for path in TABLES.glob("*.csv")}
    actual_reports = {path.name for path in REPORTS.glob("*.md")}
    v.check("artifacts", "all required pre-gate tables exist", required_tables, sorted(actual_tables), required_tables <= actual_tables)
    v.check("artifacts", "all required pre-gate reports exist", required_reports, sorted(actual_reports), required_reports <= actual_reports)
    v.check("artifacts", "final gate intentionally pending", False, gate_path.exists(), not gate_path.exists(), detail="Main writes RECON_GATE.md only after validator completion.")

    generated_names = [path.name.lower() for directory in (TABLES, REPORTS) for path in directory.iterdir() if path.is_file()]
    forbidden_metric_files = [name for name in generated_names if any(token in name for token in ("mae", "rmse", "bias", "forecast_error"))]
    v.check("scope", "no forecast-error metric artifact generated", 0, len(forbidden_metric_files), not forbidden_metric_files)
    forbidden_dirs = [path.name for path in A2_DIR.iterdir() if path.is_dir() and path.name.lower() in {"eda", "model", "models", "optimization"}]
    v.check("scope", "no EDA/model output directory created", 0, len(forbidden_dirs), not forbidden_dirs)

    append_checks(v.rows)
    if not quiet:
        print(f"RECON VALIDATOR: {'FAIL' if v.blocking_failures else 'PASS'}")
        print(f"PASS={sum(row['status'] == 'PASS' for row in v.rows)} FAIL={sum(row['status'] == 'FAIL' for row in v.rows)}")
    return 1 if v.blocking_failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    raise SystemExit(validate(quiet=args.quiet))
