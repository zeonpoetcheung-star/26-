########## recipe:advanced.lollipop ##########
## 1. Lollipop Chart — 棒棒糖图（渐变色茎 + 排名徽章 + 中位数参考线）

**样式保真强要求（绘制时执行）**：使用本配方时，必须以尽可能复现原版样式为目标，保留连续渐变配色、随得分变化的茎线粗细与端点大小、排名徽章、首名背景高亮及中位数参考线与标注；配色需适配当前风格时仍保留连续渐变和层次关系，不要直接改成普通离散配色、等粗线条的棒棒糖图。仅按真实数据语义和可读性作必要调整，不虚构排名或统计值；原代码出现颜色类型不兼容、圆形徽章变形或裁切时，应修正实现并保留视觉意图，不要以删除或简化这些元素代替修正。

**场景**: 按单一指标对方法/方案排名。比柱状图更简洁，常见于 Nature/Science。
**防重叠**: 使用 `smart_labels()` 自动推开重叠的数值标签。
**风格**: 渐变色从紫罗兰（高分）过渡到珊瑚橙（低分）；线粗、圆点大小也随分数渐变。前三名有排名徽章。中位数参考线分割图面。
**⚠ 关键要点**: 茎线从 x=0 开始；颜色按 HSL 明度线性渐变（避免相邻项同色）；前三名实心圆徽章。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten, smart_labels
setup_style()
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import numpy as np
import colorsys

methods = ['Ours', 'Baseline-A', 'Baseline-B', 'Baseline-C', 'Baseline-D']
scores = [0.923, 0.887, 0.862, 0.841, 0.815]

n = len(methods)
score_min, score_max = min(scores), max(scores)
score_range = score_max - score_min if score_max > score_min else 1

# ── 渐变配色：从紫罗兰 → 珊瑚橙（明度和色相同时渐变）
color_top = '#7B6BA5'     # 紫罗兰（高分，偏冷一点）
color_bottom = '#E08B74'  # 珊瑚橙（低分，偏暖）

def interpolate_color(c1, c2, t):
    """HSL 空间插值：t=0 返回 c1，t=1 返回 c2"""
    r1, g1, b1 = mc.to_rgb(c1)
    r2, g2, b2 = mc.to_rgb(c2)
    h1, l1, s1 = colorsys.rgb_to_hls(r1, g1, b1)
    h2, l2, s2 = colorsys.rgb_to_hls(r2, g2, b2)
    if abs(h2 - h1) > 0.5:
        if h1 < h2: h1 += 1.0
        else: h2 += 1.0
    h = (h1 + (h2 - h1) * t) % 1.0
    l = l1 + (l2 - l1) * t
    s = s1 + (s2 - s1) * t
    return colorsys.hls_to_rgb(h, l, s)

item_colors = [interpolate_color(color_top, color_bottom, i / (n - 1) if n > 1 else 0) for i in range(n)]

# ── 自适应高度（每项 0.46 高度 + 上下留白）
_fig_h = max(4, n * 0.46 + 1.8)
fig, ax = plt.subplots(figsize=(7.5, _fig_h))
y_pos = np.arange(n)

# 极浅网格线
ax.grid(axis='x', alpha=0.12, linestyle='-', color=COLORS['grid'])
ax.set_axisbelow(True)

# 中位数参考线（置于底层）
median_val = np.median(scores)
ax.axvline(median_val, color=COLORS['ref_line'], linestyle=':', linewidth=1.0, alpha=0.5, zorder=1)

# ── 主体：渐变色茎线 + 渐变圆点
for i, (m, s) in enumerate(zip(methods, scores)):
    c = item_colors[i]
    ratio = (s - score_min) / score_range
    lw = 1.6 + 2.0 * ratio

    # 茎线从 0 开始
    ax.plot([0, s], [y_pos[i], y_pos[i]],
            color=c, linewidth=lw, zorder=3, solid_capstyle='round')

    # 端点圆点 —— 大小随分数渐变
    dot_size = 55 + 120 * ratio
    ax.scatter(s, y_pos[i], color=c, s=dot_size, zorder=5,
               edgecolors='white', linewidths=1.8)

    # 数值标签
    ax.text(s + score_range * 0.03, y_pos[i], f'{s:.3f}',
            fontsize=8.5, fontweight='bold' if i < 3 else 'normal',
            color=c, va='center', ha='left')

    # ── 排名徽章区域
    badge_x = -score_range * 0.065
    rank = i + 1
    if rank <= 3:
        badge = plt.Circle((badge_x, y_pos[i]), 0.3,
                            color=_lighten(c, 0.15), zorder=6,
                            transform=ax.transData)
        ax.add_patch(badge)
        ax.text(badge_x, y_pos[i], str(rank),
                fontsize=8.5, fontweight='bold', color='white',
                ha='center', va='center', zorder=7)
    else:
        ax.text(badge_x, y_pos[i], str(rank),
                fontsize=7.5, color=_lighten(c, 0.2),
                ha='center', va='center', fontweight='bold')

