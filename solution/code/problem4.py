"""问题四：女胎异常判定方法（13/18/21 染色体非整倍体分类）。

以 AB 列（染色体非整倍体，空白=正常）为标签，综合 13/18/21/X 的 Z 值、
GC 含量、读段数及相关比例、BMI、年龄、X 浓度等特征建立判定模型，
并与临床 |Z|>3 基线对比。
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from utils import CODE_OUTPUT_DIR, FIG_DIR, RESULT_DIR, load_data, save_fig

import matplotlib.pyplot as plt

# 特征列（女胎数据）
FEATURES = [
    "13号染色体的Z值",
    "18号染色体的Z值",
    "21号染色体的Z值",
    "X染色体的Z值",
    "X染色体浓度",
    "13号染色体的GC含量",
    "18号染色体的GC含量",
    "21号染色体的GC含量",
    "原始读段数",
    "唯一比对的读段数",
    "在参考基因组上比对的比例",
    "重复读段的比例",
    "被过滤掉读段数的比例",
    "GC含量",
    "年龄",
    "孕妇BMI",
]


def evaluate(y_true, y_pred, y_prob=None):
    """计算分类指标。"""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    acc = accuracy_score(y_true, y_pred)
    sens = recall_score(y_true, y_pred)  # 灵敏度/召回
    spec = tn / (tn + fp)  # 特异度
    f1 = f1_score(y_true, y_pred)
    auc = roc_auc_score(y_true, y_prob) if y_prob is not None else float("nan")
    return {
        "准确率": round(float(acc), 4),
        "灵敏度(召回)": round(float(sens), 4),
        "特异度": round(float(spec), 4),
        "F1": round(float(f1), 4),
        "AUC": round(float(auc), 4),
        "TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn),
    }


def main() -> None:
    _, female = load_data()
    fdf = female.dropna(subset=["孕妇BMI"]).copy()
    fdf = fdf[FEATURES + ["异常"]].dropna(subset=FEATURES)

    X = fdf[FEATURES].values
    y = fdf["异常"].values
    print(f"=== 女胎样本：正常 {int((y==0).sum())}，异常 {int((y==1).sum())} ===")

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # ---- 1. 基线：|Z| > 3 判异常 ----
    z_cols = ["13号染色体的Z值", "18号染色体的Z值", "21号染色体的Z值"]
    zmax = np.max(np.abs(fdf[z_cols].values), axis=1)
    base_pred = (zmax > 3).astype(int)
    base_metrics = evaluate(y, base_pred, zmax)
    print("\n=== 基线 |Z|>3 ===")
    print(base_metrics)

    # ---- 2. 逻辑回归 ----
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
    lr_pred = cross_val_predict(lr, X, y, cv=skf, method="predict")
    lr_prob = cross_val_predict(lr, X, y, cv=skf, method="predict_proba")[:, 1]
    lr_metrics = evaluate(y, lr_pred, lr_prob)
    print("\n=== 逻辑回归（5 折交叉验证）===")
    print(lr_metrics)

    # ---- 3. 随机森林 ----
    rf = RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=42)
    rf_pred = cross_val_predict(rf, X, y, cv=skf, method="predict")
    rf_prob = cross_val_predict(rf, X, y, cv=skf, method="predict_proba")[:, 1]
    rf_metrics = evaluate(y, rf_pred, rf_prob)
    print("\n=== 随机森林（5 折交叉验证）===")
    print(rf_metrics)

    # ---- 4. 特征重要性 ----
    rf_full = RandomForestClassifier(n_estimators=500, class_weight="balanced", random_state=42)
    rf_full.fit(X, y)
    imp = pd.Series(rf_full.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print("\n=== 特征重要性 Top ===")
    print(imp.head(10).to_string())

    # ---- 5. 图：ROC 曲线 ----
    from sklearn.metrics import roc_curve
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for name, prob in [("逻辑回归", lr_prob), ("随机森林", rf_prob), ("基线|Z|>3", zmax)]:
        if name == "基线|Z|>3":
            fpr, tpr, _ = roc_curve(y, prob)
        else:
            fpr, tpr, _ = roc_curve(y, prob)
        auc = roc_auc_score(y, prob)
        ax.plot(fpr, tpr, lw=2, label=f"{name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="gray")
    ax.set_xlabel("假阳性率")
    ax.set_ylabel("真阳性率")
    ax.set_title("女胎异常判定 ROC 曲线")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    save_fig(fig, "fig4_1_roc.pdf")

    # ---- 6. 图：特征重要性 ----
    fig, ax = plt.subplots(figsize=(6, 4.5))
    top = imp.head(8)
    ax.barh(top.index[::-1], top.values[::-1], color="#1f77b4")
    ax.set_xlabel("特征重要性")
    ax.set_title("女胎异常判定特征重要性")
    ax.grid(alpha=0.3, axis="x")
    save_fig(fig, "fig4_2_feature_importance.pdf")

    # ---- 7. 图：Z 值分布（正常 vs 异常）----
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for i, c in enumerate(z_cols):
        ax = axes[i]
        ax.hist(fdf.loc[y == 0, c], bins=30, alpha=0.6, color="#2ca02c", label="正常", density=True)
        ax.hist(fdf.loc[y == 1, c], bins=30, alpha=0.6, color="#d62728", label="异常", density=True)
        ax.axvline(3, ls="--", color="k", lw=1)
        ax.axvline(-3, ls="--", color="k", lw=1)
        ax.set_xlabel(c.replace("染色体的Z值", "号Z值"))
        ax.set_title(f"{c.split('号')[0]}号染色体 Z 值分布")
        if i == 0:
            ax.legend(fontsize=8)
    save_fig(fig, "fig4_3_z_distribution.pdf")

    # ---- 8. 保存 ----
    results = {
        "样本量": {"正常": int((y == 0).sum()), "异常": int((y == 1).sum())},
        "基线_Z阈值": base_metrics,
        "逻辑回归": lr_metrics,
        "随机森林": rf_metrics,
        "特征重要性": {k: float(v) for k, v in imp.items()},
    }
    with open(os.path.join(RESULT_DIR, "problem4.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print("\n结果已保存到 results/problem4.json")


if __name__ == "__main__":
    main()
