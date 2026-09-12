# Codex｜P3 A-4 Model Plan Check 与冻结

## 1. 本轮授权

用户已进入正式建模，但本轮到A-4为止。请读取当前目录README、P3_MODEL_PLAN、P3_DESIGN_BASIS、P3_VALIDATION_PLAN和contracts/P3_MODEL_SPEC.json。参考脚本是人工小例模型核，不是年度Batch入口。

不要问是否执行：本任务已授权执行。仅当必要输入确实缺失、哈希冲突或公式存在实质错误时阻塞，并给具体原因。

## 2. 源和路径

工作根目录优先由当前仓库定位，不要求目录名大小写重新整理。现有结构：
`A_route/problem3/00_semantic_audit/`、`00_information_audit/`、`01_model_plan/`。
必须读取语义contracts、P3-0 local_verification Gate与checks，P3-1主报告/Gate及run manifest。按其记录定位三个Common表、官方模板和P2预热/冻结身份；路径差异可解析并记录，不修改这些文件。

只读查验P2 `p2_warmup_actual.csv`的字段、唯一策略和1月连续时间/SOC终态；不重跑P2模型。核验结果与共享初始化约定一致。

不读取外部同题稿、社交平台答案、B_route或GitHub上其他队的代码。文献仅是设计依据页列出的学术方法背景，不据此变更合同。

## 3. 环境

沿用已可用的 `D:\Anaconda3\python.exe`，优先 PowerShell：
```powershell
& "D:\Anaconda3\python.exe" -B -s -c "import sys,numpy,scipy; print(sys.executable); print(numpy.__version__,scipy.__version__)"
```
不安装包、不升级、不要新建环境。此轮不需要LightGBM、torch或商业求解器。如果导入失败，报告实测输出并停止，不反复猜解释器。

## 4. 需要完成

A. 核对P3-0合同逐条被MODEL_SPEC继承，包括调整表EQ为含紧急费最终日账、主结算final-vs-g0、发行边界、小时映射、次日不签订等。

B. 检查负荷回归和历史残差时间链：使用此前完整日估计αβ，使用原发行版本的完整成熟24h残差；无审计全年统计作为训练参数；28条不足时冷启动定义清楚。只读检查数据结构与能否满足日期范围，不正式训练。

C. 检查数学表达：普通费线性化、缺额方向、单位、共享储能、终端价值、去循环证明、KEEP限制、历史情景因果回放评分和实际账单分离。不要将名义LP短缺代理与actual emergency混写。

D. 运行：
```powershell
& "D:\Anaconda3\python.exe" -B -s "A_route\problem3\01_model_plan\scripts\check_p3_model_math.py" "A_route\problem3\01_model_plan\local_check\model_math_selftest.json"
```
相对路径以项目根为准，找不到时用已定位的绝对路径。

E. 按P3_VALIDATION_PLAN A节用自己独立的少量代码核对至少6组逻辑，可额外最多12次人工微型LP；不使用真实全年目标进行试算，不求“第一天看看是否便宜”。即使原型可接受，独立报告仍要写出共享轨迹/假想延续/有限历史风险的近似边界。

F. 确认11条政策矩阵和下一阶段输出schema可落地；当前只写数据字典和函数接口建议，不建立正式年度结果。标清哪些新设计的效果未验证。

## 5. 允许修改与禁止项

只允许新增 `01_model_plan/local_check/` 产物。如果发现本包笔误或代码实现bug，先记录文件/行号/证据；可以在local_check放修复补丁用于小例，但不得静默修改数学决策、参数、源合同或本包冻结文件。实质设计冲突输出BLOCKED并等待裁决。

禁止训练、全文外部答案检索、实日/全年策略回放、A5预算、result3导出、图、To B/To C、CURRENT_STATE修改、P1/P2/Common/00目录改写。

## 6. 输出

仅生成：
- `local_check/P3_MODEL_PLAN_CHECK.md`：来源、语义、预测链、LP/回放、单因素矩阵、近似与问题。
- `local_check/model_math_selftest.json`：所附小例在用户环境的结果。
- `local_check/independent_checks.json`：独立小例结果与实际LP调用数。
- `local_check/P3_MODEL_PLAN_FREEZE_MANIFEST.json`：本包及所依赖关键合同/输入身份的路径、size、sha256；不要复制全部数据。
- `local_check/P3_MODEL_PLAN_GATE.md`。

通过：`PASS_P3_MODEL_PLAN_WITH_OPEN_ISSUES`，附 `READY_FOR_P3_A5_AFTER_EXPLICIT_AUTHORIZATION=true`。
阻塞：`BLOCKED_P3_MODEL_PLAN`，附具体冲突。
不得预填PASS，不要求小例恰为多少条才合格；数量如实统计。

## 7. 聊天汇报

只报Gate、语义一致性、数学小例/独立小例PASS/FAIL、LP小例调用数、正式训练/回放/工作簿均为0、blocking/open边界、模型主名称与两个报告路径。
完成后停止，不自动进入02_batch_run。