# 第一名背景高亮条
ax.axhspan(y_pos[0] - 0.42, y_pos[0] + 0.42, alpha=0.06,
           color=item_colors[0], zorder=0)

# 中位数标注 —— 置于图的顶部
ax.text(median_val, -0.9, f'中位数 {median_val:.3f}',
        fontsize=8, color=COLORS['ref_line'], ha='center', va='bottom',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                  edgecolor=COLORS['ref_line'], alpha=0.85))

ax.set_yticks(y_pos)
ax.set_yticklabels(methods, fontsize=10)
ax.set_xlabel('F1 Score', fontsize=11)
ax.set_xlim(-score_range * 0.13, score_max + score_range * 0.15)
ax.set_ylim(n - 0.5, -1.4)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_lollipop.pdf')
```

**⚠ 易踩的坑（棒棒糖图专用）：**
```python
# 1. ylim 上方留空：ax.set_ylim(n-0.5, -1.4)，给中位数标注留空间
# 2. xlim 右侧留余量（score_max + score_range*0.15），给数值标签留空间
# 3. xlim 左侧留负值（-score_range*0.13），给排名徽章留空间
# 4. 数值标签偏移用相对值（score_range*0.03），不要用固定像素偏移
# 5. 排名徽章用 plt.Circle + transData，确保圆形不变形
# 6. 中位数标注放在 y=-0.9（图面上方），需要配合上方留空设置
# 7. 当条目数 >15 时，_fig_h 公式自动增高（每项 0.46 高度不会挤压）
```

---

########## recipe:advanced.waterfall ##########
## 6. Waterfall Chart — 瀑布图（彩色渐变柱图 + 连接线 + 顶部数值标注）

**样式保真强要求（绘制时执行）**：使用本配方时，必须以尽可能复现原版样式为目标，保留各步向右延伸的半透明层叠色带、连续阶梯线、白色描边圆点、累计值标注、总增量标注及贡献图例，不要仅因普通浮动柱瀑布图更容易实现就替换原版设计。按实际正负增量重算层带位置、累计值和标注；发生重叠时先调整透明度、间距、尺寸和标注位置。仅在数据语义不支持或调整后仍妨碍阅读时作必要删改，并说明原因；原代码兼容问题应修正实现，不应成为省略原版样式的理由。

**场景**: 因素分解、消融贡献分析。比柱状图更适合展示增量贡献。
**风格**: 彩色层叠（每步增量形成一层从当前步延伸到右边的色带层）+ 阶梯连线 + 圆点 + 数值标注统一在上方 + 贡献信息图例。比传统瀑布图（仅柱+连线）多了"层叠"视觉隐喻。

```python
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

labels = ['Baseline', '+Attention', '+Augment', '+Pretrain', '-Dropout']
deltas = [0.82,        0.04,          0.02,       0.05,       -0.01]

cum = [deltas[0]]
for d in deltas[1:]:
    cum.append(cum[-1] + d)
final_val = cum[-1]
total_delta = final_val - deltas[0]

layer_colors = [COLORS['up'] if d >= 0 else COLORS['down'] for d in deltas[1:]]
n = len(labels)

fig, ax = plt.subplots(figsize=(9, 5))
ax.grid(axis='y', alpha=0.12, linestyle='-', color=COLORS['grid'])
ax.set_axisbelow(True)

x_positions = np.arange(n)

# ── 色带层叠（每步增量的层带位置，延伸到最右边）
for i in range(1, n):
    c = layer_colors[i - 1]
    bottom = min(cum[i-1], cum[i])
    top = max(cum[i-1], cum[i])
    ax.fill_between([x_positions[i] - 0.5, x_positions[-1] + 0.5], bottom, top,
                    alpha=0.15, color=c, zorder=1 + i)
    ax.plot([x_positions[i] - 0.5, x_positions[-1] + 0.5], [cum[i], cum[i]],
            color=c, linewidth=0.7, linestyle='--', alpha=0.35, zorder=1 + i)

