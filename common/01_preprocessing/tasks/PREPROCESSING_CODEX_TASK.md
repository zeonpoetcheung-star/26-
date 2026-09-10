# 2026 CUMCM C题｜A-1 Deterministic Preprocessing｜Codex Task

**当前阶段**：A-1 Deterministic Preprocessing  
**上游阶段**：A-0 Problem Formulation（已确认）  
**下游阶段**：A-2 Recon（本轮不得进入）  
**执行者**：Codex  
**目标**：把官方附件转换成可追溯、结构稳定、可供后续 Recon/EDA/Model Planning 使用的 canonical 数据层，并完成数据结构与时间结构的确定性审计。  

> 本轮不是 EDA，不是 Recon，不是建模。不要解释“规律”，不要比较预测方法，不要求最优购电策略。

---

## 0. 开始前先读什么

先读取且仅作为规则依据：

```text
A_route/common/00_problem_formulation/C_PROBLEM_FORMULATION.md
A_route/common/00_problem_formulation/DATA_REQUIREMENTS.md
A_route/common/00_problem_formulation/OPEN_ISSUES.md
```

再读取官方输入：

```text
input/original/C题.pdf
input/original/附件1.xlsx
input/original/附件2.xlsx
input/original/附件3.xlsx
input/original/附件4.xlsx

input/templates/result1.xlsx
input/templates/result2.xlsx
input/templates/result3.xlsx
input/templates/result4-2.xlsx
input/templates/result4-3.xlsx
```

允许写入且只允许写入：

```text
A_route/common/01_preprocessing/
```

**不要读取**：

```text
references/
A_route/common/02_recon/
A_route/common/03_eda/
A_route/problem1/
A_route/problem2/
A_route/problem3/
A_route/problem4/
任何 B_route / 其他队伍答案 / 往届解答 / 网络资料
```

如果本地文件名略有不同，只可通过文件内容和 A-0 文档确认映射；不得自行替换数据源。

---

# 1. 本轮边界：允许做什么，禁止做什么

## 1.1 允许的操作

只允许确定性、可逆或可追溯的转换：

- 读取 Excel 原始值、单元格位置、必要的 number format；
- 计算输入文件 SHA-256；
- Excel 日期序号无歧义地转换为标准日期；
- Excel 时间小数无歧义地转换为显示时刻；
- 宽表转长表；
- 创建 `slot_id`；
- 构造唯一键并验证唯一性；
- 统一数值类型，但保留原始值/来源；
- 附件3在严格验证四行块结构后，基于每块 0:00 首行日期派生 6:00/12:00/18:00 行的日期；
- 将 `预报1小时` 至 `预报24小时` 转为 `horizon_hour=1...24`；
- 构造 `issue_datetime` 和 `nominal_target_datetime`；
- 对 result 模板做只读结构审计；
- 计算缺失、非有限、负值、零值、重复、键冲突等数据质量计数；
- 生成可复现脚本、canonical CSV、审计表和 Markdown 报告。

## 1.2 严格禁止

本轮不得：

- 做 EDA；
- 画趋势图、热力图、相关图或任何分析图；
- 计算自相关、日周期、周周期、季节性；
- 计算 MAE/RMSE/Bias 等预测误差；
- 做 D1/W1 naive forecast；
- 将附件3预报与附件2实际 PV 强行对齐；
- 建立任何预测模型；
- 建立 LP / MILP / MPC / 动态规划 / 启发式优化；
- 求购电策略或储能策略；
- 删除异常值、负值或零值；
- 夜间 PV 强制归零；
- 均值/中位数填补；
- 插值或平滑实际测量值；
- 将小时级光伏预报复制/插值为10分钟数据；
- 标准化、归一化、特征筛选；
- 自动去重；
- 把 OOXML `<v>28</v>` 错当作日期列业务字面值，或覆盖附件3语义原始日期值；
- 将 `0:10` 擅自解释为区间起点或区间终点；
- 擅自定义储能90%效率的数学口径；
- 擅自处理 P2/P3/P4 的跨日 SOC；
- 修改任何官方 `result*.xlsx`；
- 写论文或“推荐最终模型”。

