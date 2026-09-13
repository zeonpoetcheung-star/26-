# P3 To B Figure Workspace

<!-- MH_DATA_FIG_PALETTE=tol_vibrant -->
<!-- MH_DATA_FIG_STYLE=clean_open -->

本工作区用于 Problem 3 论文图。上面两个标记把数据图配色（tol_vibrant）与版式
（clean_open）**钉死**，使其不随工作区目录名变化——与 P1 / P2 绘图 session 对齐。

字体（Times New Roman + SimSun/SimHei）与具体字号由 `figures/_figbase.py` 的
`configure_publication_style()` 统一设置，与 Problem 1 / Problem 2 图件对齐。

数据来源：本交接包的 A-route Final canonical 数据（`data/`），不混入 B-route
的费用或轨迹，不重算、不平滑。
