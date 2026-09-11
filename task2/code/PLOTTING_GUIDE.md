# 统一科研绘图调用说明

`plot_style.py` 已统一处理：

- Windows、macOS、Linux 中文字体自动回退。
- 坐标轴负号正常显示。
- 隐藏上边框和右边框。
- 坐标轴标签 12 pt，刻度 10 pt。
- 浅灰色半透明虚线网格。
- 300 DPI 高清输出并自动去除白边。
- PDF 使用 TrueType 字体，SVG 保留可编辑文字。

最简用法：

```python
import matplotlib.pyplot as plt
from plot_style import save_high_res

fig, ax = plt.subplots()
ax.plot([-2, -1, 0, 1, 2], [4, 1, 0, 1, 4])
ax.set_xlabel("时间 / h")
ax.set_ylabel("功率 / kW")

save_high_res(fig, "figures/example.png")
```

一次生成 PNG、PDF 和 SVG：

```python
save_high_res(
    fig,
    "figures/example",
    formats=("png", "pdf", "svg"),
)
```

模块在导入时自动完成全局字体和样式设置，保存函数还会在输出前再次检查所有普通坐标轴，因此日常绘图只需要导入并调用 `save_high_res()`。