**原则：发现问题只做 `记录 + 定位 + 计数 + 报告`。不要为了让数据变得整齐而修数据。**

---

# 2. 实现方法锁定

为了避免工具链发散，本轮使用 Python 完成。

优先使用：

```text
openpyxl：读取 Excel 原始单元格、number_format、工作表结构和模板结构
pandas：仅用于已经明确的表格转换、合并和 CSV 输出
Python 标准库：hashlib / pathlib / datetime / math / json / csv 等
```

不要安装新的包，不要使用 R、MATLAB、数据库或外部服务。

必须生成：

```text
A_route/common/01_preprocessing/scripts/preprocess_c2026.py
A_route/common/01_preprocessing/scripts/validate_preprocessing.py
```

`validate_preprocessing.py` 必须在主脚本运行后独立读取原始输入和生成的 CSV，对核心结构不变量重新检查；不要只打印主脚本内部已有变量。

---

# 3. 第一部分：输入 Manifest 与 Workbook Schema Audit

对 10 个官方输入文件计算 SHA-256，并记录：

```text
file_name
relative_path
sha256
file_size_bytes
sheet_name
used_range_or_dimensions
row_count
column_count
```

输出：

```text
A_route/common/01_preprocessing/tables/data_manifest.csv
A_route/common/01_preprocessing/tables/schema_audit.csv
```

作为本次聊天中官方文件副本的参考 SHA-256（只用于复核，不要因不一致而自动修改数据）：

```text
C题.pdf       2c098f6ae9dd47ae965aebdec3b9facf3de6c173f999783c1012c08fc5fb9d2d
附件1.xlsx    66b87134f5ecccd68184d3539bb1293ef039f9e0fdd955a589b9bfa7f227c377
附件2.xlsx    2e95fd446bfafa0d8c59577b5c2e2ea8b3f1def20dde54a3062556f4da9b4c72
附件3.xlsx    8a61b06c52bd0d639a1cc37c61a7d9f5b75edcbca718f64c1bd3498ec9f9d843
附件4.xlsx    20e9c93aeab5e8e21ae4dd15587f9e190f7408692504c1319598461cd654fe71
result1.xlsx  28360e0974e7d6065394a8aba4e14a86773ae0036cc7d3ea1b211b515b03d688
result2.xlsx  1c26494cfc6d754e0bd9bff7e13e1126a73d2d2da6c5336eb251d89b9a1a1a47
result3.xlsx  c59da470cabd0be23f602c95c8aa9d11ec224a0cdac216b3e1f218e65d006bdc
result4-2.xlsx 1c26494cfc6d754e0bd9bff7e13e1126a73d2d2da6c5336eb251d89b9a1a1a47
result4-3.xlsx c59da470cabd0be23f602c95c8aa9d11ec224a0cdac216b3e1f218e65d006bdc
```

若本地副本 hash 不同：

- 记录 `INPUT_HASH_MISMATCH`；
- 继续做结构核验；
- 不因 hash 不同自动判定数据错误；
- 最终报告必须明确列出。

---

# 4. 第二部分：附件1确定性标准化

附件1预期：

```text
Sheet1
A1:D145
1行表头 + 144条记录
字段：时间 / 电价 / 小区负载 / 光伏发电预测功率
```

实际源数据中前部时间可能以 Excel 小数存储，例如：

```text
1/144 = 0:10
2/144 = 0:20
...
```

最后一个标记为文本：

```text
0:00+1
```

生成：

```text
A_route/common/01_preprocessing/processed/fixed_day_10min.csv
```

字段冻结为：

```text
slot_id
source_file
source_sheet
source_row
source_time_cell
raw_time_value
raw_time_type
raw_time_number_format
time_marker_normalized
price_fixed_yuan_per_kwh
load_kw
pv_forecast_kw
```

要求：

- `slot_id=1...144`，严格按原始列/行顺序；
- 时间小数只转换为显示时刻，例如 `0:10`，不得转成区间；
- `0:00+1` 原样保留为该语义标签；
- 不计算购电量；
- 不计算净负荷；`net_load` 留到 Recon/EDA，如确需用于后续可在 A-2 再派生；
- 原值不删除、不平均。

