"""P3生产数学核；参考模型等价实现，输入防御及调用日志显式集成。"""
from __future__ import annotations
import math
import numpy as np
from scipy.sparse import coo_matrix
from p3_batch_support import Battery, validate_battery, ordinary_cost, rollout
Risk = str

def feedback(s,a,load,pv,b=Battery()):
    validate_battery(b)
    if not all(math.isfinite(float(x)) for x in (s,a,load,pv)):
        raise ValueError('当前槽含非有限输入')
    if min(a,load,pv)<0 or not b.lo-1e-7<=s<=b.hi+1e-7:
        raise ValueError('非法当前槽输入')
    capc=max(0.,min(b.max_kwh,(b.hi-s)/b.eta_c))
    capd=max(0.,min(b.max_kwh,b.eta_d*(s-b.lo)))
    u=min(capc,max(-capd,a+pv-load));c=max(u,0.);d=max(-u,0.)
    r=load-pv+c-d-a;e=max(r,0.);excess=max(-r,0.);unused=min(a,excess)
    return {'charge_bus_kwh':c,'discharge_bus_kwh':d,'emergency_kwh':e,
            'grid_used_kwh':a-unused,'grid_unused_kwh':unused,
            'pv_curtailment_kwh':excess-unused,'soc_end_kwh':s+b.eta_c*c-d/b.eta_d}

def solve_plan(net_scenarios: np.ndarray, price: np.ndarray, s0: float,
               current_slots: int, original_g0: np.ndarray | None = None,
               keep_current: np.ndarray | None = None, risk: Risk = 'mean',
               terminal_value: float = 0., battery: Battery = Battery(), invoke=None) -> dict:
    """Solve one event's 24h *surrogate*, no forecast/actual file access.

    original_g0=None is the 0h case (all N slots must belong to current day).
    At an intraday event original_g0 has length current_slots. The remaining
    N-current_slots purchases are hypothetical next-day continuation only.
    KEEP fixes only current-day quantities, not the hypothetical continuation.
    """
    validate_battery(battery)
    if not isinstance(current_slots, (int, np.integer)) or isinstance(current_slots, (bool, np.bool_)):
        raise ValueError('current_slots必须是整数')
    if not math.isfinite(float(terminal_value)) or terminal_value < 0:
        raise ValueError('终端系数必须有限非负')
    if invoke is None: raise ValueError('必须通过调用账本求解')
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
    sol = invoke(obj, A_ub=Aub, b_ub=np.asarray(rhs_ub), A_eq=Aeq,
                  b_eq=np.asarray(rhs_eq), bounds=bounds, method='highs',
                  options={'primal_feasibility_tolerance':1e-8,
                           'dual_feasibility_tolerance':1e-8})
    if not sol.success: raise RuntimeError(f'LP failed: {sol.status}, {sol.message}')
    lower=np.array([x[0] if x[0] is not None else -np.inf for x in bounds])
    upper=np.array([x[1] if x[1] is not None else np.inf for x in bounds])
    residual=max(float(np.max(np.abs(Aeq@sol.x-np.asarray(rhs_eq)))),
                 float(np.max(np.maximum(Aub@sol.x-np.asarray(rhs_ub),0))),
                 float(np.max(np.maximum(lower-sol.x,0))),float(np.max(np.maximum(sol.x-upper,0))))
    if residual>1e-6: raise RuntimeError(f'LP约束残差过大: {residual}')
    negative_zero_count=int(np.count_nonzero((sol.x<0)&(lower==0)))
    if np.any((sol.x < -1e-8)&(lower==0)): raise RuntimeError('求解器返回实质负值')
    sol.x[(sol.x<0)&(lower==0)]=0
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
            'solver_status':int(sol.status), 'solver_iterations':int(sol.nit),
            'primal_residual':residual, 'raw_objective':raw_plus_constant,
            'negative_zero_count':negative_zero_count,'call_id':sol['call_id'],
            'solver_seconds':sol['solver_seconds']}



def choose(keep,adjust,l,pv,p,s,m,g,grid,risk,terminal):
    records=[]
    for alpha in grid:
        q=(1-alpha)*keep+alpha*adjust
        diff=float(np.max(np.abs(q[:m]-keep[:m])))
        eligible=alpha==0 or diff>1e-7
        record={'alpha':float(alpha),'eligible':eligible,'q':q,'max_change_kwh':diff,
                'reason':'KEEP' if alpha==0 else ('已评分' if eligible else '仅延续或当日变化小于容差')}
        if eligible:
            record.update(rollout(q,l,pv,p,s,m,g,risk,terminal))
        else: record['score']=None
        records.append(record)
    eps=max(1e-6,1e-10*max(1,abs(records[0]['score'])))
    best=min(x['score'] for x in records if x['eligible'])
    selected=min((r for r in records if r['eligible'] and r['score']<=best+eps),key=lambda x:x['alpha'])
    return selected,records,eps

