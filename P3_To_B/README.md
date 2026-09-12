# Problem 3｜To B 绘图交接

这不是另一条 B-route 的 Task3 结果，而是 **A-route 最终 Candidate `P3_MAIN_MEAN_ROLLOUT_061218` 的作图数据包**。绘图时只使用本包 A canonical/final 数据，不混入 B-route 的费用或轨迹。

解题主线：W1 周同期负荷基线 → 6/12/18 当天已观测前缀修正 → 附件3官方滚动 PV 预报 → 最近成熟历史残差路径形成不确定性场景 → 0/6/12/18 24h rolling LP → KEEP/ADJUST 同信息情景回放筛选 → 当前真实 SOC 下逐10min执行与结算。

MAIN 正式期 334 天，总费用约 1374.18 万元。最有论文价值的证据不是 A/B 总费用，而是 **P3 自身机会组合消融**：只0时不调整约1421.62万元，开放6/12/18后降至1374.18万元，下降约3.34%。

## 先看什么
1. `FIGURE_GUIDE.md`：推荐图及用哪些 CSV。
2. `DATA_DICTIONARY.md`：关键字段含义。
3. `P3_TO_B_MASTER.md`：把整问从预测到结算讲清楚。
4. `data/`：优先直接作图的数据。
5. `references/`：需要确认模型语义或结果时再看。
6. `code/`：理解数据如何生成，不建议为了作图重跑全年。

## 大文件/日志
P3 没有 LightGBM 或神经网络；只有低维前缀收缩回归。`data/p3_load_fit_log.csv` 就是完整拟合日志，GitHub 可直接传。超大的 checkpoint/solver 日志不应作为绘图输入。`data_large_optional/` 中已把两个最有价值的大 CSV gzip 压到 GitHub 单文件限制以内；若仍需本地 logs，见 `LOG_TRANSFER_GUIDE.md`。