> 注意：这里刻意不提前计算 `net_load`，避免 Preprocessing 向分析层扩张。P1/P2/P3 的净负荷定义应由后续 Recon/Model Planning 明确使用。

---

# 5. 第三部分：附件2两张全年实际数据表

附件2预期两张 sheet：

```text
小区负载
光伏发电实际功率
```

每张预期：

```text
A1:EO366
1行表头 + 365个日期
A列日期
B:EO 共144个时间位置
```

## 5.1 时间表头标准化

为两张 sheet 分别读取 144 个时间表头，保留：

```text
slot_id
source_sheet
source_column
source_cell
raw_time_value
raw_time_type
raw_time_number_format
time_marker_normalized
```

生成：

```text
A_route/common/01_preprocessing/tables/time_marker_map_attachment2.csv
```

必须逐 slot 比较两张 sheet 的 normalized 时间标记是否完全一致。

## 5.2 日期标准化

读取 A2:A366：

- 保留原 Excel storage value；
- 保留 number format；
- 无歧义解析为 ISO 日期；
- 检查日期是否从 `2025-01-01` 到 `2025-12-31` 连续覆盖365天；
- 不允许通过“补缺日期”修复。

## 5.3 宽表转长表

分别生成：

```text
A_route/common/01_preprocessing/processed/year_load_10min.csv
A_route/common/01_preprocessing/processed/year_pv_actual_10min.csv
```

字段：

```text
date
slot_id
time_marker_normalized
value_kw
source_file
source_sheet
source_row
source_column
source_cell
raw_date_value
raw_time_value
raw_value
```

其中在各自文件中将 `value_kw` 重命名为：

```text
year_load_10min.csv      -> load_kw
year_pv_actual_10min.csv -> pv_actual_kw
```

预期各有：

```text
365 × 144 = 52,560 rows
```

## 5.4 确定性合并

只有同时满足：

- 日期集合一致；
- 144 个 slot 一致；
- `(date, slot_id)` 在两表中均唯一；
- 每个 key 两边都有值行；

才生成：

```text
A_route/common/01_preprocessing/processed/year_actual_10min.csv
```

字段：

```text
date
slot_id
time_marker_normalized
load_kw
pv_actual_kw
load_source_cell
pv_source_cell
```

预期：

```text
52,560 rows
```

如果 key 不完整或不唯一，不要 inner join 后丢行；必须阻塞该合并并记录问题。

---

# 6. 第四部分：附件3四次/日光伏预报结构专项处理

这是 A-1 的最高风险点之一，对应 `OI-02`。

附件3预期：

```text
Sheet1
A1:Z1461
1行表头 + 1460条发布记录
日期 / 预报时刻 / 预报1小时 ... 预报24小时
```

## 6.1 先审计原始四行块，后派生日期

复核已确认：6:00、12:00、18:00 行日期单元格在工作簿语义层面解析为空字符串。低层 OOXML 中这些单元格为 shared-string 类型，`<v>28</v>` 中的 `28` 是共享字符串索引，索引 28 解析为空字符串；因此绝不能将 `28` 当作业务字面值。

必须先逐行验证整个文件是否严格满足 365 个四行块：

```text
第1行：日期为可解析日期，issue_clock = 0:00
第2行：日期语义值为空，issue_clock = 6:00
第3行：日期语义值为空，issue_clock = 12:00
第4行：日期语义值为空，issue_clock = 18:00
```

并验证每个四行块首行日期：

```text
2025-01-01
2025-01-02
...
2025-12-31
```

严格连续、唯一。

若脚本读取 OOXML 底层信息，应额外审计后3行是否具有一致的 shared-string 空白编码，并保留 `<v>28</v>` 与 shared-string-resolution 结果；该低层编码只作为可追溯证据，不作为业务值。

生成：

```text
A_route/common/01_preprocessing/tables/attachment3_block_audit.csv
```

至少包含：

```text
block_id
source_rows
anchor_date_raw
anchor_date_parsed
issue_clock_sequence
trailing_date_raw_values
trailing_xml_raw_v_values
trailing_shared_string_resolved_values
structure_ok
issue_detail
```

**只要任意一个四行块结构不符合上述模式：**

