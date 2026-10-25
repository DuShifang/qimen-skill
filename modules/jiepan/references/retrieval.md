# 精确查表与原文回读

在本 skill 目录按当前需要调用，不要求每题遍历条目。返回原文、适用条件、标题、相对文件、1 起算的闭合行段和 0 起算右端不含的原文件 UTF-8 字节段。`state: unknown` 表示缺项或歧义，先看 reason/candidates；非法输入退出码为 2。`scope: partial` 指原文选段，`full` 指明确请求全文。

```powershell
python './scripts/qimen_tools.py' lookup --kind topic --item '借入、放贷与讨债'
python './scripts/qimen_tools.py' lookup --kind star --item '天心'
python './scripts/qimen_tools.py' lookup --kind door --item '开门'
python './scripts/qimen_tools.py' lookup --kind god --item '九地'
python './scripts/qimen_tools.py' lookup --kind palace --item '4'
python './scripts/qimen_tools.py' lookup --kind stem-symbol --item '辛'
python './scripts/qimen_tools.py' lookup --kind branch --item '巳'
python './scripts/qimen_tools.py' lookup --kind stem --sky '丙' --earth '戊'
python './scripts/qimen_tools.py' lookup --kind door-relation --item '开门' --second '丁' --stem-layer sky
python './scripts/qimen_tools.py' twelve-state --stem '辛' --branch '巳'
python './scripts/qimen_tools.py' twelve-state --stem '辛' --palace 4
```

`stem` 的前者明确是天盘、后者明确是地盘；主干还是寄干须保留当次选层，不能从不同层凑组合。返回逆序对照、原文前项或具名依赖及共用限制，所取片段有原文字段，不替代当前问事的判断。甲无独立表项时返回 unknown，不自动换成某一六仪。门加门须另行确认活动门、本位门与盘式；门加干必须用 `--stem-layer sky|earth|hostedSky|hostedEarth` 明确当前层，工具不将它升级成原书统一指定的层。

具名依赖只在原文明示参照或比较、且名称能唯一指向另一条目时标为 `original named comparison`，并给出引用措辞与目标名称定义的原文行/UTF-8证据。仅共享格名不自动附项；引用对象多义或无法确认时列入 `unresolvedNamedReferences`，可继续回读，不暗示作者指定了某一对照项。逆序与“前者”等原文依赖另行保留。

`twelve-state` 读的是天干寄生十二状态表，与 JSON 字段的 present/unknown 等可用状态不同。按原表给具体干和具体支的值，月令适用条件随结果返回；双支宫分别列值，不合成一个宫状态，中宫不造地支。也可从当前指定 JSON 取一个明确主/寄层：

```powershell
python './scripts/qimen_tools.py' twelve-state --json './current-chart.json' --palace 4 --layer hostedSky
```

源字段 unknown 或非单干时不推测，不回写原盘；主干与寄干分开返回输入 pointer。没有明确选支时，采用原文给定的该宫各支逐项查表。

小节标题可先列出，再定位或回读完整文件：

```powershell
python './scripts/qimen_tools.py' theory --files
python './scripts/qimen_tools.py' theory --file 'references/timing.md' --sections
python './scripts/qimen_tools.py' theory --file 'references/timing.md' --section '已判断可成的事项'
python './scripts/qimen_tools.py' theory --file 'references/timing.md' --full
```

小节名须以实际 `--sections` 结果为准；不存在或不唯一时返回 unknown/candidates。`--files` 列出发布包中可查询的 19 份纯理论集合；adapter.md 与 calculation-rules.md 是原命令接口和计算说明，仍按原导航读取，不列入此查表集合。导航、脚本、任意额外文件、研发材料和私人文件不进入检索。绝对路径、路径逃逸、隐藏路径、symlink/junction 均拒绝。需要更完整条件时，使用结果中的 fullRead 指向同一允许文件全文；不向包外寻找案例。