# Baseline 底层
ax.fill_between([x_positions[0] - 0.5, x_positions[-1] + 0.5], 0, cum[0],
                alpha=0.06, color=PALETTE[0], zorder=0)

# ── 阶梯连线
ax.step(x_positions, cum, where='mid', color=PALETTE[0], linewidth=2.8, zorder=10)

# ── 圆点
for i in range(n):
    c = PALETTE[0] if i == 0 else layer_colors[i - 1]
    ax.scatter(x_positions[i], cum[i], color=c, s=90, zorder=11,
               edgecolors='white', linewidths=2.0)

# ── 数值标注 —— 所有步骤都标，统一放在圆点上方
for i in range(n):
    c = PALETTE[0] if i == 0 else layer_colors[i - 1]
    ax.text(x_positions[i], cum[i] + 0.008, f'{cum[i]:.3f}', ha='center', va='bottom',
            fontsize=8.5, fontweight='bold' if (i == 0 or i == n-1) else 'normal',
            color=c,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                      edgecolor=c if (i == 0 or i == n-1) else 'none',
                      alpha=0.9, linewidth=0.5), zorder=12)

# ── 总增量标注（右上角）
ax.text(0.97, 0.95, f'Total: +{total_delta:.2f} (+{total_delta/deltas[0]*100:.1f}%)',
        transform=ax.transAxes, fontsize=9.5, ha='right', va='top',
        fontweight='bold', color=COLORS['up'],
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=COLORS['up'], alpha=0.9, linewidth=1.0), zorder=15)

# ── 贡献图例（将贡献信息全部放在图例，而非图面上标）
legend_patches = []
for i in range(1, n):
    d = deltas[i]
    c = layer_colors[i - 1]
    sign = '+' if d >= 0 else ''
    pct = abs(d) / total_delta * 100
    patch = mpatches.Patch(facecolor=_lighten(c, 0.4), edgecolor=c, linewidth=1.2,
                           label=f'{labels[i]}  {sign}{d:.2f} ({pct:.0f}%)')
    legend_patches.append(patch)
legend = ax.legend(handles=legend_patches, loc='lower right',
                   frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8.5,
                   facecolor='white', title='Contribution', title_fontsize=9,
                   handlelength=1.5, handleheight=1.0)
legend.set_zorder(15)

ax.set_xticks(x_positions)
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel('Accuracy', fontsize=11)
ax.set_xlim(-0.7, n - 0.3)
ax.set_ylim(deltas[0] * 0.92, final_val * 1.12)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_waterfall.pdf')
```

**⚠ 易踩的坑（彩色层叠瀑布图专用）：**
```python
# 1. 数值标注统一在圆点上方（va='bottom'），不要放在下方（色带层叠在下方会遮挡）
# 2. 首尾端点有边框 bbox，中间步骤无边框白底（视觉层次分明）
# 3. 贡献信息放图例而非图面：避免色带中间的标注和阶梯线重叠
# 4. ylim 上方留 12%，给最高点的标注留空间
# 5. 总增量标注用 transform=ax.transAxes 固定在右上角，不受数据范围影响
# 6. 色带 alpha=0.15：太深会让标注不清楚，太浅没有层次感
```


---

########## recipe:basic.scatter_regression ##########
## 4. 散点图（KDE 等高线 + 柔和边际密度 + 回归公式框 + 年份标签）

**场景**：两变量相关性探索、模型预测值 vs 实际值、数据初步探索。
**要点**：KDE 等高线背景、边际密度分布、拟合线+置信带、R² 标注框、半透明散点防重叠。

```python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.stats import gaussian_kde
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()

np.random.seed(42)
n = 150
x = np.random.uniform(1, 10, n)
y = 2.5 * x + np.random.normal(0, 3, n)

fig = plt.figure(figsize=(7, 6))
gs = gridspec.GridSpec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
                       wspace=0.05, hspace=0.05)

ax_main = fig.add_subplot(gs[1, 0])
ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)

# KDE 等高线背景
xy = np.vstack([x, y])
kde = gaussian_kde(xy, bw_method=0.3)
xg = np.linspace(x.min() - 1, x.max() + 1, 80)
yg = np.linspace(y.min() - 3, y.max() + 3, 80)
Xg, Yg = np.meshgrid(xg, yg)
Z = kde(np.vstack([Xg.ravel(), Yg.ravel()])).reshape(Xg.shape)
ax_main.contourf(Xg, Yg, Z, levels=8, cmap='Blues', alpha=0.15)
ax_main.contour(Xg, Yg, Z, levels=5, colors=PALETTE[0], alpha=0.2, linewidths=0.5)