- 不允许自动 forward-fill；
- 不允许猜日期；
- 该部分状态必须为 `BLOCKED_ATTACHMENT3_DATE_DERIVATION`；
- 保留原始审计结果并停止附件3 canonical date 派生。

若 365 个块全部通过，则“从同块 0:00 首行日期派生后3行日期”属于确定性结构恢复，允许继续。

## 6.2 结构通过后才能派生 issue_date

通过后，对每块后3行派生：

```text
issue_date = anchor 0:00 行的日期
date_derivation = original_0h_date / from_verified_0h_block
```

原始/审计字段必须同时保存：

```text
date_raw
date_derivation
```

如已读取 OOXML 底层信息，应同时保留：

```text
date_ooxml_type
date_ooxml_v
date_shared_string_resolved
```

语义原始值不得被覆盖；`<v>28</v>` 仅作为底层 shared-string 索引证据保存。

## 6.3 宽转长

生成：

```text
A_route/common/01_preprocessing/processed/pv_forecast_hourly_long.csv
```

字段冻结为：

```text
issue_date
issue_clock
issue_datetime
horizon_hour
nominal_target_datetime
pv_forecast_kw

date_raw
date_derivation
source_file
source_sheet
source_row
source_forecast_column
source_cell
raw_forecast_value
```

定义：

```text
horizon_hour = 1,...,24
nominal_target_datetime = issue_datetime + horizon_hour hours
```

预期行数：

```text
1460 × 24 = 35,040 rows
```

允许 `nominal_target_datetime` 跨越当日，甚至跨到 `2026-01-01`；不得因为超出附件2实际值覆盖范围而删除。

本轮 **禁止** 判断该预测值表示“整点瞬时值”还是“一小时平均值”，也禁止和10分钟实际 PV 计算误差。

---

# 7. 第五部分：附件4动态价格确定性标准化

附件4预期：

```text
Sheet1
A1:EO366
365个日期 × 144个时间位置
单位：元/kWh
```

处理方法与附件2宽转长保持一致。

生成：

```text
A_route/common/01_preprocessing/processed/dynamic_price_10min.csv
```

字段：

```text
date
slot_id
time_marker_normalized
price_yuan_per_kwh
source_file
source_sheet
source_row
source_column
source_cell
raw_date_value
raw_time_value
raw_value
```

预期：

```text
52,560 rows
```

日期必须核验为 `2025-01-01` 至 `2025-12-31` 连续365天。

---

# 8. 第六部分：跨附件时间标记一致性审计

生成：

```text
A_route/common/01_preprocessing/tables/time_marker_crosswalk.csv
```

逐 `slot_id=1...144` 放置：

```text
attachment1_time_marker
attachment2_load_time_marker
attachment2_pv_time_marker
attachment4_time_marker
all_sources_same_marker
```

只比较“原始位置/显示时刻的一致性”。

不要把这些 marker 转成 interval start/end。

特别报告：

- 第1个 marker；
- 第143个 marker；
- 第144个 marker；
- `0:00+1` 的位置；
- 是否四个数据源完全一致。

---

# 9. 第七部分：结果模板只读审计

不得修改模板。

生成：

```text
A_route/common/01_preprocessing/tables/template_contract.csv
A_route/common/01_preprocessing/reports/TEMPLATE_AUDIT.md
```

对每个 workbook/sheet 记录：

```text
workbook
sheet
used_range
rows
cols
first_date_or_time_label
last_date_or_time_label
main_fields
ellipsis_present
notes
```

必须实际读取模板，不得仅抄 A-0 文档。

尤其核验并原样报告这些时间标签，不要“纠正”：

### result1.xlsx

`计划购电量`：

```text
首段：0:10-0:20
...
倒数第二段：23:50-0:00+1
末段：0:00+1-0:10+1
```

### result2.xlsx / result3.xlsx / result4-2.xlsx / result4-3.xlsx

计划/调整购电表需要实际检查首尾标签。

本次官方模板副本中可观察到末列标签为：

```text
0:00-0:10+1
```

它与 result1 的：

```text
0:00+1-0:10+1
```

**并不完全一致。**

把这个差异记录为：

