"""P3 A5唯一入口：预检、连续Pilot、12政策正式回放、独立验证、单次导出。"""
from __future__ import annotations
import argparse,sys,traceback
from pathlib import Path
import numpy as np
import pandas as pd
from p3_io import (Journal,Paused,read_json,save_json,save_day,read_day,file_hash,digest,append_json)
from p3_data import Data,stamp,freeze_sources
from p3_forecast import build_forecasts
from p3_dispatch import solve_plan,feedback,rollout,choose
from p3_preflight import preflight

def production_freeze(base,sources):
    files=[{'path':str(p.relative_to(base)),'sha256':file_hash(p)} for p in sorted((base/'scripts').glob('*.py'))]
    files +=[{'path':str(p.relative_to(base)),'sha256':file_hash(p)} for p in sorted((base/'scripts').glob('*.mjs'))]
    record={'source_signature':sources['signature'],'files':files,'signature':digest(files)}
    target=base/'logs/production_manifest.json'
    if target.exists() and read_json(target)!=record: raise RuntimeError('生产签名冲突，不能覆盖旧代码产物')
    save_json(target,record);return record['signature']

def event(context,fixed_price,policy,day,hour,s,g0,old,journal):
    pid=policy['policy_id'];cutoff=day*144+hour*6;m=144-hour*6
    p=fixed_price[(np.arange(144)+hour*6)%144]
    terminal=0. if policy['terminal']=='ZERO' else .9*float(fixed_price.min())
    open_=hour==0 or hour in policy['opportunity_hours']
    ev={'issue_datetime':stamp(cutoff),'issue_hour':hour,'opportunity_open':open_,
        'soc_actual_kwh':s,'forecast_branch':policy['forecast_branch'],
        'information_signature':context['information_signature'],'scenario_source_issues':context['source_issues'],
        'scenario_source_versions':context['source_versions'],'forecast_version':context['forecast_version'],
        'alpha':0.,'accepted':False,'epsilon':0.,'keep_score':None,'selected_score':None,'candidates':[],
        'solution_ids':[],'old_a':old if old is not None else [],'g0':g0 if g0 is not None else [],
        'current_slots':m,'risk':policy['risk'],'terminal_value':terminal}
    if not open_: return ev,[],old
    kw={'net_scenarios':context['load_kwh']-context['pv_kwh'],'price':p,'s0':s,
        'current_slots':m,'original_g0':g0,'risk':policy['risk'],'terminal_value':terminal}
    solutions=[]
    for mode in (['INITIAL'] if hour==0 else ['KEEP','ADJUST']):
        label=f"formal/{pid}/{stamp(cutoff)[:10]}/{hour:02d}/{mode}"
        inputs={**kw,'keep_current':old if mode=='KEEP' else None}
        result=solve_plan(**inputs,invoke=lambda *a,**k:journal.invoke('formal',label,*a,**k))
        solutions.append({'label':label,'call_id':result['call_id'],'input':inputs,'output':result})
    ev['solution_ids']=[x['call_id'] for x in solutions]
    if hour==0:
        q=solutions[0]['output']['commitment']
        score=rollout(q,context['load_kwh'],context['pv_kwh'],p,s,144,None,policy['risk'],terminal)
        ev['candidates']=[{'alpha':1.,'eligible':True,'q':q,'max_change_kwh':0.,**score}]
        ev.update(alpha=1.,selected_score=score['score'])
        return ev,solutions,q
    k,a=[x['output']['commitment'] for x in solutions]
    selected,records,eps=choose(k,a,context['load_kwh'],context['pv_kwh'],p,s,m,g0,
                                policy['alpha_grid'],policy['risk'],terminal)
    ev.update(alpha=selected['alpha'],accepted=selected['alpha']>0,epsilon=eps,keep_score=records[0]['score'],
              selected_score=selected['score'],candidates=records)
    return ev,solutions,selected['q'][:m].copy() if ev['accepted'] else old.copy()

