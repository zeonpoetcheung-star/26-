#!/usr/bin/env python3
"""P3-0：只读语义预检。仅 Python 标准库；不训练、不优化、不输出工作簿。

当地执行：python -B -s p3_semantic_audit.py --project-root <项目根目录>
源码核对：--reference-only 只用于已上传官方附件的参考运行，不能替代本地验收。
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import os
import posixpath
import sys
import tempfile
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
START = date(2025, 1, 1)
FORMAL = date(2025, 2, 1)
HOURS = (0, 6, 12, 18)
BASE = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def col(i: int) -> str:
    s = ""
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def clock(minutes: int) -> str:
    if minutes == 1440:
        return "24:00"
    return f"{minutes // 60}:{minutes % 60:02d}"


def marker(value: object) -> str:
    if isinstance(value, (float, int)):
        m = round(float(value) * 1440) % 1440
        return clock(m)
    return str(value).strip()


def asdate(value: object) -> date:
    if isinstance(value, (float, int)):
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
    text = str(value).strip().replace("/", "-").replace(".", "-")
    return datetime.strptime(text[:10] if " " in text else text, "%Y-%m-%d").date()


def astime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("T", " "))


class XlsxReadOnly:
    """直接读取OOXML语义值。尤其不把空sharedString的索引28当成日期28。"""
    def __init__(self, path: Path):
        self.path = path
        self.sheets: dict[str, dict[str, object]] = {}
        with zipfile.ZipFile(path) as z:
            self.strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                root = ET.fromstring(z.read("xl/sharedStrings.xml"))
                self.strings = ["".join(si.itertext()) for si in root]
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
            workbook = ET.fromstring(z.read("xl/workbook.xml"))
            for sheet in workbook.find("s:sheets", NS):
                target = targets[sheet.attrib[f"{{{REL}}}id"]]
                member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
                root = ET.fromstring(z.read(member))
                cells, formulas, raw = {}, {}, {}
                for c in root.findall(".//s:sheetData/s:row/s:c", NS):
                    addr = c.attrib["r"]
                    v = c.find("s:v", NS)
                    vtext = v.text if v is not None else None
                    typ = c.attrib.get("t", "n")
                    raw[addr] = {"type": typ, "v": vtext}
                    if typ == "s":
                        value = self.strings[int(vtext)] if vtext is not None else ""
                    elif typ == "inlineStr":
                        node = c.find("s:is", NS)
                        value = "".join(node.itertext()) if node is not None else ""
                    elif vtext is None:
                        value = None
                    elif typ in ("str", "e", "d"):
                        value = vtext
                    elif typ == "b":
                        value = vtext == "1"
                    else:
                        value = float(vtext)
                    cells[addr] = value
                    f = c.find("s:f", NS)
                    if f is not None:
                        formulas[addr] = f.text
                dimension = root.find("s:dimension", NS)
                merges = [m.attrib["ref"] for m in root.findall("s:mergeCells/s:mergeCell", NS)]
                self.sheets[sheet.attrib["name"]] = {
                    "cells": cells, "raw": raw, "formulas": formulas,
                    "dimension": dimension.attrib.get("ref") if dimension is not None else None,
                    "merges": merges,
                }


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(8):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.15 * (attempt + 1))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        raise ValueError(f"拒绝写空事实表：{path}")
    s = io.StringIO(newline="")
    writer = csv.DictWriter(s, fieldnames=list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    atomic_text(path, "\ufeff" + s.getvalue())


def final_contract(g: Fraction, a: Fraction, p: Fraction, e: Fraction = Fraction(0)) -> Fraction:
    if min(g, a, p, e) < 0:
        raise ValueError("电量和P3固定价格不得为负")
    return p * (a + abs(a - g) / 2 + 5 * e)


def incremental_contract(path: list[Fraction], p: Fraction) -> Fraction:
    if len(path) < 1 or min(path) < 0 or p < 0:
        raise ValueError("非法合同路径")
    return p * (path[-1] + sum(abs(b-a) for a, b in zip(path, path[1:])) / 2)


def nonrefundable_contract(g: Fraction, a: Fraction, p: Fraction) -> Fraction:
    return p * (g + Fraction(3,2)*max(a-g, 0) + Fraction(1,2)*max(g-a, 0))


def pwl_energy(nodes: list[Fraction]) -> list[Fraction]:
    if len(nodes) != 25 or min(nodes) < 0:
        raise ValueError("需h0锚点及h1..24非负功率，合计25点")
    result = []
    for j in range(144):
        h, q = divmod(j, 6)
        w = Fraction(2*q+1, 12)
        avg = (1-w)*nodes[h] + w*nodes[h+1]
        result.append(avg/Fraction(6))
    return result


def event_table() -> list[dict]:
    return [{"issue_hour": h, "completed_slots": 6*h, "soc_boundary_index": 6*h,
             "first_adjustable_slot": 6*h+1, "last_adjustable_slot": 144,
             "remaining_today_slots": 144-6*h, "continuation_slots": 6*h,
             "latest_observed_interval_end": clock(60*h)} for h in HOURS]


def geometry_table() -> list[dict]:
    out = []
    for issue in HOURS:
        for j in range(144):
            h, q = divmod(j, 6)
            start = issue*60 + j*10
            w = Fraction(2*q+1,12)
            slot = (start % 1440)//10 + 1
            out.append({"issue_hour": issue, "forecast_slot": j+1,
                        "delivery_day_offset": start//1440, "delivery_slot_id": slot,
                        "physical_start": clock((slot-1)*10), "physical_end": clock(slot*10),
                        "left_forecast_node_hour": h, "right_forecast_node_hour": h+1,
                        "right_node_weight_for_interval_average": str(w),
                        "energy_multiplier_hours": "1/6",
                        "left_node_source": "已完成槽观测代理；首日首发行用h1" if h==0 else "同一发行的小时预报",
                        "is_current_day_contract": start < 1440})
    return out


def toy_checks(check) -> list[dict]:
    F = Fraction
    cases = [
        ("no_adjust",100,100,1,0,100), ("decrease",100,80,1,0,90),
        ("increase",100,150,1,0,175), ("cancel_all",100,0,1,0,50),
        ("zero_plan",0,20,1,0,30), ("emergency_separate",100,80,1,10,140),
        ("price_scale",100,80,2,0,180), ("zero_price",100,80,0,10,0),
    ]
    table=[]
    for label,g,a,p,e,expected in cases:
        actual=final_contract(F(g),F(a),F(p),F(e))
        check("TOY_"+label,actual==expected,f"actual={actual}; expected={expected}")
        table.append({"case":label,"g0_kwh":g,"a_final_kwh":a,"price_cny_per_kwh":p,
                      "emergency_kwh":e,"ordinary_plus_emergency_expected_cny":expected,
                      "contract":"FINAL_VS_0H_CANCEL_SUBSTITUTION"})
    check("TOY_repeated_final", final_contract(F(100),F(80),F(1))==90,"100→150→80只按末值与0时比较")
    check("TOY_repeated_incremental", incremental_contract([F(100),F(150),F(80)],F(1))==140,"逐次替代型敏感性，额外路径费用50")
    check("TOY_monotone_equal",incremental_contract([F(100),F(90),F(80)],F(1))==90,"单向调整两种路径口径相同")
    check("TOY_nonrefundable",nonrefundable_contract(F(100),F(80),F(1))==110,"原款不退+罚金为110，不是主口径")
    check("TOY_no_discard_refund",final_contract(F(100),F(100),F(1))==100,"最终承诺100，即使实际只取80仍付100")
    bad=False
    try: final_contract(F(1),F(-1),F(1))
    except ValueError: bad=True
    check("TOY_negative_rejected",bad,"负的调整差可以记录，但负的最终普通购电量不可输入")
    constant=pwl_energy([F(120)]*25)
    check("TOY_constant_power",all(x==20 for x in constant),"120kW×1/6h=20kWh")
    linear=pwl_energy([F(60+60*h) for h in range(25)])
    check("TOY_first_hour_integral",sum(linear[:6])==90,"h0=60,h1=120，首小时积分90kWh")
    check("TOY_first_slot_integral",linear[0]==F(65,6),"首槽平均65kW，电量65/6")
    check("TOY_integral_24h",sum(linear)==sum(F((60+60*h)+(120+60*h),2) for h in range(24)),"六槽和等于梯形小时积分")
    check("TOY_first_issue_fallback",pwl_energy([F(120),F(120)]+[F(0)]*23)[0]==20,"首日无观测只用当次h1，不偷取slot1 actual")
    check("TOY_6h_boundary",event_table()[1]["first_adjustable_slot"]==37,"6点已完成1..36，只改37..144")
    check("TOY_12h_boundary",event_table()[2]["soc_boundary_index"]==72,"12点使用S72，不用S73或名义SOC")
    check("TOY_18h_continuation",event_table()[3]["continuation_slots"]==108,"18点预测次日18h，非提前锁定次日计划")
    return table


def audit(root: Path, output: Path, reference: bool) -> dict:
    checks=[]
    def check(name: str, ok: bool, detail: str=""):
        checks.append({"check_id":name,"status":"PASS" if ok else "FAIL","detail":detail})
    cfg=json.loads((BASE/"contracts/p3_semantic_contract.json").read_text(encoding="utf-8"))
    rawfiles={k:root/v["relative_path"] for k,v in cfg["official_inputs"].items()}
    tracked={}
    def track(path:Path,expected:str|None=None):
        if not path.is_file():
            check("FILE_"+str(path),False,"必需文件缺失；不搜索或替换为同题外部文件")
            return False
        digest=sha(path);tracked[path]=digest
        if expected:
            check("HASH_"+path.name,digest==expected,f"SHA256={digest}")
        return True
    for key,path in rawfiles.items():
        track(path,cfg["official_inputs"][key]["sha256"])
    if any(c["status"]=="FAIL" for c in checks):
        return finish(output, checks, reference, {},tracked)
    a1=XlsxReadOnly(rawfiles["attachment1"])
    a2=XlsxReadOnly(rawfiles["attachment2"])
    a3=XlsxReadOnly(rawfiles["attachment3"])
    template=XlsxReadOnly(rawfiles["result3_template"])
    fc=a3.sheets["Sheet1"]["cells"]
    check("FORECAST_header", [fc.get(col(j)+"1") for j in range(3,27)]==[f"预报{h}小时" for h in range(1,25)],"C:Z是h1..24，不是h0..23")
    check("FORECAST_dimension", a3.sheets["Sheet1"]["dimension"]=="A1:Z1461")
    check("FORECAST_sst28_blank", len(a3.strings)>28 and a3.strings[28]=="","索引28解析为空串")
    forecast={};blocks_ok=0;blanks=0;negative=0
    for d in range(365):
        day=START+timedelta(days=d); r0=2+4*d
        ok=asdate(fc[f"A{r0}"])==day
        for off,hour in enumerate(HOURS):
            r=r0+off;ok=ok and marker(fc.get(f"B{r}"))==f"{hour}:00"
            if off:
                blanks += int(fc.get(f"A{r}") in ("",None))
                ok=ok and fc.get(f"A{r}") in ("",None)
            issue=datetime.combine(day,datetime.min.time())+timedelta(hours=hour)
            for h in range(1,25):
                value=fc.get(f"{col(h+2)}{r}")
                if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                    negative+=1
                forecast[(issue,h)]=value
        blocks_ok+=int(ok)
    check("FORECAST_blocks",blocks_ok==365,f"正确四行日期块={blocks_ok}/365")
    check("FORECAST_blank_dates",blanks==1095,f"语义空日期={blanks}")
    check("FORECAST_count",len(forecast)==35040,f"长表键={len(forecast)}")
    check("FORECAST_values",negative==0,f"非法/负功率={negative}")
    yearcross=sum((t+timedelta(hours=h)).year>2025 for t,h in forecast)
    beyond=sum(t+timedelta(hours=h)>datetime(2026,1,1) for t,h in forecast)
    check("FORECAST_crossyear",yearcross==40 and beyond==36,f"目标日期跨年={yearcross}；超过最后观测边界={beyond}")
    fixed=a1.sheets["Sheet1"]["cells"]
    markers=[marker(fixed.get(f"A{j+1}")) for j in range(1,145)]
    expected=[clock(10*j) if j<144 else "0:00+1" for j in range(1,145)]
    check("FIXED_markers",markers==expected,"10分钟原marker 0:10..0:00+1")
    actu={}
    for name in ["小区负载","光伏发电实际功率"]:
        cs=a2.sheets[name]["cells"]
        check("ACTUAL_markers_"+name,[marker(cs.get(col(j+1)+"1")) for j in range(1,145)]==expected)
        check("ACTUAL_dates_"+name,all(asdate(cs[f"A{i+2}"])==START+timedelta(days=i) for i in range(365)))
        actu[name]={(START+timedelta(days=i),j):float(cs[f"{col(j+1)}{i+2}"]) for i in range(365) for j in range(1,145)}
    geometry=geometry_table()
    check("GEOMETRY_weights",all(0<Fraction(r["right_node_weight_for_interval_average"])<1 for r in geometry))
    check("GEOMETRY_576",len(geometry)==576)
    wanted=["计划购电量","调整购电量","充放电量","紧急购电量"]
    check("TEMPLATE_sheets",list(template.sheets)==wanted)
    tmap=[]
    for name in wanted[:2]:
        s=template.sheets[name];c=s["cells"]
        check("TEMPLATE_dates_"+name,all(asdate(c[f"A{i+2}"])==FORMAL+timedelta(days=i) for i in range(334)))
        check("TEMPLATE_dimension_"+name,s["dimension"]=="A1:EQ335")
        check("TEMPLATE_blank_"+name,all(c.get(f"{col(j+1)}{r}") in (None,"") for r in range(2,336) for j in range(1,145)),"原始模板数值区为空")
        check("TEMPLATE_total_labels_"+name,c.get("EP1")=="全天购电量" and c.get("EQ1")=="全天购电费")
        check("TEMPLATE_no_version_axis_"+name,len([c.get(col(j)+"1") for j in range(1,148)])==147,"每天一行；没有6/12/18三条版本记录位置")
    tc=template.sheets["计划购电量"]["cells"]
    check("TEMPLATE_known_label_conflict",tc.get("B1")=="0:10-0:20" and tc.get("EO1")=="0:00-0:10+1")
    for j in range(1,145):
        tmap.append({"slot_id":j,"source_marker":markers[j-1],"excel_column":col(j+1),
                     "template_label":tc.get(col(j+1)+"1"),"physical_interval":f"{clock((j-1)*10)}-{clock(j*10)}",
                     "plan_semantics":"g0_kwh","adjustment_semantics":"a_final_kwh, not delta",
                     "latest_possible_issue_hour":((j-1)//36)*6})
    toy=toy_checks(check)
    local_detail={"checked":False}
    if not reference:
        common={k:root/v["relative_path"] for k,v in cfg["common_inputs"].items()}
        present=[track(common[k],cfg["common_inputs"][k]["sha256"]) for k in common]
        if all(present):
            fl=rows(common["pv_hourly"]); seen=set();valueerr=0;timeerr=0
            for r in fl:
                key=(astime(r["issue_datetime"]),int(r["horizon_hour"]))
                if key in seen: timeerr+=1
                seen.add(key)
                if key not in forecast: timeerr+=1;continue
                if abs(float(r["pv_forecast_kw"])-forecast[key])>1e-9:valueerr+=1
                if astime(r["nominal_target_datetime"])!=key[0]+timedelta(hours=key[1]):timeerr+=1
            check("COMMON_forecast",seen==set(forecast) and len(fl)==35040 and valueerr==0 and timeerr==0,f"值差项={valueerr}；时间/重复项={timeerr}")
            ar=rows(common["actual"]);keys=set();bad=0
            for r in ar:
                k=(asdate(r["date"]),int(r["slot_id"]));keys.add(k)
                if k not in actu["小区负载"]:bad+=1;continue
                bad += int(abs(float(r["load_kw"])-actu["小区负载"][k])>1e-9 or abs(float(r["pv_actual_kw"])-actu["光伏发电实际功率"][k])>1e-9)
            check("COMMON_actual",len(ar)==52560 and len(keys)==52560 and bad==0,f"官方逐槽对账差异={bad}")
            fx=rows(common["fixed"])
            check("COMMON_fixed",len(fx)==144 and all(int(r["slot_id"])==i+1 and abs(float(r["price_fixed_yuan_per_kwh"])-float(fixed[f"B{i+2}"]))<1e-12 for i,r in enumerate(fx)))
            # 锚点键：只按区间终点<=发行时刻取最后完成槽，不从未来取值。
            observed={(datetime.combine(d,datetime.min.time())+timedelta(minutes=j*10)):v for (d,j),v in actu["光伏发电实际功率"].items()}
            missing=[t for t in sorted({t for t,h in forecast}) if t not in observed]
            check("ANCHOR_only_first_issue_missing",missing==[datetime(2025,1,1)],f"没有已完成槽锚点的发行次数={len(missing)}")
            check("ANCHOR_6h_is_slot36",observed[datetime(2025,2,1,6)]==actu["光伏发电实际功率"][(FORMAL,36)])
            for cut in [datetime(2025,2,1,6),datetime(2025,6,21,12),datetime(2025,12,31,18)]:
                base_nodes=[Fraction(str(observed[cut]))]+[Fraction(str(forecast[(cut,h)])) for h in range(1,25)]
                # 制造一个完全隔离的as-of视图：未来actual及未来发行预报均不能访问。
                past={k:v for k,v in observed.items() if k<=cut}
                published={k:v for k,v in forecast.items() if k[0]<=cut}
                prefix_nodes=[Fraction(str(past[cut]))]+[Fraction(str(published[(cut,h)])) for h in range(1,25)]
                check("PREFIX_mapping_"+cut.isoformat(),pwl_energy(base_nodes)==pwl_energy(prefix_nodes),"仅验证本轮映射函数，不宣称未来预测器/LP/控制器已验证")
            local_detail={"checked":True,"common_forecast_rows":len(fl),"common_actual_rows":len(ar)}
        p2path=root/cfg["p2_protection"]["result2_relative_path"]
        track(p2path,cfg["p2_protection"]["result2_sha256"])
        mp=root/"A_route/problem2/03_candidate/CANDIDATE_FREEZE_MANIFEST.json"
        if track(mp):
            m=json.loads(mp.read_text(encoding="utf-8-sig"))
            check("P2_frozen_identity",m.get("candidate_id")=="ORIGINAL_MAIN" and m.get("canonical_result2_sha256")==cfg["p2_protection"]["result2_sha256"])
    for path,digest in tracked.items():
        check("UNCHANGED_"+str(path.relative_to(root)),sha(path)==digest,"只读输入哈希前后相同")
    summary={"official_issue_rows":1460,"official_hourly_forecasts":len(forecast),
             "verified_date_blocks":blocks_ok,"semantic_blank_dates":blanks,
             "crossyear_target_date_rows":yearcross,"outside_actual_end_rows":beyond,
             "forecast_geometry_rows":len(geometry),"result3_slot_map_rows":len(tmap),
             "template_sheet_dimensions":{k:v["dimension"] for k,v in template.sheets.items()},
             "common_local_verification":local_detail,
             "new_fit_count":0,"lp_solve_count":0,"actual_replay_count":0,"forecast_accuracy_metrics_computed":False,
             "workbooks_created_or_modified":0}
    write_csv(output/"p3_event_clock_map.csv",event_table())
    write_csv(output/"p3_forecast_interpolation_map.csv",geometry)
    write_csv(output/"p3_result3_slot_map.csv",tmap)
    write_csv(output/"p3_settlement_examples.csv",toy)
    return finish(output,checks,reference,summary,tracked)


def finish(output:Path,checks:list[dict],reference:bool,summary:dict,tracked:dict) -> dict:
    fails=sum(r["status"]=="FAIL" for r in checks)
    gate=("BLOCKED_P3_SEMANTIC_AUDIT" if fails else
          "REFERENCE_SOURCE_CHECKED_LOCAL_PENDING" if reference else
          "PASS_P3_SEMANTIC_AUDIT_WITH_OPEN_ISSUES")
    result={"audit_id":"P3_SEMANTIC_20260912_V1","gate":gate,
            "run_scope":"official_source_reference" if reference else "local_official_and_frozen_common",
            "checked_at_utc":datetime.now(timezone.utc).isoformat(),
            "python_executable":sys.executable,"python_version":sys.version,
            "PASS":len(checks)-fails,"FAIL":fails,"blocking":fails,
            "open_issues":["OI-01","OI-13","P3-S01","P3-S02","P3-S03","P3-S04","P3-S05"],
            "permit_p3_1":not reference and fails==0,
            "permit_training_or_batch":False,
            "summary":summary,
            "read_only_input_hashes":{str(p):h for p,h in tracked.items()},"checks":checks}
    atomic_text(output/"p3_semantic_check_results.json",json.dumps(result,ensure_ascii=False,indent=2))
    write_csv(output/"p3_semantic_checks.csv",checks)
    md=f"# P3-0 本次机械检查\n\nGate：`{gate}`\n\nPASS {result['PASS']} / FAIL {fails} / blocking {fails}\n\n本轮为时间、字段、计费算术和文件一致性检查，不是策略性能验证。" \
       +"\n\n题面未明示的合同假设仍保持开放，见 `P3_SEMANTIC_AUDIT.md`。" \
       +"\n\n通过后仅允许进入 P3-1 Information Audit，禁止自动训练或全年优化。\n"
    atomic_text(output/"P3_SEMANTIC_GATE.md",md)
    return result


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--reference-only",action="store_true")
    args=parser.parse_args()
    root=args.project_root.resolve()
    output=(args.output or BASE/"local_verification").resolve()
    # 脚本不会对既有Common/P1/P2写入；输出只允许审计目录，参考运行可用独立工作区。
    if not args.reference_only and output!=BASE/"local_verification":
        parser.error("本地运行只允许写入本审计目录下local_verification")
    try:
        res=audit(root,output,args.reference_only)
    except Exception as exc:
        output.mkdir(parents=True,exist_ok=True)
        atomic_text(output/"P3_EXECUTION_ERROR.txt",type(exc).__name__+": "+str(exc)+"\n")
        print("BLOCKED_P3_SEMANTIC_AUDIT",type(exc).__name__,str(exc))
        return 2
    print(json.dumps({k:res[k] for k in ["gate","PASS","FAIL","blocking","permit_p3_1","permit_training_or_batch"]},ensure_ascii=False,indent=2))
    return 0 if res["FAIL"]==0 else 2


if __name__=="__main__":
    raise SystemExit(main())
