# Problem 3｜To C 论文写作交接

这个包的目的不是让 C 重新跑模型，而是让 C 能从“题意 → 预测 → 不确定性 → 滚动优化 → 调整筛选 → 实际执行 → 结算 → 消融 → Review”完整写出问题3。

## 建议阅读顺序
1. `P3_TO_C_MASTER.md`：最完整的论文写作主线。
2. `P3_EQUATIONS.md`：核心公式，可改写进论文。
3. `PAPER_TABLES.md`：论文建议表格与关键数值。
4. `CLAIMS_AND_LIMITATIONS.md`：哪些能写、哪些不能写。
5. `WRITING_HANDOFF.md`：推荐章节结构与通俗解释。
6. `P3_FILE_GUIDE.md` / `P3_HANDOFF_INVENTORY.md`：需要找原始证据时用。
7. `references/`：Model Plan、Batch、Review、Crosscheck 原件。
8. `data/`：论文表格与数字来源。

`result3.xlsx` 是冻结结果文件，只读。论文中最重要的经济证据优先用 P3 内部机会组合消融，而不是拿 A/B 或 P2/P3 总费用直接做因果结论。