# 散点
ax_main.scatter(x, y, s=30, alpha=0.5, color=PALETTE[0], edgecolor='white', linewidth=0.5, zorder=3)

# 拟合线 + 置信带
z = np.polyfit(x, y, 1)
p = np.poly1d(z)
x_fit = np.linspace(x.min(), x.max(), 100)
ax_main.plot(x_fit, p(x_fit), color=PALETTE[1], linewidth=2, zorder=4)
residuals = y - p(x)
se = residuals.std()
for layer, alpha in enumerate([0.15, 0.08, 0.03]):
    ax_main.fill_between(x_fit, p(x_fit) - 1.96 * se * (0.3 + layer * 0.1),
                         p(x_fit) + 1.96 * se * (0.3 + layer * 0.1),
                         alpha=alpha, color=PALETTE[1], linewidth=0)

# R² 标注框
r2 = 1 - np.sum(residuals ** 2) / np.sum((y - y.mean()) ** 2)
ax_main.text(0.05, 0.92, f'R² = {r2:.3f}\ny = {z[0]:.2f}x + {z[1]:.2f}\nn = {n}',
             transform=ax_main.transAxes, fontsize=9, verticalalignment='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                       edgecolor=PALETTE[0], alpha=0.9, linewidth=0.8))

# 边际密度（顶部）
kde_x = gaussian_kde(x, bw_method=0.3)
xd = np.linspace(x.min() - 1, x.max() + 1, 200)
ax_top.fill_between(xd, kde_x(xd), alpha=0.2, color=PALETTE[0])
ax_top.plot(xd, kde_x(xd), color=PALETTE[0], linewidth=1.2)
ax_top.set_yticks([])
ax_top.spines['top'].set_visible(False)
ax_top.spines['right'].set_visible(False)
ax_top.spines['left'].set_visible(False)
plt.setp(ax_top.get_xticklabels(), visible=False)

# 边际密度（右侧）
kde_y = gaussian_kde(y, bw_method=0.3)
yd = np.linspace(y.min() - 3, y.max() + 3, 200)
ax_right.fill_betweenx(yd, kde_y(yd), alpha=0.2, color=PALETTE[0])
ax_right.plot(kde_y(yd), yd, color=PALETTE[0], linewidth=1.2)
ax_right.set_xticks([])
ax_right.spines['top'].set_visible(False)
ax_right.spines['right'].set_visible(False)
ax_right.spines['bottom'].set_visible(False)
plt.setp(ax_right.get_yticklabels(), visible=False)

ax_main.set_xlabel('自变量 X', fontsize=11)
ax_main.set_ylabel('因变量 Y', fontsize=11)
ax_main.grid(alpha=0.12, linestyle='--', color=COLORS['grid'])
ax_main.spines['top'].set_visible(False)
ax_main.spines['right'].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_scatter.pdf')
```

**★ 防遮挡技巧（散点图专用）：**
```python
# 1. R² 标注框放在左上角：因为拟合线通常从左下到右上，左上角空间最大
# 2. KDE 等高线用极淡色（alpha=0.15）：不要遮挡散点
# 3. 散点数 >500 时：降低 alpha 到 0.3，或用 hexbin 替代
# 4. 边际密度图高度控制在主图的 1/5：不要喧宾夺主
```

---

########## recipe:basic.grouped_bar ##########
## 1. 分组柱状图（Grouped Bar）— 淡色填充 + 原色边框 + 参考线 + 顶部数值 + 最优高亮

**场景**：多方法在多指标上的对比，如不同模型在 Accuracy/F1/Recall 上的得分对比。
**要点**：淡色填充+原色边框柱体、水平参考线标注均值、顶部数值标注、最优值★高亮、误差线、淡色背景渐变 + 柱子阴影。

```python
import numpy as np
import matplotlib.pyplot as plt
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()

categories = ['指标A', '指标B', '指标C', '指标D']
groups = {
    '本文方法': [85.2, 78.3, 92.1, 88.5],
    '方法B':   [82.1, 80.5, 88.7, 85.2],
    '方法C':   [79.8, 75.2, 85.3, 82.0],
}
stds = {
    '本文方法': [1.2, 1.5, 0.8, 1.0],
    '方法B':   [1.8, 2.0, 1.3, 1.5],
    '方法C':   [2.1, 2.5, 1.6, 1.8],
}

fig, ax = plt.subplots(figsize=(9, 5.5))
x = np.arange(len(categories))
n = len(groups)
width = 0.22

# 淡蓝背景渐变
ax.axhspan(0, max(max(v) for v in groups.values()) * 1.2, alpha=0.03, color=PALETTE[0], zorder=0)

for i, (name, vals) in enumerate(groups.items()):
    offset = (i - n / 2 + 0.5) * width
    is_ours = '本文' in name
    # 柱子阴影
    ax.bar(x + offset + 0.02, vals, width, color='#cccccc', alpha=0.08, zorder=1)
    # ★ 主柱子：淡色填充 + 原色边框
    bars = ax.bar(x + offset, vals, width, yerr=stds[name], capsize=3,
                  color=_lighten(PALETTE[i], 0.4), edgecolor=PALETTE[i],
                  linewidth=1.5 if is_ours else 1.2,
                  label=name, zorder=2,
                  error_kw={'elinewidth': 0.8, 'capthick': 0.6, 'color': COLORS['text']})

    for j, (bar, v, s) in enumerate(zip(bars, vals, stds[name])):
        all_vals_j = [groups[g][j] for g in groups]
        is_best = (v == max(all_vals_j))
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + s + 0.5,
                f'{"★" if is_best else ""}{v:.1f}',
                ha='center', va='bottom', fontsize=7.5,
                fontweight='bold' if is_best else 'normal',
                color=PALETTE[i] if is_best else COLORS['text'],
                bbox=dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none', alpha=0.7) if is_best else {})

# 水平参考线：全局均值
global_mean = np.mean([v for vals in groups.values() for v in vals])
ax.axhline(y=global_mean, color=COLORS['ref_line'], linestyle='--', linewidth=0.8, alpha=0.4)
ax.text(len(categories) - 0.3, global_mean + 0.5, f'均值 {global_mean:.1f}',
        fontsize=8, color=COLORS['ref_line'], ha='right', style='italic',
        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.8))

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylabel('得分', fontsize=11)
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=9, loc='best')
ax.set_ylim(0, max(max(v) for v in groups.values()) * 1.2)
ax.grid(axis='y', alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_grouped_bar.pdf')
```

**★ 防遮挡技巧（分组柱状图专用）：**
```python
# 1. 顶部数值标签：bar_height + 0.01，不要放在柱子内部（柱子矮时会溢出）
# 2. 柱子多（>6 组 × 4 指标）时：fontsize 降到 7，或只标注最优值
# 3. ylim 上方留 15%：ax.set_ylim(0, max_val * 1.15)，给标签留空间
# 4. x 轴标签长（中文>4 字）：rotation=15, ha='right'，防止重叠
# 5. 图例放在图外上方：bbox_to_anchor=(0.5, 1.12), loc='center', ncol=N
# 6. 参考线标注放在图右边缘：x=len(categories)-0.5，不要放在数据密集区
```

---

########## recipe:basic.stacked_bar ##########
## 2. 堆叠柱状图（Stacked Bar）— 淡色填充 + 原色边框 + 趋势线 + 自动对比度标签 + 同比变化

**场景**：展示各部分占总量的构成变化，如产业结构变迁、各类别占比随年份变化。
**要点**：淡色填充+原色边框堆叠柱、顶部趋势折线、自动对比度百分比标签（深色块白字/浅色块黑字）、末端同比变化标注、微妙网格。

```python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()

categories = ['2019', '2020', '2021', '2022', '2023']
components = {
    '第一产业': [8.2, 7.8, 7.5, 7.2, 6.9],
    '第二产业': [38.5, 37.2, 36.8, 36.1, 35.5],
    '第三产业': [53.3, 55.0, 55.7, 56.7, 57.6],
}

fig, ax = plt.subplots(figsize=(8, 5.5))
x = np.arange(len(categories))
bottom = np.zeros(len(categories))
bar_width = 0.55

for i, (name, vals) in enumerate(components.items()):
    vals_arr = np.array(vals)
    # ★ 淡色填充 + 原色边框
    bars = ax.bar(x, vals_arr, bar_width, bottom=bottom,
                  color=_lighten(PALETTE[i], 0.4), edgecolor=PALETTE[i],
                  linewidth=1.2, label=name, zorder=2)

    # 自动对比度标签：深色块白字 / 浅色块黑字
    for bar, v, b in zip(bars, vals_arr, bottom):
        if v > 5:
            r, g, b_c = mcolors.to_rgb(_lighten(PALETTE[i], 0.4))
            luminance = 0.299 * r + 0.587 * g + 0.114 * b_c
            text_color = 'white' if luminance < 0.6 else COLORS['text']
            ax.text(bar.get_x() + bar.get_width() / 2, b + v / 2,
                    f'{v:.1f}%', ha='center', va='center', fontsize=8,
                    color=text_color, fontweight='bold')
    bottom += vals_arr

# 顶部趋势折线（总量）
totals = bottom
ax.plot(x, totals, 'o-', color=COLORS['text'], linewidth=1.5, markersize=5,
        markeredgecolor='white', markeredgewidth=1, zorder=3)
for xi, t in zip(x, totals):
    ax.text(xi, t + 1.0, f'{t:.1f}', ha='center', va='bottom', fontsize=8,
            fontweight='bold', color=COLORS['text'])

# 末端同比变化标注
for i, (name, vals) in enumerate(components.items()):
    change = vals[-1] - vals[-2]
    sign = '+' if change >= 0 else ''
    color = COLORS['up'] if change >= 0 else COLORS['down']
    y_pos = sum(components[n][-1] for n in list(components.keys())[:i]) + vals[-1] / 2
    ax.annotate(f'{sign}{change:.1f}%', xy=(len(categories) - 1 + 0.35, y_pos),
                fontsize=7, color=color, fontweight='bold', va='center',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor=color, alpha=0.8, linewidth=0.5))

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylabel('占比 (%)', fontsize=11)
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=9, loc='upper left')
ax.grid(axis='y', alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_stacked_bar.pdf')
```

**★ 防遮挡技巧（堆叠柱状图专用）：**
```python
# 1. 百分比标签只在块高度 >5% 时显示：太小的块标签会溢出
# 2. 趋势折线标注放在柱子上方：不要和堆叠块内的标签重叠
# 3. 同比变化标注放在最右侧柱子外：x = len(categories) - 1 + 0.35
# 4. 图例放在左上角：因为通常数据在右侧增长，左上角空间最大
```

---

########## recipe:basic.line ##########
## 3. 折线图（渐变填充 + 极值标注箭头 + 微妙网格）

**场景**：时序趋势展示、多方法性能随参数/epoch 变化、年度指标对比。
**要点**：渐变填充置信带、极值点★标注+箭头、白色描边标记点、微妙网格背景。

```python
import numpy as np
import matplotlib.pyplot as plt
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()

x = np.arange(2015, 2025)
series = {
    '本文方法': np.array([72, 75, 78, 80, 83, 85, 87, 89, 91, 92]),
    '方法B':    np.array([70, 73, 76, 79, 81, 82, 84, 86, 88, 89]),
    '方法C':    np.array([68, 70, 72, 75, 77, 79, 80, 82, 83, 84]),
}
markers = ['o', 's', '^']
stds = {k: np.random.uniform(1.5, 3.0, len(v)) for k, v in series.items()}

fig, ax = plt.subplots(figsize=(8, 5))

# 淡色背景渐变
ax.axhspan(min(min(v) for v in series.values()) - 5,
           max(max(v) for v in series.values()) + 5,
           alpha=0.02, color=PALETTE[0], zorder=0)

for i, (name, y) in enumerate(series.items()):
    is_ours = '本文' in name
    noise = stds[name]

    # 渐变填充置信带
    for layer, alpha in enumerate([0.15, 0.08, 0.03]):
        ax.fill_between(x, y - noise * (1 - layer * 0.2), y + noise * (1 - layer * 0.2),
                        alpha=alpha, color=PALETTE[i], linewidth=0)

    # 主折线
    ax.plot(x, y, f'{markers[i]}-', color=PALETTE[i],
            linewidth=2.5 if is_ours else 1.8, markersize=7 if is_ours else 5,
            markeredgecolor='white', markeredgewidth=1.2, label=name, zorder=3)

    # 极值标注（最大值）
    max_idx = np.argmax(y)
    ax.scatter(x[max_idx], y[max_idx], s=120 if is_ours else 80, color=PALETTE[i],
               edgecolor='white', linewidth=2, zorder=4, marker='*')
    if is_ours:
        ax.annotate(f'★ {y[max_idx]:.1f}',
                    xy=(x[max_idx], y[max_idx]),
                    xytext=(x[max_idx] - 1.5, y[max_idx] + 3),
                    fontsize=9, fontweight='bold', color=PALETTE[i],
                    arrowprops=dict(arrowstyle='->', color=PALETTE[i], lw=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor=PALETTE[i], alpha=0.9))

ax.set_xlabel('年份', fontsize=11)
ax.set_ylabel('准确率 (%)', fontsize=11)
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=9, loc='best')
ax.set_xticks(x)
ax.grid(alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.tight_layout()
save_fig(fig, 'figures/fig_line.pdf')
```

**★ 防遮挡技巧（折线图专用）：**
```python
# 1. 极值标注箭头方向：根据数据走势选择 xytext 偏移方向，避免和折线重叠
# 2. 置信带层数 3 层渐变：最内层 alpha=0.15，最外层 alpha=0.03
# 3. 多系列（>4 条）时：只标注本文方法的极值，其余省略
# 4. x 轴标签密集时：每隔 2 个标注一次，或 rotation=30
```

---

########## recipe:basic.multipanel ##########
## 12. 多面板子图（淡色填充 + 原色边框 + 带背景框标签 + 统一风格）

**场景**：多个相关图表组合成一张大图，如同一实验的不同视角、多数据集结果并排展示。
**要点**：(a)(b)(c)(d) 带背景框子图标签、淡色填充+原色边框统一风格、tight_layout 自动对齐。

```python
import numpy as np
import matplotlib.pyplot as plt
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()

np.random.seed(42)
fig, axes = plt.subplots(2, 2, figsize=(5.0, 4.9))   # ⛔ 2×2 是近方图，上页只显示 4.55in → 原生 5.0in（写 10 会缩到 0.46、刻度腰斩）

# (a) 折线图 — 渐变填充
ax = axes[0, 0]
for i in range(3):
    y = np.cumsum(np.random.randn(10))
    ax.plot(range(10), y, 'o-', color=PALETTE[i], linewidth=1.8, markersize=5,
            markeredgecolor='white', markeredgewidth=0.8, label=f'系列{i + 1}')
    ax.fill_between(range(10), y - 1, y + 1, alpha=0.08, color=PALETTE[i])
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8)
ax.set_ylabel('累计值', fontsize=10)
ax.grid(alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# (b) 分组柱状图 — 淡色填充 + 原色边框
ax = axes[0, 1]
x = np.arange(5)
for i, label in enumerate(['方法A', '方法B']):
    vals = np.random.uniform(60, 95, 5)
    offset = (i - 0.5) * 0.3
    ax.bar(x + offset, vals, 0.28, color=_lighten(PALETTE[i], 0.4),
           edgecolor=PALETTE[i], linewidth=1.2, label=label)
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8)
ax.set_ylabel('得分', fontsize=10)
ax.grid(axis='y', alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# (c) 散点图 — KDE 等高线背景
ax = axes[1, 0]
for i in range(3):
    pts = np.random.randn(30, 2)
    ax.scatter(pts[:, 0], pts[:, 1], s=25, alpha=0.6, color=PALETTE[i],
               edgecolor='white', linewidth=0.5, label=f'类{i + 1}')
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8)
ax.grid(alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# (d) 直方图 — 淡色填充 + 原色边框
ax = axes[1, 1]
for i in range(3):
    vals = np.random.normal(i * 2, 1, 200)
    ax.hist(vals, bins=20, alpha=0.5, color=_lighten(PALETTE[i], 0.4),
            edgecolor=PALETTE[i], linewidth=0.8, label=f'分布{i + 1}')
ax.legend(frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=8)
ax.set_ylabel('频次', fontsize=10)
ax.grid(axis='y', alpha=0.12, linestyle='--', color=COLORS['grid'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# ★ 带背景框子图标签（用 set_title 紧贴子图顶部）
for i, ax in enumerate(axes.flat):
    ax.set_title(f'({chr(97 + i)})', fontsize=12, fontweight='bold', loc='left', pad=3)

fig.tight_layout(pad=0.5)
save_fig(fig, 'figures/fig_subplots.pdf')
```

**★ 防遮挡技巧（多面板子图专用）：**
```python
# 1. 子图标签 (a)(b)(c)(d) 用 ax.set_title(loc='left', pad=3) 紧贴子图顶部
#    ⛔ 不要用 ax.text(transAxes) — set_aspect('equal') 时标注会远离子图
# 2. tight_layout(pad=0.5)：紧凑布局，子图不会被压缩
#    ⛔ 不要用 pad=2.0 — 紧凑布局下会导致子图极小
# 3. 每个子图的图例放在各自内部：不要用全局图例
# 4. 统一 fontsize：标题 10pt，标签 8pt，刻度 8pt
# 5. 统一配色：所有子图使用相同的 PALETTE 序列
```

########## recipe:basic.dual_axis ##########
## 10. 双轴图（淡色填充 + 原色边框柱 + 渐变填充折线 + 相关性标注框 + 峰值高亮）

**场景**：两种不同量纲的数据在同一图中展示，如数量（柱）+ 增长率（线）、产量 + 价格。
**要点**：淡色填充+原色边框柱、渐变填充折线、合并图例、相关性标注框、峰值高亮。

```python
import numpy as np
import matplotlib.pyplot as plt
from _utils.plot_utils import setup_style, save_fig, PALETTE, COLORS, _lighten
setup_style()

years = np.arange(2016, 2025)
bar_data = np.array([120, 145, 168, 195, 230, 260, 310, 355, 400])
line_data = np.array([15.2, 18.5, 22.1, 25.8, 30.2, 35.5, 38.1, 42.3, 45.0])

fig, ax1 = plt.subplots(figsize=(8, 5.5))
ax2 = ax1.twinx()

# ★ 淡色填充 + 原色边框柱
bars = ax1.bar(years, bar_data, width=0.6,
               color=_lighten(PALETTE[0], 0.4), edgecolor=PALETTE[0],
               linewidth=1.2, label='数量', zorder=2)

# 柱子阴影
ax1.bar(years + 0.03, bar_data, width=0.6, color='#cccccc', alpha=0.08, zorder=1)

# 渐变填充折线
line = ax2.plot(years, line_data, 'o-', color=PALETTE[1], linewidth=2.2, markersize=7,
                markeredgecolor='white', markeredgewidth=1.2, label='增长率', zorder=5)
for layer, alpha in enumerate([0.15, 0.08, 0.03]):
    ax2.fill_between(years, min(line_data) - 2 + layer * 0.5,
                     np.array(line_data) - layer * 0.5,
                     alpha=alpha, color=PALETTE[1], linewidth=0)

# 峰值高亮
peak_idx = np.argmax(line_data)
ax2.scatter(years[peak_idx], line_data[peak_idx], s=150, color=PALETTE[1],
            edgecolor='white', linewidth=2.5, zorder=6)
ax2.annotate(f'峰值 {line_data[peak_idx]:.1f}%',
             xy=(years[peak_idx], line_data[peak_idx]),
             xytext=(years[peak_idx] - 2, line_data[peak_idx] + 3),
             fontsize=9, fontweight='bold', color=PALETTE[1],
             arrowprops=dict(arrowstyle='->', color=PALETTE[1], lw=1.2),
             bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                       edgecolor=PALETTE[1], alpha=0.9))

# 相关性标注框
corr = np.corrcoef(bar_data, line_data)[0, 1]
ax1.text(0.02, 0.95, f'r = {corr:.3f}',
         transform=ax1.transAxes, fontsize=9, va='top',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                   edgecolor=COLORS['grid'], alpha=0.9, linewidth=0.8))

ax1.set_xlabel('年份', fontsize=11)
ax1.set_ylabel('数量 (个)', fontsize=11, color=PALETTE[0])
ax2.set_ylabel('增长率 (%)', fontsize=11, color=PALETTE[1])
ax1.tick_params(axis='y', labelcolor=PALETTE[0])
ax2.tick_params(axis='y', labelcolor=PALETTE[1])

# 合并图例
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, labelspacing=0.35, handlelength=1.6, fontsize=9, loc='upper left')

ax1.spines['top'].set_visible(False)
ax1.grid(axis='y', alpha=0.12, linestyle='--', color=COLORS['grid'])
fig.tight_layout()
save_fig(fig, 'figures/fig_dual_axis.pdf')
```

**★ 防遮挡技巧（双轴图专用）：**
```python
# 1. 柱子用半透明（alpha=0.7）：不要遮挡折线
# 2. 折线 zorder=5：确保在柱子上方
# 3. 峰值标注箭头方向：根据数据走势选择，避免和柱子重叠
# 4. 双轴标签颜色和对应数据系列一致
```

---