```text
TEMPLATE_TIME_LABEL_INCONSISTENCY
```

不要在 Preprocessing 中判断哪个是正确版本，也不要修改模板。

另外核验：

- result2/result3/result4-2/result4-3 的计划购电日期从 `2025-02-01` 到 `2025-12-31`；
- 应有334个日期数据行；
- `充放电量` / `紧急购电量` 中存在示例行和 `⁝`；
- result3/result4-3 有 `调整购电量` sheet。

---

# 10. 第八部分：数据质量审计（只做质量，不做 EDA）

对 canonical 数值变量做机械质量检查：

```text
row_count
missing_count
blank_string_count
non_numeric_count
nan_count
positive_inf_count
negative_inf_count
negative_count
zero_count
min
max
```

变量至少包括：

```text
附件1：price_fixed_yuan_per_kwh, load_kw, pv_forecast_kw
附件2：load_kw, pv_actual_kw
附件3：pv_forecast_kw
附件4：price_yuan_per_kwh
```

这里的 `min/max` 仅是数据质量审计，不做统计解释。

生成：

```text
A_route/common/01_preprocessing/tables/numeric_quality_audit.csv
```

对于逐单元格异常，生成：

```text
A_route/common/01_preprocessing/tables/data_issues.csv
```

字段至少：

```text
issue_id
severity
source_file
source_sheet
source_cell
field
raw_value
issue_type
detail
handling_status
```

`handling_status` 默认应是：

```text
retained_not_modified
```

除非是确定性的日期/时间派生，并且原始值仍被保留。

---

# 11. 第九部分：主键、覆盖率和不变量验证

主脚本和独立 validator 都必须验证：

## 附件1

```text
144 rows
slot_id unique
slot_id exactly 1..144
```

## 附件2

```text
load:      52,560 rows
pv actual: 52,560 rows
(date, slot_id) unique in each
365 dates
144 slots per date
same date set
same slot/time-marker map
```

若合并表生成：

```text
year_actual_10min = 52,560 rows
no key lost
no key duplicated
```

## 附件3

```text
1460 issue rows
365 verified four-row blocks
issue clocks exactly {0:00,6:00,12:00,18:00} per date
35,040 long forecast rows
(issue_datetime, horizon_hour) unique
horizon exactly 1..24 per issue
```

## 附件4

```text
52,560 rows
365 dates
144 slots/date
(date, slot_id) unique
```

## 原始文件保护

主脚本运行前后重新计算所有 `input/` 文件 hash，确认没有被修改。

---

# 12. 不要在本阶段解决的 Open Issues

本轮只允许真正关闭：

```text
OI-02 附件3共享字符串空白编码及四行块派生规则
```

前提是全表结构验证成功。

以下问题只能保留，不得在本轮解决：

```text
OI-01 10分钟marker对应哪个实际交易区间
OI-03 90%充放电效率口径
OI-04 P2/P3/P4跨日SOC
OI-05 P2 0:00可用信息集
OI-06 小时预测到10分钟调度映射
OI-07 P3调整购电费用精确结算
OI-08 弃光/反送电
OI-09 同时充放电
OI-10 外网购电上限
OI-11 P3可调整时间范围
OI-12 P4实时电价未来可知性
OI-13 附件3forecast与附件2actual精确对齐
OI-14~OI-15 最终结果模板写入规则
OI-16 外部信息使用
```

如果脚本运行中发现新的非确定性语义问题：

- 新增到 `data_issues.csv`；
- 在 `PREPROCESSING_AUDIT.md` 的 Open Issues 部分单独列出；
- 不自行解释。

---

# 13. 最终必须生成的文件

目录结构：

