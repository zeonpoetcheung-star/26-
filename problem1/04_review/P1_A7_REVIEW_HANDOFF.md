# Problem 1｜A-7 Review Handoff

这是 Problem 1 A-route 的 Candidate 审查包。

请将审查限制在 **critical defect detection**，不要重新自由建模。

优先核对：

1. `P1_MODEL_PLAN.md` 与 `solve_p1_lp.py` 的目标函数、变量和全部约束是否一致；
2. kW → kWh 是否始终按 10 分钟乘 `1/6`；
3. `H-END` 内部时间轴及 `result1.xlsx` 循环映射是否自洽；
4. SOC 是否确实为 145 个状态点，且首尾 6000 kWh；
5. 90% 效率在 SOC 方程中的方向是否与变量定义一致；
6. 最大充放电功率 5000 kW 是否正确转为 833.333333 kWh/10min；
7. 是否遗漏题面明确规定的硬约束，或自行加入题面没有的机制；
8. Candidate 报告中的关键数值能否从 canonical schedule/result1 复现。

输出只允许三类：

```text
PASS
PASS_WITH_MINOR_FIXES
CRITICAL_DEFECT
```

若为 `CRITICAL_DEFECT`，必须指出：

- 精确位置；
- 为什么会改变模型或答案；
- 最小修正方式。

不要提出 PSO、GA、MILP 等替代算法作为“改进建议”，除非能证明当前 Candidate 本身不可行或数学上错误。
