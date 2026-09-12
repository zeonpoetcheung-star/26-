# P3 A-6 冻结检查

Gate：`PASS_P3_CANDIDATE_FREEZE_WITH_OPEN_ISSUES`。

Candidate：`P3_MAIN_MEAN_ROLLOUT_061218`；本地检查 302 PASS / 0 FAIL。

MAIN底账复算总费：13741771.833637909964元。原表总费：13741771.83363791元。

受保护源文件：4253个；前后字节指纹及文件集合不变。工作簿SHA256：`4d63a8e740d872c71994d75bdf42865fc3e595f75968ced03e3c968870d8ffa8`。

只做来源/身份核验、逐日范围核对、MAIN账本算术和派生24行指定10min表；不重训、不求解、不回放、不重导或复制工作簿。未重做未来扰动试验，A-7独立Review尚未开始。

旧 `p3_specified_purchase_intervals.csv` 是4h汇总，原样保留。正确10min提取另存 `tables/p3_candidate_specified_purchase_10min.csv`，需随Review检查。

日期格式恢复原件和脚本只列入清单，没有再次执行。保持所有工作假设，见 `CLAIMS_AND_LIMITATIONS.md`。

`CURRENT_STATE`未由脚本修改；由Codex按任务仅更新既有文件P3小节。
