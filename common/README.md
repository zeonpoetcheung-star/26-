# 2026 C题｜A_route 当前进度

当前状态：**Common 阶段已全部完成并冻结，下一步进入 Problem 1｜A-4 Model Planning。**

---

## Common 阶段

### ✅ A-0 Problem Formulation
**状态：已完成**

主要工作：
- 题目整体拆解
- 明确四个 Problem 的目标与依赖关系
- 明确各问输入、输出、决策对象
- 梳理数据附件与模板关系
- 建立开放问题清单 `OPEN_ISSUES`
- 明确信息边界与后续需要核验的问题

↓

### ✅ A-1 Deterministic Preprocessing
**状态：已完成并通过 Gate**

主要工作：
- 原始数据审计
- 时间、日期与字段解析
- canonical 数据生成
- 跨附件数据结构整理
- 附件3四行块结构恢复与验证
- result 模板结构审计
- 独立 validator

最终状态：

`PASS_PREPROCESSING_WITH_OPEN_ISSUES`

↓

### ✅ A-2 Recon
**状态：已完成并通过 Gate**

主要工作：
- 跨附件主键与 join 关系核验
- 10 分钟时间语义冲突分析
- forecast issue / horizon / target 时间网格核验
- 决策时信息可得性分析
- 储能参数、单位与状态时间轴核验
- 输出模板与正式结果时间范围核验

当前保留：
- `OI-01`：10 分钟 marker 的 H-END / H-START 语义冲突
- `OI-13`：小时级官方光伏预报与 10 分钟实际值的物理语义对齐问题

最终状态：

`PASS_RECON_WITH_OPEN_ISSUES`

↓

### ✅ A-3 EDA
**状态：已完成并通过 Gate**

主要工作：
- 负荷 / 光伏 / 净负荷 / 电价描述统计
- 日内、月份、星期结构分析
- 时间依赖分析
- D1 / W1 predictability probe
- official PV forecast revision 分析
- 动态电价结构分析
- 电池与系统负荷 / 能量量级分析
- 8 张内部诊断图
- 独立 validator

最终状态：

`PASS_EDA_WITH_OPEN_ISSUES`

↓

## ✅ COMMON_FROZEN

`A_route/common/` 当前已经冻结。

Common 现在作为 Problem 1–4 共用的上游数据与分析基础。

后续各 Problem：

- 可以读取 Common；
- 默认不得修改 Common；
- 如果发现真正的上游错误，需要明确重新打开对应阶段；
- 不允许为了方便后续模型而静默修改 preprocessing / Recon / EDA 结果。

---

# Problem 1

### ⬜ A-4 Model Planning
**状态：未开始**

下一步：

由 GPT + 人工基于原题与 Common evidence 确定：

- 数学对象
- 主模型
- 必要 baseline
- 必要敏感性分析
- 验证标准
- 停止规则

↓

### ⬜ A-5 Batch Run
**状态：未开始**

由 Codex 一次性执行：

- 正式模型
- baseline
- 必要敏感性
- validation
- 结果表

↓

### ⬜ A-6 Candidate
**状态：未开始**

由 GPT + 人工：

- 对比 Batch Run 结果
- 选定 Candidate
- 停止开放式模型搜索

↓

### ⬜ A-7 Review
**状态：未开始**

主要包括：

- 人工 crosscheck
- Claude Code 技术审查
- 组员 / OpenCode 独立交叉检查

只有发现 `CRITICAL_DEFECT` 才重新打开模型。

↓

### ⬜ A-8 Final
**状态：未开始**

最终完成：

- 冻结模型
- 冻结代码
- 冻结关键结果
- 冻结论文结论
- 生成 `paper_handoff`
- GitHub 提交
- 交给论文手继续整合

---

# 当前总流程

```text
✅ A-0 Problem Formulation
        ↓
✅ A-1 Deterministic Preprocessing
        ↓
✅ A-2 Recon
        ↓
✅ A-3 EDA
        ↓
✅ COMMON_FROZEN
        ↓
────────────────────────
        ↓
⬜ Problem 1｜A-4 Model Planning
        ↓
⬜ A-5 Batch Run
        ↓
⬜ A-6 Candidate
        ↓
⬜ A-7 Review
        ↓
⬜ A-8 Final
        ↓
⬜ paper_handoff
        ↓
⬜ GitHub push / 论文整合
