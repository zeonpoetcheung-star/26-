"""问题一：Y 染色体浓度与孕周、BMI 的关系模型及显著性检验。

采用面板数据（纵向重复测量）分析方法：组内（固定效应）分离孕周效应，
组间（between）分离 BMI 效应，并用混合效应模型综合。
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from utils import CODE_OUTPUT_DIR, FIG_DIR, RESULT_DIR, load_data, save_fig

import matplotlib.pyplot as plt
from scipy import stats as sps


def main() -> None:
    male, _ = load_data()
    df = male[["孕妇代码", "孕周", "孕妇BMI", "Y染色体浓度", "年龄", "体重", "身高"]].dropna().copy()
    df.columns = ["code", "week", "bmi", "y", "age", "weight", "height"]

    # ---- 1. 横截面相关性（会被混淆）----
    pearson = {
        "孕周": df["week"].corr(df["y"]),
        "BMI": df["bmi"].corr(df["y"]),
        "年龄": df["age"].corr(df["y"]),
        "体重": df["weight"].corr(df["y"]),
        "身高": df["height"].corr(df["y"]),
    }
    spearman = {
        k: df[k].corr(df["y"], method="spearman")
        for k in ["week", "bmi", "age", "weight", "height"]
    }

    # ---- 2. 面板分解：组内（within）与组间（between）----
    df["y_mean"] = df.groupby("code")["y"].transform("mean")
    df["week_mean"] = df.groupby("code")["week"].transform("mean")
    df["bmi_mean"] = df.groupby("code")["bmi"].transform("mean")
    df["y_w"] = df["y"] - df["y_mean"]
    df["week_w"] = df["week"] - df["week_mean"]

    within_corr = df["y_w"].corr(df["week_w"])

    # 组内（固定效应）回归：Y 的组内变化 ~ 孕周组内变化
    fe = smf.ols("y_w ~ week_w - 1", data=df).fit()
    fe_slope = fe.params["week_w"]
    fe_se = fe.bse["week_w"]
    fe_t = fe.tvalues["week_w"]
    fe_p = fe.pvalues["week_w"]

    # 组间回归：Y 个体均值 ~ BMI
    gb = df.drop_duplicates("code")
    between = smf.ols("y_mean ~ bmi_mean", data=gb).fit()
    between_slope = between.params["bmi_mean"]
    between_p = between.pvalues["bmi_mean"]
    between_t = between.tvalues["bmi_mean"]
    between_r2 = between.rsquared

    # ---- 3. 混合效应模型（随机截距）----
    me = smf.mixedlm("y ~ week + bmi", data=df, groups=df["code"]).fit(reml=True)
    me_coef = {k: float(v) for k, v in me.params.items()}
    me_p = {k: float(v) for k, v in me.pvalues.items()}

    # 含交互与二次项对比（用 ML 估计以比较 AIC/BIC）
    n = len(df)
    me_ml = smf.mixedlm("y ~ week + bmi", data=df, groups=df["code"]).fit(reml=False)
    me_int_ml = smf.mixedlm("y ~ week + bmi + week:bmi", data=df, groups=df["code"]).fit(
        reml=False
    )
    df["week2"] = df["week"] ** 2
    me_quad_ml = smf.mixedlm(
        "y ~ week + bmi + week:bmi + week2", data=df, groups=df["code"]
    ).fit(reml=False)

    def _aic_bic(m, k_fixed, k_var):
        aic = -2 * m.llf + 2 * (k_fixed + k_var)
        bic = -2 * m.llf + (k_fixed + k_var) * np.log(n)
        return round(aic, 2), round(bic, 2)

    aic1, bic1 = _aic_bic(me_ml, 3, 2)
    aic2, bic2 = _aic_bic(me_int_ml, 4, 2)
    aic3, bic3 = _aic_bic(me_quad_ml, 5, 2)
    compare = pd.DataFrame(
        [
            {"模型": "混合效应_线性", "AIC": aic1, "BIC": bic1, "logLik": round(float(me_ml.llf), 2)},
            {"模型": "混合效应_交互", "AIC": aic2, "BIC": bic2, "logLik": round(float(me_int_ml.llf), 2)},
            {"模型": "混合效应_交互二次", "AIC": aic3, "BIC": bic3, "logLik": round(float(me_quad_ml.llf), 2)},
        ]
    )

    # 显著性汇总
    summary_rows = [
        {"效应": "组内孕周(固定效应)", "系数": round(fe_slope, 5), "统计量": round(fe_t, 3), "p值": f"{fe_p:.2e}"},
        {"效应": "组间BMI", "系数": round(between_slope, 5), "统计量": round(between_t, 3), "p值": f"{between_p:.2e}"},
        {"效应": "混合模型-孕周", "系数": round(me_coef["week"], 5), "统计量": round(me.tvalues["week"], 3), "p值": f"{me_p['week']:.2e}"},
        {"效应": "混合模型-BMI", "系数": round(me_coef["bmi"], 5), "统计量": round(me.tvalues["bmi"], 3), "p值": f"{me_p['bmi']:.2e}"},
    ]
    summary_df = pd.DataFrame(summary_rows)

    print("=== 横截面相关（Pearson）===")
    print({k: round(v, 4) for k, v in pearson.items()})
    print("=== 组内 Y~week 相关（固定效应）===", round(within_corr, 4))
    print("=== 面板分解 ===")
    print(summary_df.to_string(index=False))
    print("\n=== 混合效应模型选择 ===")
    print(compare.to_string(index=False))
    print("\n=== 混合效应线性模型 ===")
    print(me.summary().tables[1])

    # ---- 4. 图 ----
    # (a) Y vs 孕周 按 BMI 分层（横截面，展示混淆）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    bmi_grp = pd.cut(
        df["bmi"], bins=[20, 28, 32, 36, 40, 50],
        labels=["[20,28)", "[28,32)", "[32,36)", "[36,40)", ">=40"],
    )
    colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e"]
    for i, (g, c) in enumerate(
        zip(["[20,28)", "[28,32)", "[32,36)", "[36,40)", ">=40"], colors)
    ):
        sub = df[bmi_grp == g]
        axes[0].scatter(sub["week"], sub["y"], s=10, alpha=0.5, color=c, label=f"BMI {g}")
    axes[0].axhline(0.04, ls="--", color="k", lw=1, label="达标阈值 4%")
    axes[0].set_xlabel("孕周（周）")
    axes[0].set_ylabel("Y 染色体浓度")
    axes[0].set_title("横截面：Y 浓度与孕周（按 BMI 分层）")
    axes[0].legend(fontsize=7)
    axes[0].grid(alpha=0.3)

    # (b) 组内趋势（去均值后）展示强相关
    axes[1].scatter(df["week_w"], df["y_w"], s=10, alpha=0.4, color="#1f77b4")
    w = np.linspace(df["week_w"].min(), df["week_w"].max(), 100)
    axes[1].plot(w, fe_slope * w, color="red", lw=2, label=f"斜率={fe_slope:.4f}/周")
    axes[1].set_xlabel("孕周（组内去均值，周）")
    axes[1].set_ylabel("Y 浓度（组内去均值）")
    axes[1].set_title("组内（固定效应）：Y 浓度随孕周上升")
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    save_fig(fig, "fig1_1_scatter_within.pdf")

    # (c) 组间 Y_mean vs BMI
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.scatter(gb["bmi_mean"], gb["y_mean"], s=14, alpha=0.55, color="#2ca02c")
    bmin, bmax = gb["bmi_mean"].min(), gb["bmi_mean"].max()
    bb = np.linspace(bmin, bmax, 100)
    ax.plot(bb, between.params["Intercept"] + between_slope * bb, color="red", lw=2,
            label=f"斜率={between_slope:.4f}")
    ax.set_xlabel("孕妇 BMI (kg/m²)")
    ax.set_ylabel("Y 染色体浓度（个体均值）")
    ax.set_title("组间：Y 浓度随 BMI 下降")
    ax.legend()
    ax.grid(alpha=0.3)
    save_fig(fig, "fig1_2_between_bmi.pdf")

    # (d) 混合模型拟合曲线
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for bmi_val in [25, 30, 35, 40]:
        ww = np.linspace(df["week"].min(), df["week"].max(), 100)
        pred = me_coef["Intercept"] + me_coef["week"] * ww + me_coef["bmi"] * bmi_val
        ax.plot(ww, pred, label=f"BMI={bmi_val}")
    ax.axhline(0.04, ls="--", color="k", lw=1, label="达标阈值 4%")
    ax.set_xlabel("孕周（周）")
    ax.set_ylabel("Y 染色体浓度")
    ax.set_title("混合效应模型拟合：Y = 常数 + beta1*孕周 + beta2*BMI")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    save_fig(fig, "fig1_3_fitted.pdf")

    # ---- 5. 保存结果 ----
    results = {
        "pearson": {k: round(float(v), 4) for k, v in pearson.items()},
        "spearman": {k: round(float(v), 4) for k, v in spearman.items()},
        "within_corr": round(float(within_corr), 4),
        "panel_decomposition": summary_df.to_dict(orient="records"),
        "fixed_effect_week": {
            "slope": round(float(fe_slope), 5),
            "se": round(float(fe_se), 5),
            "t": round(float(fe_t), 3),
            "p": float(fe_p),
        },
        "between_bmi": {
            "slope": round(float(between_slope), 5),
            "t": round(float(between_t), 3),
            "p": float(between_p),
            "r2": round(float(between_r2), 4),
        },
        "mixed_model": {
            "coef": me_coef,
            "pvalues": me_p,
            "group_var": float(me.cov_re.iloc[0, 0]) if me.cov_re is not None else None,
        },
        "model_comparison": compare.to_dict(orient="records"),
    }
    with open(os.path.join(RESULT_DIR, "problem1.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    summary_df.to_csv(os.path.join(CODE_OUTPUT_DIR, "problem1_summary.csv"), index=False)
    print("\n结果已保存到 results/problem1.json")


if __name__ == "__main__":
    main()
