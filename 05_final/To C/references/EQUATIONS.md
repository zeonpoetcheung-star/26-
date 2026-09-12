# Problem 2｜Candidate Equations

## 净负荷

\[
N_{d,t}=L_{d,t}-PV_{d,t}.
\]

## 历史基准

\[
b_{d,t}=L_{d-7,t}-PV_{d-1,t}.
\]

## LightGBM残差目标

\[
r_{d,t}=N_{d,t}-b_{d,t}.
\]

## Q80风险需求

\[
\widehat n_{d,t}^{80}
=
\widehat N_{d,t}^{80}\Delta t,
\qquad
\Delta t=1/6.
\]

## 48h名义LP

\[
\min \sum_k p_kG_k
\]

\[
G_k+D_k=\widehat n_k+C_k+W_k
\]

\[
S_k=S_{k-1}+0.9C_k-\frac{D_k}{0.9}
\]

\[
1200\le S_k\le10800
\]

\[
0\le C_k,D_k\le\frac{5000}{6}
\]

\[
G_k,W_k\ge0
\]

\[
S_{288}=S_0.
\]

不设置 \(S_{144}=S_0\)。

## 实际反馈

当前槽计划购电为 \(g\)，实际负荷/PV电量为 \(l,v\)，当前SOC为 \(s\)。

\[
\bar c(s)=
\max\left(0,\min\left\{\frac{5000}{6},\frac{10800-s}{0.9}\right\}\right)
\]

\[
\bar d(s)=
\max\left(0,\min\left\{\frac{5000}{6},0.9(s-1200)\right\}\right)
\]

\[
a=\operatorname{clip}(g+v-l,-\bar d,\bar c)
\]

\[
C^{act}=\max(a,0),\qquad D^{act}=\max(-a,0)
\]

\[
r=l-v+C^{act}-D^{act}-g
\]

\[
E^{emg}=\max(r,0)
\]

并按实际动作更新：

\[
S' = S+0.9C^{act}-D^{act}/0.9.
\]

## 实际费用

\[
J^{plan}=\sum_t p_tG_t^{plan}
\]

\[
J^{emg}=\sum_t5p_tE_t^{emg}
\]

\[
J^{total}=J^{plan}+J^{emg}.
\]
