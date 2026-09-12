#!/usr/bin/env python3
"""把 P3 本地大日志/大CSV整理成 GitHub 可传的压缩包。
默认不包含 checkpoints；绘图通常完全不需要它们。
"""
from pathlib import Path
import argparse, gzip, shutil, hashlib, csv

MAX=90*1024*1024

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def split_file(src, outdir):
    parts=[]
    with src.open('rb') as f:
        i=1
        while True:
            b=f.read(MAX)
            if not b: break
            p=outdir/f'{src.name}.part{i:03d}'
            p.write_bytes(b); parts.append(p); i+=1
    return parts

ap=argparse.ArgumentParser()
ap.add_argument('project_root')
ap.add_argument('output_dir')
ap.add_argument('--include-checkpoints', action='store_true')
a=ap.parse_args()
root=Path(a.project_root)
out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
paths=[
 root/'A_route/problem3/02_batch_run/results/p3_load_fit_log.csv',
 root/'A_route/problem3/02_batch_run/results/p3_forecast_ledger.csv',
 root/'A_route/problem3/02_batch_run/results/p3_scenario_quantile_diagnostics.csv',
 root/'A_route/problem3/02_batch_run/logs/run_info.json',
 root/'A_route/problem3/02_batch_run/logs/causality_validation.json',
 root/'A_route/problem3/02_batch_run/logs/output_manifest.json',
 root/'A_route/problem3/02_batch_run/logs/production_manifest.json',
 root/'A_route/problem3/02_batch_run/logs/solver_invocations.jsonl',
]
if a.include_checkpoints:
    paths += list((root/'A_route/problem3/02_batch_run/logs/checkpoints').rglob('*'))
rows=[]
for p in paths:
    if not p.is_file(): continue
    rel=p.relative_to(root)
    gz=out/(str(rel).replace('/','__').replace('\\','__')+'.gz')
    with p.open('rb') as fi, gzip.open(gz,'wb',compresslevel=9) as fo: shutil.copyfileobj(fi,fo)
    if gz.stat().st_size>MAX:
        parts=split_file(gz,out); gz.unlink()
        for part in parts: rows.append({'source':str(rel),'artifact':part.name,'size_bytes':part.stat().st_size,'sha256':sha(part)})
    else:
        rows.append({'source':str(rel),'artifact':gz.name,'size_bytes':gz.stat().st_size,'sha256':sha(gz)})
with (out/'MANIFEST.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['source','artifact','size_bytes','sha256']); w.writeheader(); w.writerows(rows)
print(f'created {len(rows)} artifacts in {out}')
