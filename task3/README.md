# C题问题三独立项目

本目录包含问题三的全部新增代码、结果、报告和图表，不依赖或覆盖问题一、问题二的输出文件。

## 方法

采用因果负载预测、附件 3 原始光伏预报、历史误差情景、四阶段随机 MPC 和 CVaR 风险控制。电价与功率时间点均按十分钟区间右端点解释。

## 运行

在 `/mnt/d/mathmodel/C题/task3` 下执行：

```bash
conda run -n mathmodel python code/problem3.py
```

仅重新生成最终模型、不重复更新频次消融：

```bash
conda run -n mathmodel python code/problem3.py --skip-ablation
```

完整运行约 3 分钟。程序只读取 `../附件/`，所有新文件均写入当前 `task3/`。

## 主要结果

- 随机 CVaR 主模型总费用：15018433.14 元；
- 紧急购电量：76721.43 kWh；
- 全更新确定性对照总费用：14958609.43 元；
- 相比仅 0:00 确定性方案，全更新使费用下降 10.37%；
- 所有能量、储能、非预见性和工作簿检查均通过。

## 目录

```text
task3/
├── code/problem3.py
├── reports/
│   ├── ANALYSIS_MODELING_REPORT.md
│   ├── RESULTS_REPORT.md
│   └── METHOD_COMPARISON.md
├── outputs/
├── figures/
└── result3.xlsx
```

`result3.xlsx` 的计划和调整表按模板 0:10 至次日 0:10 的运营窗口填写；充放电表按日历日 0:00--24:00 汇总。调整表“全天购电费”是初始计划费加历次合同调整增量，不包含紧急购电费。
