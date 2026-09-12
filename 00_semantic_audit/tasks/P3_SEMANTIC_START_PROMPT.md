现在执行 Problem 3｜P3-0 Semantic Audit。本轮只做题面/数据结构/时间映射/结算合同/结果模板的本地验收，不训练、不优化、不跑全年，不修改P2 Final和Common。

请完整读取：
A_route/problem3/00_semantic_audit/P3_SEMANTIC_AUDIT.md
A_route/problem3/00_semantic_audit/contracts/p3_semantic_contract.json
A_route/problem3/00_semantic_audit/tasks/P3_SEMANTIC_CODEX_TASK.md

然后直接执行下面的PowerShell命令，无需再问是否启动：

& "D:\Anaconda3\python.exe" -B -s "D:\2026数模国赛\CUMCM2026_C\A_route\problem3\00_semantic_audit\scripts\p3_semantic_audit.py" --project-root "D:\2026数模国赛\CUMCM2026_C"

项目根目录确有变更时仅修正两处路径；不要调整模型、公式、参数、预期哈希或官方模板。脚本使用Python标准库，不需要安装包。

已有 evidence/reference_run 只是上传原件的参考核验，不代替这次本地Common对账。禁止使用 --reference-only 来绕过本地检查。

所有源文件只读，只向本轮local_verification目录写入。出现文件缺失、哈希冲突、字段不符、日期错误或计算失败，报告具体证据后停止；不要自动重做Common或切换来源。

通过后输出 PASS_P3_SEMANTIC_AUDIT_WITH_OPEN_ISSUES，明确“题面未消歧处仍为已披露工作假设”，并停在P3-0，不自动进入P3-1。失败则输出 BLOCKED_P3_SEMANTIC_AUDIT。
