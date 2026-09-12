# P3-0 Semantic Audit

这是第三问的前置语义审计，不是最终模型或结果。将本文件夹内容放入 `A_route/problem3/00_semantic_audit/`。

先读 `P3_SEMANTIC_AUDIT.md`：其中明确区分官方事实、沿用P2的假设、本轮新选的工作合同和未决事项。`contracts/p3_semantic_contract.json` 是机器可读取的相同合同与原始文件哈希。`tasks/P3_SEMANTIC_START_PROMPT.md` 是唯一启动提示词，复制其正文给Codex即可；更详细的执行边界在 `P3_SEMANTIC_CODEX_TASK.md`。标准库脚本位于 `scripts/p3_semantic_audit.py`。

`tables/` 提供4个可直接核对的表：四次发行的已执行/可调整槽位、4×144个预测积分映射、144个result3物理时间映射、小额计费例子。`evidence/` 保存官方原件来源哈希和本环境参考检查；它们不能代替本地冻结Common的检查。`p3_open_issues.csv` 给出旧OI与P3具体歧义的对应。

本地执行只会新增 `local_verification/`，包含本地Gate、完整检查JSON/CSV及重建的映射表。无模型训练、无LP求解、无全年策略、无新的xlsx。Common、P1/P2、原始附件与模板都保持不变。只有本地通过后才进入P3-1信息审计；P3-1本轮不自动执行。

主线目录继续沿用P1/P2的编号：`01_model_plan/ → 02_batch_run/ → 03_candidate/ → 04_review/ → 05_final/`；本轮为 `00_semantic_audit/`，后续信息审计使用 `00_information_audit/`，不因多了前置步骤把正式阶段整体顺延。
