#!/usr/bin/env python3
"""Problem 3: causal rolling electricity procurement and storage dispatch."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from copy import copy
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from scipy.optimize import linprog
from scipy.sparse import lil_matrix


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "附件"
OUT = ROOT / "outputs"
FIG = ROOT / "figures"
REPORT = ROOT / "reports"
ETA_C = ETA_D = 0.9
SOC_MIN, SOC_MAX, SOC_INITIAL = 1200.0, 10800.0, 6000.0
STEP_MAX = 833.3333
ALPHA, RISK_LAMBDA, EMERGENCY_MULT = 0.9, 0.2, 5.0
ISSUES = (0, 6, 12, 18)


def load_inputs():
    tariff = pd.read_excel(DATA / "附件1.xlsx")
    price = tariff["电价"].to_numpy(float)
    nominal_load = tariff["小区负载"].to_numpy(float)
    nominal_pv = tariff["光伏发电预测功率"].to_numpy(float)
    load_df = pd.read_excel(DATA / "附件2.xlsx", sheet_name="小区负载")
    pv_df = pd.read_excel(DATA / "附件2.xlsx", sheet_name="光伏发电实际功率")
    dates = pd.to_datetime(load_df.iloc[:, 0]).dt.normalize()
    load = load_df.iloc[:, 1:].to_numpy(float)
    pv = pv_df.iloc[:, 1:].to_numpy(float)
    f = pd.read_excel(DATA / "附件3.xlsx")
    f["日期"] = pd.to_datetime(f["日期"].ffill()).dt.normalize()
    f["issue"] = f["预报时刻"].astype(str).str.extract(r"(\d+)")[0].astype(int)
    fvals = f.filter(regex=r"^预报\d+小时$").to_numpy(float)
    forecast = {(r["日期"], int(r["issue"])): fvals[i] for i, r in f.iterrows()}
    return dates, load, pv, price, nominal_load, nominal_pv, forecast


def endpoint_value(arr, date_index, day, minute):
    """Value at a right endpoint; minute may be on the following day."""
    target_day = day + pd.Timedelta(days=minute // 1440)
    m = minute % 1440
    # The row-end `0:00+1` is midnight at the end of its row date.
    source_day = target_day - pd.Timedelta(days=1) if m == 0 else target_day
    idx = date_index.get(source_day)
    proxy = False
    if idx is None:
        idx = date_index[day]
        m = 10
        proxy = True
    col = m // 10 - 1 if m else 143
    return float(arr[idx, col]), proxy


def operational_profile(arr, date_index, day):
    vals, proxy = [], False
    for m in range(20, 1451, 10):
        v, p = endpoint_value(arr, date_index, day, m)
        vals.append(v)
        proxy |= p
    return np.asarray(vals), proxy


def build_load_forecasts(dates, load):
    """Expanding causal blend of weekly persistence and adaptive ridge."""
    n, slots = load.shape
    pred = np.zeros_like(load, dtype=float)
    blend = np.zeros(n)
    nominal = np.nanmean(load[: min(7, n)], axis=0)
    for d in range(n):
        if d == 0:
            pred[d] = nominal
            continue
        weekly = load[d - 7] if d >= 7 else np.mean(load[:d], axis=0)
        start = max(7, d - 35)
        rows = np.arange(start, d)
        if len(rows) >= 4:
            x = np.column_stack([
                np.ones(len(rows) * slots),
                load[rows - 1].ravel(),
                load[rows - 7].ravel(),
                np.repeat(np.sin(2 * np.pi * rows / 7), slots),
                np.repeat(np.cos(2 * np.pi * rows / 7), slots),
            ])
            y = load[rows].ravel()
            scale = np.std(x[:, 1:3], axis=0)
            scale[scale < 1] = 1
            xs = x.copy()
            xs[:, 1:3] /= scale
            reg = np.diag([0, 8, 8, 8, 8])
            beta = np.linalg.solve(xs.T @ xs + reg, xs.T @ y)
            xt = np.column_stack([
                np.ones(slots), load[d - 1], weekly,
                np.full(slots, np.sin(2 * np.pi * d / 7)),
                np.full(slots, np.cos(2 * np.pi * d / 7)),
            ])
            xt[:, 1:3] /= scale
            ridge = xt @ beta
        else:
            ridge = 0.55 * load[d - 1] + 0.45 * weekly
        hist = np.arange(max(1, d - 14), d)
        if len(hist) and d >= 8:
            ridge_err = np.sqrt(np.mean((load[hist] - pred[hist]) ** 2))
            week_err = np.sqrt(np.mean((load[hist] - load[hist - 7]) ** 2))
            w = week_err / max(ridge_err + week_err, 1e-9)
        else:
            w = 0.6
        blend[d] = w
        pred[d] = np.maximum(0, w * ridge + (1 - w) * weekly)
    return pred, blend


def hourly_actual(pv, date_index, day, issue):
    vals = []
    for lead in range(1, 25):
        v, _ = endpoint_value(pv, date_index, day, issue * 60 + lead * 60)
        vals.append(v)
    return np.asarray(vals)


def prepare_pv_errors(dates, pv, forecast):
    date_index = {d: i for i, d in enumerate(dates)}
    corrected_residuals = {}
    bias_before = {}
    for issue in ISSUES:
        running = []
        for day in dates:
            raw = forecast[(day, issue)]
            actual = hourly_actual(pv, date_index, day, issue)
            bias = np.zeros(24)
            # Validate each lead-time correction on the latest seven completed
            # days; estimate the candidate on the preceding rolling window.
            if len(running) >= 14:
                history = np.asarray(running[-35:])
                train, validation = history[:-7], history[-7:]
                candidate = np.median(train, axis=0)
                use = np.mean(np.abs(validation - candidate), axis=0) < np.mean(
                    np.abs(validation), axis=0
                )
                current = np.median(history, axis=0)
                bias[use] = current[use]
            bias_before[(day, issue)] = bias
            residual = actual - raw - bias
            corrected_residuals[(day, issue)] = residual
            running.append(actual - raw)
    return bias_before, corrected_residuals


def raw_pv_residuals(dates, pv, forecast):
    date_index = {d: i for i, d in enumerate(dates)}
    return {
        (day, issue): hourly_actual(pv, date_index, day, issue) - forecast[(day, issue)]
        for issue in ISSUES
        for day in dates
    }


def january_bias_gate(dates, pv, forecast, candidate_bias):
    date_index = {d: i for i, d in enumerate(dates)}
    raw_errors, corrected_errors = [], []
    for day in dates[dates < pd.Timestamp("2025-02-01")]:
        for issue in ISSUES:
            actual = hourly_actual(pv, date_index, day, issue)
            raw = forecast[(day, issue)]
            corrected = np.maximum(0, raw + candidate_bias[(day, issue)])
            raw_errors.extend(np.abs(actual - raw))
            corrected_errors.extend(np.abs(actual - corrected))
    raw_mae = float(np.mean(raw_errors))
    corrected_mae = float(np.mean(corrected_errors))
    return corrected_mae < raw_mae, raw_mae, corrected_mae


def interpolate_hourly(issue, hourly, target_minutes, anchor=None):
    xp = issue * 60 + np.arange(1, 25) * 60
    values = np.asarray(hourly)
    if anchor is not None:
        xp = np.r_[issue * 60, xp]
        values = np.r_[anchor, values]
    return np.interp(target_minutes, xp, values, left=values[0], right=values[-1])


def pv_scenarios(day, issue, dates, forecast, bias_before, residuals, target_minutes,
                 anchor_actual, count=5):
    corrected_hourly = np.maximum(0, forecast[(day, issue)] + bias_before[(day, issue)])
    central = interpolate_hourly(issue, corrected_hourly, target_minutes, anchor_actual)
    past = [d for d in dates if d < day and (d, issue) in residuals]
    if not past:
        return np.repeat(central[None, :], count, axis=0), central, []
    trajectories = np.asarray([residuals[(d, issue)] for d in past])
    scores = trajectories.sum(axis=1)
    order = np.argsort(scores)
    qidx = np.rint(np.quantile(np.arange(len(order)), [0.1, 0.3, 0.5, 0.7, 0.9])).astype(int)
    chosen = [past[order[min(i, len(order) - 1)]] for i in qidx]
    scenarios = []
    for chosen_day in chosen:
        err10 = interpolate_hourly(issue, residuals[(chosen_day, issue)], target_minutes, 0.0)
        scenarios.append(np.maximum(0, central + err10))
    return np.asarray(scenarios), central, chosen


def aggregate_blocks(x10):
    return np.asarray([np.sum(x10[a:min(a + 6, len(x10))]) for a in range(0, len(x10), 6)])


def solve_stochastic_lp(net_scenarios, prices_h, block_lengths, soc0, terminal_soc, previous=None,
                        risk_lambda=RISK_LAMBDA):
    """Common contract with scenario storage recourse and emergency-cost CVaR."""
    s_count, h_count = net_scenarios.shape
    # g, up, down, then scenario blocks [charge, discharge, curtail, emergency, soc(H+1)], eta, excess
    common = 3 * h_count
    block = 5 * h_count + 1
    eta_i = common + s_count * block
    excess0 = eta_i + 1
    nvar = excess0 + s_count
    c = np.zeros(nvar)
    if previous is None:
        c[:h_count] = prices_h
    else:
        c[h_count:2*h_count] = 1.5 * prices_h
        c[2*h_count:3*h_count] = -0.5 * prices_h
    weights = np.full(s_count, 1 / s_count)
    for s in range(s_count):
        b = common + s * block
        c[b + 3*h_count:b + 4*h_count] = (1 - risk_lambda) * weights[s] * EMERGENCY_MULT * prices_h
    c[eta_i] = risk_lambda
    c[excess0:] = risk_lambda * weights / (1 - ALPHA)

    eq_rows = h_count * (1 if previous is not None else 0) + s_count * (2*h_count + 2)
    aeq = lil_matrix((eq_rows, nvar)); beq = np.zeros(eq_rows); r = 0
    if previous is not None:
        for h in range(h_count):
            aeq[r, h] = 1; aeq[r, h_count+h] = -1; aeq[r, 2*h_count+h] = 1
            beq[r] = previous[h]; r += 1
    for s in range(s_count):
        b = common + s * block
        ch, dis, curt, emer, soc = b, b+h_count, b+2*h_count, b+3*h_count, b+4*h_count
        for h in range(h_count):
            aeq[r, h] = 1; aeq[r, dis+h] = 1; aeq[r, emer+h] = 1
            aeq[r, ch+h] = -1; aeq[r, curt+h] = -1
            beq[r] = net_scenarios[s, h]; r += 1
            aeq[r, soc+h+1] = 1; aeq[r, soc+h] = -1
            aeq[r, ch+h] = -ETA_C; aeq[r, dis+h] = 1/ETA_D; r += 1
        aeq[r, soc] = 1; beq[r] = soc0; r += 1
        aeq[r, soc+h_count] = 1; beq[r] = terminal_soc; r += 1

    aub = lil_matrix((s_count, nvar)); bub = np.zeros(s_count)
    for s in range(s_count):
        b = common + s * block
        emer = b + 3*h_count
        for h in range(h_count):
            aub[s, emer+h] = EMERGENCY_MULT * prices_h[h]
        aub[s, eta_i] = -1; aub[s, excess0+s] = -1
    bounds = []
    bounds += [(0, None)] * h_count
    bounds += [(0, None)] * (2*h_count)
    power_bounds = [(0, n*STEP_MAX) for n in block_lengths]
    for _ in range(s_count):
        bounds += power_bounds * 2
        bounds += [(0, None)] * h_count * 2
        bounds += [(SOC_MIN, SOC_MAX)] * (h_count + 1)
    bounds += [(None, None)] + [(0, None)] * s_count
    result = linprog(c, A_ub=aub.tocsr(), b_ub=bub, A_eq=aeq.tocsr(), b_eq=beq,
                     bounds=bounds, method="highs", options={"presolve": True})
    if not result.success:
        raise RuntimeError(f"LP failed: {result.message}")
    return result.x[:h_count], float(result.fun)


def distribute_hourly(g_h, net10):
    g = np.zeros(len(net10))
    for h, total in enumerate(g_h):
        sl = slice(6*h, min(6*h+6, len(net10)))
        w = np.maximum(net10[sl], 0) + 1.0
        g[sl] = total * w / w.sum()
    return g


def execute_interval(contract, load_kw, pv_kw, soc):
    demand = load_kw / 6
    solar = pv_kw / 6
    balance = contract + solar - demand
    charge = discharge = emergency = curtail = spill = 0.0
    if balance >= 0:
        charge = min(balance, STEP_MAX, (SOC_MAX - soc) / ETA_C)
        remainder = balance - charge
        curtail = min(remainder, solar)
        spill = max(0, remainder - curtail)
        soc_next = soc + ETA_C * charge
    else:
        need = -balance
        discharge = min(need, STEP_MAX, (soc - SOC_MIN) * ETA_D)
        emergency = need - discharge
        soc_next = soc - discharge / ETA_D
    return charge, discharge, emergency, curtail, spill, soc_next


def run_policy(policy, dates, load, pv, prices, load_pred, forecast, bias, residuals,
               stochastic=True, collect=False):
    date_index = {d: i for i, d in enumerate(dates)}
    output_days = [d for d in dates if d >= pd.Timestamp("2025-02-01")]
    allowed = tuple(policy)
    soc = SOC_INITIAL
    rows, adjustments, daily = [], [], []
    previous_calendar_first = None
    proxy_used = False
    for day in dates:
        load_actual, proxy_l = operational_profile(load, date_index, day)
        pv_actual, proxy_p = operational_profile(pv, date_index, day)
        proxy_used |= proxy_l or proxy_p
        # Causal day-ahead load profile; update bias uses only already observed intervals.
        load_fc_base, _ = operational_profile(load_pred, date_index, day)
        price10 = np.r_[prices[1:], prices[0]] / 1.0
        contract0 = np.zeros(144); contract = np.zeros(144)
        settlement = 0.0; issue_objectives = []
        day_soc0 = soc
        versions = []
        executed_today = []
        next_issue_pos = {0: 0, 6: 35, 12: 71, 18: 107}
        update_points = sorted(set(allowed) | {24})
        for ui, issue in enumerate(update_points[:-1]):
            start = next_issue_pos[issue]
            if issue == 0:
                load_fc = load_fc_base.copy()
            else:
                observed_error = load_actual[:start] - load_fc_base[:start]
                correction = float(np.mean(observed_error[-min(18, len(observed_error)):]))
                decay = np.exp(-np.arange(144-start) / 36)
                load_fc = load_fc_base.copy()
                load_fc[start:] = np.maximum(0, load_fc[start:] + correction * decay)
            target_minutes = np.arange(20 + 10*start, 1451, 10)
            anchor_actual, anchor_proxy = endpoint_value(pv, date_index, day, issue * 60)
            proxy_used |= anchor_proxy
            pv_s, pv_central, selected = pv_scenarios(day, issue, dates, forecast, bias,
                                                       residuals, target_minutes, anchor_actual)
            load_energy = load_fc[start:] / 6
            net10_s = load_energy[None, :] - pv_s / 6
            net_h = np.asarray([aggregate_blocks(x) for x in net10_s])
            block_lengths = [min(6, len(load_energy)-a) for a in range(0, len(load_energy), 6)]
            p_h = np.asarray([np.mean(price10[start+a:start+min(a+6, len(load_energy))])
                              for a in range(0, len(load_energy), 6)])
            prev_h = aggregate_blocks(contract[start:]) if issue else None
            if not stochastic:
                net_h = np.mean(net_h, axis=0, keepdims=True)
            g_h, objective = solve_stochastic_lp(net_h, p_h, block_lengths, soc, day_soc0, prev_h,
                                                  RISK_LAMBDA if stochastic else 0.0)
            central_net10 = load_energy - pv_central / 6
            new10 = distribute_hourly(g_h, central_net10)
            old = contract[start:].copy()
            contract[start:] = new10
            if issue == 0:
                contract0 = contract.copy()
                increment = float(np.sum(price10 * contract0))
            else:
                delta = contract[start:] - old
                increment = float(np.sum(price10[start:] * (1.5*np.maximum(delta, 0) - 0.5*np.maximum(-delta, 0))))
            settlement += increment
            issue_objectives.append(objective)
            versions.append((issue, start, contract.copy(), selected, increment))
            if collect and day in output_days:
                for t in range(start, 144):
                    adjustments.append({
                        "date": day.date().isoformat(), "issue_hour": issue, "slot": t,
                        "endpoint_minute": 20 + 10*t, "previous_kwh": old[t-start] if issue else 0.0,
                        "new_kwh": contract[t], "up_kwh": max(contract[t]-(old[t-start] if issue else 0), 0),
                        "down_kwh": max((old[t-start] if issue else 0)-contract[t], 0),
                        "incremental_cost": increment, "scenario_dates": ";".join(str(x.date()) for x in selected),
                    })
            end = next_issue_pos.get(update_points[ui+1], 144)
            for t in range(start, end):
                ch, dis, emerg, curt, spill, soc_next = execute_interval(
                    contract[t], load_actual[t], pv_actual[t], soc)
                executed = {
                    "charge_kwh": ch, "discharge_kwh": dis,
                    "emergency_kwh": emerg, "curtailment_kwh": curt,
                    "grid_spill_kwh": spill, "soc_start_kwh": soc,
                    "soc_end_kwh": soc_next,
                }
                executed_today.append(executed)
                if collect and day in output_days:
                    rows.append({
                        "date": day.date().isoformat(), "slot": t, "endpoint_minute": 20+10*t,
                        "price": price10[t], "load_kw": load_actual[t], "pv_kw": pv_actual[t],
                        "load_forecast_kw": load_fc[t], "pv_forecast_kw": pv_central[t-start] if t >= start else np.nan,
                        "initial_contract_kwh": contract0[t], "final_contract_kwh": np.nan,
                        "active_contract_kwh": contract[t], "charge_kwh": ch, "discharge_kwh": dis,
                        "emergency_kwh": emerg, "curtailment_kwh": curt, "grid_spill_kwh": spill,
                        "soc_start_kwh": soc, "soc_end_kwh": soc_next, "active_issue": issue,
                    })
                soc = soc_next
        if collect and day in output_days:
            final_contract = versions[-1][2]
            day_rows = rows[-144:]
            calendar_rows = [previous_calendar_first, *executed_today[:143]]
            if previous_calendar_first is None or len(calendar_rows) != 144:
                raise RuntimeError("缺少上一运营日0:00-0:10执行记录")
            for r in day_rows:
                r["final_contract_kwh"] = final_contract[r["slot"]]
            day_summary = {
                "date": day.date().isoformat(),
                "soc_start_kwh": calendar_rows[0]["soc_start_kwh"],
                "soc_end_kwh": calendar_rows[-1]["soc_end_kwh"],
                "initial_contract_kwh": float(contract0.sum()), "final_contract_kwh": float(final_contract.sum()),
                "settlement_cost": settlement, "emergency_kwh": sum(r["emergency_kwh"] for r in day_rows),
                "emergency_cost": sum(EMERGENCY_MULT*r["price"]*r["emergency_kwh"] for r in day_rows),
                "charge_kwh": sum(r["charge_kwh"] for r in day_rows),
                "discharge_kwh": sum(r["discharge_kwh"] for r in day_rows),
                "curtailment_kwh": sum(r["curtailment_kwh"] for r in day_rows),
                "grid_spill_kwh": sum(r["grid_spill_kwh"] for r in day_rows),
                "total_cost": settlement + sum(EMERGENCY_MULT*r["price"]*r["emergency_kwh"] for r in day_rows),
                "mean_lp_objective": float(np.mean(issue_objectives)),
            }
            for block in range(6):
                block_rows = calendar_rows[block * 24:(block + 1) * 24]
                day_summary[f"block_{block}_charge_kwh"] = sum(r["charge_kwh"] for r in block_rows)
                day_summary[f"block_{block}_discharge_kwh"] = sum(r["discharge_kwh"] for r in block_rows)
            daily.append(day_summary)
        previous_calendar_first = executed_today[-1]
    return pd.DataFrame(rows), pd.DataFrame(adjustments), pd.DataFrame(daily), proxy_used


def forecast_metrics(dates, load, load_pred, forecast, bias, pv):
    records = []
    date_index = {d: i for i, d in enumerate(dates)}
    for day in dates:
        if day < pd.Timestamp("2025-02-01"):
            continue
        i = date_index[day]
        records.append({"date": day.date().isoformat(), "series": "load_day_ahead",
                        "issue_hour": 0, "mae_kw": np.mean(np.abs(load[i]-load_pred[i])),
                        "rmse_kw": np.sqrt(np.mean((load[i]-load_pred[i])**2))})
        for issue in ISSUES:
            actual = hourly_actual(pv, date_index, day, issue)
            raw = forecast[(day, issue)]
            corrected = np.maximum(0, raw + bias[(day, issue)])
            records.append({"date": day.date().isoformat(), "series": "pv_raw",
                            "issue_hour": issue, "mae_kw": np.mean(np.abs(actual-raw)),
                            "rmse_kw": np.sqrt(np.mean((actual-raw)**2))})
            records.append({"date": day.date().isoformat(), "series": "pv_corrected",
                            "issue_hour": issue, "mae_kw": np.mean(np.abs(actual-corrected)),
                            "rmse_kw": np.sqrt(np.mean((actual-corrected)**2))})
    return pd.DataFrame(records)


def emergency_periods(schedule):
    result = []
    for date, group in schedule.groupby("date", sort=False):
        active = group["emergency_kwh"].to_numpy() > 1e-8
        starts = np.where(active & ~np.r_[False, active[:-1]])[0]
        ends = np.where(active & ~np.r_[active[1:], False])[0]
        for a, b in zip(starts, ends):
            sm = 10 + 10*a; em = 20 + 10*b
            label = f"{sm//60%24}:{sm%60:02d}-{em//60%24}:{em%60:02d}" + ("+1" if em >= 1440 else "")
            result.append({"日期": date, "购电时间段": label,
                           "购电量": group.iloc[a:b+1]["emergency_kwh"].sum()})
    return pd.DataFrame(result)


def write_workbook(schedule, daily):
    shutil.copy2(DATA / "附件5" / "result3.xlsx", ROOT / "result3.xlsx")
    workbook = load_workbook(ROOT / "result3.xlsx")
    plan_sheet = workbook["计划购电量"]
    adjusted_sheet = workbook["调整购电量"]
    for row, (date, g) in enumerate(schedule.groupby("date", sort=False), start=2):
        day = daily[daily["date"] == date].iloc[0]
        date_value = datetime.fromisoformat(date)
        for sheet in (plan_sheet, adjusted_sheet):
            sheet.cell(row, 1, date_value)
        for column, value in enumerate(g["initial_contract_kwh"], start=2):
            plan_sheet.cell(row, column, float(value))
        for column, value in enumerate(g["final_contract_kwh"], start=2):
            adjusted_sheet.cell(row, column, float(value))
        plan_sheet.cell(row, 146, float(day["initial_contract_kwh"]))
        plan_sheet.cell(row, 147, float(np.sum(g["price"] * g["initial_contract_kwh"])))
        adjusted_sheet.cell(row, 146, float(day["final_contract_kwh"]))
        adjusted_sheet.cell(row, 147, float(day["settlement_cost"]))

    storage = workbook["充放电量"]
    storage_styles = [
        [copy(storage.cell(row, column)._style) for column in range(1, 7)]
        for row in range(2, 8)
    ]
    storage.delete_rows(2, storage.max_row - 1)
    labels = ["0:00-4:00", "4:00-8:00", "8:00-12:00", "12:00-16:00",
              "16:00-20:00", "20:00-24:00"]
    row = 2
    for _, day in daily.iterrows():
        for block, label in enumerate(labels):
            for column, style in enumerate(storage_styles[block], start=1):
                storage.cell(row, column)._style = copy(style)
            storage.cell(row, 1, datetime.fromisoformat(day["date"]) if block == 0 else None)
            storage.cell(row, 2, label)
            storage.cell(row, 3, float(day[f"block_{block}_charge_kwh"]))
            storage.cell(row, 4, float(day[f"block_{block}_discharge_kwh"]))
            if block == 0:
                storage.cell(row, 5, "0:00")
                storage.cell(row, 6, float(day["soc_start_kwh"]))
            elif block == 1:
                storage.cell(row, 5, "24:00")
                storage.cell(row, 6, float(day["soc_end_kwh"]))
            row += 1

    emergency = workbook["紧急购电量"]
    emergency_style = [copy(emergency.cell(2, column)._style) for column in range(1, 4)]
    emergency.delete_rows(2, emergency.max_row - 1)
    row = 2
    periods = emergency_periods(schedule)
    previous_date = None
    for _, item in periods.iterrows():
        for column, style in enumerate(emergency_style, start=1):
            emergency.cell(row, column)._style = copy(style)
        emergency.cell(row, 1, datetime.fromisoformat(item["日期"]) if item["日期"] != previous_date else None)
        emergency.cell(row, 2, item["购电时间段"])
        emergency.cell(row, 3, float(item["购电量"]))
        previous_date = item["日期"]
        row += 1
    workbook.save(ROOT / "result3.xlsx")


def make_figures(schedule, daily, metrics, comparison):
    plt.rcParams.update({
        "font.size": 9,
        "font.sans-serif": ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "Droid Sans Fallback"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
    })
    pv_m = metrics[metrics.series.str.startswith("pv")].groupby(["series", "issue_hour"])["mae_kw"].mean().unstack(0)
    ax = pv_m.plot(marker="o", figsize=(6.2, 3.5)); ax.set_xlabel("预报发布时间 / h"); ax.set_ylabel("光伏预报 MAE / kW")
    ax.legend(["候选残差校正", "附件原始预报"]); plt.tight_layout(); plt.savefig(FIG/"forecast_update_comparison.pdf"); plt.savefig(FIG/"forecast_update_comparison.png", dpi=300); plt.close()
    labels = [
        row.policy + ("\n随机CVaR" if "stochastic" in row.model else "\n确定性")
        for row in comparison.itertuples()
    ]
    colors = ["#396A93"] * (len(comparison) - 1) + ["#B04A3A"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0)); ax.bar(labels, comparison.total_cost/1e6, color=colors)
    ax.set_ylabel("总费用 / 百万元"); ax.tick_params(axis="x", rotation=15)
    plt.tight_layout(); plt.savefig(FIG/"model_cost_comparison.pdf"); plt.savefig(FIG/"model_cost_comparison.png", dpi=300); plt.close()
    selected = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.8), sharex=True)
    for ax, date in zip(axes.flat, selected):
        g = schedule[schedule.date == date]; x = np.arange(len(g))/6 + 1/6
        ax.plot(x, g.load_kw/6, label="实际负载", lw=1); ax.plot(x, g.pv_kw/6, label="实际光伏", lw=1)
        ax.plot(x, g.active_contract_kwh, label="生效合同", lw=1); ax.plot(x, g.soc_end_kwh/10, label="储电量/10", lw=1)
        ax.set_title(date, fontsize=10); ax.set_ylabel("电量 / kWh"); ax.grid(alpha=.2)
    axes[-1, 0].set_xlabel("运营窗口时刻 / h"); axes[-1, 1].set_xlabel("运营窗口时刻 / h")
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.01))
    plt.tight_layout(rect=(0, 0, 1, 0.95)); plt.savefig(FIG/"selected_days_dispatch.pdf"); plt.savefig(FIG/"selected_days_dispatch.png", dpi=300); plt.close()
    savings = comparison[comparison.model.str.startswith("deterministic")].copy(); base = float(savings.iloc[0].total_cost); savings["saving"] = base-savings.total_cost
    fig, ax = plt.subplots(figsize=(6.2, 3.5)); ax.plot(savings.policy, savings.saving/1e6, marker="o", color="#b04a3a")
    ax.set_xlabel("可用预报发布时间"); ax.set_ylabel("相对仅0:00节省 / 百万元"); ax.tick_params(axis="x", rotation=20); ax.grid(alpha=.25)
    plt.tight_layout(); plt.savefig(FIG/"update_value_analysis.pdf"); plt.savefig(FIG/"update_value_analysis.png", dpi=300); plt.close()


def validate(schedule, adjustments, daily, proxy_used):
    balance = (schedule.active_contract_kwh + schedule.pv_kw/6 + schedule.discharge_kwh +
               schedule.emergency_kwh - schedule.load_kw/6 - schedule.charge_kwh -
               schedule.curtailment_kwh - schedule.grid_spill_kwh)
    soc_transition = schedule.soc_end_kwh - schedule.soc_start_kwh - ETA_C*schedule.charge_kwh + schedule.discharge_kwh/ETA_D
    continuity = []
    for _, g in schedule.groupby("date", sort=False):
        continuity.append(float(g.iloc[-1].soc_end_kwh))
    frozen_violations = int((adjustments["slot"] < adjustments["issue_hour"].map({0:0,6:35,12:71,18:107})).sum())
    cost_recalc = []
    for date, g in schedule.groupby("date", sort=False):
        h = adjustments[adjustments.date == date]
        initial = np.sum(g.price*g.initial_contract_kwh)
        increments = h.groupby("issue_hour").first()
        # incremental_cost is repeated by version, so count once for issues after zero.
        calc = initial + increments.loc[increments.index > 0, "incremental_cost"].sum()
        stated = daily.loc[daily.date == date, "settlement_cost"].iloc[0]
        cost_recalc.append(calc-stated)
    checks = {
        "energy_balance_max_abs_kwh": float(np.abs(balance).max()),
        "soc_transition_max_abs_kwh": float(np.abs(soc_transition).max()),
        "soc_min_kwh": float(schedule.soc_end_kwh.min()), "soc_max_kwh": float(schedule.soc_end_kwh.max()),
        "charge_max_kwh": float(schedule.charge_kwh.max()), "discharge_max_kwh": float(schedule.discharge_kwh.max()),
        "cross_day_continuity_max_abs_kwh": float(np.abs(schedule.groupby("date").tail(1).soc_end_kwh.to_numpy()[:-1] - schedule.groupby("date").head(1).soc_start_kwh.to_numpy()[1:]).max()),
        "executed_slot_modification_count": frozen_violations,
        "workbook_expected_days": 334, "workbook_actual_days": int(daily.shape[0]),
        "settlement_recalculation_max_abs": float(np.max(np.abs(cost_recalc))),
        "dec31_next_0010_proxy_used": bool(proxy_used),
    }
    workbook = load_workbook(ROOT / "result3.xlsx", read_only=True, data_only=True)
    plan = workbook["计划购电量"]
    adjusted = workbook["调整购电量"]
    storage = workbook["充放电量"]
    emergency = workbook["紧急购电量"]
    plan_rows = list(plan.iter_rows(min_row=2, values_only=True))
    adjusted_rows = list(adjusted.iter_rows(min_row=2, values_only=True))
    workbook_plan = np.asarray([[float(value) for value in row[1:145]] for row in plan_rows])
    workbook_adjusted = np.asarray([[float(value) for value in row[1:145]] for row in adjusted_rows])
    expected_plan = np.vstack([group.initial_contract_kwh.to_numpy() for _, group in schedule.groupby("date", sort=False)])
    expected_adjusted = np.vstack([group.final_contract_kwh.to_numpy() for _, group in schedule.groupby("date", sort=False)])
    emergency_total = sum(
        float(row[2] or 0) for row in emergency.iter_rows(min_row=2, values_only=True)
    )
    checks.update({
        "workbook_plan_days": plan.max_row - 1,
        "workbook_adjusted_days": adjusted.max_row - 1,
        "workbook_storage_rows": storage.max_row - 1,
        "workbook_emergency_segments": emergency.max_row - 1,
        "workbook_plan_blank_cells": sum(
            cell is None for row in plan.iter_rows(min_row=2, values_only=True) for cell in row
        ),
        "workbook_adjusted_blank_cells": sum(
            cell is None for row in adjusted.iter_rows(min_row=2, values_only=True) for cell in row
        ),
        "workbook_plan_max_abs_kwh": float(np.max(np.abs(workbook_plan - expected_plan))),
        "workbook_adjusted_max_abs_kwh": float(np.max(np.abs(workbook_adjusted - expected_adjusted))),
        "workbook_settlement_cost_residual_yuan": float(
            sum(float(row[146]) for row in adjusted_rows) - daily.settlement_cost.sum()
        ),
        "workbook_emergency_residual_kwh": float(emergency_total - schedule.emergency_kwh.sum()),
    })
    checks["all_pass"] = bool(checks["energy_balance_max_abs_kwh"] < 1e-6 and checks["soc_transition_max_abs_kwh"] < 1e-6 and checks["soc_min_kwh"] >= SOC_MIN-1e-6 and checks["soc_max_kwh"] <= SOC_MAX+1e-6 and checks["charge_max_kwh"] <= STEP_MAX+1e-6 and checks["discharge_max_kwh"] <= STEP_MAX+1e-6 and frozen_violations == 0 and checks["workbook_actual_days"] == 334 and checks["settlement_recalculation_max_abs"] < 1e-5)
    checks["all_pass"] = bool(checks["all_pass"] and checks["workbook_plan_days"] == 334
                              and checks["workbook_adjusted_days"] == 334
                              and checks["workbook_storage_rows"] == 2004
                              and checks["workbook_plan_blank_cells"] == 0
                              and checks["workbook_adjusted_blank_cells"] == 0
                              and checks["workbook_plan_max_abs_kwh"] < 1e-8
                              and checks["workbook_adjusted_max_abs_kwh"] < 1e-8
                              and abs(checks["workbook_settlement_cost_residual_yuan"]) < 1e-5
                              and abs(checks["workbook_emergency_residual_kwh"]) < 1e-5)
    return checks


def write_reports(daily, metrics, comparison, checks, elapsed, bias_enabled,
                  january_raw_mae, january_corrected_mae):
    total = daily.sum(numeric_only=True)
    raw_mae = metrics[metrics.series == "pv_raw"].mae_kw.mean(); corr_mae = metrics[metrics.series == "pv_corrected"].mae_kw.mean()
    analysis = f"""# 问题三分析与建模报告

