# Problem 1｜EQUATIONS

**状态**：A-8 Final  
**当前状态文件**：`CURRENT_STATE`

## 1. 时间离散

一天划分为 \(N=144\) 个 10 分钟区间：

\[
\Delta t=\frac{1}{6}\text{ h}.
\]

采用 H-END：

\[
0{:}10\rightarrow[0{:}00,0{:}10),\quad \ldots,\quad
0{:}00+1\rightarrow[23{:}50,24{:}00).
\]

负载和光伏由功率换算为区间电量：

\[
E_t^L=L_t\Delta t,\qquad
E_t^{PV}=P_t^{PV}\Delta t.
\]

## 2. 变量

\[
G_t\ge0
\]

计划购电量，kWh；

\[
C_t\ge0
\]

母线侧充电量，kWh；

\[
D_t\ge0
\]

母线侧放电量，kWh；

\[
W_t\ge0
\]

弃光量，kWh；

\[
S_t,\quad t=0,\ldots,144
\]

储能状态，kWh。

## 3. 目标函数

\[
\min J=\sum_{t=1}^{144}p_tG_t.
\]

## 4. 能量平衡

\[
G_t+E_t^{PV}+D_t=E_t^L+C_t+W_t,
\qquad t=1,\ldots,144.
\]

## 5. SOC 状态方程

主效率口径：

\[
\eta_c=\eta_d=0.9.
\]

状态递推：

\[
S_t=S_{t-1}+\eta_c C_t-\frac{D_t}{\eta_d}.
\]

## 6. SOC 与首尾约束

\[
1200\le S_t\le10800.
\]

\[
S_0=S_{144}=6000.
\]

## 7. 充放电功率约束

最大功率为 5000 kW，因此单槽上限：

\[
E_{\max}=5000\times\frac16=833.333333\text{ kWh}.
\]

\[
0\le C_t\le E_{\max},
\]

\[
0\le D_t\le E_{\max}.
\]

## 8. 弃光与购电

\[
0\le W_t\le E_t^{PV},
\]

\[
G_t\ge0.
\]

本问不设置售电变量，也不人为设置外网购电上限。

## 9. 无储能基准

\[
G_t^{base}=\max(E_t^L-E_t^{PV},0).
\]

\[
W_t^{base}=\max(E_t^{PV}-E_t^L,0).
\]

\[
J_{base}=\sum_{t=1}^{144}p_tG_t^{base}.
\]

## 10. 敏感性口径

若将题面的 90% 理解为整体往返效率：

\[
\eta_c=\eta_d=\sqrt{0.9}.
\]

其余模型结构保持不变。
