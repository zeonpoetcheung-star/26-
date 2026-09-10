# A-3 电价结构

## 固定电价

- 固定日价格共 137 个唯一水平，分成 143 个位置上连续的等价块。
- 最低价 0.3713 元/kWh，最高价 1.3952 元/kWh；槽位位置见 `fixed_tariff_structure.csv`。

## 动态电价

- 全年均值 0.7662 元/kWh，P10 0.3824，P50 0.7385，P90 1.2619。
- 日内价差的 P50 为 1.0560 元/kWh，P90 为 1.3492 元/kWh。

## 事后描述关联

- 动态电价与 `load_kw`：Pearson=0.5077，Spearman=0.5798，n=52,560，`EX_POST_DESCRIPTIVE_ONLY`。
- 动态电价与 `pv_actual_kw`：Pearson=0.0284，Spearman=0.1894，n=52,560，`EX_POST_DESCRIPTIVE_ONLY`。
- 动态电价与 `net_load_kw`：Pearson=0.2602，Spearman=0.2624，n=52,560，`EX_POST_DESCRIPTIVE_ONLY`。

上述关联不表示价格在决策时可知，也不表示因果关系。OI-12 仍需在 A-4 明确信息集假设。
