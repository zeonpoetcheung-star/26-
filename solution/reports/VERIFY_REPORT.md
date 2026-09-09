# 验证和验收报告

## 结论

**PASS**（附一条脚本误报说明）

论文可正常编译（26 页，A4），章节结构完整、图表全部嵌入、数值与结果记录一致、无占位符与内部文件名泄露、参考文献真实且已引用。唯一 FAIL 为验收脚本对 LaTeX 图片路径的解析约定与本项目实际编译方式不一致导致的误报，已核实为假阳性（详见"文本质量门禁"）。

## 检查项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 入口文件 | PASS | `paper/main.tex` 存在 |
| 章节结构 | PASS | 10 个正文节 + 附录 + 参考文献，顺序正确 |
| 章节标题 | PASS | 每节均有 `\section{}` 一级标题 |
| 图表引用 | PASS | 15 张图全部存在并嵌入 PDF |
| 数值一致性 | PASS | 关键数值与 `RESULTS_REPORT.md` 一致 |
| 文本质量门禁 | PASS（脚本 1 项误报） | 无占位符、无泄露（详见下） |
| 参考文献 | PASS | 6 篇真实文献，正文已 `\cite` 引用 |
| 编译 | PASS | xelatex 两遍编译成功，26 页 |
| PDF 视觉检查 | 未执行（无视觉能力） | 已做程序化替代检查 |

## 章节结构

入口 `main.tex` 依次 `\input` 以下章节，顺序与文件名前缀一致：

1. 1_restatement —— 问题重述
2. 2_analysis —— 数据理解与总体思路
3. 3_assumptions —— 模型假设
4. 4_symbols —— 符号说明
5. 5_problem1 —— 问题一
6. 6_problem2 —— 问题二
7. 7_problem3 —— 问题三
8. 8_problem4 —— 问题四
9. 9_sensitivity —— 灵敏度分析
10. 10_evaluation —— 模型评价与推广
11. A_code —— 附录核心代码
12. references —— 参考文献

共 4 个子问题，与 `ANALYSIS_MODELING_REPORT.md` 一致；无缺失、重复、未被引用的章节文件。

## 图表引用

正文共引用 15 张图（11 张数据图 + 4 张非数据流程图）：

- 问题一：fig1_1_scatter_within、fig1_2_between_bmi、fig1_3_fitted
- 问题二：fig2_1_attainment_vs_bmi、fig2_2_optimal_timing、fig2_3_error_sensitivity、fig_flow_optimal
- 问题三：fig3_1_feature_importance、fig3_2_cluster_timing
- 问题四：fig4_1_roc、fig4_2_feature_importance、fig4_3_z_distribution、fig_flow_q4
- 总体/数据：fig_roadmap、fig_pipeline

所有 15 张 PDF 均存在于 `figures/`，且经编译确认已嵌入 PDF（通过矢量绘图内容检测确认图表渲染）。数据图位于对应结果章节，非数据流程图位于方法/总体思路章节，符合规范。

## 数值一致性

对论文 PDF 全文提取文本，逐一核对关键数值与 `reports/RESULTS_REPORT.md`：

| 数值 | 含义 | 状态 |
| --- | --- | --- |
| 0.00319 | 固定效应斜率（问题一） | 一致 |
| 0.00313 | 混合模型孕周系数 | 一致 |
| 0.00138 | 混合模型 BMI 系数 | 一致 |
| 0.757 | 达标时间—BMI 斜率（问题二） | 一致 |
| 15.5 / 16.1 / 20.1 | 各 BMI 组最佳时点 | 一致 |
| 14.5 / 20.2 | 问题三各组最佳时点 | 一致 |
| 0.789 / 0.957 / 0.479 | 问题四 AUC / 特异度 / 基线 AUC | 一致 |
| −19.46 | 达标时间回归截距 | 一致 |

无冲突；公式符号均在"符号说明"或首次出现处解释。

## 文本质量门禁

运行 `writing_check.sh`（参数按本项目实际布局传入）：

- 章节标题顺序、章节数量、一级标题：全部通过。
- 占位符（TODO/PLACEHOLDER/待补充等）：未发现。
- 内部工作流文件名泄露（reports/、figures/、code/、problem*.py、RESULTS_REPORT 等）：未发现。
- **误报说明**：脚本对 LaTeX `\includegraphics` 的路径按"相对于 section 文件所在目录"解析（Typst 的约定），而本项目 LaTeX 按"相对于编译工作目录 paper/"解析（`../figures/`）。二者相差一层，导致脚本报 15 条"图片不存在"。经核实：xelatex 以 `-halt-on-error` 编译**无任何图片加载错误**，且 PDF 中 15 张图均已嵌入（矢量绘图内容检测确认），故该 FAIL 为脚本约定差异导致的假阳性，非真实错误。

其余 WARN（如 3_assumptions/4_symbols 章节偏短、部分章节图表周围文字偏少）属提示级，不影响论文正确性。

## 编译

```bash
cd paper
xelatex -interaction=nonstopmode -halt-on-error main.tex   # 两遍
```

两遍编译均成功，无 `!` 错误；交叉引用无 undefined、无"may have changed"残留；输出 `main.pdf` 736 KB、26 页。唯一字体告警为 Fandol 楷体斜体字形缺失的自动替换，不影响排版。

## PDF 视觉检查

本模型不具备图像输入能力，无法逐页人工视觉检查，已在报告中如实说明。已完成的程序化替代检查：

- 页面尺寸：全部 595×842 pt（A4），无异常尺寸页。
- 空白页：无（所有页均有正文或图表）。
- 文本溢出：扫描全文块边界，无超出页面右边界的文本块。
- 图表渲染：检测到多个页面含大量矢量绘图元素（第 10、12、19、20、25、26 页等），确认图表已嵌入。
- 标题/摘要/目录/正文/参考文献/附录均存在。

## 仍需处理的问题

- （WARN）`3_assumptions.tex`、`4_symbols.tex` 章节偏短，属模板常规结构，可接受。
- （WARN）部分章节图表密集、说明文字可再充实，不影响验收通过。
- 极端 BMI 组（[20,28)、≥40）样本量小导致最佳时点估计稳定性低，已在论文"模型不足"中如实说明。
