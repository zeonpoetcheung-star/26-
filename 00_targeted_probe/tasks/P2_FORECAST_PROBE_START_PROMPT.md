当前任务：Problem 2｜A-4 内的限定预测实验。当前状态文件：CURRENT_STATE。

请读取 A_route/problem2/01_model_plan/P2_MODEL_PLAN.md 和 A_route/problem2/00_targeted_probe/tasks/P2_FORECAST_PROBE_CODEX_TASK.md，直接编写并执行任务单规定的代码，不另写方案审查或Preflight报告，不调用其他AI。

本轮只使用2025年1月数据，比较一个固定历史基准和一个固定配置的LightGBM残差分位数预测方法：3个拟合日期×2个分位数，最多6次fit；计算指定指标、无储能费用筛查并自动校验。机器学习没赢也按真实结果完成，不调参、不增加模型。

写入范围只限 A_route/problem2/00_targeted_probe/。不修改Common/P1/input/CURRENT_STATE，不读B路线，不读二月至十二月的数值，不做全年预测，不做储能优化、不写result2.xlsx、不作图。每个日期段完成即落盘。

遇到真正的依赖缺失或数据/计算错误才停止报告；正常情况下连续完成代码、运行、校验和精简报告。最终给出任务规定的Gate和选择结果后停止，不进入A-5。