## 时间语义与数据处理
附件1电价及附件2功率均按10分钟区间右端点解释。模板首列 `0:10-0:20` 映射到当天 `0:20`，末列映射次日 `0:10`。输出覆盖2025-02-01至2025-12-31。12月31日次日0:10缺失，采用12月31日0:10周期代理。

## 因果预测
负载预测仅使用目标日前数据，以周同期与扩展窗口岭回归组合；权重由过去14日误差反比自适应。6/12/18时利用当日已观测误差作指数衰减偏差修正。PV按发布日期、发布时刻和提前期构造候选滚动中位残差校正；1月预验证中原始/候选校正MAE为 {january_raw_mae:.2f}/{january_corrected_mae:.2f} kW，因此正式调度{'启用校正' if bias_enabled else '保留原始预报，不启用校正'}。插值以发布时间的已观测光伏为锚点；按24小时累计残差的10%、30%、50%、70%、90%分位选取五条完整残差轨迹，保留时序相关。

## 随机优化
每个发布时刻求解五情景线性规划。共同一阶段变量为合同购电，情景补救变量包括充电、放电、弃光、紧急购电和SOC。风险目标为合同增量成本 + `(1-lambda)` 期望紧急费 + `lambda*CVaR_0.9`，取 `lambda=0.2`，紧急电价为5倍。初始费用为 `p*g0`；调整满足 `new-prev=up-down`，增量结算为 `1.5p*up-0.5p*down`。日末情景SOC等于当日初SOC。

