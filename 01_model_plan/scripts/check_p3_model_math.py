"""Small synthetic model checks only: no official data, fitting or annual replay."""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path
import numpy as np
from p3_lp_reference import Battery, ordinary_cost, feedback, solve_plan, causal_rollout


def run_checks() -> dict:
    checks=[]
    calls=0
    def check(name, passed, detail):
        checks.append({'check':name,'pass':bool(passed),'detail':detail})
        if not passed: raise AssertionError(name+': '+str(detail))
    def close(x,y,tol=1e-7): return abs(float(x)-float(y))<=tol
    for a,expect in [(100,100),(80,90),(150,175),(0,50)]:
        x=ordinary_cost(np.array([100.]),np.array([float(a)]),np.ones(1))[0]
        check('settlement_100_to_'+str(a),close(x,expect),{'value':float(x),'expected':expect})
    path=[100.,150.,80.]
    inc=path[-1]+.5*sum(abs(x-y) for x,y in zip(path[:-1],path[1:]))
    check('path_vs_final_not_mixed',close(inc,140) and close(ordinary_cost(np.array([100.]),np.array([80.]),np.ones(1))[0],90),{'incremental':inc,'main':90})
    check('plan_quote_not_added_twice',close(90+5*10,140),{'final_bill':140,'not':240})

    no_battery=Battery(0.,0.,0.,1.,1.)
    n=np.arange(0.,101.,10.).reshape(-1,1); p=np.ones(1)
    for g,expect in [(None,80.),(100.,90.),(40.,70.),(80.,80.)]:
        ans=solve_plan(n,p,0.,1,None if g is None else np.array([g]),battery=no_battery);calls+=1
        check('newsvendor_'+str(g),close(ans['commitment'][0],expect),{'q':float(ans['commitment'][0]),'expected':expect})
    worst=solve_plan(n,p,0.,1,risk='worst',battery=no_battery);calls+=1
    check('finite_set_worst_case',close(worst['commitment'][0],100.),{'q':float(worst['commitment'][0])})
    keep=solve_plan(n,p,0.,1,np.array([40.]),np.array([40.]),battery=no_battery);calls+=1
    adj=solve_plan(n,p,0.,1,np.array([40.]),battery=no_battery);calls+=1
    check('keep_nested_in_adjust',adj['objective_surrogate']<=keep['objective_surrogate']+1e-7,{'keep':keep['objective_surrogate'],'adjust':adj['objective_surrogate']})

    b=Battery();r=feedback(1200.,50.,100.,0.,b)
    check('empty_storage_emergency',close(r['emergency'],50.) and close(r['soc_end'],1200.),r)
    r=feedback(10800.,500.,100.,700.,b)
    check('unused_vs_pv_spill',close(r['grid_unused'],500.) and close(r['pv_spill'],600.) and close(r['emergency'],0),r)
    # Algebraic SOC-preserving loop removal.
    c,d=300.,200.; eps=min(c,d/(.9*.9))
    cc,dd=c-eps,d-.9*.9*eps
    check('loop_removal_preserves_soc',close(.9*c-d/.9,.9*cc-dd/.9) and min(cc,dd)<1e-8,{'C':cc,'D':dd})

    l=np.array([[300.,400.,600.,350.],[400.,500.,500.,400.],[350.,450.,700.,400.]])
    pv=np.array([[500.,300.,0.,0.],[400.,400.,0.,0.],[600.,200.,0.,0.]])
    price=np.array([.5,1.,1.5,.5]);g=np.array([50.,50.])
    ans=solve_plan(l-pv,price,6000.,2,g,terminal_value=.45);calls+=1
    score=causal_rollout(ans['commitment'],l,pv,price,6000.,2,g,terminal_value=.45)
    maxbalance=0.;maxsoc=0.;mind=1e9;maxd=-1e9
    for k,rows in enumerate(score['trajectories']):
        s=6000.
        for j,r in enumerate(rows):
            balance=r['grid_used']+r['emergency']+pv[k,j]+r['discharge']-l[k,j]-r['charge']-r['pv_spill']
            maxbalance=max(maxbalance,abs(balance))
            maxsoc=max(maxsoc,abs(r['soc_end']-(s+.9*r['charge']-r['discharge']/.9)))
            mind=min(mind,r['soc_end']);maxd=max(maxd,r['soc_end']);s=r['soc_end']
            check(f'current_feedback_non_simultaneous_{k}_{j}',min(r['charge'],r['discharge'])<1e-9 and (r['emergency']<1e-9 or r['charge']<1e-9),{})
    check('rollout_physical_balance',maxbalance<1e-8 and maxsoc<1e-8 and mind>=1200-1e-8 and maxd<=10800+1e-8,{'balance':maxbalance,'soc':maxsoc})
    l2=l.copy();l2[:,2:]+=1000
    score2=causal_rollout(ans['commitment'],l2,pv,price,6000.,2,g,terminal_value=.45)
    prefix_equal=all(score['trajectories'][k][:2]==score2['trajectories'][k][:2] for k in range(3))
    check('rollout_future_perturbation',prefix_equal,{'future_changed_after_slot':2})
    check('continuation_not_returned_as_today',len(ans['commitment'][:2])==2 and len(ans['commitment'][2:])==2,{})
    for h,expected in [(0,1),(6,37),(12,73),(18,109)]:
        check('clock_first_modifiable_'+str(h),6*h+1==expected,{'slot':expected})
    # Interpolation of 0→600 kW across an hour has 300 kWh integral.
    avgs=np.array([(2*q+1)/12*600 for q in range(6)])
    check('pwl_energy_conservation',close(avgs.sum()/6,300.),{'integral_kwh':float(avgs.sum()/6)})
    return {'scope':'SYNTHETIC_MODEL_MATH_ONLY','status':'PASS','checks':checks,
            'pass_count':len(checks),'fail_count':0,'lp_calls':calls,
            'official_data_fit':0,'annual_strategy_runs':0,'result_workbooks_generated':0,
            'not_a_gate':'Does not certify local sources, forecast quality or annual economic performance.'}

if __name__=='__main__':
    result=run_checks()
    if len(sys.argv)>1:
        path=Path(sys.argv[1]);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
