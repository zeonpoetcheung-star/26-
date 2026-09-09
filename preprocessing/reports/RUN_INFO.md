# A-1.1 运行信息

- 实际运行时间：`2026-09-06T19:33:53+08:00`
- 当前工作目录：`D:\2026数模国赛`
- 脚本路径：`D:\2026数模国赛\scripts\prepare_data.py`
- 输入路径：`D:\2026数模国赛\附件.xlsx`
- 输出根目录：`D:\2026数模国赛`
- 输入 SHA-256：`14827156218bd4f7e4f16db4aa6d9f757c6648379e038ae6c6b58383648614af`
- Python 可执行文件：`C:\Users\JINPU\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Python 版本：`3.12.14`
- openpyxl 版本：`3.1.5`
- 操作系统：`Windows-11-10.0.26200-SP0`

## 实际运行命令

```powershell
C:\Users\JINPU\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe D:\2026数模国赛\scripts\prepare_data.py --input D:\2026数模国赛\附件.xlsx --output-root D:\2026数模国赛
```

## 本次生成文件

- `D:\2026数模国赛\data\processed_male.csv`
- `D:\2026数模国赛\data\processed_female.csv`
- `D:\2026数模国赛\reports\DATA_CHECK.md`
- `D:\2026数模国赛\reports\DATA_ISSUES.csv`
- `D:\2026数模国赛\reports\RUN_INFO.md`

## 已实际执行的检查

- 成功打开工作簿并读取全部可见工作表的 A—AE 列。
- 核对每个输出数据表的行数与输入行数一致。
- 核对 record_id 在各输出表内唯一。
- 核对女胎 U、V 派生字段全空，未填 0。
- 核对脚本没有删除、合并或平均记录。
- 对任务单所列参考计数进行了独立复算；结果见 DATA_CHECK.md。