## 实现粒度与因果执行
为保证全年四次滚动速度，随机LP按小时聚合（小时充放上限为六倍10分钟上限），合同按小时内预测净负荷权重分解到10分钟；实际执行和全部物理校验均为10分钟。发布时刻之后才更新，已执行合同冻结。调整费用已在目标函数中形成隐式经济触发。实际富余依次充电、弃光/记录电网溢出，缺口依次放电、紧急购电，SOC跨日连续。计划和调整按模板的0:10至次日0:10运营窗口输出，充放电量则严格按日历日0:00--24:00汇总。
"""
    results = f"""# 问题三计算结果

## 运行结果
- 全更新合同结算费：{total['settlement_cost']:.2f}
- 紧急购电费：{total['emergency_cost']:.2f}
- 总成本：{total['total_cost']:.2f}
- 紧急购电量：{total['emergency_kwh']:.2f} kWh
- 充电/放电量：{total['charge_kwh']:.2f} / {total['discharge_kwh']:.2f} kWh
- 弃光量：{total['curtailment_kwh']:.2f} kWh
- PV原始/校正MAE：{raw_mae:.2f} / {corr_mae:.2f} kW
- 1月门控结论：{'启用残差校正' if bias_enabled else '原始预报更优，正式调度拒绝残差校正'}
- 运行时间：{elapsed:.1f} s

