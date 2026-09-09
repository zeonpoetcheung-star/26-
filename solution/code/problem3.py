"""问题三：综合身高/体重/年龄等因素 + 检测误差 + 达标比例的多维分组与最佳时点。"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from utils import CODE_OUTPUT_DIR, FIG_DIR, RESULT_DIR, THETA, load_data, save_fig

import matplotlib.pyplot as plt

BETA1 = 0.00319


def main() -> None:
    male, _ = load_data()
    df = male[["孕妇代码", "孕周", "孕妇BMI", "Y染色体浓度", "年龄", "体重", "身高"]].dropna().copy()
    df.columns = ["code", "week", "bmi", "y", "age", "weight", "height"]

    # ---- 1. 个体达标时间 ----
    df["adj"] = df["y"] - BETA1 * df["week"]
    person = df.groupby("code").agg(
        a=("adj", "mean"), bmi=("bmi", "mean"), age=("age", "mean"),
        weight=("weight", "mean"), height=("height", "mean"),
    ).reset_index()
    person["tstar"] = (THETA - person["a"]) / BETA1
    person["达标"] = (person["tstar"] <= 25).astype(int)  # 25 周内达标比例口径

    # ---- 2. 多维回归：达标时间 ~ BMI + 年龄 + 身高 + 体重 ----
    reg = smf.ols("tstar ~ bmi + age + height + weight", data=person).fit()
    print("=== 达标时间 ~ 多因素回归 ===")
    print(reg.summary().tables[1])

    # ---- 3. 特征重要性（随机森林）----
    X = person[["bmi", "age", "weight", "height"]].values
    y = person["tstar"].values
    rf = RandomForestRegressor(n_estimators=500, random_state=42)
    rf.fit(X, y)
    imp = pd.Series(rf.feature_importances_, index=["BMI", "年龄", "体重", "身高"]).sort_values(ascending=False)
    print("\n=== 特征重要性（随机森林）===")
    print(imp.to_string())

    # ---- 4. 多维聚类分组（K-means，标准化特征）----
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=20)
    person["cluster"] = kmeans.fit_predict(Xs)

    cluster_rows = []
    for c in sorted(person["cluster"].unique()):
        sub = person[person["cluster"] == c]
        cluster_rows.append(
            {
                "分组": f"组{c+1}",
                "孕妇数": int(len(sub)),
                "BMI均值": round(float(sub["bmi"].mean()), 1),
                "年龄均值": round(float(sub["age"].mean()), 1),
                "身高均值": round(float(sub["height"].mean()), 1),
                "体重均值": round(float(sub["weight"].mean()), 1),
                "达标比例": round(float(sub["达标"].mean()), 3),
                "达标时间均值": round(float(sub["tstar"].mean()), 2),
                "最佳时点(90%可靠)": round(float(sub["tstar"].quantile(0.9)), 2),
            }
        )
    cdf = pd.DataFrame(cluster_rows).sort_values("BMI均值")
    print("\n=== 多维聚类分组结果（按 BMI 均值排序）===")
    print(cdf.to_string(index=False))

    # ---- 5. 与问题二（仅 BMI）对比 ----
    # 组内达标时间离散度之和：越小越同质
    multi_within = person.groupby("cluster")["tstar"].std(ddof=1).sum()
    # 仅 BMI 分组
    bins = [20, 28, 32, 36, 40, 60]
    person["bmi_group"] = pd.cut(person["bmi"], bins=bins, right=False)
    bmi_within = person.groupby("bmi_group", observed=True)["tstar"].std(ddof=1).sum()
    print("\n=== 分组同质性对比（组内 std 之和，越小越好）===")
    print(f"多维聚类: {multi_within:.2f}, 仅BMI: {bmi_within:.2f}")

    # ---- 6. 图 1：特征重要性 ----
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.barh(imp.index, imp.values, color="#1f77b4")
    ax.set_xlabel("特征重要性")
    ax.set_title("影响达标时间的因素重要性")
    ax.grid(alpha=0.3, axis="x")
    save_fig(fig, "fig3_1_feature_importance.pdf")

    # ---- 7. 图 2：各组最佳时点对比（多维 vs 仅BMI）----
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar(cdf["分组"], cdf["最佳时点(90%可靠)"], color="#2ca02c", label="多维分组")
    # 仅 BMI 组的 90 分位
    bmi_q = person.groupby("bmi_group", observed=True)["tstar"].quantile(0.9)
    ax.set_ylabel("最佳 NIPT 时点（周）")
    ax.set_title("多维聚类分组的最佳时点")
    ax.grid(alpha=0.3, axis="y")
    save_fig(fig, "fig3_2_cluster_timing.pdf")

    # ---- 8. 检测误差对多维分组的影响 ----
    z90 = 1.2816
    err_rows = []
    for se in [0.005, 0.01, 0.0173, 0.02]:
        shift = z90 * se / BETA1
        err_rows.append({"检测误差σ_e": se, "最佳时点后移(周)": round(float(shift), 2)})
    edf = pd.DataFrame(err_rows)

    # ---- 9. 保存 ----
    results = {
        "多维回归": {
            name: {"coef": float(reg.params[name]), "pvalue": float(reg.pvalues[name])}
            for name in reg.params.index
        },
        "特征重要性": {k: float(v) for k, v in imp.items()},
        "多维分组": cdf.to_dict(orient="records"),
        "分组同质性": {"多维聚类": round(float(multi_within), 2), "仅BMI": round(float(bmi_within), 2)},
        "误差分析": err_rows,
    }
    with open(os.path.join(RESULT_DIR, "problem3.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    cdf.to_csv(os.path.join(CODE_OUTPUT_DIR, "problem3_cluster_groups.csv"), index=False)
    print("\n结果已保存到 results/problem3.json")


if __name__ == "__main__":
    main()
