# P3 A-6 冻结前阻塞记录

Gate：`BLOCKED_P3_CANDIDATE_FREEZE`。本轮停在 A-6，尚未完成 Candidate 冻结，不进入 A-7 或 Final。

## 已确认的单一阻塞

`02_batch_run/scripts/node_modules` 是目录联接，目标为：

`C:/Users/JINPU/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules`

使用指定解释器 `D:/Anaconda3/python.exe`，只读执行 `Path.rglob` 有界遍历及原冻结脚本的 `safe_join` 路径函数，确认：

- 枚举能到达 `02_batch_run/scripts/node_modules/.modules.yaml`，且原 `excluded` 函数返回 `False`。
- 该路径是文件，`is_symlink()` 返回 `False`；其父目录 `is_junction()` 返回 `True`。
- 原 `safe_join` 对同一路径抛出 `FreezeError: Unsafe source path: A_route/problem3/02_batch_run/scripts/node_modules/.modules.yaml`。

原脚本第 97 行的 `inventory_tree` 会纳入此路径；第 329 行的来源复核和第 280 行的 manifest 核验又要求解析后的路径位于项目内，两者冲突。合同现有排除项仅为 `__pycache__`、`*.pyc`、`*.tmp`、`*.temp`、`*.part`，没有授权排除此目录联接。

本轮没有执行完整 freeze 主入口，没有创建成功 manifest，没有删除或修改联接，没有扫描或签名完整外部依赖库。路径诊断只导入了无主入口副作用的标准库冻结模块，未导入或执行 A-5 生产模块。

## 结果与核验状态

唯一候选仍为 `P3_MAIN_MEAN_ROLLOUT_061218`。A-5 本地报告记载总费用为 13,741,771.83363791 元，12 政策各 334 天、MAIN 48,096 槽；这些是本轮读取的既有结论，不冒充已完成 A-6 有限算术复核。

实际只读计算的 `result3.xlsx` SHA-256 为：

`4d63a8e740d872c71994d75bdf42865fc3e595f75968ced03e3c968870d8ffa8`

原 Candidate 冻结脚本与合同的实际指纹仍匹配交付记录，详见 `FREEZE_FAILURE.json`。没有执行 142 文件全量指纹核验或源文件全集前后复核；本地冻结文件数为 0，不能称为已完成冻结。

24 行指定时段的工作簿逐格核对尚未执行，未生成派生表。格式修复目录、实际修复脚本、只读验证脚本、修正检查记录和闭合记录已读取，未执行修复；本轮完整恢复链指纹核验及冻结未完成，不预填交接 PASS 标志。

新增拟合、LP、政策回放、工作簿导出和工作簿复制均为 0。本轮未修改任何业务源文件，未修改 `CURRENT_STATE.md`。14 项既有边界说明全部保留；新增 blocking 为 1。

## 待授权的最小修复

建议仅修复 Candidate 的文件枚举边界：明确登记上述唯一外部依赖目录联接及目标，不向其中递归；其余 A-5 真实文件、恢复证据、142 文件参考清单、受保护输入及原数学检查全部保留。该动作会改变现有冻结排除范围，因此本轮未擅自修改脚本或合同。

不得以删除 A-5 联接、放宽 `safe_join`、把外部运行库当业务源或伪造成功 manifest 代替该授权。用户确认后才能修复并继续原 A-6 检查。

本轮使用 `data-analytics:validate-data` 的来源与范围核验，以及 `spreadsheets:Spreadsheets` 的工作簿只读约束；它们用于保留未完成标记和原工作簿，不构成新增 A-7 Review。

冻结 manifest：未生成。`READY_FOR_P3_REVIEW=false`。
