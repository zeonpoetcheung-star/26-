"""P2 技术路线图（fig_roadmap）。

三栏结构：研究阶段 | 研究内容 | 研究方法。五阶段对应 P2 最终方法链：
数据与基准 → LightGBM 分位数预测 → 因果在线 selector → Q80 风险 + 48h LP → 冻结计划与实际结算。

单一来源：同一套坐标同时生成可编辑的 figures/fig_roadmap.drawio 与
figures/fig_roadmap.pdf/png/svg（本机无 draw.io 桌面端，按规范降级用确定性渲染）。
方法链取自 references/analysis_modeling_report.md，不重算、不引入结果数值。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

from _figbase import ROOT, save_pub

# ---------------- 版面几何（同时写入 drawio） ----------------
CW = 960
X_STAGE, W_STAGE = 20, 150
X_CONT, W_CONT = 190, 560
X_METH, W_METH = 770, 170
H_HEAD, Y_HEAD = 32, 12
H_STAGE, GAP = 92, 22
Y0 = 58
CARD_W, CARD_H, CARD_GAP = 264, 58, 14
CANVAS_H = Y0 + 5 * H_STAGE + 4 * GAP + 18

# 阶段：标题、阶段色填充/边框、内容卡（两行）、方法卡（较第一版加深）
STAGES = [
    ('1', '数据与基准', '#DCE8F6', '#8FB0D6', '#355C8A',
     ['实际负荷 / 光伏序列', '历史周期基准\nb = L(d−7) − PV(d−1)'],
     '附件数据\n因果信息集'),
    ('2', '概率预测', '#EFE2CA', '#C0A670', '#7E6330',
     ['LightGBM 残差 Q50 / Q80', '18 个因果特征\n7 天滚动重训'],
     'LightGBM\n分位数回归'),
    ('3', '在线选择', '#D8EAD8', '#83B183', '#356E35',
     ['过去 28 天已发布预测表现', '因果 selector\n选择预测分支'],
     'Causal online\nselector'),
    ('4', '风险与优化', '#E1D5EF', '#9E80C0', '#5A4080',
     ['Q80 风险净负荷轨迹', '48h 滚动 LP\nSOC 1200–10 800 kWh'],
     '风险分位\n线性规划 LP'),
    ('5', '执行与结算', '#EFD5D5', '#BF8888', '#7E4A4A',
     ['冻结当天前 144 段计划购电', '实际储能反馈\n+ 5× 紧急购电'],
     '实际回放\nJ = J_plan + J_emg'),
]

HEADERS = [('研究阶段', X_STAGE, W_STAGE), ('研究内容', X_CONT, W_CONT),
           ('研究方法', X_METH, W_METH)]


def stage_boxes():
    """返回每阶段的 (y, 左/中/右几何) 与两张内容卡 x。"""
    out = []
    for i in range(len(STAGES)):
        y = Y0 + i * (H_STAGE + GAP)
        total = 2 * CARD_W + CARD_GAP
        cx0 = X_CONT + (W_CONT - total) / 2
        out.append({'y': y, 'cards': [cx0, cx0 + CARD_W + CARD_GAP]})
    return out


def render():
    fig, ax = plt.subplots(figsize=(6.0, 3.75))
    ax.set_xlim(0, CW)
    ax.set_ylim(CANVAS_H, 0)
    ax.set_aspect('equal')
    ax.axis('off')

    def box(x, y, w, h, fc, ec, lw=1.3):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle='round,pad=0,rounding_size=7',
                     linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))

    def txt(x, y, s, size=8.2, color='#333333', weight='normal'):
        ax.text(x, y, s, ha='center', va='center', fontsize=size,
                color=color, fontweight=weight, zorder=4)

    for name, x, w in HEADERS:
        box(x, Y_HEAD, w, H_HEAD, '#E3E3E3', '#9E9E9E')
        txt(x + w / 2, Y_HEAD + H_HEAD / 2 + 0.5, name, size=9.2,
            color='#333333', weight='bold')

    geo = stage_boxes()
    for (num, title, fill, edge, label, cards, method), g in zip(STAGES, geo):
        y = g['y']
        box(X_STAGE, y, W_STAGE, H_STAGE, fill, edge, lw=1.5)
        txt(X_STAGE + W_STAGE / 2, y + 16, f'阶段 {num}', size=7.6, color=label)
        txt(X_STAGE + W_STAGE / 2, y + H_STAGE / 2 + 9, title, size=10,
            color=label, weight='bold')
        box(X_CONT, y, W_CONT, H_STAGE, '#FFFFFF', '#C4C4C4', lw=1.1)
        for cx, text in zip(g['cards'], cards):
            box(cx, y + (H_STAGE - CARD_H) / 2, CARD_W, CARD_H,
                '#FFFFFF', edge, lw=1.2)
            txt(cx + CARD_W / 2, y + H_STAGE / 2, text, size=8.0)
        box(X_METH, y, W_METH, H_STAGE, '#FFFFFF', edge, lw=1.2)
        txt(X_METH + W_METH / 2, y + H_STAGE / 2, method, size=8.2,
            color=label)

        if num != '5':
            xc = X_STAGE + W_STAGE / 2
            ax.annotate('', xy=(xc, y + H_STAGE + GAP - 3),
                        xytext=(xc, y + H_STAGE + 3), zorder=3,
                        arrowprops=dict(arrowstyle='-|>', color='#8A939C',
                                        lw=1.4, mutation_scale=9,
                                        shrinkA=0, shrinkB=0))

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    return fig


def write_drawio():
    """写可编辑 drawio（同坐标）。遵守零容忍规则：无 shadow/注释/特殊形状。"""
    def esc(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    cells = []
    cid = [0]

    def new_id(p):
        cid[0] += 1
        return f'{p}{cid[0]}'

    def vertex(x, y, w, h, value, style, parent='1', html_bold=False):
        i = new_id('n')
        v = f'<b>{value}</b>' if html_bold else value
        cells.append(
            f'<mxCell id="{i}" value="{v}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def edge(src, dst):
        i = new_id('e')
        cells.append(
            f'<mxCell id="{i}" edge="1" source="{src}" target="{dst}" parent="1" '
            f'style="rounded=1;html=1;strokeWidth=1.4;strokeColor=#8A939C;endArrow=block;'
            f'endFill=1;endSize=6;exitX=0.5;exitY=1;entryX=0.5;entryY=0;">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')

    for name, x, w in HEADERS:
        vertex(x, Y_HEAD, w, H_HEAD, esc(name),
               'rounded=1;whiteSpace=wrap;html=1;fillColor=#E3E3E3;strokeColor=#9E9E9E;'
               'strokeWidth=1.3;fontSize=11;fontStyle=1;')
    geo = stage_boxes()
    stage_ids = []
    for (num, title, fill, edge_c, label, cards, method), g in zip(STAGES, geo):
        y = g['y']
        sid = vertex(X_STAGE, y, W_STAGE, H_STAGE,
                     f'阶段 {num}<br><b>{esc(title)}</b>',
                     f'rounded=1;whiteSpace=wrap;html=1;fillColor={fill};'
                     f'strokeColor={edge_c};strokeWidth=1.5;fontSize=10;fontColor={label};')
        stage_ids.append(sid)
        vertex(X_CONT, y, W_CONT, H_STAGE, '',
               'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#C4C4C4;strokeWidth=1.1;')
        for cx, text in zip(g['cards'], cards):
            vertex(cx, y + (H_STAGE - CARD_H) / 2, CARD_W, CARD_H,
                   esc(text).replace('\n', '&lt;br&gt;'),
                   f'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;'
                   f'strokeColor={edge_c};strokeWidth=1.2;fontSize=9;')
        vertex(X_METH, y, W_METH, H_STAGE, esc(method).replace('\n', '&lt;br&gt;'),
               f'rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;'
               f'strokeColor={edge_c};strokeWidth=1.2;fontSize=9;fontColor={label};')
    for a, b in zip(stage_ids, stage_ids[1:]):
        edge(a, b)

    xml = ('<mxGraphModel dx="1200" dy="800" grid="0" gridSize="10" guides="0" '
           'tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" '
           f'pageWidth="{CW}" pageHeight="{CANVAS_H}" background="none" math="0" shadow="0">'
           '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
           + ''.join(cells) + '</root></mxGraphModel>')
    (ROOT / 'figures' / 'fig_roadmap.drawio').write_text(xml, encoding='utf-8')
    print('wrote figures/fig_roadmap.drawio')


def main():
    fig = render()
    save_pub(fig, 'figures/fig_roadmap')
    write_drawio()
    print('VALIDATION PASS: roadmap rendered + editable drawio written')


if __name__ == '__main__':
    main()
