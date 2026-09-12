#!/usr/bin/env python3
"""P3 A-6: read-only A-5 checks and metadata freeze; Python standard library only.

No production-module import, solver, model fitting, workbook write or network I/O.
A successful local run is a Candidate identity/integrity gate, not final Review.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

MAIN = 'P3_MAIN_MEAN_ROLLOUT_061218'
PARTIAL = 'P3_PARTIAL_ADJUST_MEAN_ROLLOUT_061218'
PASS_GATE = 'PASS_P3_CANDIDATE_FREEZE_WITH_OPEN_ISSUES'
FAIL_GATE = 'BLOCKED_P3_CANDIDATE_FREEZE'
COSTS = ['retained_cost_yuan','increase_cost_yuan','cancellation_cost_yuan',
         'emergency_cost_yuan','total_cost_yuan']
ENERGIES = ['g0_kwh','a_kwh','grid_used_kwh','grid_unused_kwh','pv_curtailment_kwh',
            'charge_bus_kwh','discharge_bus_kwh','emergency_kwh']
STATE_OUTPUTS = {'CANDIDATE_FREEZE_MANIFEST.json','CANDIDATE_MANIFEST_SHA256.txt',
                 'STATE_UPDATE_RECORD.json','FREEZE_FAILURE.json'}

class FreezeError(RuntimeError):
    pass

class Checks:
    def __init__(self):
        self.rows: list[dict] = []
    def add(self, name: str, ok: bool, detail: str = ''):
        self.rows.append({'check_id':name,'status':'PASS' if ok else 'FAIL','detail':detail})
    @property
    def failures(self):
        return [r for r in self.rows if r['status']=='FAIL']
    def require_ok(self):
        if self.failures:
            raise FreezeError('; '.join(r['check_id']+': '+r['detail'] for r in self.failures[:12]))


def read_json(path: Path):
    with path.open(encoding='utf-8-sig') as f:
        return json.load(f)


def csv_rows(path: Path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        yield from csv.DictReader(f)


def number(row: dict, key: str) -> float:
    x = float(row[key])
    if not math.isfinite(x):
        raise FreezeError(f'Non-finite {key}: {row.get("policy_id", "")} {row.get("date", "")}')
    return x


def equal(x: float, y: float, tol: float = 1e-6) -> bool:
    return math.isfinite(x) and math.isfinite(y) and abs(x-y)<=tol


def safe_join(root: Path, rel: str) -> Path:
    rel = rel.replace('\\','/')
    path = root/rel
    if Path(rel).is_absolute() or '..' in Path(rel).parts or not path.resolve().is_relative_to(root.resolve()):
        raise FreezeError('Unsafe source path: '+rel)
    if path.is_symlink():
        raise FreezeError('Symlink not accepted as frozen source: '+str(path))
    return path


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(4*1024*1024): h.update(data)
    return h.hexdigest()


def file_record(path: Path, root: Path, role: str) -> dict:
    if not path.is_file() or path.is_symlink():
        raise FreezeError('Missing/non-regular source: '+str(path))
    return {'path':path.relative_to(root).as_posix(),'size_bytes':path.stat().st_size,
            'sha256':digest(path),'role':role}


def excluded(path: Path) -> bool:
    return '__pycache__' in path.parts or path.suffix.lower() in {'.pyc','.tmp','.temp','.part'}


def inventory_tree(folder: Path, root: Path, role: str) -> list[dict]:
    records=[]
    for path in sorted(folder.rglob('*')):
        if path.is_symlink(): raise FreezeError('Symlink in frozen tree: '+str(path))
        if path.is_file() and not excluded(path): records.append(file_record(path,root,role))
    return records


def atomic_text(path: Path, text: str):
    """Writes only Candidate outputs; never silently widens Windows permissions."""
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with tmp.open('w',encoding='utf-8',newline='') as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        for i in range(8):
            try:
                os.replace(tmp,path);return
            except OSError as ex:
                if getattr(ex,'winerror',None) not in {5,32,33} or i==7: raise
                time.sleep(min(0.1*(2**i),1.5))
    finally:
        if tmp.exists():tmp.unlink()


def write_json(path: Path, obj):
    atomic_text(path,json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def write_csv(path: Path, rows: list[dict], columns: list[str]):
    import io
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=columns)
    w.writeheader();w.writerows(rows);atomic_text(path,'\ufeff'+buf.getvalue())


def verify_uploaded_identity(batch: Path, reference: dict, check: Checks):
    for item in reference['files']:
        p=safe_join(batch,item['path'])
        ok=p.is_file() and p.stat().st_size==item['size_bytes'] and digest(p)==item['sha256']
        check.add('A5_UPLOAD_SHA:'+item['path'],ok,item['sha256'])
    check.require_ok()


def audit_batch(batch: Path, spec: dict, check: Checks):
    """Deterministic bookkeeping only. This is intentionally not a model replay."""
    source_spec=read_json(batch/'contracts/P3_BATCH_SPEC.json')
    decision=read_json(batch/'reports/p3_batch_decision.json')
    matrix=read_json(batch/'contracts/P3_POLICY_MATRIX.json')
    check.add('A5_GATE',decision.get('gate')=='PASS_P3_BATCH_WITH_OPEN_ISSUES'
              and decision.get('blocking')==0 and decision.get('FAIL')==0
              and decision.get('all_12_policies_complete') is True,str(decision.get('gate')))
    check.add('PRIMARY_FIXED',source_spec.get('primary_policy')==MAIN
              and source_spec.get('result3_policy')==MAIN and decision.get('primary_policy')==MAIN)
    check.add('NO_AUTO_SWAP',source_spec.get('automatic_primary_swap') is False
              and decision.get('automatic_primary_swap') is False)
    check.add('TWELVE_REGISTERED_POLICIES',len(matrix)==12
              and {p['policy_id'] for p in matrix}==set(spec['policy_ids']))
    check.add('WORKBOOK_SHA256',digest(batch/spec['workbook_relative_path'])==spec['workbook_sha256'])
    check.require_ok()

    comparison=list(csv_rows(batch/'tables/p3_policy_comparison.csv'))
    policies={r['policy_id']:r for r in comparison}
    check.add('POLICY_TABLE_KEYS',len(comparison)==12 and set(policies)==set(spec['policy_ids']))
    check.require_ok()
    main=policies[MAIN]
    check.add('CANDIDATE_NOT_POSTHOC_SWAP',main['role']=='PRIMARY' and main['is_primary'].lower()=='true')
    check.add('MAIN_LOWEST_REPORTED',all(number(r,'total_cost_yuan')>=number(main,'total_cost_yuan')-0.01 for r in comparison))
    for key in COSTS+ENERGIES+['soc_start_kwh','soc_end_kwh']:
        check.add('REPORTED_MAIN:'+key,equal(number(main,key),number(spec['expected_main'],key),
                    spec['annual_money_abs_tolerance'] if key.endswith('_yuan') else 1e-6))
    start=date.fromisoformat(spec['formal_start']);dates=[(start+timedelta(days=i)).isoformat() for i in range(spec['days'])]
    daily=list(csv_rows(batch/'results/p3_daily_summary.csv'))
    groups=defaultdict(list)
    for r in daily:groups[r['policy_id']].append(r)
    check.add('DAILY_ROWS',len(daily)==spec['expected_daily_rows'] and set(groups)==set(policies),str(len(daily)))
    for pid in spec['policy_ids']:
        rows=groups[pid]
        check.add('DAILY_COVERAGE:'+pid, [r['date'] for r in rows]==dates)
        sums={k:math.fsum(number(r,k) for r in rows) for k in COSTS+ENERGIES}
        err=max([abs(sums[k]-number(policies[pid],k)) for k in sums],default=0.)
        check.add('DAILY_TOTALS:'+pid,all(equal(sums[k],number(policies[pid],k),0.01 if k.endswith('_yuan') else 1e-6) for k in sums),f'max_difference={err}')
        continuous=all(equal(number(rows[i-1],'soc_end_kwh'),number(rows[i],'soc_start_kwh')) for i in range(1,len(rows)))
        check.add('DAILY_SOC:'+pid,continuous and rows and equal(number(rows[0],'soc_start_kwh'),number(main,'soc_start_kwh'))
                  and equal(number(rows[-1],'soc_end_kwh'),number(policies[pid],'soc_end_kwh')))
        check.add('POLICY_FILES:'+pid,all((batch/'results/policies'/pid/f).is_file() for f in
               ['p3_actual_schedule.csv','p3_initial_plan.csv','p3_final_commitment.csv','p3_settlement_ledger.csv','p3_decision_ledger.csv','p3_commitment_versions.csv','p3_candidate_scores.csv']))
    check.require_ok()

    aliases=['p3_actual_schedule.csv','p3_initial_plan.csv','p3_final_commitment.csv','p3_settlement_ledger.csv','p3_decision_ledger.csv']
    for name in aliases:
        check.add('MAIN_ALIAS:'+name,digest(batch/'results'/name)==digest(batch/'results/policies'/MAIN/name))
    check.require_ok()
    actual=list(csv_rows(batch/'results/p3_actual_schedule.csv'))
    key_list=[(r['date'],int(r['slot_id'])) for r in actual]
    expected_keys=[(d,j) for d in dates for j in range(1,145)]
    check.add('MAIN_48096_KEYS',key_list==expected_keys and all(r['policy_id']==MAIN for r in actual))
    check.require_ok()
    recomputed={k:[] for k in COSTS};worst_cost=0.;worst_balance=0.;worst_soc=0.
    physical_bad=0;effective_bad=0;events=0;positive_slots=0;prev_date=None;prev_positive=False;prev_soc=None
    for r in actual:
        g,a,p,E=[number(r,k) for k in ['g0_kwh','a_kwh','price_yuan_per_kwh','emergency_kwh']]
        calc=[p*min(g,a),1.5*p*max(a-g,0),.5*p*max(g-a,0),5*p*E]
        calc.append(math.fsum(calc))
        for k,x in zip(COSTS,calc):
            recomputed[k].append(x);worst_cost=max(worst_cost,abs(x-number(r,k)))
        c,dd,s0,s1,used,U,W=[number(r,k) for k in ['charge_bus_kwh','discharge_bus_kwh','soc_start_kwh','soc_end_kwh','grid_used_kwh','grid_unused_kwh','pv_curtailment_kwh']]
        balance=used+E+number(r,'pv_actual_kw')/6+dd-number(r,'load_kw')/6-c-W
        worst_balance=max(worst_balance,abs(balance),abs(a-used-U))
        worst_soc=max(worst_soc,abs(s1-s0-.9*c+dd/.9),0. if prev_soc is None else abs(s0-prev_soc))
        if (min(g,a,p,E,c,dd,used,U,W)<-1e-6 or min(s0,s1)<1200-1e-6 or max(s0,s1)>10800+1e-6 or
            max(c,dd)>5000/6+1e-6 or min(c,dd)>1e-6 or min(c,E)>1e-6):physical_bad+=1
        dt0=datetime.fromisoformat(r['physical_interval_start']);dt1=datetime.fromisoformat(r['physical_interval_end'])
        base=datetime.fromisoformat(r['date']);j=int(r['slot_id'])
        eff=datetime.fromisoformat(r['effective_issue'])
        if dt0!=base+timedelta(minutes=(j-1)*10) or dt1!=base+timedelta(minutes=j*10) or eff>dt0 or eff.date()!=base.date() or eff.hour not in {0,6,12,18} or eff.minute!=0: effective_bad+=1
        pos=E>spec['emergency_event_threshold_kwh'];positive_slots+=int(pos)
        if pos and (r['date']!=prev_date or not prev_positive):events+=1
        prev_date=r['date'];prev_positive=pos;prev_soc=s1
    check.add('MAIN_BILL_FORMULA',worst_cost<=1e-6,f'max={worst_cost}')
    check.add('MAIN_BALANCE_CONTINUITY_BOUNDS',worst_balance<=1e-6 and worst_soc<=1e-6 and physical_bad==0,
              f'balance={worst_balance}; soc={worst_soc}; violations={physical_bad}')
    check.add('MAIN_EFFECTIVE_TIMES',effective_bad==0,f'violations={effective_bad}')
    totals={k:math.fsum(v) for k,v in recomputed.items()}
    totals.update({k:math.fsum(number(r,k) for r in actual) for k in ENERGIES})
    for k,v in totals.items():check.add('MAIN_RECALC:'+k,equal(v,number(main,k),.01 if k.endswith('_yuan') else 1e-6),f'{v:.12f}')
    check.add('MAIN_EVENT_COUNTS',positive_slots==int(main['emergency_positive_slots']) and events==int(main['emergency_events']),f'slots={positive_slots}; events={events}')
    bykey=dict(zip(key_list,actual))
    for name,fields in [('p3_initial_plan.csv',['g0_kwh']),('p3_final_commitment.csv',['g0_kwh','a_kwh']),('p3_settlement_ledger.csv',COSTS+['g0_kwh','a_kwh','emergency_kwh'])]:
        rows=list(csv_rows(batch/'results'/name));ks=[(r['date'],int(r['slot_id'])) for r in rows]
        ok=ks==expected_keys
        if ok:ok=all(r['policy_id']==MAIN and all(equal(number(r,f),number(bykey[k],f)) for f in fields) for r,k in zip(rows,ks))
        check.add('MAIN_LEDGER:'+name,ok)
    vcounts=Counter(r['status'] for r in csv_rows(batch/'tables/p3_validation_checks.csv'))
    check.add('BATCH_CHECK_STATUS_COUNTS',vcounts==Counter(spec['expected_validation_counts']),str(dict(vcounts)))
    dm=list(csv_rows(batch/'results/p3_decision_ledger.csv'))
    dkeys={(r['date'],int(r['issue_hour'])) for r in dm}
    accepted=sum(r['accepted'].lower()=='true' for r in dm if int(r['issue_hour'])>0)
    check.add('MAIN_DECISION_COUNTS',len(dm)==334*4 and dkeys=={(d,h) for d in dates for h in (0,6,12,18)} and accepted==int(main['actual_adjustments']))
    check.require_ok()
    derived=[]
    for d in spec['specified_dates']:
        for j in spec['specified_slots']:
            r=bykey[(d,j)]
            derived.append({'policy_id':MAIN,'date':d,'slot_id':j,
                            'physical_interval_start':r['physical_interval_start'],'physical_interval_end':r['physical_interval_end'],
                            'g0_kwh':r['g0_kwh'],'a_kwh':r['a_kwh'],'emergency_kwh':r['emergency_kwh'],
                            'source_path':'../../02_batch_run/results/p3_actual_schedule.csv','source_key':f'{MAIN}|{d}|{j}'})
    check.add('SPECIFIED_24_CORRECT_KEYS',len(derived)==24 and len({(r['date'],r['slot_id']) for r in derived})==24)
    old=list(csv_rows(batch/'tables/p3_specified_purchase_intervals.csv'))
    old_intervals=sorted({r.get('time_interval','') for r in old})
    old_is_4h=set(old_intervals)=={'0:00-4:00','4:00-8:00','8:00-12:00','12:00-16:00','16:00-20:00','20:00-24:00'}
    check.add('OLD_AUXILIARY_TABLE_CLASSIFIED',old_is_4h,'Known 4h summary preserved; separate Candidate 10min extraction generated')
    return {'main':main,'policy_rows':comparison,'totals':totals,'specified':derived,'batch_decision':decision,
            'old_auxiliary_intervals':old_intervals,'positive_slots':positive_slots,'events':events}


def audit_local_evidence(root: Path, batch: Path, spec: dict, check: Checks) -> list[dict]:
    handoff=root/spec['candidate_path']/'P3_LOCAL_HANDOFF_CHECK.md'
    text=handoff.read_text(encoding='utf-8-sig') if handoff.is_file() else ''
    check.add('LOCAL_HANDOFF_READ_CHECK', all(x in text for x in
              ['SPECIFIED_24_CELLS_MATCH=PASS','FORMAT_RECOVERY_CHAIN=PASS']),
              'Codex must first read and document the 24 workbook cells per sheet and the actual repair chain.')
    batch_spec=read_json(batch/'contracts/P3_BATCH_SPEC.json')
    records=[]
    for item in batch_spec['protected_sources']:
        p=safe_join(root,item['relative_path'])
        ok=p.is_file() and digest(p)==item['sha256']
        check.add('UPSTREAM_SHA:'+item['relative_path'],ok)
        if ok:records.append(file_record(p,root,'upstream_protected'))
    for rel in spec['required_log_files']:
        p=safe_join(batch,rel);check.add('LOCAL_LOG:'+rel,p.is_file() and p.stat().st_size>0)
    recovery=safe_join(batch,spec['format_recovery_directory'])
    scripts=[p for p in recovery.rglob('*') if p.is_file() and p.suffix.lower() in {'.py','.js','.mjs','.ps1'}] if recovery.exists() else []
    check.add('ORIGINAL_FORMAT_FIX_SCRIPT_PRESENT',bool(scripts),'Read/freeze only; never run repair on correct workbook')
    failed=[p for p in recovery.rglob('*.xlsx') if digest(p)==spec['failed_workbook_sha256']] if recovery.exists() else []
    check.add('ORIGINAL_FAILED_WORKBOOK_PRESERVED',bool(failed),str(spec['failed_workbook_sha256']))
    check.require_ok()
    return records


def verify_manifest(root: Path, cand: Path):
    manifest=read_json(cand/'CANDIDATE_FREEZE_MANIFEST.json');bad=[]
    for item in manifest['files']:
        p=safe_join(root,item['path'])
        if not p.is_file() or p.stat().st_size!=item['size_bytes'] or digest(p)!=item['sha256']:bad.append(item['path'])
    receipt=(cand/'CANDIDATE_MANIFEST_SHA256.txt').read_text(encoding='utf-8').split()[0]
    if receipt!=digest(cand/'CANDIDATE_FREEZE_MANIFEST.json'):bad.append('manifest receipt')
    batch=root/manifest['batch_path']
    current={p.relative_to(root).as_posix() for p in batch.rglob('*') if p.is_file() and not excluded(p)}
    frozen={r['path'] for r in manifest['files'] if r['role']=='batch_canonical_or_evidence'}
    if current!=frozen:bad.append('batch file set changed')
    if bad:raise FreezeError('Freeze mismatch: '+str(bad[:20]))
    return {'gate':'PASS_P3_EXISTING_FREEZE_VERIFICATION','file_count':len(manifest['files']),
            'candidate':manifest['candidate_id'],'review_started':False}


def write_outputs(root: Path, batch: Path, cand: Path, spec: dict, data: dict,
                  check: Checks, before: list[dict], state_before: str | None):
    """After source checks only. No output is written outside 03_candidate."""
    main=data['main']
    keys=[]
    for k in COSTS+ENERGIES+['initial_quote_yuan','soc_start_kwh','soc_end_kwh','soc_min_kwh','soc_max_kwh',
        'emergency_positive_slots','emergency_events','allowed_adjustments','actual_adjustments','rejected_adjustments']:
        unit='元' if k.endswith('_yuan') else ('kWh' if k.endswith('_kwh') else '次或槽')
        keys.append({'metric':k,'value':main[k],'unit':unit,'source_path':'../02_batch_run/tables/p3_policy_comparison.csv','source_key':MAIN})
    write_csv(cand/'KEY_RESULTS.csv',keys,['metric','value','unit','source_path','source_key'])
    write_csv(cand/'tables/p3_candidate_specified_purchase_10min.csv',data['specified'],list(data['specified'][0]))
    m=number(main,'total_cost_yuan');partials=next(r for r in data['policy_rows'] if r['policy_id']==PARTIAL)
    comparison=[{'policy_id':r['policy_id'],'role':r['role'],'total_cost_yuan':r['total_cost_yuan'],
                 'increase_vs_main_yuan':f'{number(r,"total_cost_yuan")-m:.12f}',
                 'source_path':'../../02_batch_run/tables/p3_policy_comparison.csv'} for r in data['policy_rows']]
    write_csv(cand/'tables/p3_candidate_policy_selection.csv',comparison,list(comparison[0]))
    source_map=[
      {'purpose':'官方工作簿','source_path':'../02_batch_run/results/result3.xlsx','usage':'只读原件，禁止复制重导'},
      {'purpose':'MAIN执行与账单','source_path':'../02_batch_run/results/p3_actual_schedule.csv','usage':'48,096个真实槽，非LP预测'},
      {'purpose':'全部政策','source_path':'../02_batch_run/results/policies/','usage':'12个策略各自完整连续轨迹'},
      {'purpose':'12政策汇总','source_path':'../02_batch_run/tables/p3_policy_comparison.csv','usage':'候选选择对照'},
      {'purpose':'指定10分钟提取','source_path':'tables/p3_candidate_specified_purchase_10min.csv','usage':'候选派生；4日×6时段，g0/a分开'},
      {'purpose':'旧辅助表','source_path':'../02_batch_run/tables/p3_specified_purchase_intervals.csv','usage':'实际为4小时区段；禁止当10min表'},
      {'purpose':'4小时储能','source_path':'../02_batch_run/tables/p3_storage_4h_summary.csv','usage':'充放电与SOC'},
      {'purpose':'原始扰动与调用日志','source_path':'../02_batch_run/logs/','usage':'A-7解释；本轮只核验来源与保留'},
      {'purpose':'格式修复链','source_path':'../02_batch_run/logs/export_format_recovery/','usage':'原失败、修复脚本和验证；不再执行修复'},
      {'purpose':'模型设计','source_path':'../01_model_plan/P3_MODEL_PLAN.md','usage':'已冻结方案，原样保留'}]
    write_csv(cand/'SOURCE_MAP.csv',source_map,list(source_map[0]))
    evidence_rows=[]
    for rec in before:
        if '/logs/' in rec['path']:
            evidence_rows.append({'path':rec['path'],'sha256':rec['sha256'],'size_bytes':rec['size_bytes'],
                                  'role':'format_recovery' if '/export_format_recovery/' in rec['path'] else 'batch_log_or_checkpoint',
                                  'action':'只读冻结；未执行'})
    write_csv(cand/'P3_REPRODUCIBILITY_INVENTORY.csv',evidence_rows,['path','sha256','size_bytes','role','action'])
    after=[]
    for rec in before:after.append(file_record(safe_join(root,rec['path']),root,rec['role']))
    check.add('PROTECTED_FILES_UNCHANGED',before==after)
    current_paths={p.relative_to(root).as_posix() for p in batch.rglob('*') if p.is_file() and not excluded(p)}
    check.add('BATCH_FILE_SET_UNCHANGED',current_paths=={r['path'] for r in before if r['role']=='batch_canonical_or_evidence'})
    st=root/'A_route/CURRENT_STATE.md'
    check.add('CURRENT_STATE_UNCHANGED_BY_SCRIPT',state_before==(digest(st) if st.exists() else None))
    check.require_ok()
    counts=Counter(r['status'] for r in check.rows)
    report={'gate':PASS_GATE,'candidate_id':MAIN,'PASS':counts['PASS'],'FAIL':counts['FAIL'],'blocking':0,
            'scope':'identity+finite bookkeeping+freeze only; not independent A7 review',
            'new_model_fits':0,'new_lp_calls':0,'new_policy_replays':0,'new_workbook_exports':0,
            'new_workbook_copies':0,'source_modifications':0,'main_recomputed_totals':data['totals'],
            'source_file_count':len(before),'batch_validation_counts_inherited':spec['expected_validation_counts'],
            'checks':check.rows,'result3_sha256':spec['workbook_sha256'],'ready_for_review':True,
            'review_execution_authorized':False,'open_issue_register':'CLAIMS_AND_LIMITATIONS.md',
            'old_auxiliary_table_issue':'4h contents preserved; Candidate 24-row 10min derivative created',
            'utc_time':datetime.now(timezone.utc).isoformat()}
    write_json(cand/'P3_CANDIDATE_FREEZE_CHECKS.json',report)
    atomic_text(cand/'P3_CANDIDATE_FREEZE_CHECK.md',f'''# P3 A-6 冻结检查\n\nGate：`{PASS_GATE}`。\n\nCandidate：`{MAIN}`；本地检查 {counts['PASS']} PASS / {counts['FAIL']} FAIL。\n\nMAIN底账复算总费：{data['totals']['total_cost_yuan']:.12f}元。原表总费：{main['total_cost_yuan']}元。\n\n受保护源文件：{len(before)}个；前后字节指纹及文件集合不变。工作簿SHA256：`{spec['workbook_sha256']}`。\n\n只做来源/身份核验、逐日范围核对、MAIN账本算术和派生24行指定10min表；不重训、不求解、不回放、不重导或复制工作簿。未重做未来扰动试验，A-7独立Review尚未开始。\n\n旧 `p3_specified_purchase_intervals.csv` 是4h汇总，原样保留。正确10min提取另存 `tables/p3_candidate_specified_purchase_10min.csv`，需随Review检查。\n\n日期格式恢复原件和脚本只列入清单，没有再次执行。保持所有工作假设，见 `CLAIMS_AND_LIMITATIONS.md`。\n\n`CURRENT_STATE`未由脚本修改；由Codex按任务仅更新既有文件P3小节。\n''')
    atomic_text(cand/'P3_CANDIDATE_GATE.md',f'''# P3 A-6 Candidate Gate\n\n`{PASS_GATE}`\n\n唯一候选：`{MAIN}`。PARTIAL不替换MAIN。\n\n总费用：{main['total_cost_yuan']}元；PARTIAL较MAIN多{number(partials,'total_cost_yuan')-m:.12f}元。\n\ncanonical result3：`../02_batch_run/results/result3.xlsx`\n\nSHA256：`{spec['workbook_sha256']}`\n\n阻塞：0。工作假设与已知辅助表/复现说明均随候选保留。\n\n`READY_FOR_P3_REVIEW=true`，`REVIEW_STARTED=false`，`FINAL_STARTED=false`。\n\n通过表示候选身份和冻结完整性已本地核对，不表示A-7通过或全局最优。停在A-6，下一阶段需用户明确授权。\n''')
    candidate_files=[file_record(p,root,'candidate_artifact') for p in sorted(cand.rglob('*'))
                     if p.is_file() and not excluded(p) and p.name not in STATE_OUTPUTS]
    manifest={'schema':'P3_CANDIDATE_FREEZE_MANIFEST_V1','gate':PASS_GATE,'candidate_id':MAIN,
              'batch_path':spec['batch_path'],'candidate_path':spec['candidate_path'],
              'created_utc':report['utc_time'],'canonical_source':'02_batch_run unchanged',
              'files':before+candidate_files,'file_count':len(before)+len(candidate_files),
              'source_file_count':len(before),'candidate_file_count_excluding_manifest_and_receipt':len(candidate_files),
              'excluded_self_referential_files':sorted(STATE_OUTPUTS),
              'non_scientific_state_update':'single CURRENT_STATE after freeze, tracked separately; not in scientific manifest'}
    write_json(cand/'CANDIDATE_FREEZE_MANIFEST.json',manifest)
    atomic_text(cand/'CANDIDATE_MANIFEST_SHA256.txt',digest(cand/'CANDIDATE_FREEZE_MANIFEST.json')+'  CANDIDATE_FREEZE_MANIFEST.json\n')
    verify_manifest(root,cand)
    return {k:report[k] for k in ['gate','candidate_id','PASS','FAIL','blocking','result3_sha256','new_lp_calls','new_model_fits','new_workbook_exports','ready_for_review','review_execution_authorized']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=None)
    parser.add_argument('--verify-only',action='store_true',help='Read existing freeze; no writes.')
    args=parser.parse_args()
    cand=Path(__file__).resolve().parents[1]
    root=(args.project_root or Path(__file__).resolve().parents[4]).resolve()
    check=Checks()
    try:
        spec=read_json(cand/'contracts/P3_CANDIDATE_SPEC.json')
        if safe_join(root,spec['candidate_path']).resolve()!=cand:
            raise FreezeError('Place this package at <project-root>/A_route/problem3/03_candidate first.')
        if args.verify_only:
            print(json.dumps(verify_manifest(root,cand),ensure_ascii=False,indent=2));return 0
        if (cand/'CANDIDATE_FREEZE_MANIFEST.json').exists():
            raise FreezeError('Freeze already exists. Use --verify-only; never overwrite an existing freeze.')
        batch=safe_join(root,spec['batch_path'])
        refs=read_json(cand/'contracts/P3_A5_UPLOADED_REFERENCE.json')
        verify_uploaded_identity(batch,refs,check)
        upstream=audit_local_evidence(root,batch,spec,check)
        print('来源核验完成；只读取既有结果，不运行生产模型。',flush=True)
        before=inventory_tree(batch,root,'batch_canonical_or_evidence')+upstream
        st=root/'A_route/CURRENT_STATE.md';state_before=digest(st) if st.exists() else None
        data=audit_batch(batch,spec,check);check.require_ok()
        result=write_outputs(root,batch,cand,spec,data,check,before,state_before)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as ex:
        payload={'gate':FAIL_GATE,'error':str(ex),'checks':check.rows,
                 'new_model_fits':0,'new_lp_calls':0,'new_workbook_exports':0,'ready_for_review':False,
                 'instruction':'Stop and locate missing/mismatched evidence; do not rerun A5, rewrite data or downgrade checks.'}
        if not args.verify_only and not (cand/'CANDIDATE_FREEZE_MANIFEST.json').exists():
            write_json(cand/'FREEZE_FAILURE.json',payload)
        print(json.dumps(payload,ensure_ascii=False,indent=2),file=sys.stderr);return 2

if __name__=='__main__':
    raise SystemExit(main())
