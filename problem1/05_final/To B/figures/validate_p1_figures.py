"""Cross-check P1 figure inputs and outputs against all frozen result files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIGURE_STEMS = (
    "fig_p1_energy_dispatch_price",
    "fig_p1_storage_operation_soc",
)


def main() -> None:
    schedule = pd.read_csv(ROOT / "p1_schedule_internal.csv")
    key_results = pd.read_csv(ROOT / "KEY_RESULTS.csv")
    specified = pd.read_csv(ROOT / "p1_specified_purchase_intervals.csv")
    storage_4h = pd.read_csv(ROOT / "p1_storage_4h_summary.csv")

    values = {
        (row["category"], row["metric"]): float(row["value"])
        for _, row in key_results.iterrows()
        if row["metric"] != "time_convention"
    }
    checks: dict[str, bool] = {}
    checks["144 H-END slots"] = (
        len(schedule) == 144
        and schedule["source_marker"].iloc[0] == "0:10"
        and schedule["source_marker"].iloc[-1] == "0:00+1"
    )
    checks["physical 0-24h"] = bool(
        np.allclose(schedule["interval_start_hour"], np.arange(144) / 6, atol=1e-9)
        and np.isclose(schedule["interval_end_hour"].iloc[-1], 24.0)
    )
    checks["purchase total"] = bool(
        np.isclose(
            schedule["purchase_kwh"].sum(),
            values[("final", "total_purchase")],
            atol=1e-6,
        )
    )
    checks["purchase cost"] = bool(
        np.isclose(
            np.dot(schedule["purchase_kwh"], schedule["price_yuan_per_kwh"]),
            values[("final", "total_purchase_cost")],
            atol=1e-6,
        )
    )
    checks["charge total"] = bool(
        np.isclose(
            schedule["charge_bus_kwh"].sum(),
            values[("storage", "total_charge_bus")],
            atol=1e-6,
        )
    )
    checks["discharge total"] = bool(
        np.isclose(
            schedule["discharge_bus_kwh"].sum(),
            values[("storage", "total_discharge_bus")],
            atol=1e-6,
        )
    )

    specified_actual = []
    for _, row in specified.iterrows():
        match = schedule.loc[
            schedule["slot_id"].eq(int(row["slot_id"])), "purchase_kwh"
        ]
        specified_actual.append(match.iloc[0])
    checks["six specified intervals"] = bool(
        np.allclose(specified_actual, specified["计划购电量_kWh"], atol=1e-8)
    )

    grouped = (
        schedule.groupby((schedule["slot_id"] - 1) // 24)[
            ["charge_bus_kwh", "discharge_bus_kwh"]
        ]
        .sum()
        .to_numpy()
    )
    checks["six four-hour blocks"] = bool(
        np.allclose(
            grouped,
            storage_4h[["充电量_kWh", "放电量_kWh"]].to_numpy(),
            atol=1e-6,
        )
    )

    soc = np.r_[schedule["soc_start_kwh"].iloc[0], schedule["soc_end_kwh"]]
    checks["SOC endpoints and bounds"] = bool(
        np.isclose(soc[0], 6000.0)
        and np.isclose(soc[-1], 6000.0)
        and np.isclose(soc.min(), values[("storage", "soc_min")])
        and np.isclose(soc.max(), values[("storage", "soc_max")])
    )
    checks["all figure formats"] = all(
        (ROOT / "figures" / f"{stem}.{suffix}").stat().st_size > 0
        for stem in FIGURE_STEMS
        for suffix in ("pdf", "png", "svg")
    )

    for name, passed in checks.items():
        print(("PASS " if passed else "FAIL ") + name)
    if not all(checks.values()):
        raise SystemExit(1)
    print("INDEPENDENT VALIDATION PASS")


if __name__ == "__main__":
    main()
