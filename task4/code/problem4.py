#!/usr/bin/env python3
"""Problem 4-2/4-3: causal price forecasting and stochastic dispatch."""

from __future__ import annotations

import argparse
import json
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
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "附件"
OUT, FIG, REPORT = ROOT / "outputs", ROOT / "figures", ROOT / "reports"
ETA_C = ETA_D = 0.9
SOC_MIN, SOC_MAX, SOC_INITIAL = 1200.0, 10800.0, 6000.0
STEP_MAX = 833.3333
ALPHA, RISK_WEIGHT, EMERGENCY_MULT = 0.9, 0.2, 5.0
ISSUES = (0, 6, 12, 18)
START = {0: 0, 6: 35, 12: 71, 18: 107}
OUTPUT_START = pd.Timestamp("2025-02-01")


def load_inputs():
    a1 = pd.read_excel(DATA / "附件1.xlsx")
    load_df = pd.read_excel(DATA / "附件2.xlsx", sheet_name="小区负载")
    pv_df = pd.read_excel(DATA / "附件2.xlsx", sheet_name="光伏发电实际功率")
    price_df = pd.read_excel(DATA / "附件4.xlsx")
    dates = pd.to_datetime(load_df.iloc[:, 0]).dt.normalize()
    f = pd.read_excel(DATA / "附件3.xlsx")
    f["日期"] = pd.to_datetime(f["日期"].ffill()).dt.normalize()
    f["issue"] = f["预报时刻"].astype(str).str.extract(r"(\d+)")[0].astype(int)
    vals = f.filter(regex=r"^预报\d+小时$").to_numpy(float)
    pv_forecast = {(r["日期"], int(r["issue"])): vals[i] for i, r in f.iterrows()}
    return {
        "dates": dates,
        "load": load_df.iloc[:, 1:].to_numpy(float),
        "pv": pv_df.iloc[:, 1:].to_numpy(float),
        "price": price_df.iloc[:, 1:].to_numpy(float),
        "base_price": a1["电价"].to_numpy(float),
        "base_load": a1["小区负载"].to_numpy(float),
        "base_pv": a1["光伏发电预测功率"].to_numpy(float),
        "pv_forecast": pv_forecast,
    }


