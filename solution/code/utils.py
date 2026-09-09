"""公共工具：数据加载、孕周解析、matplotlib 中文配置。"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")  # 无界面后端，用于批量出图
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---- 路径 ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "..", "附件.xlsx")
FIG_DIR = os.path.join(BASE_DIR, "figures")
RESULT_DIR = os.path.join(BASE_DIR, "results")
CODE_OUTPUT_DIR = os.path.join(BASE_DIR, "code", "outputs")

for d in (FIG_DIR, RESULT_DIR, CODE_OUTPUT_DIR):
    os.makedirs(d, exist_ok=True)

# ---- matplotlib 中文配置 ----
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False  # 负号正常显示
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.bbox"] = "tight"

THETA = 0.04  # Y 染色体浓度达标阈值 4%


def parse_wk(s: object) -> float:
    """解析孕周字符串（如 ``11w+6``、``16W+1``）为连续数值周。

    Args:
        s: 孕周字符串。

    Returns:
        数值孕周（周 + 天/7）。
    """
    t = str(s).lower()
    if "w" not in t:
        return float("nan")
    w = float(t.split("w")[0])
    d = float(t.split("+")[1]) if "+" in t else 0.0
    return w + d / 7.0


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """加载男胎、女胎数据并做基础清洗。

    Returns:
        (男胎数据, 女胎数据)，均已解析数值孕周。
    """
    xl = pd.ExcelFile(DATA_PATH)
    male = pd.read_excel(xl, "男胎检测数据")
    female = pd.read_excel(xl, "女胎检测数据")

    male["孕周"] = male["检测孕周"].apply(parse_wk)
    female["孕周"] = female["检测孕周"].apply(parse_wk)

    male["达标"] = (male["Y染色体浓度"] >= THETA).astype(int)
    male["异常"] = male["染色体的非整倍体"].notna().astype(int)
    female["异常"] = female["染色体的非整倍体"].notna().astype(int)

    return male, female


def save_fig(fig: plt.Figure, name: str) -> str:
    """保存图片为 PDF 到 figures/ 并返回相对路径。"""
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path, format="pdf")
    plt.close(fig)
    return os.path.join("figures", name)


if __name__ == "__main__":
    m, f = load_data()
    print("男胎:", m.shape, "女胎:", f.shape)
    print("孕周解析 NaN 数:", m["孕周"].isna().sum(), f["孕周"].isna().sum())
    print("男胎达标比例:", round(m["达标"].mean(), 4))