## 约束校验
`validation_checks.json` 的 `all_pass={checks['all_pass']}`。最大能量平衡误差 {checks['energy_balance_max_abs_kwh']:.3e} kWh，最大SOC转移误差 {checks['soc_transition_max_abs_kwh']:.3e} kWh，SOC范围 [{checks['soc_min_kwh']:.2f}, {checks['soc_max_kwh']:.2f}] kWh，已执行时段修改数 {checks['executed_slot_modification_count']}，费用复算最大误差 {checks['settlement_recalculation_max_abs']:.3e}。

## 输出说明
`complete_schedule.csv` 为10分钟实际执行，`adjustment_history.csv` 保存每次合同版本的未执行部分，`daily_summary.csv` 为日汇总，`forecast_metrics.csv` 为预测指标。`result3.xlsx` 的计划购电为0点合同，调整购电为最终生效合同；全天费用为初始计划加历次调整增量，不含紧急费用。紧急购电连续区间已合并。
"""
    header = "| " + " | ".join(comparison.columns) + " |\n"
    separator = "| " + " | ".join(["---"] * len(comparison.columns)) + " |\n"
    table_rows = "".join("| " + " | ".join(f"{v:.4f}" if isinstance(v, float) else str(v)
                                              for v in row) + " |\n"
                         for row in comparison.itertuples(index=False, name=None))
    method = "# 方法对比\n\n消融为保证运行速度采用**确定性滚动LP**（中心PV情景、风险系数0）；最终提交方案单独采用五情景随机LP+CVaR，二者不可将绝对成本直接解释为仅由更新频次引起。\n\n" + header + separator + table_rows
    readme = """# 问题三复现说明

