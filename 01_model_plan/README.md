# P3｜01_model_plan

当前进入正式模型规划，不是全年Batch Run。先确认同级已有并通过：`00_semantic_audit/`、`00_information_audit/`。

主候选：`P3_MAIN_MEAN_ROLLOUT_061218`。路线是W1+因果前缀回归、官方PV、历史配对误差情景、滚动短缺风险LP及因果执行回放验收；允许每个发行机会不改计划。另预登记有限情景鲁棒候选，不预先宣布它更好。

- `P3_MODEL_PLAN.md`：完整预测、场景、数学模型、合同、控制、评价及阶段边界。
- `P3_DESIGN_BASIS.md`：审计发现、此前图片/讨论与模型设计的一一对应，以及参考文献边界。
- `contracts/P3_MODEL_SPEC.json`：工程参数、源文件身份、实验矩阵和不可越过的规则。
- `P3_VALIDATION_PLAN.md`：A-4小例和后续A-5全量验证要求。
- `scripts/p3_lp_reference.py`：参考LP与因果回放核；不读取文件、不训练、不是年度运行入口。
- `scripts/check_p3_model_math.py`：纯人工小例；依赖现有NumPy/SciPy。
- `evidence/MODEL_MATH_SELFTEST.json`：本次参考环境35项小例通过记录，8次微型LP；不证明本地数据或全年效果。
- `evidence/SOURCE_SNAPSHOT_MANIFEST.json`：本次实际阅读的审计快照哈希。
- `tasks/P3_MODELPLAN_CODEX_TASK.md`：Codex本轮仅A-4审查和冻结任务。
- `tasks/P3_MODELPLAN_START_PROMPT.md`：唯一启动入口；复制其正文给Codex，不另找第二份prompt。

Codex只在本目录`local_check/`输出核验结果。通过后停止，得到人工下一步授权才进入`02_batch_run/`。不自动创建result3，不修改P2，不更改已核准语义合同。
