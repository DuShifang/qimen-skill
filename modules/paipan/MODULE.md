> **统一总包内部说明：** 本文件原为独立Skill的入口，现只作为内部模块参考。 对外触发和调用以总包根目录 `SKILL.md` 为准；所有命令必须使用 `qimen/modules/...` 的实际路径。 不要调用宿主中旧的同名独立Skill，也不要把旧的绝对路径当成当前总包路径。

# 奇门九宫排盘

运行脚本计算并展示九宫图。**默认排盘方式为时家转盘拆补，寄宫法为寄坤二宫，九星顺逆选项为阳顺阴逆。** 用户未指定流派时直接使用默认，不要求先选流派。引擎和界面独立编写，运行不依赖 APK、服务器或大型星历。引擎版本0.4.1、输出工具0.5.0、JSON格式1.0.0分别管理。不要加载整份节气 JSON 到上下文。

## 输入与方法

1. 提取公历年月日、北京时间的时分、时间层级、盘式及已给设置。沿用对话已明确的值；日期时间、主要流派以及需要用户选择的下一级设置收齐后再起盘，不重复询问已知项。
2. 流派未指定时使用默认 `shijia-zhuanpan-chaibu`，只询问缺少的日期或时间。用户想换流派但未明确哪一种时，按 [settings.md](references/settings.md) 的16种 profile 表列出已实现选项，让用户自己选择。已明确非默认流派时跳过主要流派问题，进入下一层。明确选择默认流派且未要求自定规则时直接使用默认配置。不要把日／月家套成时家定局，或静默替换不支持的流派。
3. **用户指定非默认流派或要求自定规则后，必须继续询问适用且尚未明确的下一级设置。** 读 [settings.md](references/settings.md) 的“按流派逐层询问”分流表，列出可选值和推荐值；独立项目可以同轮问，选择触发新依赖时继续追问。置闰天数只是例子，不限于此项。已明确值不重复问；用户明确“按默认／其余默认”才在授权范围采用推荐值，工具预填不算用户选择。可以内部确定定局和阴阳以判断问题是否适用，收齐选择后才交付最终盘，并将所选适用参数显式传给脚本。
4. “现在”取工具时间并转 UTC+8；“9点”可说明按09:00。只给时辰且钟点未明确时询问。保留原输入日期和23点，引擎处理23:00换日；立春换年、节换月。日家起盘用日柱，月家用月柱，时家用时柱，实际四柱仍一起输出。
5. 默认配置及七项设置的适用范围以 [settings.md](references/settings.md) 为准。默认转盘不调用九星飞布方向；依据 `inactiveSettings` 说明未参与的选值，完整 settings 仍随快照保存。
6. 原有时家转盘／飞盘显示鸣法暗干支。两个混合盘以及日／月家的专用附干层尚未接入，`darkMode=unavailable`，不能声称暗干与原软件一致、用其他暗干填空或把空字符串读成不存在暗干。
7. 茅山、阴盘定局、年家、刻家、自定义盘、农历输入、真太阳时及其他日界未实现；不收集姓名、性别或出生地，不自行推断成其他方法。

## 计算与出图

> **总包特别约定：** 当前包的PNG出图应使用 `../jiepan/scripts/render_snapshot.py`，并指向此模块的 `scripts/render_chart.py`，按总 `SKILL.md` 所示传入**同一快照**的三种源文件。以下命令中的 `<SKILL_ROOT>` 指统一包根目录，使用前替换为实际绝对路径。

定位技能目录后使用由总包根目录解析的绝对路径。输出放当前任务 outputs 或用户指定目录；Windows 用 PowerShell 7，各参数独立引用。正常排盘由脚本调用原引擎一次，校验并形成快照，再从同一份结果生成 JSON、HTML、Markdown；随后尝试出 PNG。