运行：

```bash
conda run -n mathmodel python code/problem3.py
```

程序只读取 `../附件`，全部写入当前 `task3`。最终模型为0/6/12/18四次更新、5情景随机LP与CVaR；四组频次消融使用确定性滚动LP。随机LP小时聚合，实际调度、SOC和能量平衡按10分钟执行。附件时间均按区间右端点解释；计划表按模板运营窗口输出，充放电表按日历日0:00--24:00汇总。
"""
    return analysis, results, method, readme


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--refresh-brief-docs", action="store_true")
    args = parser.parse_args()
    for p in (OUT, FIG, REPORT): p.mkdir(parents=True, exist_ok=True)
    started = time.time()
    dates, load, pv, prices, _, _, forecast = load_inputs()
    load_pred, blend = build_load_forecasts(dates, load)
    candidate_bias, candidate_residuals = prepare_pv_errors(dates, pv, forecast)
    bias_enabled, january_raw_mae, january_corrected_mae = january_bias_gate(
        dates, pv, forecast, candidate_bias
    )
    if bias_enabled:
        bias, residuals = candidate_bias, candidate_residuals
    else:
        bias = {key: np.zeros(24) for key in candidate_bias}
        residuals = raw_pv_residuals(dates, pv, forecast)
    schedule, adjustments, daily, proxy = run_policy(ISSUES, dates, load, pv, prices, load_pred,
                                                       forecast, bias, residuals, stochastic=True, collect=True)
    # Keep candidate-correction metrics for an auditable comparison even when
    # January validation rejects that correction for the operational model.
    metrics = forecast_metrics(dates, load, load_pred, forecast, candidate_bias, pv)
    comparisons = []
    policies = [(0,), (0,6), (0,6,12), (0,6,12,18)]
    if args.skip_ablation:
        policies = [(0,6,12,18)]
    for policy in policies:
        _, _, dsum, _ = run_policy(policy, dates, load, pv, prices, load_pred, forecast, bias,
                                    residuals, stochastic=False, collect=True)
        comparisons.append({"policy": "+".join(map(str, policy)), "model": "deterministic LP ablation",
                            "settlement_cost": dsum.settlement_cost.sum(), "emergency_cost": dsum.emergency_cost.sum(),
                            "total_cost": dsum.total_cost.sum(), "emergency_kwh": dsum.emergency_kwh.sum()})
    comparisons.append({"policy": "0+6+12+18", "model": "5-scenario stochastic LP + CVaR",
                        "settlement_cost": daily.settlement_cost.sum(),
                        "emergency_cost": daily.emergency_cost.sum(),
                        "total_cost": daily.total_cost.sum(), "emergency_kwh": daily.emergency_kwh.sum()})
    comparison = pd.DataFrame(comparisons)
    schedule.to_csv(OUT/"complete_schedule.csv", index=False)
    adjustments.to_csv(OUT/"adjustment_history.csv", index=False)
    daily.to_csv(OUT/"daily_summary.csv", index=False)
    metrics.to_csv(OUT/"forecast_metrics.csv", index=False)
    comparison.to_csv(OUT/"method_comparison.csv", index=False)
    write_workbook(schedule, daily)
    checks = validate(schedule, adjustments, daily, proxy)
    (OUT/"validation_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    make_figures(schedule, daily, metrics, comparison)
    analysis, results, method, readme = write_reports(
        daily, metrics, comparison, checks, time.time()-started,
        bias_enabled, january_raw_mae, january_corrected_mae
    )
    (OUT/"generated_run_summary.md").write_text(results, encoding="utf-8")
    if args.refresh_brief_docs:
        (REPORT/"ANALYSIS_MODELING_REPORT.md").write_text(analysis, encoding="utf-8")
        (REPORT/"RESULTS_REPORT.md").write_text(results, encoding="utf-8")
        (REPORT/"METHOD_COMPARISON.md").write_text(method, encoding="utf-8")
        (ROOT/"README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"days": len(daily), "total_cost": daily.total_cost.sum(),
                      "emergency_kwh": daily.emergency_kwh.sum(), "validation": checks,
                      "elapsed_seconds": time.time()-started}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
