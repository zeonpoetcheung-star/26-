# Problem 1 Publication Figures

本目录中的图均直接读取 A Final H-END canonical 数据生成，不重新求解模型，也不修改调度值。

## 图件

- `fig_p1_energy_dispatch_price`：全天负荷、光伏预测、计划购电与电价。
- `fig_p1_storage_operation_soc`：母线侧充放电量与储能 SOC 轨迹。
- `fig_p1_sensitivity_cost`（补充图）：全天购电费的口径敏感性。
  - (a) 无储能基准与主口径对比，突出节省 12,925 元（−26.9%）。
  - (b) 纵轴放缩，对比主口径、效率敏感性 √0.9、时间口径 H-START。
  - 全部数值取自 `KEY_RESULTS.csv`。本图为确定性单日 LP，无重复样本，因此**不使用误差线**。

每张图同时提供 PDF、PNG 和 SVG。PDF/SVG 用于论文排版或后续编辑，PNG 用于快速预览。

## 建议图题

1. 图 P1-1 全天能源调度与分时电价。上图展示各 10 min 区间的负荷、光伏预测与计划购电量，下图展示对应购电价格。
2. 图 P1-2 储能充放电计划与 SOC 轨迹。充电量取正、放电量取负；虚线表示 SOC 上下限。
3. 图 P1-3（补充）全天购电费对储能基准与口径假设的敏感性。H-START 仅作时间口径敏感性，不代表 Final 调度。

## 数据来源

- `../p1_schedule_internal.csv`
- `../p1_summary.json`
- `../KEY_RESULTS.csv`

脚本运行前会检查 144 个 H-END 物理区间、关键总量、购电费用及 SOC 状态。验证失败时不会输出新图。

## 复现

在 `To B` 目录运行：

```bash
conda run -n mathmodel python figures/gen_fig_p1_energy_dispatch_price.py
conda run -n mathmodel python figures/gen_fig_p1_storage_operation_soc.py
conda run -n mathmodel python figures/gen_fig_p1_sensitivity_cost.py
conda run -n mathmodel python figures/validate_p1_figures.py
```
