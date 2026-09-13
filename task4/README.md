# C题问题四独立项目

本目录包含问题四 4-2、4-3 的全部新增代码、工作簿、结果、报告和图表，不覆盖问题一至问题三成果。

## 运行

在 `C题/task4/` 下执行：

```bash
conda run -n mathmodel python code/problem4.py
```

只重新计算正式方案、跳过 Oracle 和其他对照：

```bash
conda run -n mathmodel python code/problem4.py --skip-comparisons
```

完整运行约 5 分钟。程序只读取 `../附件/`，所有输出均写入当前目录。

## 正式方法

- 4-2：因果负载、光伏和价格预测，5 条联合误差情景，随机线性规划与 CVaR；
- 4-3：附件 3 原始光伏预报、因果负载和价格预测、0/6/12/18 确定性滚动 MPC；
- 所有十分钟数据采用右端点口径；
- 附件 4 当天价格只用于事后结算；
- Oracle 只作为不可执行下界。

## 核心结果

| 分支 | 总费用/元 | 紧急购电量/kWh |
| --- | ---: | ---: |
| 4-2 正式方案 | 16055575.16 | 275948.18 |
| 4-3 正式方案 | 15720915.37 | 108084.52 |

两套正式结果的能量、储能、费用、非预见性和 Excel 检查均通过。

## 目录

```text
task4/
├── code/problem4.py
├── reports/
│   ├── ANALYSIS_MODELING_REPORT.md
│   ├── RESULTS_REPORT.md
│   └── METHOD_COMPARISON.md
├── outputs/
├── figures/
├── result4-2.xlsx
└── result4-3.xlsx
```
