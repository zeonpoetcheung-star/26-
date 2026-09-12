"""只从已提交轨迹聚合，不训练、不优化、不改变任何历史决策。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from p3_io import (read_day,read_json,save_json,write_csv,atomic_write_bytes,file_hash,serial)

SPECIFIED=['2025-03-20','2025-06-21','2025-09-23','2025-12-21']
COSTS=['retained_cost_yuan','increase_cost_yuan','cancellation_cost_yuan','emergency_cost_yuan','total_cost_yuan']
QUANTITIES=['g0_kwh','a_kwh','grid_used_kwh','grid_unused_kwh','pv_curtailment_kwh','charge_bus_kwh','discharge_bus_kwh','emergency_kwh']

def flat(record):
    return {k:json.dumps(v,ensure_ascii=False,default=serial,separators=(',',':')) if isinstance(v,(list,dict,np.ndarray)) else v for k,v in record.items()}

def emergency_events(actual,pid):
    records=[]
    for date,day in actual.groupby('date',sort=True):
        ids=np.flatnonzero(day.emergency_kwh.to_numpy()>1e-8)
        for group in np.split(ids,np.where(np.diff(ids)>1)[0]+1):
            if not len(group): continue
            part=day.iloc[group]
            records.append({'policy_id':pid,'date':date,'start_slot':int(part.slot_id.iloc[0]),'end_slot':int(part.slot_id.iloc[-1]),
                'physical_interval_start':part.physical_interval_start.iloc[0],'physical_interval_end':part.physical_interval_end.iloc[-1],
                'slot_count':len(part),'emergency_kwh':float(part.emergency_kwh.sum()),'emergency_cost_yuan':float(part.emergency_cost_yuan.sum()),'threshold_kwh':1e-8})
    return records

def aggregate(root,base,spec,forecasts):
    daily=[];allevents=[];policies=[];monthly=[];partials=[];gaps=[];storage=[];specified=[];intervals=[]
    for policy in spec['policies']:
        pid=policy['policy_id'];paths=sorted((base/'logs/checkpoints'/pid).glob('*.json.gz'))
        if len(paths)!=334: raise RuntimeError('不完整政策不能聚合全年: '+pid)
        rows=[];versions=[];decisions=[];scores=[]
        for path in paths:
            day=read_day(path);a=pd.DataFrame(day['actual']);rows.extend(day['actual'])
            events=day['events'];allowed=[e for e in events if e['issue_hour']>0 and e['opportunity_open']]
            d={'policy_id':pid,'date':day['date'],**{c:float(a[c].sum()) for c in COSTS+QUANTITIES},
               'initial_quote_yuan':float(np.dot(a.g0_kwh,a.price_yuan_per_kwh)),'soc_start_kwh':day['soc_start'],'soc_end_kwh':day['soc_end'],
               'soc_min_kwh':min(a.soc_start_kwh.min(),a.soc_end_kwh.min()),'soc_max_kwh':max(a.soc_start_kwh.max(),a.soc_end_kwh.max()),
               'allowed_adjustments':len(allowed),'actual_adjustments':sum(e['accepted'] for e in allowed),
               'rejected_adjustments':sum(not e['accepted'] for e in allowed),
               'emergency_positive_slots':int((a.emergency_kwh>1e-8).sum()),
               'emergency_subthreshold_kwh':float(a.loc[(a.emergency_kwh>0)&(a.emergency_kwh<=1e-8),'emergency_kwh'].sum()),
               'unused_normal_price_proxy_yuan':float(np.dot(a.grid_unused_kwh,a.price_yuan_per_kwh)),
               'net_contract_change_kwh':float((a.a_kwh-a.g0_kwh).sum()),
               'revision_absolute_kwh':sum(abs(v['new_a_kwh']-v['old_a_kwh']) for v in day['versions'] if v['issue_datetime'][11:13]!='00')}
            de=emergency_events(a,pid);d['emergency_events']=len(de);allevents.extend(de);daily.append(d)
            versions.extend({'policy_id':pid,'date':day['date'],**v} for v in day['versions'])
            for e in events:
                decisions.append(flat({'policy_id':pid,'date':day['date'],**{k:v for k,v in e.items() if k not in ('candidates','g0','old_a')}}))
                for c in e['candidates']:
                    scores.append(flat({'policy_id':pid,'date':day['date'],'issue_datetime':e['issue_datetime'],'issue_hour':e['issue_hour'],**c}))
                for sid in e['solution_ids']:
                    sol=next(s for s in day['solutions'] if s['call_id']==sid)
                    endpoint=0. if sol['input']['keep_current'] is not None else 1.
                    c=next((c for c in e['candidates'] if c['alpha']==endpoint and c['eligible']),None)
                    if c:
                        gaps.append({'policy_id':pid,'issue_datetime':e['issue_datetime'],'candidate_alpha':endpoint,'call_id':sid,
                            'lp_surrogate_yuan':sol['output']['objective_surrogate'],'rollout_score_yuan':c['score'],
                            'rollout_minus_proxy_yuan':c['score']-sol['output']['objective_surrogate'],
                            'lp_proxy_emergency_kwh_mean':float(np.sum(sol['output']['shortfall_proxy'],axis=1).mean()),
                            'rollout_emergency_kwh_mean':float(np.mean(c['emergency_kwh'])),
                            'interpretation':'同事件重叠24h条件诊断，不是年度费用'})
                if pid.endswith('PARTIAL_ADJUST_MEAN_ROLLOUT_061218') and e['issue_hour']:
                    valid=[c for c in e['candidates'] if c['eligible']]
                    endpoint=min(c['score'] for c in valid if c['alpha'] in (0.,1.))
                    gridmin=min(c['score'] for c in valid)
                    partials.append({'policy_id':pid,'date':day['date'],'month':day['date'][:7],
                        'issue_hour':e['issue_hour'],'selected_alpha':e['alpha'],'accepted':e['accepted'],
                        'endpoint_best_score':endpoint,'grid_best_score':gridmin,'conditional_improvement_yuan':endpoint-gridmin,
                        'selected_score':e['selected_score'],'epsilon':e['epsilon'],
                        'continuation_only_filtered':sum(not c['eligible'] for c in e['candidates']),
                        'contract_change_l1_kwh':sum(abs(v['new_a_kwh']-v['old_a_kwh']) for v in day['versions'] if v['issue_datetime']==e['issue_datetime'])})
            if pid==spec['primary_policy']:
                for b in range(6):
                    segment=a.iloc[b*24:(b+1)*24]
                    st={'policy_id':pid,'date':day['date'],'block':b+1,'time_interval':f'{4*b}:00-{4*(b+1)}:00',
                        'charge_bus_kwh':float(segment.charge_bus_kwh.sum()),'discharge_bus_kwh':float(segment.discharge_bus_kwh.sum()),
                        'soc_start_kwh':float(segment.soc_start_kwh.iloc[0]),'soc_end_kwh':float(segment.soc_end_kwh.iloc[-1])}
                    storage.append(st)
                    if day['date'] in SPECIFIED: intervals.append({**st,'g0_kwh':float(segment.g0_kwh.sum()),'a_kwh':float(segment.a_kwh.sum())})
                if day['date'] in SPECIFIED: specified.append(d)
        actual=pd.DataFrame(rows);actual.insert(0,'policy_id',pid);out=base/'results/policies'/pid
        initial=actual[['policy_id','date','slot_id','g0_kwh','price_yuan_per_kwh']].copy();initial['initial_quote_yuan']=initial.g0_kwh*initial.price_yuan_per_kwh
        final=actual[['policy_id','date','slot_id','g0_kwh','a_kwh','effective_issue']].copy();final['net_change_kwh']=final.a_kwh-final.g0_kwh
        exports={'p3_initial_plan.csv':initial,'p3_final_commitment.csv':final,'p3_actual_schedule.csv':actual,
            'p3_settlement_ledger.csv':actual[['policy_id','date','slot_id','g0_kwh','a_kwh','price_yuan_per_kwh','emergency_kwh']+COSTS],
            'p3_commitment_versions.csv':versions,'p3_decision_ledger.csv':decisions,'p3_candidate_scores.csv':scores}
        for name,frame in exports.items():
            write_csv(out/name,frame)
            if pid==spec['primary_policy'] and name not in ('p3_commitment_versions.csv','p3_candidate_scores.csv'):
                atomic_write_bytes(base/'results'/name,(out/name).read_bytes())
        ds=pd.DataFrame([r for r in daily if r['policy_id']==pid])
        numeric=COSTS+QUANTITIES+['initial_quote_yuan','allowed_adjustments','actual_adjustments','rejected_adjustments','emergency_positive_slots','emergency_subthreshold_kwh','emergency_events','unused_normal_price_proxy_yuan','net_contract_change_kwh','revision_absolute_kwh']
        summary={'policy_id':pid,'role':policy['role'],'opportunity_hours':','.join(map(str,policy['opportunity_hours'])) or '无',
                 'days':334,'is_primary':pid==spec['primary_policy'],**{c:float(ds[c].sum()) for c in numeric},
                 'soc_start_kwh':float(ds.soc_start_kwh.iloc[0]),'soc_end_kwh':float(ds.soc_end_kwh.iloc[-1]),
                 'soc_min_kwh':float(ds.soc_min_kwh.min()),'soc_max_kwh':float(ds.soc_max_kwh.max())}
        policies.append(summary)
        ds['month']=ds.date.str[:7]
        for month,frame in ds.groupby('month'):
            monthly.append({'policy_id':pid,'month':month,**{c:float(frame[c].sum()) for c in numeric},
                'soc_start_kwh':float(frame.soc_start_kwh.iloc[0]),'soc_end_kwh':float(frame.soc_end_kwh.iloc[-1])})
    comparison=pd.DataFrame(policies);main=comparison.loc[comparison.policy_id==spec['primary_policy']].iloc[0]
    comparison['raw_saving_vs_main_yuan']=main.total_cost_yuan-comparison.total_cost_yuan
    comparison['endpoint_pressure_yuan']=5*1.3952/.9*np.maximum(main.soc_end_kwh-comparison.soc_end_kwh,0)
    comparison['saving_after_endpoint_pressure_yuan']=comparison.raw_saving_vs_main_yuan-comparison.endpoint_pressure_yuan
    for name,rows in [('p3_daily_summary.csv',daily),('p3_emergency_events.csv',allevents)]: write_csv(base/'results'/name,rows)
    tablelist={'p3_policy_comparison.csv':comparison,'p3_opportunity_comparison.csv':comparison.iloc[:8],
      'p3_component_ablation.csv':comparison.iloc[8:],'p3_partial_adjustment_summary.csv':partials,
      'p3_monthly_cost_summary.csv':monthly,'p3_proxy_rollout_gap.csv':gaps,
      'p3_endpoint_fairness.csv':comparison[['policy_id','soc_start_kwh','soc_end_kwh','total_cost_yuan','raw_saving_vs_main_yuan','endpoint_pressure_yuan','saving_after_endpoint_pressure_yuan']],
      'p3_specified_purchase_intervals.csv':intervals,'p3_specified_daily_summary.csv':specified,'p3_storage_4h_summary.csv':storage}
    for name,rows in tablelist.items(): write_csv(base/'tables'/name,rows)
    partialframe=pd.DataFrame(partials)
    frequencies=[]
    for month in ['全年']+sorted(partialframe.month.unique().tolist()):
        subset=partialframe if month=='全年' else partialframe[partialframe.month==month]
        for alpha in (0,.25,.5,.75,1): frequencies.append({'month':month,'alpha':alpha,'count':int((subset.selected_alpha==alpha).sum())})
    write_csv(base/'tables/p3_partial_alpha_frequency.csv',frequencies)
    forecast_metrics(root,base)

def forecast_metrics(root,base):
    ledger=pd.read_csv(base/'results/p3_forecast_ledger.csv');actual=pd.read_csv(root/'A_route/common/01_preprocessing/processed/year_actual_10min.csv')
    actual['target_interval_start']=(pd.to_datetime(actual.date)+pd.to_timedelta((actual.slot_id-1)*10,unit='m')).dt.strftime('%Y-%m-%dT%H:%M:%S')
    merged=ledger.merge(actual[['target_interval_start','load_kw','pv_actual_kw']],on='target_interval_start',how='left',validate='many_to_one')
    merged['lead_hour']=(merged.lead_slot-1)//6+1
    h=pd.to_datetime(merged.target_interval_start).dt.hour;merged['daylight']=np.where((h>=6)&(h<18),'白昼','夜间')
    rows=[]
    for keys,group in merged.groupby(['forecast_branch','issue_hour','horizon_class','daylight','lead_hour'],sort=True):
        valid=group.dropna(subset=['load_kw','pv_actual_kw'])
        for variable,pred,truth in [('LOAD','load_forecast_kw','load_kw'),('PV','pv_forecast_kw','pv_actual_kw')]:
            error=valid[pred]-valid[truth]
            rows.append(dict(zip(['forecast_branch','issue_hour','horizon_class','daylight','lead_hour'],keys))|
                {'variable':variable,'sample_count':len(valid),'unavailable_count':len(group)-len(valid),
                 'mae_kw':float(abs(error).mean()) if len(valid) else None,'rmse_kw':float(np.sqrt(np.mean(error**2))) if len(valid) else None,
                 'bias_kw':float(error.mean()) if len(valid) else None,'scope':'发行—目标重叠记录，非独立样本'})
    write_csv(base/'tables/p3_forecast_metrics.csv',rows)

def markdown_table(frame,columns):
    data=frame[columns].copy()
    for c in data.columns:
        if pd.api.types.is_float_dtype(data[c]): data[c]=data[c].map(lambda x:f'{x:.6f}')
    return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in data.to_numpy())

def finalize(root,base,spec,journal,validation,causal,exported):
    from p3_data import Data
    Data(root,spec)
    if file_hash(root/'A_route/CURRENT_STATE.md')!=read_json(base/'logs/input_manifest.json')['stage_authorization_sha256']:
        raise RuntimeError('本轮CURRENT_STATE被修改')
    comparison=pd.read_csv(base/'tables/p3_policy_comparison.csv');main=comparison[comparison.policy_id==spec['primary_policy']].iloc[0]
    part=comparison[comparison.policy_id=='P3_PARTIAL_ADJUST_MEAN_ROLLOUT_061218'].iloc[0]
    improved=part.total_cost_yuan<main.total_cost_yuan-.01
    checks=[r for r in validation['checks'] if r['status']!='NOT_CHECKED']+causal['checks']+exported['checks']
    for pending in validation.get('coverage_pending',[]):
        name=pending['check_id']
        resolved=((name=='INDEPENDENT_LP_OPTIMALITY' and causal['validation_lp_calls']>0 and causal['FAIL']==0)
                  or (name=='FRESH_PIPELINE_CAUSALITY' and causal['FAIL']==0)
                  or (name=='WORKBOOK_READBACK' and exported['FAIL']==0))
        checks.append({'check_id':name+'_FINAL_COVERAGE','status':'PASS' if resolved else 'FAIL',
                       'detail':'由causality_validation.json或workbook_validation.json本轮实际证据闭合；保留原分层记录','max_residual':0.})
    counts=journal.counts()
    checks.append({'check_id':'ACTUAL_CALL_BUDGETS','status':'PASS' if counts['formal_unique']==20040 and counts['formal_recovery']<=256 and counts['total_actual']<=20416 and counts['synthetic']<=48 and counts['validation']<=72 and counts['unclosed_starts']==0 else 'FAIL',
                   'detail':json.dumps(counts),'max_residual':0.})
    fail=sum(r['status']=='FAIL' for r in checks)
    gate='BLOCKED_P3_BATCH' if fail else 'PASS_P3_BATCH_WITH_OPEN_ISSUES'
    decision={'gate':gate,'primary_policy':spec['primary_policy'],'all_12_policies_complete':True,
              'extension_flag':'EXTENSION_IMPROVEMENT_OBSERVED_PENDING_HUMAN_REVIEW' if improved else 'NO_EXTENSION_IMPROVEMENT_OBSERVED',
              'automatic_primary_swap':False,'next_stage_authorized':False,'candidate_review_ready':not fail,
              'PASS':sum(r['status']=='PASS' for r in checks),'FAIL':fail,'blocking':fail,
              'result3_sha256':exported['sha256'],'counts':journal.counts()}
    write_csv(base/'tables/p3_validation_checks.csv',checks);save_json(base/'reports/p3_batch_decision.json',decision)
    limitations='所有结论仅为开发知情的因果历史回放，非盲测。H-END、PWL、最终对0时结算与槽内反馈为已披露工作假设；共享名义储能、损失代理、假想次日合同及线性终端价值均是规划近似，有限历史情景无分布外保证。普通未取用量不退款；p×U仅为正常价代理。期末压力是诊断，不改写真实账单。'
    econ=markdown_table(comparison,['policy_id','total_cost_yuan','emergency_kwh','grid_unused_kwh','pv_curtailment_kwh','soc_end_kwh'])
    freq=pd.read_csv(base/'tables/p3_partial_alpha_frequency.csv');freq=freq[freq.month=='全年']
    reports={
      'P3_RUN_REPORT.md':f'# P3 A-5 正式运行报告\n\nGate：{gate}\n\n12政策均完成334天，共4008政策日、577152实际槽。连续Pilot前三日直接复用，政策状态各自连续。主候选固定为 `{spec["primary_policy"]}`。\n\n{econ}\n\n调用与累计运行信息见logs/run_info.json，实际调用账见solver_invocations.jsonl。生产源码、输入与结果分别签名；计数不含A-4历史调用。\n\n{json.dumps(journal.counts(),ensure_ascii=False)}\n\n原始输入、Common、P1/P2、P3前序阶段与CURRENT_STATE未修改。独立验证使用 data-analytics:validate-data 的独立重算与来源审计；工作簿按 Spreadsheets 技能保持模板并读回。\n\n{limitations}\n',
      'P3_EXTENSION_REPORT.md':f'# 部分调整扩展结果\n\n{decision["extension_flag"]}\n\nMAIN实际总费：{main.total_cost_yuan:.6f}元；PARTIAL实际总费：{part.total_cost_yuan:.6f}元。相对MAIN原始节省：{part.raw_saving_vs_main_yuan:.6f}元；期末库存压力后节省：{part.saving_after_endpoint_pressure_yuan:.6f}元。负数表示更贵。未自动替换MAIN。\n\n'+markdown_table(freq,['alpha','count'])+'\n\n条件得分与真实收益分开；逐月变化和同事件端点改善见对应CSV，不据此按月或按日拼接赢家。\n\n'+limitations+'\n',
      'P3_FORECAST_REPORT.md':'# 因果发布预测报告\n\n两分支各1432次发行、每次144个目标，保留跨年目标且不填2026实际。PREFIX日内估计最多1074次，成功次数及fallback见p3_load_fit_log.csv。NO_PREFIX使用自己的原始W1发布残差。\n\n逐发行、lead、当日/延续、白昼分层指标见p3_forecast_metrics.csv；误差只在共同有标签样本上计算，不用全年统计回填在线参数。独立validator重算全部发行和成熟链。\n\n'+limitations+'\n',
      'P3_VALIDATION_REPORT.md':f'# P3 独立验证\n\nPASS {decision["PASS"]} / FAIL {fail} / blocking {fail}\n\n覆盖全部政策日物理与账单、预测训练与发布版本、成熟配对情景、候选评分、版本生效、源指纹、CSV与模板逐格输出。独立LP及3日×4事件重新构造未来扰动详见causality_validation.json；未用缓存遮蔽受测管线。\n\n独立目标和masked重求LP次数：{causal["validation_lp_calls"]}。生产拟合与验证公式重算分列，验证重算没有发布新模型或回填历史。\n\n{limitations}\n',
      'P3_SETTLEMENT_AND_TIME_NOTE.md':'# 结算与时间口径\n\n普通真实费为保留1p、调增1.5p、取消0.5p；紧急购电5p。每交付槽只结算一次，a相对原始g0，不相对中间版本；p按交付槽取值。\n\n计划页保存g0及初始报价；调整页保存最终a及含紧急费的最终日账单，不相加两个EQ。储能页仅真实C/D和真实边界SOC；紧急页只合并同日相邻E>1e-8的槽，阈值以下残余另计。\n\n原模板B:EO表头原样保留，物理槽按H-END映射；模板储能和紧急页省略号展开为完整日期/事件列表，不新增或改名四表。\n\n'+limitations+'\n',
      'P3_GATE.md':f'# P3 A-5 Gate\n\n{gate}\n\n12政策334/334天；独立PASS {decision["PASS"]} / FAIL {fail} / blocking {fail}。主候选不变。\n\nresult3 SHA256：{exported["sha256"]}\n\n{decision["extension_flag"]}\n\n{limitations}\n\n停止在A-5；未进入Candidate、Review或Final。\n'}
    for name,text in reports.items(): atomic_write_bytes(base/'reports'/name,text.encode('utf-8'))
    return decision

def update_output_manifest(base,spec):
    manifest=[]
    for folder in ('results','tables','reports','logs'):
        for path in sorted((base/folder).rglob('*')):
            if not path.is_file() or path.name=='output_manifest.json' or path.suffix=='.tmp': continue
            if 'checkpoints' in path.parts: continue
            count=None
            if path.suffix=='.csv':
                import csv
                with path.open('r',encoding='utf-8-sig',newline='') as f: count=sum(1 for _ in csv.reader(f))-1
            scope=next((p['policy_id'] for p in spec['policies'] if p['policy_id'] in path.parts),'共享/全部政策')
            if path.parent==base/'results' and path.name in ('p3_initial_plan.csv','p3_final_commitment.csv','p3_actual_schedule.csv','p3_settlement_ledger.csv','p3_decision_ledger.csv','result3.xlsx'): scope=spec['primary_policy']
            manifest.append({'relative_path':str(path.relative_to(base)),'row_count':count,'policy_scope':scope,
                             'source_signature':read_json(base/'logs/production_manifest.json')['signature'],
                             'sha256':file_hash(path),'size_bytes':path.stat().st_size})
    save_json(base/'logs/output_manifest.json',manifest)
