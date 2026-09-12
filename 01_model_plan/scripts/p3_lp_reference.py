"""P3 planning surrogate and causal rollout, NOT the annual solver.

All inputs are caller-supplied forecasts/scenarios. This module never reads files,
loads actual future data, trains a model, or exports a competition workbook.
The storage trajectory in the LP is SHARED across scenarios. Scenario shortage
variables are loss proxies, not the actual controller's output. Replay candidates
with causal_rollout before accepting an intraday plan revision.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import math
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

Risk = Literal['mean', 'worst']

@dataclass(frozen=True)
class Battery:
    lo: float = 1200.0
    hi: float = 10800.0
    max_kwh: float = 5000.0 / 6.0
    eta_c: float = 0.9
    eta_d: float = 0.9


def ordinary_cost(g0: np.ndarray, a: np.ndarray, price: np.ndarray) -> np.ndarray:
    """Final-vs-0h cancellation substitution. No emergency included."""
    return price * (a + 0.5 * np.abs(a - g0))


def feedback(s: float, a: float, load: float, pv: float, b: Battery) -> dict:
    """One CURRENT slot, all energies in kWh. Same source-priority as P2."""
    if not all(math.isfinite(x) for x in (s, a, load, pv)):
        raise ValueError('Non-finite current-slot input')
    if min(a, load, pv) < -1e-9 or not b.lo - 1e-7 <= s <= b.hi + 1e-7:
        raise ValueError('Invalid current-slot input')
    a, load, pv = max(a, 0.), max(load, 0.), max(pv, 0.)
    cap_c = max(0., min(b.max_kwh, (b.hi - s) / b.eta_c))
    cap_d = max(0., min(b.max_kwh, b.eta_d * (s - b.lo)))
    action = min(cap_c, max(-cap_d, a + pv - load))
    c, d = max(action, 0.), max(-action, 0.)
    residual = load - pv + c - d - a
    emergency, excess = max(residual, 0.), max(-residual, 0.)
    unused = min(a, excess)
    return {'charge': c, 'discharge': d, 'emergency': emergency,
            'grid_used': a - unused, 'grid_unused': unused,
            'pv_spill': excess - unused,
            'soc_end': s + b.eta_c * c - d / b.eta_d}


def solve_plan(net_scenarios: np.ndarray, price: np.ndarray, s0: float,
               current_slots: int, original_g0: np.ndarray | None = None,
               keep_current: np.ndarray | None = None, risk: Risk = 'mean',
               terminal_value: float = 0., battery: Battery = Battery()) -> dict:
    """Solve one event's 24h *surrogate*, no forecast/actual file access.

    original_g0=None is the 0h case (all N slots must belong to current day).
    At an intraday event original_g0 has length current_slots. The remaining
    N-current_slots purchases are hypothetical next-day continuation only.
    KEEP fixes only current-day quantities, not the hypothetical continuation.
    """
    n = np.asarray(net_scenarios, dtype=float)
    p = np.asarray(price, dtype=float)
    if n.ndim != 2 or p.shape != (n.shape[1],) or n.shape[0] < 1:
        raise ValueError('Expected scenarios KxN and prices N')
    K, N = n.shape
    if not np.isfinite(n).all() or not np.isfinite(p).all() or np.any(p <= 0):
        raise ValueError('Finite inputs and strictly positive prices required')
    if not 1 <= current_slots <= N or not battery.lo <= s0 <= battery.hi:
        raise ValueError('Invalid event boundary or initial SOC')
    if not (battery.lo <= battery.hi and battery.max_kwh >= 0):
        raise ValueError('Invalid battery bounds')
    if not (0 < battery.eta_c <= 1 and 0 < battery.eta_d <= 1):
        raise ValueError('Efficiencies must be in (0,1]')
    if risk not in ('mean', 'worst') or terminal_value < 0:
        raise ValueError('Invalid risk measure/terminal value')
    g = None if original_g0 is None else np.asarray(original_g0, dtype=float)
    keep = None if keep_current is None else np.asarray(keep_current, dtype=float)
    if g is None and current_slots != N:
        raise ValueError('0h case must consist solely of the current day')
    for x in (g, keep):
        if x is not None and (x.shape != (current_slots,) or not np.isfinite(x).all() or np.any(x < 0)):
            raise ValueError('Bad commitment vector')
    if keep is not None and g is None:
        raise ValueError('KEEP is an intraday comparison, not an initial plan')

    q0, c0, d0, sbase, e0 = 0, N, 2*N, 3*N, 4*N
    pos = e0 + K*N
    up0 = down0 = None
    if g is not None:
        up0, down0 = pos, pos + current_slots
        pos += 2*current_slots
    theta = pos if risk == 'worst' else None
    nv = pos + (risk == 'worst')
    obj = np.zeros(nv)
    obj[q0:q0+N] = p
    obj[sbase+N-1] = -terminal_value
    if g is not None:
        obj[up0:up0+current_slots] = .5*p[:current_slots]
        obj[down0:down0+current_slots] = .5*p[:current_slots]
    if risk == 'mean':
        obj[e0:e0+K*N] = np.tile(5*p/K, K)
    else:
        obj[theta] = 1.
    bounds = [(0., None)] * nv
    for j in range(N):
        bounds[c0+j] = (0., battery.max_kwh)
        bounds[d0+j] = (0., battery.max_kwh)
        bounds[sbase+j] = (battery.lo, battery.hi)
    if keep is not None:
        for j in range(current_slots): bounds[q0+j] = (keep[j], keep[j])

    er, ec, ev, rhs_eq = [], [], [], []
    def eq(entries, rhs):
        row = len(rhs_eq); rhs_eq.append(rhs)
        for col, value in entries: er.append(row); ec.append(col); ev.append(value)
    for j in range(N):
        terms = [(sbase+j,1.), (c0+j,-battery.eta_c), (d0+j,1/battery.eta_d)]
        if j: terms.append((sbase+j-1,-1.))
        eq(terms, s0 if j == 0 else 0.)
    if g is not None:
        for j in range(current_slots): eq([(q0+j,1.), (up0+j,-1.), (down0+j,1.)], g[j])
    ur, uc, uv, rhs_ub = [], [], [], []
    def ub(entries, rhs):
        row = len(rhs_ub); rhs_ub.append(rhs)
        for col, value in entries: ur.append(row); uc.append(col); uv.append(value)
    for k in range(K):
        for j in range(N):
            ub([(c0+j,1.), (d0+j,-1.), (q0+j,-1.), (e0+k*N+j,-1.)], -n[k,j])
    if risk == 'worst':
        for k in range(K):
            ub([(e0+k*N+j,5*p[j]) for j in range(N)] + [(theta,-1.)], 0.)
    Aeq = coo_matrix((ev,(er,ec)), shape=(len(rhs_eq),nv)).tocsr()
    Aub = coo_matrix((uv,(ur,uc)), shape=(len(rhs_ub),nv)).tocsr()
    sol = linprog(obj, A_ub=Aub, b_ub=np.asarray(rhs_ub), A_eq=Aeq,
                  b_eq=np.asarray(rhs_eq), bounds=bounds, method='highs',
                  options={'primal_feasibility_tolerance':1e-8,
                           'dual_feasibility_tolerance':1e-8})
    if not sol.success: raise RuntimeError(f'LP failed: {sol.status}, {sol.message}')
    q = sol.x[q0:q0+N].copy()
    c, d = sol.x[c0:c0+N].copy(), sol.x[d0:d0+N].copy()
    # SOC-preserving removal of simultaneous charge/discharge.
    # This never worsens shortage cost when surplus can be discarded freely.
    cycle = np.minimum(c, d/(battery.eta_c*battery.eta_d))
    c -= cycle; d -= battery.eta_c*battery.eta_d*cycle
    c[np.abs(c)<1e-10]=0.; d[np.abs(d)<1e-10]=0.
    states = s0 + np.cumsum(battery.eta_c*c - d/battery.eta_d)
    shortfall = np.maximum(n+c-d-q, 0.)
    ordinary = float(p@q) if g is None else float(
        ordinary_cost(g,q[:current_slots],p[:current_slots]).sum() + p[current_slots:]@q[current_slots:])
    losses = (shortfall*(5*p)).sum(axis=1)
    risk_loss = float(losses.mean() if risk == 'mean' else losses.max())
    value = ordinary + risk_loss - terminal_value*(states[-1]-battery.lo)
    raw_plus_constant = float(sol.fun + terminal_value*battery.lo)
    if value > raw_plus_constant + max(1e-6, abs(raw_plus_constant)*1e-8):
        raise RuntimeError('Loop-removal unexpectedly worsened the economic objective')
    return {'commitment':q, 'nominal_charge':c, 'nominal_discharge':d,
            'nominal_soc_end':states, 'shortfall_proxy':shortfall,
            'objective_surrogate':value, 'ordinary_horizon_cost':ordinary,
            'risk_shortfall_proxy_cost':risk_loss, 'cycle_removed_kwh':float(cycle.sum()),
            'solver_status':int(sol.status), 'solver_iterations':int(sol.nit)}


def causal_rollout(commitment: np.ndarray, load_scenarios: np.ndarray,
                   pv_scenarios: np.ndarray, price: np.ndarray, s0: float,
                   current_slots: int, original_g0: np.ndarray | None,
                   risk: Risk = 'mean', terminal_value: float = 0.,
                   battery: Battery = Battery()) -> dict:
    """Historical-scenario CONDITIONAL score, never an actual annual bill.

    The ordinary candidate vector (including hypothetical next-day quantities)
    is fixed before each simulated path. Within a path, feedback sees only its
    current load/PV and running state. No per-scenario LP or clairvoyant choice.
    """
    q=np.asarray(commitment,dtype=float); l=np.asarray(load_scenarios,dtype=float)
    v=np.asarray(pv_scenarios,dtype=float); p=np.asarray(price,dtype=float)
    if l.ndim!=2 or v.shape!=l.shape or q.shape!=(l.shape[1],) or p.shape!=q.shape:
        raise ValueError('Shape mismatch')
    if not np.isfinite(l).all() or not np.isfinite(v).all() or np.any(l<0) or np.any(v<0):
        raise ValueError('Scenarios must be finite nonnegative energies')
    if risk not in ('mean', 'worst') or not math.isfinite(terminal_value) or terminal_value < 0:
        raise ValueError('Invalid rollout risk measure/terminal value')
    if not np.isfinite(q).all() or not np.isfinite(p).all() or np.any(q < 0) or np.any(p <= 0):
        raise ValueError('Invalid commitment/prices')
    if not 1 <= current_slots <= len(q) or not battery.lo <= s0 <= battery.hi:
        raise ValueError('Invalid rollout event/state')
    g=None if original_g0 is None else np.asarray(original_g0,dtype=float)
    if g is not None and (g.shape != (current_slots,) or not np.isfinite(g).all() or np.any(g<0)):
        raise ValueError('Invalid original commitment')
    if g is None and current_slots != len(q):
        raise ValueError('Initial plan cannot contain a fictitious next-day contract')
    ordcost=float(p@q) if g is None else float(
        ordinary_cost(g,q[:current_slots],p[:current_slots]).sum()+p[current_slots:]@q[current_slots:])
    scores=[]; ends=[]; emergency=[]; per_path=[]
    for k in range(l.shape[0]):
        s=float(s0); ecost=0.; ekwh=0.; rows=[]
        for j in range(l.shape[1]):
            r=feedback(s,float(q[j]),float(l[k,j]),float(v[k,j]),battery)
            s=r['soc_end']; ekwh+=r['emergency']; ecost+=5*p[j]*r['emergency']; rows.append(r)
        scores.append(ordcost+ecost-terminal_value*(s-battery.lo))
        ends.append(s); emergency.append(ekwh); per_path.append(rows)
    value=float(np.mean(scores) if risk=='mean' else np.max(scores))
    return {'score':value,'path_scores':scores,'terminal_soc':ends,
            'emergency_kwh':emergency,'trajectories':per_path,
            'score_label':'CONDITIONAL_SCENARIO_ROLLOUT_NOT_ACTUAL_BILL'}
