# 2026 CUMCM C题｜A-0 Data Requirements

**阶段**：A-0 Problem Formulation 的数据合同  
**用途**：规定 A-1 Preprocessing 必须保留、核验和产出的数据对象；不等同于 Preprocessing 执行任务书。  
**原则**：先保证官方数据可追溯和时间语义不被破坏，再允许进入 Recon / EDA。

---

## 1. 官方数据源清单

建议项目路径：

```text
input/
├─ original/
│  ├─ C题.pdf
│  ├─ 附件1.xlsx
│  ├─ 附件2.xlsx
│  ├─ 附件3.xlsx
│  └─ 附件4.xlsx
└─ templates/
   ├─ result1.xlsx
   ├─ result2.xlsx
   ├─ result3.xlsx
   ├─ result4-2.xlsx
   └─ result4-3.xlsx
```

所有 `input/` 文件只读。A_route 的任何脚本不得覆盖原文件或原模板。

---

## 2. 已核对到的文件结构

以下是对官方附件和模板的结构性核对结果，用于后续 Preprocessing 自检；Preprocessing 仍必须独立复算，不能盲信本文件。

### 2.1 附件1

- 工作表：`Sheet1`；
- 使用区域：A1:D145；
- 1 行表头 + 144 条日内记录；
- 字段：
  - 时间；
  - 电价；
  - 小区负载；
  - 光伏发电预测功率；
- 时间标记从 `0:10` 开始，末尾为 `0:00+1`；
- 电价单位：元/kWh；
- 负载、光伏功率单位：kW。

### 2.2 附件2

两个工作表：

- `小区负载`；
- `光伏发电实际功率`。

两表均为：

- 1 行时间表头 + 365 个日期；
- A列为日期；
- 后续 144 列为日内时间位置；
- 时间表头同样从 `0:10` 延伸至 `0:00+1`；
- 单位均为 kW。

Preprocessing 必须验证两张表：

- 日期集合完全一致；
- 144 个时间位置完全一致；
- `(date, slot)` 可一一对应；
- 不允许因“看起来顺序一样”而直接按单元格位置静默拼接。

### 2.3 附件3

- 工作表：`Sheet1`；
- 使用区域：A1:Z1461；
- 1 行表头 + 1460 条预报发布记录；
- 字段：
  - 日期；
  - 预报时刻；
  - `预报1小时` … `预报24小时`；
- 每天理论上对应 0:00、6:00、12:00、18:00 四个发布时间。

**已复核的重要原始格式现象**：

0:00 行的日期列为正常日期字符串（如 `2025-1-1`）；同一日 6:00、12:00、18:00 行的日期单元格在工作簿语义层面解析为空字符串 `""`。低层 OOXML 中这些单元格具有 `t="s"` 且 `<v>28</v>`，其中 `28` 是共享字符串表索引；共享字符串索引 28 实际解析为空字符串，因此 `28` **不是单元格的业务值**。

因此 A-1 可以进行确定性的块内日期派生，但必须先验证完整结构：

1. 保留语义层面的原始日期值，例如 `date_raw_resolved`；
2. 如脚本读取 OOXML 底层信息，同时保留 `date_ooxml_type`、`date_ooxml_v`、`date_shared_string_resolved` 等审计证据；
3. 全表验证是否严格形成 365 个四行块：
   - 第1行：可解析日期 + `0:00`；
   - 第2—4行：日期语义值为空 + `6:00/12:00/18:00`；
4. 验证 365 个块首行日期从 `2025-01-01` 到 `2025-12-31` 连续且唯一；
5. 只有上述结构全部通过，才可基于同块 0:00 行日期派生后3行 `issue_date_derived`；
6. 派生值必须与原始值并存，并记录 `date_derivation = original_0h_date / from_verified_0h_block`；
7. 任一块不符合结构时，Preprocessing 阻塞，而不是猜测或静默填充。

附件3预报单位为 kW。

### 2.4 附件4

- 工作表：`Sheet1`；
- 1 行时间表头 + 365 个日期；
- A列日期；
- 后续 144 个日内时间位置；
- 时间表头从 `0:10` 至 `0:00+1`；
- 单位：元/kWh。

---

## 3. 结果模板合同

### 3.1 result1.xlsx

`计划购电量`：

- 144 个10分钟时间段；
- 首段为 `0:10-0:20`；
- 末段为 `0:00+1-0:10+1`。

`充放电量`：

- 六个4小时区间；
- 另有 0:00、24:00 储电量位置。

### 3.2 result2.xlsx / result4-2.xlsx

`计划购电量`：

- 日期从 2025-02-01 至 2025-12-31；
- 每日144个10分钟计划购电量；
- 另有全天购电量、全天购电费字段。

另含：

- `充放电量`；
- `紧急购电量`。

### 3.3 result3.xlsx / result4-3.xlsx

除上述结构外，增加：

- `调整购电量` 工作表。

### 3.4 模板中的省略结构

`充放电量` 与 `紧急购电量` 工作表并未简单预铺全年所有记录，而包含部分示例日期和 `⁝` 省略标记。

当前只记录这一事实。A-1 Preprocessing 只读审计模板，不修改模板；正式写结果时如何扩展行数属于后续 Output Contract / Result Writer 的任务。

