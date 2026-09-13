# P2 Figure Workspace

<!-- MH_DATA_FIG_PALETTE=tol_vibrant -->
<!-- MH_DATA_FIG_STYLE=clean_open -->

本工作区用于 Problem 2 论文图。上面两个标记把数据图配色（tol_vibrant）与版式
（clean_open）**钉死**，使其不随工作区目录名变化——否则目录改名会导致自动抽到的
配色改变（如 To B → TO B 会从 tol_vibrant 变成 okabe_ito）。

字体（Times New Roman + SimSun/SimHei）与具体字号由 `figures/_figbase.py` 的
`configure_publication_style()` 统一设置，与 P1 绘图 session 对齐。
