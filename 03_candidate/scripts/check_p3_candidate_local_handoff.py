"""A-6 只读交接核验。仅输出 Candidate 证据，不运行 A-5 或写入工作簿。"""
from __future__ import annotations
import ast
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import posixpath
import sys
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[4]
CAND = ROOT / 'A_route/problem3/03_candidate'
BATCH = ROOT / 'A_route/problem3/02_batch_run'
module_spec = importlib.util.spec_from_file_location('candidate_freeze', CAND/'scripts/freeze_p3_candidate.py')
freeze = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(freeze)
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
OLD_SCRIPT_SHA = '417a3bf62467918f1f038a348a7a1a002730765a6d6d9643df0c9b62b53c5194'
HISTORICAL = {
    'FREEZE_FAILURE.json': '18a7be57cad7fd643b551675b849a5083393c91d46f798b75b976e5bcd52b4e7',
    'P3_CANDIDATE_BLOCKER_REPORT.md': 'b58383f53b8f5ce99e9c2c44e8d117c51804e2750de8e2e9d6e03fc0c6cec2e3',
}


def xml_workbook(path):
    """只读 OOXML；解析共享字符串和数值，不通过导出器读写。"""
    with zipfile.ZipFile(path) as archive:
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        wb = ET.fromstring(archive.read('xl/workbook.xml'))
        relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {r.get('Id'): r.get('Target') for r in relationships}
        style = ET.fromstring(archive.read('xl/styles.xml'))
        formats = {int(x.get('numFmtId')): x.get('formatCode') for x in style.findall('m:numFmts/m:numFmt', NS)}
        formats.update({14: 'mm-dd-yy', 20: 'h:mm'})
        xfs = [formats.get(int(x.get('numFmtId', '0')), 'builtin:'+x.get('numFmtId', '0'))
               for x in style.findall('m:cellXfs/m:xf', NS)]
        sheets = {}
        for sheet in wb.findall('m:sheets/m:sheet', NS):
            target = targets[sheet.get(REL)]
            part = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
            xml = ET.fromstring(archive.read(part))
            cells = {}
            for cell in xml.findall('.//m:sheetData/m:row/m:c', NS):
                kind = cell.get('t', 'n')
                raw = cell.find('m:v', NS)
                value = None if raw is None else raw.text
                if kind == 's': value = strings[int(value)]
                elif kind == 'inlineStr': value = ''.join(cell.find('m:is', NS).itertext())
                elif kind == 'n' and value is not None: value = float(value)
                elif kind == 'd' and value is not None:
                    value = (datetime.fromisoformat(value)-datetime(1899, 12, 30)).total_seconds()/86400
                formula = cell.find('m:f', NS)
                cells[cell.get('r')] = {'value': value, 'formula': None if formula is None else formula.text,
                                        'format': xfs[int(cell.get('s', '0'))], 'type': kind}
            sheets[sheet.get('name')] = {
                'cells': cells,
                'dimension': xml.find('m:dimension', NS).get('ref') if xml.find('m:dimension', NS) is not None else None,
                'merges': [x.get('ref') for x in xml.findall('m:mergeCells/m:mergeCell', NS)],
            }
    return sheets