def run_day(data,forecasts,policy,day,s,journal,signature):
    date=stamp(day*144)[:10];g0=None;a=None;versions=[];actual=[];events=[];solutions=[]
    begin=s;effective=[stamp(day*144)]*144
    for j in range(144):
        if j%36==0:
            h=j//6;old=None if j==0 else a[j:].copy()
            context=forecasts.context(day,h,policy['forecast_branch'])
            ev,sol,new=event(context,data.price,policy,day,h,s,None if j==0 else g0[j:].copy(),old,journal)
            events.append(ev);solutions.extend(sol)
            if j==0: g0=new.copy();a=new.copy()
            elif ev['accepted']: a[j:]=new;effective[j:]=[stamp(day*144+j)]*(144-j)
            if ev['opportunity_open']:
                for t in range(j,144):
                    versions.append({'issue_datetime':ev['issue_datetime'],'slot_id':t+1,
                       'old_a_kwh':0. if j==0 else old[t-j],'new_a_kwh':a[t],
                       'alpha':ev['alpha'],'accepted':j==0 or ev['accepted']})
        # 先冻结本槽普通承诺，再取当前槽actual。下一槽不可传给feedback。
        load,pv=data.current_actual(day,j)
        step=feedback(s,float(a[j]),float(load/6),float(pv/6))
        residual_adjust=0.
        for bound in (1200.,10800.):
            if abs(step['soc_end_kwh']-bound)<=1e-9:
                residual_adjust=bound-step['soc_end_kwh'];step['soc_end_kwh']=bound
        price=data.price[j]
        retained=price*min(g0[j],a[j]);inc=1.5*price*max(a[j]-g0[j],0.);cancel=.5*price*max(g0[j]-a[j],0.)
        emergency=5*price*step['emergency_kwh']
        row={'date':date,'slot_id':j+1,'physical_interval_start':stamp(day*144+j),
             'physical_interval_end':stamp(day*144+j+1),'load_kw':load,'pv_actual_kw':pv,
             'price_yuan_per_kwh':price,'g0_kwh':g0[j],'a_kwh':a[j],'effective_issue':effective[j],
             'soc_start_kwh':s,**step,'soc_roundoff_adjustment_kwh':residual_adjust,
             'retained_cost_yuan':retained,'increase_cost_yuan':inc,'cancellation_cost_yuan':cancel,
             'emergency_cost_yuan':emergency,'total_cost_yuan':retained+inc+cancel+emergency}
        actual.append(row);s=step['soc_end_kwh']
    return {'run_id':journal.info['run_id'],'signature':signature,'policy_id':policy['policy_id'],'date':date,
            'soc_start':begin,'soc_end':s,'actual':actual,'events':events,'versions':versions,'solutions':solutions}

def progress(base,spec,journal,status):
    counts={p['policy_id']:len(list((base/'logs/checkpoints'/p['policy_id']).glob('*.json.gz'))) for p in spec['policies']}
    journal.info['status']=status;journal.sync()
    record={'gate':status,'complete_days':counts,'total_complete_days':sum(counts.values()),'counters':journal.counts(),
            'active_seconds':journal.info['active_seconds'],'run_id':journal.info['run_id']}
    save_json(base/'logs/progress.json',record);return record