```text
A_route/common/01_preprocessing/
├─ tasks/
│  └─ PREPROCESSING_CODEX_TASK.md        # 本任务文件，保留原样
├─ scripts/
│  ├─ preprocess_c2026.py
│  └─ validate_preprocessing.py
├─ processed/
│  ├─ fixed_day_10min.csv
│  ├─ year_load_10min.csv
│  ├─ year_pv_actual_10min.csv
│  ├─ year_actual_10min.csv              # 仅在key验证通过后生成
│  ├─ pv_forecast_hourly_long.csv
│  └─ dynamic_price_10min.csv
├─ tables/
│  ├─ data_manifest.csv
│  ├─ schema_audit.csv
│  ├─ time_marker_map_attachment2.csv
│  ├─ time_marker_crosswalk.csv
│  ├─ attachment3_block_audit.csv
│  ├─ template_contract.csv
│  ├─ numeric_quality_audit.csv
│  ├─ data_issues.csv
│  └─ validation_checks.csv
└─ reports/
   ├─ PREPROCESSING_AUDIT.md
   ├─ TIME_STRUCTURE_AUDIT.md
   ├─ TEMPLATE_AUDIT.md
   ├─ RUN_INFO.md
   └─ PREPROCESSING_GATE.md
```

`figures/` 本轮保持为空；不要生成图片。

---

# 14. 报告内容要求

## PREPROCESSING_AUDIT.md

只回答：

1. 实际读取了哪些文件/sheet；
2. 原始规模；
3. 做了哪些确定性转换；
4. 每个 canonical 表行数和主键；
5. 缺失/非有限/负值/重复是否存在；
6. 附件3四行块是否100%通过；
7. 有哪些问题被保留而没有修改；
8. 是否发生任何记录删除/填补/插值：必须明确回答。

不要写数据规律或模型建议。

## TIME_STRUCTURE_AUDIT.md

只回答：

- 附件1/2/4的144个时间 marker 是否一致；
- 原始 marker 的首尾和 `0:00+1` 位置；
- 附件3 issue time 与 horizon 结构；
- nominal target datetime 的构造方式；
- OI-01/OI-13 为什么仍未在本阶段解决。

## RUN_INFO.md

记录：

```text
run_datetime
working_directory
python_executable
python_version
package_versions
commands_executed
input_sha256
output_file_list
```

---

# 15. PREPROCESSING_GATE：唯一允许的最终状态

`PREPROCESSING_GATE.md` 最后一行必须且只能是以下之一：

```text
PASS_PREPROCESSING
PASS_PREPROCESSING_WITH_OPEN_ISSUES
BLOCKED_PREPROCESSING
```

## PASS_PREPROCESSING

仅当：

- 所有预期输入结构成立；
- 附件3全部365个四行块验证通过；
- canonical 数据均生成；
- 所有关键主键唯一；
- 无记录静默丢失；
- input hash 前后不变；
- 只有后续阶段本就应解决的 Open Issues。

## PASS_PREPROCESSING_WITH_OPEN_ISSUES

用于：

- canonical 数据仍然确定且可追溯；
- 但存在不阻塞 A-2 Recon 的模板/语义问题；
- 问题已明确记录，未静默猜测。

## BLOCKED_PREPROCESSING

任一情况成立即阻塞：

- 附件3任意四行块不满足“首行有效日期+0:00，后3行语义空白+6/12/18”的确定性结构，因而无法可靠派生日期；
- 关键日期缺失/重复；
- 365×144结构不成立且无法确定性解释；
- 时间表头跨 sheet 无法一一对应；
- canonical key 不唯一；
- 宽转长出现记录丢失；
- 输入文件被脚本修改；
- 发现必须依赖主观假设才能继续的数据结构问题。

阻塞时不要进入 Recon，更不要尝试“修到能跑”。

---

# 16. 执行顺序和停止规则

严格按照：

```text
1. 读取A-0规则
2. 输入hash/schema审计
3. 附件1处理
4. 附件2处理 + key核验
5. 附件3四行块审计
6. 若附件3通过，再做long table
7. 附件4处理
8. 跨附件time-marker crosswalk
9. 模板只读审计
10. 数值质量审计
11. 主脚本自检
12. 运行独立validate_preprocessing.py
13. 写reports
14. 写PREPROCESSING_GATE
15. 立即停止
```

不得在完成后“顺便开始 Recon/EDA”。

终端最终只打印简短摘要：

```text
PREPROCESSING STATUS: <one of three gate statuses>
Canonical outputs: ...
Blocking issues: ...
Open non-blocking issues: ...
See: A_route/common/01_preprocessing/reports/PREPROCESSING_GATE.md
```

**完成后立即停止，等待人工/GPT复核。**