def main():
    if (CAND/'CANDIDATE_FREEZE_MANIFEST.json').exists():
        raise RuntimeError('已有冻结，不得覆盖交接证据；只能执行 --verify-only。')
    checks = freeze.Checks()
    before = {}

    def pin(path):
        path = freeze.safe_join(ROOT, path.relative_to(ROOT).as_posix())
        before[path.relative_to(ROOT).as_posix()] = freeze.digest(path)
        return path

    spec = freeze.read_json(pin(CAND/'contracts/P3_CANDIDATE_SPEC.json'))
    refs = freeze.read_json(pin(CAND/'contracts/P3_A5_UPLOADED_REFERENCE.json'))
    checks.add('REFERENCE_COUNT', len(refs['files']) == 142)
    freeze.verify_uploaded_identity(BATCH, refs, checks)
    for item in refs['files']: before[(BATCH/item['path']).relative_to(ROOT).as_posix()] = item['sha256']
    batch_spec = freeze.read_json(BATCH/'contracts/P3_BATCH_SPEC.json')
    checks.add('PROTECTED_SOURCE_COUNT', len(batch_spec['protected_sources']) == 45)
    for item in batch_spec['protected_sources']:
        path = pin(ROOT/item['relative_path'])
        checks.add('UPSTREAM_SHA:'+item['relative_path'], freeze.digest(path) == item['sha256'])
    for name, sha in HISTORICAL.items():
        checks.add('ORIGINAL_BLOCKER_PRESERVED:'+name, freeze.digest(pin(CAND/name)) == sha)
    pin(ROOT/'A_route/CURRENT_STATE.md')
    old_path = pin(CAND/'evidence/freeze_p3_candidate_before_junction_fix.py')
    new_path = pin(CAND/'scripts/freeze_p3_candidate.py')
    checks.add('ORIGINAL_FREEZE_SCRIPT_SHA', freeze.digest(old_path) == OLD_SCRIPT_SHA)
    old_ast = ast.parse(old_path.read_text(encoding='utf-8-sig'))
    new_ast = ast.parse(new_path.read_text(encoding='utf-8-sig'))
    old_functions = {n.name: ast.dump(n) for n in old_ast.body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: ast.dump(n) for n in new_ast.body if isinstance(n, ast.FunctionDef)}
    unchanged = ['safe_join', 'excluded', 'audit_batch', 'audit_local_evidence', 'verify_uploaded_identity',
                 'number', 'equal', 'digest', 'file_record', 'read_json', 'csv_rows', 'atomic_text', 'write_json', 'write_csv']
    for name in unchanged:
        checks.add('UNCHANGED_FUNCTION:'+name, old_functions[name] == new_functions[name])
    junction_before = freeze.junction_record(ROOT)
    try:
        freeze.safe_join(ROOT, freeze.AUTHORIZED_JUNCTION+'/.modules.yaml')
    except freeze.FreezeError:
        checks.add('SAFE_JOIN_EXTERNAL_STILL_REJECTED', True)
    else:
        checks.add('SAFE_JOIN_EXTERNAL_STILL_REJECTED', False)
    with patch.object(freeze, 'AUTHORIZED_JUNCTION_TARGET', 'C:/not_the_authorized_target'):
        try: freeze.junction_record(ROOT)
        except freeze.FreezeError: checks.add('CHANGED_TARGET_REJECTED', True)
        else: checks.add('CHANGED_TARGET_REJECTED', False)
    # 在内存中模拟不同路径的普通 node_modules，验证不是同名通配排除。
    mock_root = CAND/'__memory_only_enumeration_test__'
    mock_nm = mock_root/'node_modules'
    mock_scripts = mock_root/'scripts'
    tree = {mock_root: [mock_nm, mock_scripts], mock_nm: [mock_nm/'business.csv'],
            mock_scripts: [mock_scripts/'business.py']}
    with patch.object(Path, 'iterdir', lambda p: iter(tree.get(p, []))), patch.object(Path, 'is_dir', lambda p: p in tree):
        listed = set(freeze.frozen_tree_paths(mock_root, ROOT))
    checks.add('NO_BROAD_NAME_EXCLUSION', mock_nm/'business.csv' in listed and mock_scripts/'business.py' in listed)
    with patch.object(Path, 'iterdir', lambda p: iter(tree.get(p, []))), patch.object(Path, 'is_junction', lambda p: p == mock_nm):
        try: list(freeze.frozen_tree_paths(mock_root, ROOT))
        except freeze.FreezeError: checks.add('OTHER_JUNCTION_REJECTED', True)
        else: checks.add('OTHER_JUNCTION_REJECTED', False)
    baseline_paths = []
    for directory, dirs, files in os.walk(BATCH, topdown=True, followlinks=False):
        for name in list(dirs):
            path = Path(directory)/name
            if path == ROOT/freeze.AUTHORIZED_JUNCTION:
                dirs.remove(name)
            elif path.is_junction() or path.is_symlink():
                raise RuntimeError('发现未授权的其他联接：'+str(path))
        baseline_paths.extend(Path(directory)/name for name in files if not freeze.excluded(Path(directory)/name))
    enumerated = [p for p in freeze.frozen_tree_paths(BATCH, ROOT) if p.is_file() and not freeze.excluded(p)]
    checks.add('ENUMERATION_MATCHES_INDEPENDENT_EXACT_PRUNE', set(baseline_paths) == set(enumerated))
    checks.add('AUTHORIZED_SUBTREE_NOT_ENTERED', not any((ROOT/freeze.AUTHORIZED_JUNCTION) in p.parents for p in enumerated))
    delivery = freeze.read_json(pin(CAND/'evidence/DELIVERY_MANIFEST.json'))
    for item in delivery['files']:
        path = CAND.parent/item['path']
        if path == new_path: path = old_path
        checks.add('DELIVERY_ORIGINAL_SHA:'+item['path'], freeze.digest(pin(path)) == item['sha256'])
    checks.require_ok()
    print('142 个上传文件、45 个上游源与最小修复边界核验通过。', flush=True)

    workbook_path = pin(BATCH/spec['workbook_relative_path'])
    checks.add('RESULT3_SHA', freeze.digest(workbook_path) == spec['workbook_sha256'])
    workbook = xml_workbook(workbook_path)
    wanted = {(d, j) for d in spec['specified_dates'] for j in spec['specified_slots']}
    actual = { (r['date'], int(r['slot_id'])): r for r in freeze.csv_rows(BATCH/'results/p3_actual_schedule.csv')
               if (r['date'], int(r['slot_id'])) in wanted }
    checks.add('SPECIFIED_24_SOURCE_KEYS', set(actual) == wanted and len(actual) == 24)
    mapping = []
    for d, j in sorted(wanted):
        row = actual[(d, j)]
        start = datetime.fromisoformat(d)+timedelta(minutes=(j-1)*10)
        end = start+timedelta(minutes=10)
        checks.add(f'PHYSICAL_INTERVAL:{d}:{j}', row['physical_interval_start'] == start.isoformat()
                   and row['physical_interval_end'] == end.isoformat())
        excel_row = (datetime.fromisoformat(d)-datetime(2025, 2, 1)).days+2
        n = j+1
        column = ''
        while n: n, rem = divmod(n-1, 26); column = chr(65+rem)+column
        address = column+str(excel_row)
        entry = {'date': d, 'slot_id': j, 'physical_interval_start': start.isoformat(),
                 'physical_interval_end': end.isoformat(), 'cell': address}
        for name, field in [('计划购电量', 'g0_kwh'), ('调整购电量', 'a_kwh')]:
            cells = workbook[name]['cells']
            header = cells[column+'1']['value']
            expected_header = f'{end.hour}:{end.minute:02d}-{(end+timedelta(minutes=10)).hour}:{(end+timedelta(minutes=10)).minute:02d}'
            checks.add(f'ORIGINAL_HEADER:{name}:{d}:{j}', header == expected_header)
            date_value = datetime(1899, 12, 30)+timedelta(days=cells['A'+str(excel_row)]['value'])
            checks.add(f'WORKBOOK_DATE:{name}:{d}:{j}', date_value.date().isoformat() == d)
            cell = cells[address]
            checks.add(f'WORKBOOK_CELL:{name}:{d}:{j}', cell['formula'] is None
                       and freeze.equal(float(cell['value']), float(row[field]), spec['quantity_abs_tolerance']))
            entry[field] = row[field]
            entry[field+'_workbook'] = cell['value']
            entry['original_header'] = header
        mapping.append(entry)
    checks.require_ok()

    recovery = BATCH/spec['format_recovery_directory']
    output_manifest = freeze.read_json(pin(BATCH/'logs/output_manifest.json'))
    manifest_by_path = {r['relative_path'].replace('\\', '/'): r for r in output_manifest}
    recovery_records = []
    for path in sorted(recovery.iterdir()):
        if not path.is_file(): raise RuntimeError('恢复证据存在未预期的目录：'+str(path))
        pin(path)
        item = manifest_by_path.get(path.relative_to(BATCH).as_posix())
        checks.add('FORMAT_RECOVERY_SHA:'+path.name, item is not None and path.stat().st_size == item['size_bytes']
                   and freeze.digest(path) == item['sha256'])
        recovery_records.append(freeze.file_record(path, ROOT, '原格式修复证据，仅只读核验'))
    for item in freeze.read_json(pin(BATCH/'logs/production_manifest.json'))['files']:
        path = pin(BATCH/item['path'])
        checks.add('PRODUCTION_SCRIPT_SHA:'+item['path'], freeze.digest(path) == item['sha256'])
    old_validation = freeze.read_json(recovery/'workbook_validation_first_failed.json')
    new_validation = freeze.read_json(pin(BATCH/'logs/workbook_validation.json'))
    correction = freeze.read_json(recovery/'format_correction_checks.json')
    closure = freeze.read_json(recovery/'gate_closure.json')
    old_workbook_path = recovery/'result3_first_failed.xlsx'
    checks.add('FAILED_WORKBOOK_SHA', freeze.digest(old_workbook_path) == spec['failed_workbook_sha256'])
    checks.add('FORMAT_BEFORE_AFTER_IDENTITY', correction['before_sha256'] == spec['failed_workbook_sha256']
               and correction['after_sha256'] == new_validation['sha256'] == spec['workbook_sha256'])
    checks.add('ORIGINAL_3194_CHECK_IDS_ORDER_PRESERVED', len(new_validation['checks']) == 3194
               and [r['check_id'] for r in old_validation['checks']] == [r['check_id'] for r in new_validation['checks']])
    checks.add('FORMAT_VALIDATION_COUNTS', Counter(r['status'] for r in old_validation['checks']) == {'PASS':2692, 'FAIL':502}
               and Counter(r['status'] for r in new_validation['checks']) == {'PASS':3194}
               and correction['PASS'] == 4 and correction['FAIL'] == 0)
    checks.add('FORMAT_CLOSURE_NO_RECOMPUTE', closure['formal_and_validation_calls_unchanged'] is True
               and correction['solver_calls'] == 0 and correction['fit_calls'] == 0
               and closure['final_decision']['gate'] == 'PASS_P3_BATCH_WITH_OPEN_ISSUES')
    # 只解析原检查源码，核对当时保存的 AST 指纹，不执行原 validator。
    exporter = pin(BATCH/'scripts/p3_export.py')
    function = next(n for n in ast.parse(exporter.read_text(encoding='utf-8-sig')).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'export_and_validate')
    idx = next(i for i,n in enumerate(function.body) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'template' for t in n.targets))
    segment_sha = hashlib.sha256(ast.dump(ast.Module(body=function.body[idx:], type_ignores=[])).encode()).hexdigest()
    checks.add('ORIGINAL_VALIDATOR_AND_CHECK_SEGMENT_SHA', correction['original_validator_sha256'] == freeze.digest(exporter)
               and correction['trusted_check_segment_sha256'] == segment_sha)
    old_workbook = xml_workbook(old_workbook_path)
    checks.add('FORMAT_FOUR_SHEET_NAMES', list(old_workbook) == list(workbook) and len(workbook) == 4)
    contents = []; outside = []; changes = 0; compared = 0
    for name, first in old_workbook.items():
        second = workbook[name]
        checks.add('FORMAT_STRUCTURE:'+name, first['dimension'] == second['dimension'] and first['merges'] == second['merges'])
        for coordinate in set(first['cells']) | set(second['cells']):
            a = first['cells'].get(coordinate, {'value':None, 'formula':None, 'format':'builtin:0'})
            b = second['cells'].get(coordinate, {'value':None, 'formula':None, 'format':'builtin:0'})
            compared += 1
            if a['value'] != b['value'] or a['formula'] != b['formula']: contents.append(name+'!'+coordinate)
            if a['format'] != b['format']:
                changes += 1
                col = ''.join(x for x in coordinate if x.isalpha())
                rn = int(''.join(x for x in coordinate if x.isdigit()))
                if not ((name == '充放电量' and col in ('A','E') and 2 <= rn <= 2005)
                        or (name == '紧急购电量' and col == 'A' and 2 <= rn <= 175)):
                    outside.append(name+'!'+coordinate)
    checks.add('FORMAT_ALL_EXISTING_CELL_VALUES_FORMULAS_UNCHANGED', not contents, str(contents[:8]))
    checks.add('FORMAT_CHANGES_EXACT_SCOPE', changes == 4171 and not outside, f'格式变化 {changes}；范围外 {outside[:8]}')
    checks.add('JUNCTION_UNCHANGED_DURING_HANDOFF', freeze.junction_record(ROOT) == junction_before)
    changes_before_after = [rel for rel, sha in before.items() if freeze.digest(freeze.safe_join(ROOT, rel)) != sha]
    checks.add('HANDOFF_INPUTS_UNCHANGED', not changes_before_after, str(changes_before_after[:8]))
    checks.require_ok()

    evidence = {'stage':'A-6', 'scope':'冻结前只读交接与枚举边界核验，不是 A-7',
                'PASS':len(checks.rows), 'FAIL':0, 'blocking':0, 'checks':checks.rows,
                'specified_rows':mapping, 'specified_numeric_cells':48,
                'format_recovery_files':recovery_records, 'xml_cells_compared':compared,
                'format_changes':changes, 'business_value_formula_changes':len(contents),
                'pinned_source_hashes':before, 'junction':junction_before,
                'old_script_sha256':OLD_SCRIPT_SHA, 'new_script_sha256':freeze.digest(new_path),
                'unchanged_core_functions':unchanged, 'enumerated_batch_file_count':len(enumerated),
                'new_fit':0, 'new_lp':0, 'new_replay':0, 'new_workbook_export_or_copy':0,
                'utc_time':datetime.now(timezone.utc).isoformat()}
    freeze.write_json(CAND/'evidence/P3_LOCAL_HANDOFF_CHECKS.json', evidence)
    rows = ['| 日期 | 槽 | 物理区间 | 原模板表头 | 两页单元格 | g0（kWh） | a（kWh） |',
            '| --- | ---: | --- | --- | --- | ---: | ---: |']
    for r in mapping:
        rows.append(f'| {r["date"]} | {r["slot_id"]} | {r["physical_interval_start"][11:16]}–{r["physical_interval_end"][11:16]} | {r["original_header"]} | {r["cell"]} | {float(r["g0_kwh"]):.12g} | {float(r["a_kwh"]):.12g} |')
    chain_rows = ['| 原件路径（相对项目根） | SHA-256 |', '| --- | --- |']
    chain_rows += [f'| {r["path"]} | `{r["sha256"]}` |' for r in recovery_records]
    report = f'''# P3 A-6 本地只读交接检查

SPECIFIED_24_CELLS_MATCH=PASS

FORMAT_RECOVERY_CHAIN=PASS

本轮实际完成 {len(checks.rows)} PASS / 0 FAIL；这是冻结前交接检查，最终 Candidate Gate 仍以随后从头执行的冻结脚本和 manifest 自校验为准。没有执行 A-5 runner、批量 validator、预测、LP、政策回放或工作簿导出/复制。

## 指定时段与工作簿映射

来源为 `../02_batch_run/results/p3_actual_schedule.csv` 与 `../02_batch_run/results/result3.xlsx`。计划购电量页核对 g0，调整购电量页核对 a；四日 × 六槽共 24 行、48 个数值单元格全部一致（绝对容差 1e-6 kWh），每行另核对日期与物理区间。精确数值及逐项结果见 `evidence/P3_LOCAL_HANDOFF_CHECKS.json`。

两页的日期在 A 列，行号依次 49、142、236、325。沿用已冻结 H-END 映射：物理槽 j 对应第 j+1 列。原模板表头比物理区间晚一槽，下面并列保留原表头和真实物理区间，不修改工作簿。旧四小时辅助表原样保留，不用它填指定十分钟时段。

{chr(10).join(rows)}

## 格式修复证据链

本地原失败工作簿、实际修复脚本、验证脚本、闭合脚本和记录均已读取；以下 {len(recovery_records)} 个原件的 SHA-256 均与 A-5 的 `logs/output_manifest.json` 一致。原生产脚本指纹也与 `logs/production_manifest.json` 一致，不用云端快照替代本地日志。

- `repair_date_formats.mjs`：只更改储能页日期/时刻列与紧急页日期列的格式，原失败哈希校验后修正；本轮未执行。
- `validate_format_correction.py`：提取已签名原导出器的只读检查段，保留原 3194 项 ID 和顺序；本轮只解析 AST 并核对已保存段指纹，未执行。
- `close_gate_after_format_fix.py`：合并已经完成的检查、补报告和关闭当时阻塞，保留调用数；本轮未执行。
- 首次 2692 PASS / 502 FAIL → 最终 3194 PASS / 0 FAIL；格式补查 4 PASS / 0 FAIL，闭合记录确认无新增拟合或 LP。
- 本轮另以 OOXML 只读比较 {compared} 个已有单元格位置，业务值/公式变化 0，四表维度/合并不变；4171 处格式差异全部落在当时授权范围。
- 原失败工作簿 SHA：`{spec['failed_workbook_sha256']}`。
- 最终工作簿 SHA：`{spec['workbook_sha256']}`。

{chr(10).join(chain_rows)}

## 最小联接修复与原故障证据

仅登记并跳过 `{freeze.AUTHORIZED_JUNCTION}`，解析目标为 `{freeze.AUTHORIZED_JUNCTION_TARGET}`。原因：项目外部运行时依赖目录联接，不属于 A-5 业务数据；枚举前识别，不递归外部子树。其他同名普通目录仍枚举，其他联接仍拒绝，`safe_join` 的 AST 与原件完全相同。数学对账函数 `audit_batch` 及其他 {len(unchanged)-1} 个核心函数也未改变。

原脚本另存 `evidence/freeze_p3_candidate_before_junction_fix.py`（SHA `{OLD_SCRIPT_SHA}`）；修复后脚本 SHA `{freeze.digest(new_path)}`。原 Candidate Spec 与 142 文件合同不修改，新增例外合同单独登记。独立 `os.walk` 精确裁剪与修复后枚举得到的项目内文件集合一致，共 {len(enumerated)} 个。

原 `FREEZE_FAILURE.json` 和 `P3_CANDIDATE_BLOCKER_REPORT.md` 字节指纹未改变，不改写成成功记录；它们描述的是上次失败，后续成功状态由新 Gate 表示。原失败 JSON 本次也纳入冻结清单，新的失败记录使用唯一文件名，不覆盖历史。

142 个上传文件、45 个上游源及本次只读接触的证据全部核验；{len(before)} 个已记录文件检查前后 SHA 相同，目录联接元数据相同。完整 A-5 文件树的前后指纹核验将由随后原 A-6 流程完成。所有工作假设仍保留，不宣称 A-7 已通过。

本轮使用 `data-analytics:validate-data` 的独立来源与算术核验，以及 `spreadsheets:Spreadsheets` 的只读工作簿约束。未更改工作簿数值、公式或格式。
'''
    freeze.atomic_text(CAND/'P3_LOCAL_HANDOFF_CHECK.md', report)
    print(json.dumps({k:evidence[k] for k in ['PASS','FAIL','blocking','specified_numeric_cells','xml_cells_compared','format_changes','enumerated_batch_file_count']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