---

## 4. A-1 必须保存的原始追溯字段

所有标准化数据对象至少应能够追溯到：

```text
source_file
source_sheet
source_row / source_cell_or_column
raw_date
raw_time_marker
raw_value
```

对于宽表转长表，不要求每行重复所有 Excel 元数据，但必须保留足够的 `source_*` 字段或建立映射表，使任何标准化值都能找到原始单元格位置。

---

## 5. A-1 允许进行的确定性转换

允许：

- Excel 日期序号 → 标准日期；
- Excel 时间小数 → 可读时间标记；
- 宽表 → 长表；
- 生成 `slot_id`；
- 建立明确的一一键；
- 统一数值类型；
- 将 `预报1小时`…`预报24小时` 转成长表中的 `horizon_hour=1…24`；
- 在附件3四行块完全验证后，由该块的 0:00 日期派生 6/12/18 行的 `issue_date_derived`；
- 计算 `nominal_issue_datetime` 和 `nominal_target_datetime = issue_datetime + horizon_hour`，但不得据此直接和10分钟实际值进行无审计的对齐；
- 为确定性的单位转换创建新字段，但不得覆盖原单位字段。

---

## 6. A-1 明确禁止的“清洗”

不得：

- 删除异常值；
- 删除负值；
- 把夜间 PV 自动改为0；
- 均值/中位数填补；
- 插值填补物理测量值；
- 平滑；
- Winsorize；
- 标准化/归一化；
- 特征选择；
- 根据模型表现反向清洗数据；
- 将附件3的语义空白日期在未验证四行块结构前直接 forward-fill；
- 将小时预报自动复制/插值到10分钟；
- 修改任何 result 模板；
- 拟合预测或优化模型。

发现异常时只做：**记录、计数、定位、报告**。

---

## 7. 建议的 canonical 数据对象

以下是 A-1 应建立的数据层；具体文件名可在 PREPROCESSING_CODEX_TASK 中冻结。

### 7.1 单日固定场景

`fixed_day_10min`

建议核心字段：

```text
slot_id
raw_time_marker
time_marker_normalized
price_fixed_yuan_per_kwh
load_kw
pv_forecast_kw
source_*
```

### 7.2 全年实际负荷

`year_load_10min`

```text
date
slot_id
raw_time_marker
time_marker_normalized
load_kw
source_*
```

### 7.3 全年实际光伏

`year_pv_actual_10min`

```text
date
slot_id
raw_time_marker
time_marker_normalized
pv_actual_kw
source_*
```

只有在 `(date, slot_id)` 完整核验一致后，才允许建立一个方便 Recon / EDA 的确定性合并表 `year_actual_10min`。

### 7.4 全年光伏预报

`pv_forecast_hourly_long`

```text
date_raw
issue_date_derived
date_derivation
issue_clock
issue_datetime
horizon_hour
nominal_target_datetime
pv_forecast_kw
source_*
```

必须保留日期单元格的语义原始值；如读取 OOXML 底层信息，还应保留 `<v>28</v>` 及其共享字符串解析为空的审计证据。

### 7.5 全年动态电价

`dynamic_price_10min`

```text
date
slot_id
raw_time_marker
time_marker_normalized
price_yuan_per_kwh
source_*
```

---

## 8. Preprocessing 必须完成的结构验证

A-1 至少应验证：

1. 附件1恰有144条记录；
2. 附件2两个sheet均为365天 × 144时间位置；
3. 附件2两表日期和slot键完全一致；
4. 附件3有1460条发布记录；
5. 每个日期块严格对应 0/6/12/18 四个发布时间；
6. 每个发布记录恰有24个 horizon；
7. 附件3原始日期列的异常编码模式是否全表一致；
8. 附件4为365天 × 144时间位置；
9. 附件1、2、4 的144个原始时间标记能否建立一致映射；
10. result1 / result2 / result3 / result4 模板中的时间段数量、首尾标签和官方正文要求是否一致；
11. 所有核心数值字段是否存在缺失、非数值、无限值、负值或重复键；
12. 任何异常均不得静默修复。

---

## 9. Preprocessing 不负责回答的问题

以下问题即使 A-1 看到了数据，也不得回答：

- 日周期强不强；
- 工作日/周末有没有差异；
- 哪个预测方法最好；
- 是否应该用昨天同一时刻；
- 电价和净负荷是否相关；
- 日内新预报是否显著更准；
- 电池是否有明显套利价值；
- 最终采用哪种优化模型。

这些分别属于 A-2 Recon、A-3 EDA 或 A-4 Model Planning。

---

## 10. 向 Recon / EDA 的数据交付条件

只有当 A-1 满足以下条件才允许进入 A-2：

```text
PREPROCESSING_PASS
```

最低条件：

- 原文件hash已记录；
- canonical表可重复生成；
- 关键主键唯一；
- 无静默删行；
- 无统计型填补；
- 附件3日期异常已被完整审计；
- 144-slot 时间结构被保存且没有未经确认的区间语义重命名；
- 所有结构问题进入 issue list。

若时间键或附件3块结构无法可靠构建，应返回：

```text
PREPROCESSING_BLOCKED
```

而不是继续进入 EDA。

