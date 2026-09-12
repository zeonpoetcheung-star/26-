# P3 大日志如何通过 GitHub 给 B

## 最重要的结论
**P3 不需要把巨大 `logs/checkpoints/` 发给绘图手。** P3 没有 LightGBM/神经网络模型；预测侧唯一训练模块是低维前缀收缩回归，完整拟合记录已经是 `data/p3_load_fit_log.csv`（约0.85MB）。

作图真正需要的是：政策比较、月度汇总、四指定日逐槽轨迹、预测指标、调整次数/V_score。这些都在 `data/`。

## 如果 B 仍要完整预测账本
本包已提供：
- `data_large_optional/p3_forecast_ledger.csv.gz`（约14MB）
- `data_large_optional/p3_scenario_quantile_diagnostics.csv.gz`（约7MB）

它们都低于 GitHub 100MB 单文件限制，直接上传即可；B 解压 gzip 后得到原 CSV。

## 如果 B 明确要求本地 logs
在你本地项目根运行：
`python tools/prepare_github_log_bridge.py <项目根> <输出目录>`

脚本会压缩白名单日志；超过90MB自动切片。默认不包含 checkpoint。只有审计复现明确需要时才加 `--include-checkpoints`。

不要为了作图上传数千个 checkpoint：它们既不代表机器学习训练曲线，也不是论文图的数据源。