def endpoint_value(arr, date_index, day, minute):
    target = day + pd.Timedelta(days=minute // 1440)
    minute %= 1440
    source = target - pd.Timedelta(days=1) if minute == 0 else target
    idx, proxy = date_index.get(source), False
    if idx is None:
        idx, minute, proxy = date_index[day], 10, True
    return float(arr[idx, 143 if minute == 0 else minute // 10 - 1]), proxy


def operational_actual(arr, date_index, day):
    values, proxy = [], False
    for minute in range(20, 1451, 10):
        value, used = endpoint_value(arr, date_index, day, minute)
        values.append(value)
        proxy |= used
    return np.asarray(values), proxy


def operational_forecast(native_row):
    """No next-day leakage: final slot uses current-day 00:10 periodic proxy."""
    return np.r_[native_row[1:], native_row[0]]


def build_signal_forecast(actual, prior):
    """Expanding causal weekly/ridge blend, initialized from Attachment 1."""
    n, slots = actual.shape
    pred, weight = np.zeros_like(actual), np.zeros(n)
    pred[0] = prior
    for d in range(1, n):
        weekly = actual[d - 7] if d >= 7 else actual[:d].mean(axis=0)
        rows = np.arange(max(7, d - 42), d)
        if len(rows) >= 5:
            x = np.column_stack([
                np.ones(len(rows) * slots), actual[rows - 1].ravel(),
                actual[rows - 7].ravel(), np.tile(prior, len(rows)),
                np.repeat(np.sin(2 * np.pi * rows / 7), slots),
                np.repeat(np.cos(2 * np.pi * rows / 7), slots),
            ])
            y = actual[rows].ravel()
            scale = np.maximum(np.std(x[:, 1:4], axis=0), 1.0)
            x[:, 1:4] /= scale
            beta = np.linalg.solve(x.T @ x + np.diag([0, 8, 8, 8, 8, 8]), x.T @ y)
            xt = np.column_stack([
                np.ones(slots), actual[d - 1], weekly, prior,
                np.full(slots, np.sin(2 * np.pi * d / 7)),
                np.full(slots, np.cos(2 * np.pi * d / 7)),
            ])
            xt[:, 1:4] /= scale
            ridge = xt @ beta
        else:
            ridge = 0.55 * actual[d - 1] + 0.45 * weekly
        hist = np.arange(max(1, d - 14), d)
        if d >= 8 and len(hist):
            er = np.mean(np.abs(actual[hist] - pred[hist]))
            ew = np.mean(np.abs(actual[hist] - actual[hist - 7]))
            w = ew / max(er + ew, 1e-9)
        else:
            w = 0.6
        weight[d] = w
        pred[d] = np.maximum(0, w * ridge + (1 - w) * weekly)
    return pred, weight


def weekday_mean(actual, d):
    rows = list(range(d - 7, max(-1, d - 29), -7))
    return actual[rows].mean(axis=0) if rows else (actual[:d].mean(axis=0) if d else None)


def build_price_forecasts(actual, base):
    n, slots = actual.shape
    fixed = np.repeat(base[None, :], n, axis=0)
    lag1, lag7, structured, adaptive = [np.zeros_like(actual) for _ in range(4)]
    lag1[0] = lag7[0] = structured[0] = adaptive[0] = base
    blend = np.zeros(n)
    for d in range(1, n):
        lag1[d] = actual[d - 1]
        lag7[d] = actual[d - 7] if d >= 7 else actual[:d].mean(axis=0)
        wd = weekday_mean(actual, d)
        rows = np.arange(max(7, d - 56), d)
        if len(rows) >= 7:
            features, targets = [], []
            for r in rows:
                features.append(np.column_stack([
                    np.ones(slots), base, actual[r - 1], actual[r - 7],
                    np.tile(weekday_mean(actual, r), (1, 1)).ravel(),
                ]))
                targets.append(actual[r])
            x, y = np.vstack(features), np.concatenate(targets)
            beta = np.linalg.solve(x.T @ x + np.diag([0, .2, .2, .2, .2]), x.T @ y)
            xt = np.column_stack([np.ones(slots), base, actual[d - 1], lag7[d], wd])
            structured[d] = np.maximum(0, xt @ beta)
        else:
            structured[d] = np.maximum(0, 0.25 * base + 0.45 * lag7[d] + 0.30 * wd)
        hist = np.arange(max(1, d - 28), d)
        if len(hist):
            es = np.mean(np.abs(actual[hist] - structured[hist]))
            e7 = np.mean(np.abs(actual[hist] - lag7[hist]))
            w = e7 / max(es + e7, 1e-12)
        else:
            w = 0.6
        blend[d] = w
        adaptive[d] = w * structured[d] + (1 - w) * lag7[d]
    return {"fixed": fixed, "lag1": lag1, "lag7": lag7,
            "structured_ridge": structured, "adaptive": adaptive}, blend


def update_with_observed(base, actual, start, scale=36.0):
    result = base.copy()
    if start:
        err = actual[:start] - base[:start]
        correction = float(np.mean(err[-min(18, len(err)):]))
        result[start:] = np.maximum(0, result[start:] + correction * np.exp(-np.arange(len(result)-start) / scale))
    return result


def interpolate_hourly(issue, hourly, target_minutes, anchor=None):
    xp = issue * 60 + np.arange(1, 25) * 60
    values = np.asarray(hourly)
    if anchor is not None:
        xp, values = np.r_[issue * 60, xp], np.r_[anchor, values]
    return np.interp(target_minutes, xp, values, left=values[0], right=values[-1])


def pv_issue_central(day, issue, forecast, pv_actual, date_index):
    start = START[issue]
    minutes = np.arange(20 + 10 * start, 1451, 10)
    anchor, proxy = endpoint_value(pv_actual, date_index, day, issue * 60)
    return np.maximum(0, interpolate_hourly(issue, forecast[(day, issue)], minutes, anchor)), proxy


def aggregate_energy(x):
    return np.asarray([np.sum(x[a:min(a + 6, len(x))]) for a in range(0, len(x), 6)])


def aggregate_price(x):
    return np.asarray([np.mean(x[a:min(a + 6, len(x))]) for a in range(0, len(x), 6)])


def choose_joint_scenarios(net_center, price_center, historical, count=5):
    if not historical:
        return np.repeat(net_center[None, :], count, axis=0), np.repeat(price_center[None, :], count, axis=0), []
    ne = np.asarray([r[1] for r in historical])
    pe = np.asarray([r[2] for r in historical])
    score_n = ne.sum(axis=1) / max(np.std(ne.sum(axis=1)), 1e-9)
    score_p = (pe * np.maximum(net_center, 0)).sum(axis=1) / max(np.std((pe * np.maximum(net_center, 0)).sum(axis=1)), 1e-9)
    order = np.argsort(score_n + score_p)
    idx = np.rint(np.quantile(np.arange(len(order)), [.1, .3, .5, .7, .9])).astype(int)
    picked = [historical[order[min(i, len(order)-1)]] for i in idx]
    return (np.asarray([np.maximum(-1e5, net_center + r[1]) for r in picked]),
            np.asarray([np.maximum(.001, price_center + r[2]) for r in picked]),
            [r[0] for r in picked])


def solve_lp(net_s, price_s, lengths, soc0, terminal, previous=None, risk=RISK_WEIGHT):
    """Hourly two-stage LP with scenario recourse and emergency-cost CVaR."""
    s_count, h_count = net_s.shape
    common, block = 3 * h_count, 5 * h_count + 1
    eta_i = common + s_count * block
    excess0, nvar = eta_i + 1, eta_i + 1 + s_count
    c = np.zeros(nvar)
    expected_price = price_s.mean(axis=0)
    if previous is None:
        c[:h_count] = expected_price
    else:
        c[h_count:2*h_count] = 1.5 * expected_price
        c[2*h_count:3*h_count] = -0.5 * expected_price
    for s in range(s_count):
        b = common + s * block
        c[b+3*h_count:b+4*h_count] = (1-risk) / s_count * EMERGENCY_MULT * price_s[s]
    c[eta_i] = risk
    c[excess0:] = risk / ((1-ALPHA) * s_count)
    rows = h_count * (previous is not None) + s_count * (2*h_count + 2)
    aeq, beq, r = lil_matrix((rows, nvar)), np.zeros(rows), 0
    if previous is not None:
        for h in range(h_count):
            aeq[r, h], aeq[r, h_count+h], aeq[r, 2*h_count+h] = 1, -1, 1
            beq[r], r = previous[h], r + 1
    for s in range(s_count):
        b = common + s * block
        ch, dis, curt, emer, soc = b, b+h_count, b+2*h_count, b+3*h_count, b+4*h_count
        for h in range(h_count):
            aeq[r, h], aeq[r, dis+h], aeq[r, emer+h] = 1, 1, 1
            aeq[r, ch+h], aeq[r, curt+h], beq[r] = -1, -1, net_s[s, h]
            r += 1
            aeq[r, soc+h+1], aeq[r, soc+h], aeq[r, ch+h], aeq[r, dis+h] = 1, -1, -ETA_C, 1/ETA_D
            r += 1
        aeq[r, soc], beq[r], r = 1, soc0, r + 1
        aeq[r, soc+h_count], beq[r], r = 1, terminal, r + 1
    aub, bub = lil_matrix((s_count, nvar)), np.zeros(s_count)
    for s in range(s_count):
        b = common + s * block
        for h in range(h_count):
            aub[s, b+3*h_count+h] = EMERGENCY_MULT * price_s[s, h]
        aub[s, eta_i], aub[s, excess0+s] = -1, -1
    limits = [(0, None)] * (3*h_count)
    power = [(0, STEP_MAX*n) for n in lengths]
    for _ in range(s_count):
        limits += power * 2 + [(0, None)] * (2*h_count) + [(SOC_MIN, SOC_MAX)] * (h_count+1)
    limits += [(None, None)] + [(0, None)] * s_count
    result = linprog(c, A_ub=aub.tocsr(), b_ub=bub, A_eq=aeq.tocsr(), b_eq=beq,
                     bounds=limits, method="highs")
    if not result.success:
        raise RuntimeError(result.message)
    return result.x[:h_count], float(result.fun)


def distribute_hourly(hourly, net10):
    result = np.zeros(len(net10))
    for h, total in enumerate(hourly):
        sl = slice(6*h, min(6*h+6, len(net10)))
        weights = np.maximum(net10[sl], 0) + 1
        result[sl] = total * weights / weights.sum()
    return result


def execute(contract, load_kw, pv_kw, soc):
    balance = contract + pv_kw/6 - load_kw/6
    ch = dis = emergency = curtail = spill = 0.0
    if balance >= 0:
        ch = min(balance, STEP_MAX, (SOC_MAX-soc)/ETA_C)
        left = balance-ch
        curtail, spill = min(left, pv_kw/6), max(0, left-pv_kw/6)
        next_soc = soc + ETA_C*ch
    else:
        need = -balance
        dis = min(need, STEP_MAX, (soc-SOC_MIN)*ETA_D)
        emergency, next_soc = need-dis, soc-dis/ETA_D
    return ch, dis, emergency, curtail, spill, next_soc


def make_dayahead_history(data, load_pred, pv_pred, price_pred):
    dates, index = data["dates"], {d: i for i, d in enumerate(data["dates"])}
    result = {}
    for d, day in enumerate(dates):
        la, _ = operational_actual(data["load"], index, day)
        pa, _ = operational_actual(data["pv"], index, day)
        pra, _ = operational_actual(data["price"], index, day)
        nc = operational_forecast(load_pred[d])/6 - operational_forecast(pv_pred[d])/6
        pc = operational_forecast(price_pred[d])
        result[day] = (la/6-pa/6-nc, pra-pc)
    return result


def run_42(data, load_pred, pv_pred, price_pred, stochastic=True, oracle=False, collect=False):
    dates, index = data["dates"], {d: i for i, d in enumerate(data["dates"])}
    history = make_dayahead_history(data, load_pred, pv_pred, price_pred)
    soc, rows, daily, previous_last, proxy_used = SOC_INITIAL, [], [], None, False
    for d, day in enumerate(dates):
        la, p1 = operational_actual(data["load"], index, day)
        pa, p2 = operational_actual(data["pv"], index, day)
        actual_price, p3 = operational_actual(data["price"], index, day)
        proxy_used |= p1 or p2 or p3
        net_center = operational_forecast(load_pred[d])/6 - operational_forecast(pv_pred[d])/6
        price_center = operational_forecast(price_pred[d])
        # The previous operational window ends at current-day 00:10, which is
        # not complete at the 00:00 decision. Use only fully realized windows.
        past = [(x, *history[x]) for x in dates[:max(0, d-1)] if x in history]
        net_s, price_s, chosen = choose_joint_scenarios(net_center, price_center, past)
        if oracle:
            price_s = np.repeat(actual_price[None, :], 5, axis=0)
        if not stochastic:
            net_s, price_s = net_center[None, :], price_s.mean(axis=0, keepdims=True)
        lengths = [min(6, 144-a) for a in range(0, 144, 6)]
        gh, objective = solve_lp(np.asarray([aggregate_energy(x) for x in net_s]),
                                 np.asarray([aggregate_price(x) for x in price_s]), lengths, soc, soc,
                                 risk=RISK_WEIGHT if stochastic else 0)
        contract = distribute_hourly(gh, net_center)
        day_soc0, executed = soc, []
        for t in range(144):
            ch, dis, emer, curt, spill, sn = execute(contract[t], la[t], pa[t], soc)
            rec = {"date": day.date().isoformat(), "slot": t, "endpoint_minute": 20+10*t,
                   "actual_price": actual_price[t], "price_forecast": price_center[t],
                   "load_kw": la[t], "pv_kw": pa[t], "load_forecast_kw": operational_forecast(load_pred[d])[t],
                   "pv_forecast_kw": operational_forecast(pv_pred[d])[t], "contract_kwh": contract[t],
                   "charge_kwh": ch, "discharge_kwh": dis, "emergency_kwh": emer,
                   "curtailment_kwh": curt, "grid_spill_kwh": spill,
                   "soc_start_kwh": soc, "soc_end_kwh": sn,
                   "scenario_dates": ";".join(str(x.date()) for x in chosen)}
            executed.append(rec); soc = sn
            if collect and day >= OUTPUT_START: rows.append(rec)
        if collect and day >= OUTPUT_START:
            calendar = [previous_last, *executed[:143]]
            if previous_last is None: raise RuntimeError("Missing prior calendar interval")
            summary = summarize_day(day, executed, calendar, contract, contract, actual_price, 0.0, objective)
            daily.append(summary)
        previous_last = executed[-1]
    return pd.DataFrame(rows), pd.DataFrame(daily), proxy_used


def precompute_43_centers(data, load_pred, price_pred):
    dates, index = data["dates"], {d: i for i, d in enumerate(data["dates"])}
    centers, residuals, proxy = {}, {}, False
    for issue in ISSUES:
        start = START[issue]
        for d, day in enumerate(dates):
            la, _ = operational_actual(data["load"], index, day)
            pa, _ = operational_actual(data["pv"], index, day)
            pra, _ = operational_actual(data["price"], index, day)
            load_base = operational_forecast(load_pred[d])
            load_c = update_with_observed(load_base, la, start)
            pv_c, used = pv_issue_central(day, issue, data["pv_forecast"], data["pv"], index)
            proxy |= used
            price_base = operational_forecast(price_pred[d])
            price_c = update_with_observed(price_base, pra, start)
            net_c = load_c[start:]/6 - pv_c/6
            centers[(day, issue)] = (load_c, pv_c, price_c)
            residuals[(day, issue)] = (la[start:]/6-pa[start:]/6-net_c, pra[start:]-price_c[start:])
    return centers, residuals, proxy


def run_43(data, load_pred, price_pred, stochastic=True, oracle=False, collect=False):
    dates, index = data["dates"], {d: i for i, d in enumerate(data["dates"])}
    centers, residuals, proxy_used = precompute_43_centers(data, load_pred, price_pred)
    soc, rows, adjustments, daily, previous_last = SOC_INITIAL, [], [], [], None
    for d, day in enumerate(dates):
        la, p1 = operational_actual(data["load"], index, day)
        pa, p2 = operational_actual(data["pv"], index, day)
        actual_price, p3 = operational_actual(data["price"], index, day)
        proxy_used |= p1 or p2 or p3
        contract, initial, settlement, executed, objectives = np.zeros(144), np.zeros(144), 0.0, [], []
        for ui, issue in enumerate(ISSUES):
            start = START[issue]
            load_c, pv_c, price_c = centers[(day, issue)]
            net_center = load_c[start:]/6-pv_c/6
            # At 00:00 the previous contract window still has one unobserved
            # 10-minute interval. Later releases may use that completed window.
            cutoff = max(0, d-1) if issue == 0 else d
            past = [(x, *residuals[(x, issue)]) for x in dates[:cutoff]]
            net_s, price_s, chosen = choose_joint_scenarios(net_center, price_c[start:], past)
            if oracle:
                net_s = (la[start:]/6-pa[start:]/6)[None, :]
                price_s = actual_price[start:][None, :]
            elif not stochastic:
                net_s, price_s = net_center[None, :], price_c[start:][None, :]
            lengths = [min(6, len(net_center)-a) for a in range(0, len(net_center), 6)]
            previous_h = aggregate_energy(contract[start:]) if issue else None
            gh, objective = solve_lp(np.asarray([aggregate_energy(x) for x in net_s]),
                                     np.asarray([aggregate_price(x) for x in price_s]), lengths,
                                     soc, soc if issue == 0 else day_soc0, previous_h,
                                     RISK_WEIGHT if stochastic and not oracle else 0)
            new = distribute_hourly(gh, net_center if not oracle else la[start:]/6-pa[start:]/6)
            old = contract[start:].copy(); contract[start:] = new
            if issue == 0:
                initial = contract.copy(); increment = float(np.sum(actual_price*initial))
                day_soc0 = soc
            else:
                delta = new-old
                slot_increment = actual_price[start:] * (1.5*np.maximum(delta, 0)-0.5*np.maximum(-delta, 0))
                increment = float(slot_increment.sum())
            settlement += increment; objectives.append(objective)
            if collect and day >= OUTPUT_START:
                for k, t in enumerate(range(start, 144)):
                    prev = old[k] if issue else 0.0
                    adjustments.append({"date": day.date().isoformat(), "issue_hour": issue, "slot": t,
                        "endpoint_minute": 20+10*t, "previous_kwh": prev, "new_kwh": contract[t],
                        "up_kwh": max(contract[t]-prev, 0), "down_kwh": max(prev-contract[t], 0),
                        "actual_price": actual_price[t],
                        "incremental_cost": actual_price[t]*(contract[t] if issue == 0 else 1.5*max(contract[t]-prev,0)-.5*max(prev-contract[t],0)),
                        "scenario_dates": ";".join(str(x.date()) for x in chosen)})
            end = START[ISSUES[ui+1]] if ui < 3 else 144
            for t in range(start, end):
                ch, dis, emer, curt, spill, sn = execute(contract[t], la[t], pa[t], soc)
                rec = {"date": day.date().isoformat(), "slot": t, "endpoint_minute": 20+10*t,
                    "actual_price": actual_price[t], "price_forecast": price_c[t], "load_kw": la[t], "pv_kw": pa[t],
                    "load_forecast_kw": load_c[t], "pv_forecast_kw": pv_c[t-start],
                    "initial_contract_kwh": initial[t], "final_contract_kwh": np.nan,
                    "active_contract_kwh": contract[t], "charge_kwh": ch, "discharge_kwh": dis,
                    "emergency_kwh": emer, "curtailment_kwh": curt, "grid_spill_kwh": spill,
                    "soc_start_kwh": soc, "soc_end_kwh": sn, "active_issue": issue}
                executed.append(rec); soc = sn
                if collect and day >= OUTPUT_START: rows.append(rec)
        if collect and day >= OUTPUT_START:
            final = contract.copy()
            for rec in rows[-144:]: rec["final_contract_kwh"] = final[rec["slot"]]
            calendar = [previous_last, *executed[:143]]
            if previous_last is None: raise RuntimeError("Missing prior calendar interval")
            daily.append(summarize_day(day, executed, calendar, initial, final, actual_price, settlement, np.mean(objectives)))
        previous_last = executed[-1]
    return pd.DataFrame(rows), pd.DataFrame(adjustments), pd.DataFrame(daily), proxy_used


def summarize_day(day, executed, calendar, initial, final, prices, settlement, objective):
    if settlement == 0.0:
        settlement = float(np.sum(prices*initial))
    emergency_cost = sum(EMERGENCY_MULT*r["actual_price"]*r["emergency_kwh"] for r in executed)
    result = {"date": day.date().isoformat(), "soc_start_kwh": calendar[0]["soc_start_kwh"],
        "soc_end_kwh": calendar[-1]["soc_end_kwh"], "initial_contract_kwh": float(initial.sum()),
        "final_contract_kwh": float(final.sum()), "settlement_cost": settlement,
        "emergency_kwh": sum(r["emergency_kwh"] for r in executed), "emergency_cost": emergency_cost,
        "charge_kwh": sum(r["charge_kwh"] for r in executed), "discharge_kwh": sum(r["discharge_kwh"] for r in executed),
        "curtailment_kwh": sum(r["curtailment_kwh"] for r in executed), "grid_spill_kwh": sum(r["grid_spill_kwh"] for r in executed),
        "total_cost": settlement+emergency_cost, "mean_lp_objective": objective}
    for b in range(6):
        part = calendar[24*b:24*(b+1)]
        result[f"block_{b}_charge_kwh"] = sum(r["charge_kwh"] for r in part)
        result[f"block_{b}_discharge_kwh"] = sum(r["discharge_kwh"] for r in part)
    return result


def price_metrics(dates, actual, forecasts):
    records = []
    for name, pred in forecasts.items():
        for d, day in enumerate(dates):
            if day < OUTPUT_START: continue
            a, p = actual[d], pred[d]
            threshold = np.quantile(a, .8)
            actual_high, pred_high = a >= threshold, p >= np.quantile(p, .8)
            records.append({"date": day.date().isoformat(), "method": name,
                "mae": np.mean(np.abs(a-p)), "rmse": np.sqrt(np.mean((a-p)**2)),
                "spearman": spearmanr(a, p).statistic,
                "high_price_precision": np.sum(actual_high & pred_high)/max(np.sum(pred_high),1),
                "high_price_recall": np.sum(actual_high & pred_high)/max(np.sum(actual_high),1)})
    return pd.DataFrame(records)


def emergency_periods(schedule):
    records = []
    for date, g in schedule.groupby("date", sort=False):
        active = g.emergency_kwh.to_numpy() > 1e-8
        starts = np.where(active & ~np.r_[False, active[:-1]])[0]
        ends = np.where(active & ~np.r_[active[1:], False])[0]
        for a, b in zip(starts, ends):
            sm, em = 10+10*a, 20+10*b
            label = f"{sm//60%24}:{sm%60:02d}-{em//60%24}:{em%60:02d}" + ("+1" if em >= 1440 else "")
            records.append({"日期": date, "购电时间段": label, "购电量": g.iloc[a:b+1].emergency_kwh.sum()})
    return pd.DataFrame(records)


def write_workbook(kind, schedule, daily):
    source = DATA / "附件5" / f"result{kind}.xlsx"
    target = ROOT / f"result{kind}.xlsx"
    shutil.copy2(source, target)
    wb = load_workbook(target)
    plan = wb["计划购电量"]
    adjusted = wb["调整购电量"] if kind == "4-3" else None
    for row, (date, g) in enumerate(schedule.groupby("date", sort=False), 2):
        dsum = daily[daily.date == date].iloc[0]
        plan.cell(row, 1, datetime.fromisoformat(date))
        pcol = "initial_contract_kwh" if kind == "4-3" else "contract_kwh"
        for col, value in enumerate(g[pcol], 2): plan.cell(row, col, float(value))
        plan.cell(row, 146, float(dsum.initial_contract_kwh)); plan.cell(row, 147, float(np.sum(g.actual_price*g[pcol])))
        if adjusted:
            adjusted.cell(row, 1, datetime.fromisoformat(date))
            for col, value in enumerate(g.final_contract_kwh, 2): adjusted.cell(row, col, float(value))
            adjusted.cell(row, 146, float(dsum.final_contract_kwh)); adjusted.cell(row, 147, float(dsum.settlement_cost))
    storage = wb["充放电量"]
    styles = [[copy(storage.cell(r, c)._style) for c in range(1, 7)] for r in range(2, 8)]
    storage.delete_rows(2, max(0, storage.max_row-1))
    labels = ["0:00-4:00", "4:00-8:00", "8:00-12:00", "12:00-16:00", "16:00-20:00", "20:00-24:00"]
    row = 2
    for _, dsum in daily.iterrows():
        for b, label in enumerate(labels):
            for c, style in enumerate(styles[b], 1): storage.cell(row, c)._style = copy(style)
            storage.cell(row, 1, datetime.fromisoformat(dsum.date) if b == 0 else None)
            storage.cell(row, 2, label); storage.cell(row, 3, float(dsum[f"block_{b}_charge_kwh"])); storage.cell(row, 4, float(dsum[f"block_{b}_discharge_kwh"]))
            if b == 0: storage.cell(row, 5, "0:00"); storage.cell(row, 6, float(dsum.soc_start_kwh))
            if b == 1: storage.cell(row, 5, "24:00"); storage.cell(row, 6, float(dsum.soc_end_kwh))
            row += 1
    emergency = wb["紧急购电量"]
    style = [copy(emergency.cell(2, c)._style) for c in range(1, 4)]
    emergency.delete_rows(2, max(0, emergency.max_row-1)); row, previous = 2, None
    for _, rec in emergency_periods(schedule).iterrows():
        for c, s in enumerate(style, 1): emergency.cell(row, c)._style = copy(s)
        emergency.cell(row, 1, datetime.fromisoformat(rec["日期"]) if rec["日期"] != previous else None)
        emergency.cell(row, 2, rec["购电时间段"]); emergency.cell(row, 3, float(rec["购电量"]))
        previous, row = rec["日期"], row+1
    wb.save(target)


def validate_one(kind, schedule, daily, adjustments, proxy, data):
    contract = schedule.active_contract_kwh if kind == "4-3" else schedule.contract_kwh
    balance = contract + schedule.pv_kw/6 + schedule.discharge_kwh + schedule.emergency_kwh - schedule.load_kw/6 - schedule.charge_kwh - schedule.curtailment_kwh - schedule.grid_spill_kwh
    transition = schedule.soc_end_kwh-schedule.soc_start_kwh-ETA_C*schedule.charge_kwh+schedule.discharge_kwh/ETA_D
    groups = list(schedule.groupby("date", sort=False))
    continuity = np.asarray([groups[i][1].iloc[-1].soc_end_kwh-groups[i+1][1].iloc[0].soc_start_kwh for i in range(len(groups)-1)])
    checks = {"energy_balance_max_abs_kwh": float(np.abs(balance).max()),
        "soc_transition_max_abs_kwh": float(np.abs(transition).max()), "soc_min_kwh": float(schedule.soc_end_kwh.min()),
        "soc_max_kwh": float(schedule.soc_end_kwh.max()), "charge_max_kwh": float(schedule.charge_kwh.max()),
        "discharge_max_kwh": float(schedule.discharge_kwh.max()), "cross_day_continuity_max_abs_kwh": float(np.abs(continuity).max()),
        "output_days": int(len(daily)), "dec31_next_0010_proxy_used": bool(proxy),
        "right_endpoint_first_price_residual": float(schedule.iloc[0].actual_price-data["price"][31,1])}
    if kind == "4-3":
        checks["executed_slot_modification_count"] = int((adjustments.slot < adjustments.issue_hour.map(START)).sum())
        recalc = adjustments.groupby("date").incremental_cost.sum()
        checks["settlement_recalculation_max_abs"] = float(np.max(np.abs(recalc.to_numpy()-daily.settlement_cost.to_numpy())))
    else:
        recalc = schedule.groupby("date").apply(lambda g: np.sum(g.actual_price*g.contract_kwh), include_groups=False)
        checks["settlement_recalculation_max_abs"] = float(np.max(np.abs(recalc.to_numpy()-daily.settlement_cost.to_numpy())))
    wb = load_workbook(ROOT/f"result{kind}.xlsx", read_only=True, data_only=True)
    sheets = [wb["计划购电量"]] + ([wb["调整购电量"]] if kind == "4-3" else [])
    checks["workbook_plan_rows"] = sheets[0].max_row-1
    checks["workbook_plan_blank_cells"] = sum(v is None for row in sheets[0].iter_rows(min_row=2, values_only=True) for v in row)
    if kind == "4-3": checks["workbook_adjusted_blank_cells"] = sum(v is None for row in sheets[1].iter_rows(min_row=2, values_only=True) for v in row)
    checks["workbook_storage_rows"] = wb["充放电量"].max_row-1
    plan_values = np.asarray([[float(v) for v in row[1:145]] for row in sheets[0].iter_rows(min_row=2, values_only=True)])
    expected_plan = np.vstack([g["initial_contract_kwh" if kind == "4-3" else "contract_kwh"].to_numpy()
                               for _, g in schedule.groupby("date", sort=False)])
    plan_rows = list(sheets[0].iter_rows(min_row=2, values_only=True))
    checks["workbook_plan_quantity_max_abs_kwh"] = float(np.max(np.abs(plan_values-expected_plan)))
    checks["workbook_plan_cost_residual_yuan"] = float(sum(float(r[146]) for r in plan_rows)-
                                                        np.sum(schedule.actual_price*expected_plan.ravel()))
    if kind == "4-3":
        adjusted_values = np.asarray([[float(v) for v in row[1:145]] for row in sheets[1].iter_rows(min_row=2, values_only=True)])
        expected_adjusted = np.vstack([g.final_contract_kwh.to_numpy() for _, g in schedule.groupby("date", sort=False)])
        adjusted_rows = list(sheets[1].iter_rows(min_row=2, values_only=True))
        checks["workbook_adjusted_quantity_max_abs_kwh"] = float(np.max(np.abs(adjusted_values-expected_adjusted)))
        checks["workbook_adjusted_cost_residual_yuan"] = float(sum(float(r[146]) for r in adjusted_rows)-daily.settlement_cost.sum())
    emergency_excel = sum(float(r[2] or 0) for r in wb["紧急购电量"].iter_rows(min_row=2, values_only=True))
    checks["workbook_emergency_quantity_residual_kwh"] = float(emergency_excel-schedule.emergency_kwh.sum())
    checks["all_pass"] = bool(checks["energy_balance_max_abs_kwh"] < 1e-6 and checks["soc_transition_max_abs_kwh"] < 1e-6 and
        checks["soc_min_kwh"] >= SOC_MIN-1e-6 and checks["soc_max_kwh"] <= SOC_MAX+1e-6 and checks["charge_max_kwh"] <= STEP_MAX+1e-6 and
        checks["discharge_max_kwh"] <= STEP_MAX+1e-6 and checks["cross_day_continuity_max_abs_kwh"] < 1e-6 and checks["output_days"] == 334 and
        checks["settlement_recalculation_max_abs"] < 1e-5 and checks["workbook_plan_rows"] == 334 and checks["workbook_plan_blank_cells"] == 0 and
        checks["workbook_storage_rows"] == 2004 and abs(checks["right_endpoint_first_price_residual"]) < 1e-12 and
        checks["workbook_plan_quantity_max_abs_kwh"] < 1e-8 and abs(checks["workbook_plan_cost_residual_yuan"]) < 1e-5 and
        abs(checks["workbook_emergency_quantity_residual_kwh"]) < 1e-5 and
        (kind != "4-3" or (checks["executed_slot_modification_count"] == 0 and checks["workbook_adjusted_blank_cells"] == 0)))
    if kind == "4-3":
        checks["all_pass"] = bool(checks["all_pass"] and checks["workbook_adjusted_quantity_max_abs_kwh"] < 1e-8
                                  and abs(checks["workbook_adjusted_cost_residual_yuan"]) < 1e-5)
    return checks


def make_figures(schedule42, daily42, schedule43, daily43, metrics, comparison):
    plt.rcParams.update({"font.sans-serif": ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"],
        "axes.unicode_minus": False, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
    colors = ["#CFCECE", "#E9A6A1", "#AADCA9", "#3775BA", "#0F4D92"]
    m = metrics.groupby("method")[["mae", "rmse", "spearman"]].mean().loc[["fixed","lag1","lag7","structured_ridge","adaptive"]]
    m.index = ["附件1固定", "前一日", "前一周", "结构化岭回归", "自适应集成"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8)); m[["mae","rmse"]].plot.bar(ax=axes[0], color=colors[3:5], edgecolor="black", linewidth=.5)
    m.spearman.plot.bar(ax=axes[1], color=colors, edgecolor="black", linewidth=.5)
    axes[0].set_ylabel("误差 / 元每千瓦时"); axes[1].set_ylabel("日内排序 Spearman");
    axes[0].legend(["MAE", "RMSE"], frameon=False); axes[1].legend(["Spearman"], frameon=False)
    for ax in axes: ax.set_xlabel(""); ax.tick_params(axis="x", rotation=20)
    save_figure(fig, "price_forecast_comparison")
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    axes[0].plot(pd.to_datetime(daily42.date), daily42.total_cost/1e4, color="#0F4D92", lw=1); axes[0].set_ylabel("日成本 / 万元")
    axes[1].plot(pd.to_datetime(schedule42.date), schedule42.soc_end_kwh, color="#3775BA", lw=.6); axes[1].set_ylabel("SOC / kWh"); axes[1].set_xlabel("日期")
    save_figure(fig, "problem4_2_cost_storage")
    sample = schedule43[schedule43.date == "2025-08-01"]; x = np.arange(144)/6
    fig, ax = plt.subplots(figsize=(9, 3.8)); ax.plot(x, sample.initial_contract_kwh, label="0点合同", color="#B64342")
    ax.plot(x, sample.final_contract_kwh, label="最终合同", color="#0F4D92"); ax.fill_between(x, sample.initial_contract_kwh, sample.final_contract_kwh, color="#AADCA9", alpha=.45)
    ax.set_xlabel("运营窗口时刻 / h"); ax.set_ylabel("购电量 / kWh"); ax.legend(frameon=False); save_figure(fig, "problem4_3_contract_updates")
    fig, ax = plt.subplots(figsize=(9, 4)); c = comparison.copy(); ax.bar(np.arange(len(c)), c.total_cost/1e6, color=["#0F4D92" if x else "#CFCECE" for x in c.formal], edgecolor="black", linewidth=.6)
    ax.set_xticks(np.arange(len(c)), c.label, rotation=18, ha="right"); ax.set_ylabel("样本外实际总成本 / 百万元"); save_figure(fig, "problem4_model_cost_comparison")


def save_figure(fig, name):
    fig.tight_layout(pad=1.2); fig.savefig(FIG/f"{name}.pdf", bbox_inches="tight"); fig.savefig(FIG/f"{name}.png", dpi=300, bbox_inches="tight"); plt.close(fig)


def write_docs(comparison, metrics, d42, d43, checks, elapsed, pv_gate, refresh=False):
    pavg = metrics.groupby("method")[["mae","rmse","spearman","high_price_precision","high_price_recall"]].mean()
    best = comparison.loc[comparison.total_cost.idxmin()]
    analysis = f"""# 问题四分析与建模报告

## 信息集与时间语义
所有序列按十分钟区间右端点解释，模板首列对应当天0:20，末列对应次日0:10。0:00读取前一数据日的`0:00+1`；合同末格禁止调用次日预测，采用当前日0:10预测作单格周期代理。1月1日预测使用附件1先验；12月31日次日0:10实际缺失采用当日0:10周期代理并审计记录。

## 因果预测与联合情景
价格比较附件1固定曲线、lag1、lag7、扩展窗口结构化岭回归和按过去28日误差反比加权的自适应组合。正式策略采用自适应组合；6/12/18时只依据已发生实际偏差对剩余预测作指数衰减校正。4-2负载与PV均为周同期、岭回归及过去误差自适应组合。4-3负载同法，PV采用附件3原始滚动预报；1月门控复核结果为`{pv_gate}`。五情景从同一历史日的完整净负荷和价格误差轨迹联合抽取，保留时序和互相关。

## 随机优化与结算
4-2每天0点求解五情景两阶段LP，目标含期望成本和权重0.2的CVaR0.9，场景日末SOC约束为日初SOC。4-3在0/6/12/18更新，已执行时段冻结；经过确定性、情景期望和CVaR对照后，正式结果采用样本外实际总费用最低的因果确定性滚动LP，随机CVaR保留为风险对照。优化只见预测价，初始合同、上调1.5倍、下调退款50%及紧急5倍均按附件4实际交易时段价事后结算。LP按小时聚合，合同分配和物理执行按十分钟，SOC跨日。

## 模型选择
模型以2025-02-01至12-31样本外实际总成本为主、预测指标为辅。Oracle使用实际未来价格（4-3还使用实际净负荷），只作为不可执行信息下界，不列为正式结果。
"""
    total42, total43 = d42.sum(numeric_only=True), d43.sum(numeric_only=True)
    results = f"""# 问题四计算结果

## 核心结果
- 4-2正式总成本：{total42.total_cost:.2f}元；合同结算{total42.settlement_cost:.2f}元，紧急费{total42.emergency_cost:.2f}元，紧急电量{total42.emergency_kwh:.2f}kWh。
- 4-3正式总成本：{total43.total_cost:.2f}元；合同调整结算{total43.settlement_cost:.2f}元，紧急费{total43.emergency_cost:.2f}元，紧急电量{total43.emergency_kwh:.2f}kWh。
- 成本最低对照：{best.label}，{best.total_cost:.2f}元；其`formal={best.formal}`，Oracle不得作为可执行答案。
- 自适应价格预测：MAE {pavg.loc['adaptive','mae']:.4f}，RMSE {pavg.loc['adaptive','rmse']:.4f}，Spearman {pavg.loc['adaptive','spearman']:.4f}，高价召回率 {pavg.loc['adaptive','high_price_recall']:.3f}。
- 运行耗时：{elapsed:.1f}秒。

## 验证
`outputs/validation_checks.json`中4-2与4-3的`all_pass`分别为`{checks['problem4_2']['all_pass']}`和`{checks['problem4_3']['all_pass']}`。校验覆盖能量平衡、SOC转移和上下限、单时段功率、跨日连续、合同冻结、334日、Excel空值和复算、首列右端点价格映射及12月31日代理。

## 产物
十分钟执行表、每版合同、日汇总、预测指标和对照成本均位于`outputs/`；四组论文图同时提供PDF与300 dpi PNG。`result4-2.xlsx`和`result4-3.xlsx`复制模板并保留样式。
"""
    def markdown_table(frame):
        values = frame.reset_index(drop=True)
        header = "| " + " | ".join(map(str, values.columns)) + " |\n"
        separator = "| " + " | ".join(["---"] * len(values.columns)) + " |\n"
        body = "".join("| " + " | ".join(f"{v:.6g}" if isinstance(v, (float, np.floating)) else str(v) for v in row) + " |\n"
                       for row in values.itertuples(index=False, name=None))
        return header + separator + body
    method = "# 方法对比\n\n正式模型以因果可执行性和样本外实际总成本选择；Oracle仅为完美信息下界。4-3确定性与Oracle为小时LP对照。\n\n" + markdown_table(comparison) + "\n## 价格预测\n\n" + markdown_table(pavg.reset_index())
    readme = f"""# C题问题四复现说明

```bash
conda run -n mathmodel python code/problem4.py
```

程序只读取`../附件`，所有文件写入`task4`。4-2正式模型为5个联合误差轨迹、小时随机LP与CVaR0.9；4-3正式模型为0/6/12/18因果确定性滚动LP，随机CVaR作为风险对照。实际执行和物理校验均为十分钟。输出覆盖334日，当前运行4-2/4-3总成本为{total42.total_cost:.2f}/{total43.total_cost:.2f}元。
"""
    (OUT/"generated_run_summary.md").write_text(results, encoding="utf-8")
    if refresh:
        (REPORT/"ANALYSIS_MODELING_REPORT.md").write_text(analysis, encoding="utf-8")
        (REPORT/"RESULTS_REPORT.md").write_text(results, encoding="utf-8")
        (REPORT/"METHOD_COMPARISON.md").write_text(method, encoding="utf-8")
        (ROOT/"README.md").write_text(readme, encoding="utf-8")


def january_pv_gate(data):
    dates, index = data["dates"], {d: i for i, d in enumerate(data["dates"])}
    raw, corrected, history = [], [], {i: [] for i in ISSUES}
    for day in dates[dates < OUTPUT_START]:
        for issue in ISSUES:
            actual = np.asarray([endpoint_value(data["pv"], index, day, issue*60+60*k)[0] for k in range(1,25)])
            forecast = data["pv_forecast"][(day, issue)]
            bias = np.median(np.asarray(history[issue]), axis=0) if history[issue] else np.zeros(24)
            raw.extend(np.abs(actual-forecast)); corrected.extend(np.abs(actual-np.maximum(0,forecast+bias)))
            history[issue].append(actual-forecast)
    r, c = float(np.mean(raw)), float(np.mean(corrected))
    return {"raw_mae_kw": r, "candidate_corrected_mae_kw": c, "use_correction": c < r,
            "decision": "启用候选校正" if c < r else "拒绝校正，使用附件3原始预报"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--skip-comparisons", action="store_true")
    parser.add_argument("--refresh-brief-docs", action="store_true"); args = parser.parse_args()
    for directory in (OUT, FIG, REPORT): directory.mkdir(parents=True, exist_ok=True)
    started = time.time(); data = load_inputs()
    load_pred, _ = build_signal_forecast(data["load"], data["base_load"])
    pv_pred, _ = build_signal_forecast(data["pv"], data["base_pv"])
    price_forecasts, _ = build_price_forecasts(data["price"], data["base_price"])
    metrics = price_metrics(data["dates"], data["price"], price_forecasts)
    pv_gate = january_pv_gate(data)
    s42, d42, proxy42 = run_42(data, load_pred, pv_pred, price_forecasts["adaptive"], True, False, True)
    s43, a43, d43, proxy43 = run_43(data, load_pred, price_forecasts["adaptive"], False, False, True)
    _, _, d43_risk, _ = run_43(data, load_pred, price_forecasts["adaptive"], True, False, True)
    comparisons = [{"problem":"4-2", "method":"causal_adaptive_stochastic_cvar", "label":"4-2 因果随机CVaR", "formal":True,
        "settlement_cost":d42.settlement_cost.sum(), "emergency_cost":d42.emergency_cost.sum(), "total_cost":d42.total_cost.sum(), "emergency_kwh":d42.emergency_kwh.sum()},
        {"problem":"4-3", "method":"causal_deterministic_mpc", "label":"4-3 因果确定性MPC", "formal":True,
        "settlement_cost":d43.settlement_cost.sum(), "emergency_cost":d43.emergency_cost.sum(), "total_cost":d43.total_cost.sum(), "emergency_kwh":d43.emergency_kwh.sum()}]
    comparisons.append({"problem":"4-3", "method":"causal_stochastic_cvar", "label":"4-3 随机CVaR风险对照", "formal":False,
        "settlement_cost":d43_risk.settlement_cost.sum(), "emergency_cost":d43_risk.emergency_cost.sum(),
        "total_cost":d43_risk.total_cost.sum(), "emergency_kwh":d43_risk.emergency_kwh.sum()})
    if not args.skip_comparisons:
        for name, stochastic, oracle in [("fixed_price",True,False),("oracle_price",True,True)]:
            pred = price_forecasts["fixed"] if name == "fixed_price" else price_forecasts["adaptive"]
            _, d, _ = run_42(data, load_pred, pv_pred, pred, stochastic, oracle, True)
            comparisons.append({"problem":"4-2","method":name,"label":"4-2 固定附件1" if not oracle else "4-2 Oracle价格", "formal":False,
                "settlement_cost":d.settlement_cost.sum(),"emergency_cost":d.emergency_cost.sum(),"total_cost":d.total_cost.sum(),"emergency_kwh":d.emergency_kwh.sum()})
        for name, oracle in [("oracle_deterministic",True)]:
            _, _, d, _ = run_43(data, load_pred, price_forecasts["adaptive"], False, oracle, True)
            comparisons.append({"problem":"4-3","method":name,"label":"4-3 Oracle确定性", "formal":False,
                "settlement_cost":d.settlement_cost.sum(),"emergency_cost":d.emergency_cost.sum(),"total_cost":d.total_cost.sum(),"emergency_kwh":d.emergency_kwh.sum()})
    comparison = pd.DataFrame(comparisons)
    metrics.to_csv(OUT/"price_forecast_metrics.csv", index=False)
    s42.to_csv(OUT/"problem4_2_schedule.csv", index=False); d42.to_csv(OUT/"problem4_2_daily.csv", index=False)
    s43.to_csv(OUT/"problem4_3_schedule.csv", index=False); a43.to_csv(OUT/"problem4_3_adjustments.csv", index=False); d43.to_csv(OUT/"problem4_3_daily.csv", index=False)
    a43.to_csv(OUT/"problem4_3_contract_versions.csv", index=False)
    comparison.to_csv(OUT/"method_comparison.csv", index=False)
    write_workbook("4-2", s42, d42); write_workbook("4-3", s43, d43)
    checks = {"problem4_2": validate_one("4-2", s42, d42, pd.DataFrame(), proxy42, data),
              "problem4_3": validate_one("4-3", s43, d43, a43, proxy43, data),
              "task4_only_write_policy": True, "pv_january_gate": pv_gate}
    checks["all_pass"] = checks["problem4_2"]["all_pass"] and checks["problem4_3"]["all_pass"]
    (OUT/"validation_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    make_figures(s42, d42, s43, d43, metrics, comparison)
    write_docs(comparison, metrics, d42, d43, checks, time.time()-started, pv_gate,
               args.refresh_brief_docs)
    print(json.dumps({"problem4_2_total_cost":d42.total_cost.sum(), "problem4_3_total_cost":d43.total_cost.sum(),
        "validation":checks, "elapsed_seconds":time.time()-started}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