def run(root,spec_path,stage,resume):
    base=root/'A_route/problem3/02_batch_run';spec=read_json(spec_path)
    if not (root/'A_route').is_dir() or spec_path.resolve()!= (base/'contracts/P3_BATCH_SPEC.json').resolve(): raise RuntimeError('根路径或规格位置错误')
    for folder in ('logs','reports','results','tables'): (base/folder).mkdir(parents=True,exist_ok=True)
    journal=Journal(base,spec)
    try:
        data=Data(root,spec);sources=freeze_sources(data)
        print('身份和预热检查通过；开始A5新增Preflight',flush=True)
        preflight(root,base,journal)
        signature=production_freeze(base,sources)
        if stage=='preflight': progress(base,spec,journal,'PASS_P3_BATCH_PREFLIGHT');return
        forecasts=build_forecasts(data,signature,journal)
        from p3_independent import check_day,check_forecasts
        forecast_checks,independent_provider=check_forecasts(root,base)
        save_json(base/'logs/forecast_preflight_checks.json',forecast_checks)
        if any(r['status']=='FAIL' for r in forecast_checks): raise RuntimeError('预测发布链独立预检失败，不能开始Pilot')
        initial_soc={p['policy_id']:data.initial_soc for p in spec['policies']}
        completed_hashes=read_json(base/'logs/checkpoint_manifest.json') if (base/'logs/checkpoint_manifest.json').exists() else {}
        for policy in spec['policies']:
            prev=data.initial_soc;seen_missing=False
            for day in range(31,365):
                path=base/'logs/checkpoints'/policy['policy_id']/(stamp(day*144)[:10]+'.json.gz')
                if not path.exists(): seen_missing=True;continue
                if seen_missing: raise RuntimeError('已提交政策日出现中间缺口')
                rel=str(path.relative_to(base))
                if rel in completed_hashes and file_hash(path)!=completed_hashes[rel]: raise RuntimeError('已提交日哈希改变')
                payload=read_day(path)
                if payload['signature']!=signature or abs(payload['soc_start']-prev)>1e-8: raise RuntimeError('已提交日签名/衔接冲突')
                prev=payload['soc_end'];completed_hashes[rel]=file_hash(path)
            initial_soc[policy['policy_id']]=prev
        # 先12政策各连续三日；然后从各自已提交末态补齐其余日期。
        for phase,days in [('PILOT',range(31,34)),('BATCH',range(34,365))]:
            if phase=='BATCH' and stage=='pilot': break
            for day in days:
                for policy in spec['policies']:
                    pid=policy['policy_id'];date=stamp(day*144)[:10]
                    path=base/'logs/checkpoints'/pid/(date+'.json.gz')
                    if path.exists(): continue
                    journal.check_budget()
                    payload=run_day(data,forecasts,policy,day,initial_soc[pid],journal,signature)
                    checks=check_day(payload,policy,spec,independent_provider)
                    failed=[r for r in checks if r['status']=='FAIL']
                    if failed:
                        save_day(base/'logs/failed_day'/pid/(date+'.json.gz'),payload)
                        save_json(base/'logs/failed_day_checks.json',failed)
                        raise RuntimeError('独立逐日检查失败: '+str(failed[:3]))
                    retries=save_day(path,payload)
                    if retries: append_json(base/'logs/failure_or_recovery.jsonl',{'type':'checkpoint暂态权限重试','policy_id':pid,'date':date,'retries':retries})
                    initial_soc[pid]=payload['soc_end'];completed_hashes[str(path.relative_to(base))]=file_hash(path)
                    save_json(base/'logs/checkpoint_manifest.json',completed_hashes)
                    progress(base,spec,journal,phase+'_RUNNING')
                print(f'{phase} 已提交 {date}：12政策；LP实际 {journal.counts()["formal"]}；solver {journal.counts()["solver_seconds"]:.1f}秒',flush=True)
            if phase=='PILOT':
                save_json(base/'logs/pilot_gate.json',{'gate':'PASS_P3_BATCH_PILOT','days_per_policy':3,'reused_as_formal':True,
                          'criteria_zh':'独立逐日物理、费用、状态、候选与版本正确性；不以费用排名决定继续'})
                print('Pilot通过，直接继续正式Batch；不重算前三日',flush=True)
        if stage=='pilot': progress(base,spec,journal,'PASS_P3_BATCH_PILOT');return
        from p3_reporting import aggregate
        aggregate(root,base,spec,forecasts)
        from validate_p3_batch import validate_all
        validation=validate_all(root,base,spec,journal,pre_export=True)
        if validation['blocking']: raise RuntimeError('独立pre-export验证存在blocking')
        from p3_causality import validate_causality
        causal=validate_causality(root,base,spec,journal,data,forecasts)
        if causal['FAIL']: raise RuntimeError('双层因果性验证失败')
        from p3_export import export_and_validate
        exported=export_and_validate(root,base,spec)
        from p3_reporting import finalize,update_output_manifest
        final=finalize(root,base,spec,journal,validation,causal,exported)
        progress(base,spec,journal,final['gate']);update_output_manifest(base,spec);print(final,flush=True)
    except (Paused,KeyboardInterrupt) as ex:
        record=progress(base,spec,journal,'PAUSED_P3_BATCH')
        record['reason']=str(ex);save_json(base/'reports/p3_batch_decision.json',record)
        from p3_io import atomic_write_bytes
        atomic_write_bytes(base/'reports/P3_GATE.md',('# P3 A-5 Gate\n\nPAUSED_P3_BATCH\n\n'+str(ex)+'\n\n已提交政策日：'+str(record['total_complete_days'])+'。尚无全年结论，尚未进入Candidate。\n').encode('utf-8'))
        print(record,flush=True);raise
    except Exception as ex:
        record=progress(base,spec,journal,'BLOCKED_P3_BATCH');record['reason']=str(ex)
        save_json(base/'reports/p3_batch_decision.json',record)
        append_json(base/'logs/failure_or_recovery.jsonl',{'type':'运行阻塞','error':str(ex),'traceback':traceback.format_exc()})
        from p3_io import atomic_write_bytes
        atomic_write_bytes(base/'reports/P3_GATE.md',('# P3 A-5 Gate\n\nBLOCKED_P3_BATCH\n\n'+str(ex)+'\n').encode('utf-8'))
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--project-root',required=True);parser.add_argument('--spec',required=True)
    parser.add_argument('--stage',choices=['all','preflight','pilot'],default='all');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();run(Path(args.project_root).resolve(),Path(args.spec).resolve(),args.stage,args.resume)