```powershell
node '<SKILL_ROOT>/modules/paipan/scripts/paipan.cjs' --datetime '2026-10-07T09:38' --profile 'shijia-zhuanpan-chaibu' --outdir '<TASK_OUTPUT_DIR>'
python '<SKILL_ROOT>/modules/jiepan/scripts/render_snapshot.py' --html '返回的绝对HTML路径' --json '返回的绝对JSON路径' --markdown '返回的绝对Markdown路径' --outdir '<TASK_OUTPUT_DIR>' --renderer '<SKILL_ROOT>/modules/paipan/scripts/render_chart.py'
```

日家示例 profile 为 `rijia-feipan`；月家为 `yuejia-shenzhuanfeipan`。七项命令行参数和可选值见 `references/settings.md` 或 `--help`。

例如用户已选择“时家转盘置闰、满8天、寄坤二宫”，且其余适用设置也已明确或获默认授权时，使用 `--profile 'shijia-zhuanpan-zhirun' --intercalation-days '8' --center-host 'kun2'`；阳遁时再显式传入其已选 `--yang-gods`。只收到流派名称时，先完成适用下一级选项的收集，不直接运行命令。

- stdout 返回绝对 `html`／`json`／`markdown` 路径、snapshotId、版本和排盘摘要。始终使用返回路径；PNG 路径使用 `render_snapshot.py` 实际返回的 `png` 字段，不从 HTML 文件名推测。每次生成独立快照目录，同一输出目录可保存不同设置或重复输入，不覆盖历史文件。
- 以 JSON 为计算结果，不口算覆盖宫位、四柱或方法。HTML 初始盘面直接使用内嵌快照；交互修改只改变当前试算盘，不回写原 JSON／Markdown。TXT 导出当前页面显示的数据，重开恢复原始盘面。
- PNG 用已有 Python Playwright 和 Chrome／Edge／Chromium；脚本支持 `--browser` 指定路径，不下载浏览器。缺依赖可用现成浏览器工具截取 `.board-sheet`；无法出图时交付 HTML 并说明 PNG 未生成，不擅自安装大型依赖。
- 有文件面板时打开 HTML，用绝对路径图片语法展示实际 PNG。输入错误或年份超出1900—2100时报错后修正，不改用估算。

只需记录盘文时，可优先交付 Markdown，同时保留对应 JSON。转换旧记录使用 `scripts/export_markdown.cjs --json '已有JSON路径' --markdown '新MD路径'`，不重新排盘；缺失的新元数据明确标为“旧记录未提供”，不自动迁移或覆盖原文件。数据异常、格式不支持或写入失败时修正并重试，不能把半成品当完整快照交付。

## 回复与边界

默认展示九宫 PNG，并链接 HTML、Markdown 和 JSON；简述北京时间、时间层级、盘式、实际定局、遁局、四柱、起盘柱、值符值使及调用的设置。上南下北，宫序 `4 9 2 / 3 5 7 / 8 1 6`。转盘寄干随星；星飞时天禽独立；门转时不调用中门，神转时不调用太常。

日／月家派生的定局节气标签可与当前天文节气不同，分别报告 `dingJu` 和 `solar.current`，季节寄宫依据 `hostTerm`。时家置闰同样可能超神或接气。交节前后3分钟按结果提示分钟表边界；不能承诺全范围绝对误差小于一分钟。

核心星门神干经过原生计算输出核对；历法验证与原生排布验证分开，没有完成原软件 Android 整盘逐屏或秒级历算全量对照。空亡驿马按起盘柱通行规则。本 skill 只输出盘面事实，不生成用神、格局或吉凶判断。

## 参考入口

- [settings.md](references/settings.md)：profile、默认值、可选值及分层询问流程。
- [rules.md](references/rules.md)：计算约定、既有核对记录、边界与未实现能力。
- [data-interface.md](references/data-interface.md)：JSON Schema、字段状态、快照写入与版本兼容；接入结构化数据时读。
- [markdown.md](references/markdown.md)：确定性盘文格式及旧 JSON 转换；处理记录导出时读。
- [testing.md](references/testing.md)：测试命令、回归来源与验证范围；维护脚本时读。
