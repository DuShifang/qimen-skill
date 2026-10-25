# 盘面读取与辅助命令

`scripts/qimen_tools.py` 依赖 Python 3.10+ 标准库。它读取本次指定的盘面文件，JSON 结果输出至 stdout；输入错误输出 stderr，退出码为 2。正常输出、unknown 和 notApplicable 的退出码均为 0，使用者应读取结果的 `state`。脚本不回写输入盘面。

在 skill 目录执行：

```powershell
python './scripts/qimen_tools.py' chart --json './current-chart.json' --palace 4
python './scripts/qimen_tools.py' chart --json './current-chart.json' --layer sky --symbol '乙'
python './scripts/qimen_tools.py' chart --json './current-chart.json' --layer hostedSky
python './scripts/qimen_tools.py' chart --json './current-chart.json' --metadata
python './scripts/qimen_tools.py' xun --json './current-chart.json' --pillar day
python './scripts/qimen_tools.py' xun --json './current-chart.json' --pillar hour
python './scripts/qimen_tools.py' xun --ganzhi '甲子' --pillar hour
python './scripts/qimen_tools.py' door-pattern --json './current-chart.json'
python './scripts/qimen_tools.py' palace-relation --json './current-chart.json' --from-palace 1 --to-palace 3
```

日期到盘面继续使用当前总包 `modules/paipan/` 的排盘引擎，读取其 stdout 返回的真实 JSON 路径，再交给本脚本。读取支持 schema 1.0.0、engine 0.4.1 的现有快照；不支持的版本或错误 profile 明确报错，不替换默认盘。它检查查询所需的结构、层数组、字段状态、profile/settings 一致性，不承担完整 Schema 校验或历算验证。

逐宫 `layer` 使用原字段名：`number/name/direction/earth/sky/hostedEarth/hostedSky/star/door/god/earthGod/dark/darkBranch/bird/empty/horse`。地盘主干、天盘主干与寄干分别返回，符号搜索精确匹配 `present` 字段，不把寄干混入主干。每条事实返回 `pointer/statePointer`，可对应原 JSON。已计算的 false 是 present；empty、notApplicable、notImplemented、unknown 分别保留。

`--metadata` 返回四柱、起盘柱、旬首、六甲所遁仪、值符星、值使及落宫、设置、定局、节气等原始顶层字段。八神层“值符”仍在逐宫 `god`，不与 `chiefStar` 合并。顶层没有逐宫状态表那样的引擎 availability 定义，metadata 的 `stateOrigin` 明确其状态仅表示字段是否提供。

书盘输入使用 `sourceType="book"`、中性 `chartId`、`source` 来源说明、`palaces` 及相应状态。主干字段为 `earth/sky`，寄干字段为 `hostedEarth/hostedSky`；未知格子省略或用 null，状态用 unknown。状态可放逐宫 `fieldStates` 或顶层 `palaceStates`；二者同字段矛盾会报错。明确空字符串必须给出状态。书盘不应提供 engineVersion、snapshotId 或 generator 等引擎身份。

`xun` 独立读取指定柱，不要求完整九宫，也不要求有效 profile。`--pillar` 必须明确，分别运行 day 与 hour 即可得到日空、时空。`door-pattern` 需要明确盘式；源 profile 为空而实际盘式已有依据时，可加 `--profile`。中心有门标记且其寄宫有明确依据时，可加 `--center-door-host 2` 等外宫编号；不要用这一参数猜补未知盘式或寄宫。

派生结果有输入 pointer、计算口径和规则说明，源值与派生值冲突时并列保留。具体算法、适用盘式和 unknown 条件见 [calculation-rules.md](calculation-rules.md)。宫间关系、旬空和门局识别都不输出综合吉凶分数。

运行时不需要理论 corpus、manifest、编辑层索引或历史案例目录。理论按当前子问题读取发布包 `references`；需要检索时可对这些本地文件普通全文搜索，例如 `rg -n '争讼|诉讼' './references'`，不回退到研发底本。
