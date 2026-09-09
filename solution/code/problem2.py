"""问题二：男胎孕妇 BMI 分组 + 每组最佳 NIPT 时点（风险最小）+ 检测误差影响。

方法：
1. 用问题一的固定效应斜率 beta1 作为共享"孕周→浓度"斜率；
2. 每名孕妇估计个体浓度水平 a_i，得个体达标时间 t_i = (theta - a_i)/beta1；
3. 达标时间对 BMI 回归（显著性检验）；
4. 按 BMI 合理分组，以组内"90% 孕妇可靠达标"的最早时点为最佳时点
   （早于此则大量孕妇未达标，结果不可靠；晚于此则治疗窗口风险上升）；
5. 量化检测误差对最佳时点的推迟效应。
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from utils import CODE_OUTPUT_DIR, FIG_DIR, RESULT_DIR, THETA, load_data, save_fig

import matplotlib.pyplot as plt

BETA1 = 0.00319  # 问题一固定效应斜率（Y 浓度每周增量）


def risk_tier(t: float) -> str:
    """把最佳时点映射到题面的风险等级。"""
    if t <= 12:
        return "低风险(早期)"
    if t <= 27:
        return "高风险(中期)"
    return "极高风险(晚期)"


def main() -> None:
    male, _ = load_data()
    df = male[["孕妇代码", "孕周", "孕妇BMI", "Y染色体浓度"]].dropna().copy()
    df.columns = ["code", "week", "bmi", "y"]

    # ---- 1. 个体达标时间 ----
    df["adj"] = df["y"] - BETA1 * df["week"]
    person = df.groupby("code").agg(
        a=("adj", "mean"), bmi=("bmi", "mean"), n=("week", "count")
    ).reset_index()
    person["tstar"] = (THETA - person["a"]) / BETA1

    # ---- 2. 达标时间 vs BMI 回归 ----
    reg = smf.ols("tstar ~ bmi", data=person).fit()
    bmi_slope = reg.params["bmi"]
    bmi_p = reg.pvalues["bmi"]
    print("=== 达标时间 ~ BMI 回归 ===")
    print(reg.summary().tables[1])

    # ---- 3. BMI 合理分组（题面示例区间）----
    bins = [20, 28, 32, 36, 40, 60]
    labels = ["[20,28)", "[28,32)", "[32,36)", "[36,40)", ">=40"]
    person["group"] = pd.cut(person["bmi"], bins=bins, labels=labels, right=False)
    person = person.dropna(subset=["group"])

    # 90% 分位作为"可靠达标"的最佳时点（保证组内 90% 孕妇已达 4%）
    gdf = (
        person.groupby("group", observed=True)
        .agg(
            孕妇数=("tstar", "count"),
            BMI均值=("bmi", "mean"),
            达标时间均值=("tstar", "mean"),
            达标时间std=("tstar", "std"),
            最佳时点90分位=("tstar", lambda x: x.quantile(0.9)),
        )
        .reset_index()
    )
    # 最佳时点限制在可检测窗口 [10, 25] 内
    gdf["最佳时点"] = gdf["最佳时点90分位"].clip(10, 25).round(2)
    gdf["风险等级"] = gdf["最佳时点"].apply(risk_tier)
    gdf["BMI均值"] = gdf["BMI均值"].round(2)
    gdf["达标时间均值"] = gdf["达标时间均值"].round(2)
    gdf["达标时间std"] = gdf["达标时间std"].round(2)
    print("\n=== 各 BMI 组最佳 NIPT 时点 ===")
    print(gdf.to_string(index=False))

    # ---- 4. 检测误差影响 ----
    # 检测误差 sigma_e 使个体达标时间产生 sigma_e/beta1 的不确定性，
    # 可靠时点需后移约 z_0.9 * sigma_e / beta1 周。
    z90 = 1.2816
    sigma_resid = 0.0173  # 问题一混合模型残差标准差
    err_rows = []
    for se in [0.005, 0.01, 0.0173, 0.02]:
        shift = z90 * se / BETA1
        err_rows.append(
            {
                "检测误差σ_e": se,
                "最佳时点后移(周)": round(float(shift), 2),
            }
        )
    edf = pd.DataFrame(err_rows)
    print("\n=== 检测误差对最佳时点的推迟 ===")
    print(edf.to_string(index=False))

    # ---- 5. 图 1：达标时间 vs BMI ----
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(person["bmi"], person["tstar"], s=18, alpha=0.5, color="#1f77b4")
    bmin, bmax = person["bmi"].min(), person["bmi"].max()
    bb = np.linspace(bmin, bmax, 100)
    ax.plot(bb, reg.params["Intercept"] + bmi_slope * bb, color="red", lw=2,
            label=f"斜率={bmi_slope:.3f} 周/BMI, p={bmi_p:.2e}")
    ax.axhline(10, ls=":", color="gray", lw=1, label="最早可测 10 周")
    ax.set_xlabel("孕妇 BMI (kg/m²)")
    ax.set_ylabel("Y 浓度最早达标时间（周）")
    ax.set_title("最早达标时间随 BMI 上升而推迟")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    save_fig(fig, "fig2_1_attainment_vs_bmi.pdf")

    # ---- 6. 图 2：各组最佳时点 ----
    fig, ax = plt.subplots(figsize=(6.5, 4))
    xs = np.arange(len(gdf))
    ax.bar(xs, gdf["最佳时点"], color="#2ca02c")
    for i, r in gdf.iterrows():
        ax.text(i, r["最佳时点"] + 0.15, f"{r['最佳时点']:.1f}周",
                ha="center", fontsize=9)
    ax.axhline(12, ls="--", color="#d62728", lw=1, label="12 周（早期/中期分界）")
    ax.set_xticks(xs)
    ax.set_xticklabels(gdf["group"])
    ax.set_ylabel("最佳 NIPT 时点（周）")
    ax.set_title("各 BMI 组最佳 NIPT 时点（90% 可靠达标）")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    save_fig(fig, "fig2_2_optimal_timing.pdf")

    # ---- 7. 图 3：误差影响 ----
    fig, ax = plt.subplots(figsize=(6, 3.8))
    ax.plot(edf["检测误差σ_e"], edf["最佳时点后移(周)"], "o-", color="#1f77b4", lw=2)
    ax.set_xlabel("检测误差 σ_e")
    ax.set_ylabel("最佳时点后移（周）")
    ax.set_title("检测误差越大，最佳时点越需后移")
    ax.grid(alpha=0.3)
    save_fig(fig, "fig2_3_error_sensitivity.pdf")

    # ---- 8. 保存 ----
    results = {
        "达标时间回归": {
            "截距": round(float(reg.params["Intercept"]), 4),
            "bmi斜率": round(float(bmi_slope), 4),
            "bmi_p": float(bmi_p),
            "R2": round(float(reg.rsquared), 4),
        },
        "分组最佳时点": gdf.to_dict(orient="records"),
        "误差分析": err_rows,
        "参数": {"beta1": BETA1, "theta": THETA, "z90": z90, "sigma_resid": sigma_resid},
    }
    with open(os.path.join(RESULT_DIR, "problem2.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    gdf.to_csv(os.path.join(CODE_OUTPUT_DIR, "problem2_group_timing.csv"), index=False)
    edf.to_csv(os.path.join(CODE_OUTPUT_DIR, "problem2_error_analysis.csv"), index=False)
    print("\n结果已保存到 results/problem2.json")


if __name__ == "__main__":
    main()
