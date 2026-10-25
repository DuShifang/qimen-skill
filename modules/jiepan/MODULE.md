> **统一总包内部说明：** 本文件原为独立Skill的入口，现只作为内部模块参考。 对外触发和调用以总包根目录 `SKILL.md` 为准；所有命令必须使用 `qimen/modules/...` 的实际路径。 不要调用宿主中旧的同名独立Skill，也不要把旧的绝对路径当成当前总包路径。

# 奇门综合解盘

依据当前问题与当前盘面综合分析。理论按需读取，计算和解释分工；用户当次给出的背景、盘面与补充都是正常输入。

## 输入和盘面

已有指定盘面时，先保留它的身份、盘式和原字段，不另起盘替换。JSON 接入与主寄干查询见 [adapter.md](references/adapter.md)。图上未印的空亡等仍记为未知，但有明确干支时可以另算，派生结果不回写原值。

只有起盘信息时，使用当前统一包内 `../paipan/` 模块，读取其 MODULE.md 与设置说明，按已选择或已授权的设置运行。按总 `SKILL.md` 里的相对模块路径定位；不要引用旧宿主的安装目录。使用实际 stdout 返回的 JSON 路径继续，不凭记忆排四柱或覆盖排盘。历史问事用明确历史时间；时刻或设置确实影响起盘而尚缺时，补问相应信息。已有授权无需重复收集。

本技能衔接起盘后的出图统一使用 `python scripts/render_snapshot.py --html 'stdout返回的HTML路径' --json 'stdout返回的JSON路径' --markdown 'stdout返回的markdown路径' --outdir '当前任务输出目录'`（脚本用本包实际绝对路径）。它直接调用当前总包内的排盘渲染器，先自动暂存同内容HTML到独立短路径，校验PNG后返回真实附件路径；不先尝试长路径再人工复制。总包始终建议明确传入 `--renderer '../paipan/scripts/render_chart.py的实际绝对路径'`；默认值也指向总包内渲染器。只支持当前自包含快照，缺文件、快照不一致、外部资源或浏览器失败会明确报错。成功后按返回的PNG、HTML、Markdown、JSON路径交付，宿主支持时展示PNG；失败仍可解读有效JSON，但须明确未出图，不能捏造附件。已有给定盘而未要求出图时无需调用。

本包 `scripts/qimen_tools.py` 负责读层、查宫和确定性派生。旬首旬空需明确使用哪一柱；日空、时空分开。门局识别受盘式和布局条件约束。命令及条件见 [calculation-rules.md](references/calculation-rules.md)。脚本没有某项功能，不意味着输入充分且理论清楚时不能手工推导。

## 理解、读取与综合

先读 [principles.md](references/principles.md) 和必要的 [terminology.md](references/terminology.md)。区分当前叙述者、当时求测者、实际当事人和是否真实代问；第三人称或“朋友”本身不确定代问关系。把当前问题拆成实际子事项，选主要对象与有作用的辅助对象，再读取相关理论。

| 当前需要 | 理论入口 |
|---|---|
| 宫位、干支、星门神的象义与查表 | [symbols.md](references/symbols.md) |
| 旺衰、主客、刑墓空亡和格局 | [patterns.md](references/patterns.md) |
| 迟速、远近、成功失败及找寻应期 | [timing.md](references/timing.md) |
| 考试、成绩与录取 | [examination.md](references/topics/examination.md) |
| 求职、岗位、调动与留退 | [work-transfer.md](references/topics/work-transfer.md) |
| 投资、买卖、合伙、借贷 | [business-wealth.md](references/topics/business-wealth.md) |
| 遗失、盗失与查找 | [lost-property.md](references/topics/lost-property.md) |
| 诉讼、争议与调解 | [litigation.md](references/topics/litigation.md) |
| 其他事项 | [other-topics.md](references/topics/other-topics.md) |

复合事项可以访问多个模块；一个标签不限定整题。需要补充理论时，在本包 references 中检索相关词并读前后条件，不必一次读完全部文件。

用神可以多重，先确定主要对应，再比较候选取象和支持、相反条件。可将象义用于现代场景，但应有清楚的对应理由。宫内竖看与宫间横看分开，层次和口径不可混用；主寄干、八神值符与值符星分别处理。九星旺衰本包采用落宫为主、兼看月令的口径，详见 patterns。

围绕问事权衡，不以吉凶符号计数决定结论。已有资料足以判断部分内容时继续；缺项影响结论力度或精度，只在确实影响取用、起盘或关键分支时补问。不补造出生年、经历、未刊字段或精确日期。

准备把某门吉凶、门宫关系或宫间生克作为影响主判断的重要依据时，先按[八门条件](references/tables/doors.md)与[状态表](references/tables/states.md)核清落宫、双方五行及迫、制、和、义的方向，再结合当月双方实际力量约束这条依据。凶门受制可减弱不利，不能照常累加；吉门受制、门迫、凶门受生也须区别对象和作用程度，不能见生即吉、见克即凶。让关键限制实际改变该证据的力度或判断分支，同时保留其他独立阻力。弱辅助取象不强求完整旺衰报告，成稿只自然交代影响结论的条件。

## 回答

直接回答所问事项，再说明起主要作用的盘面、权衡、必要分支及有依据的时间或行动建议。自然表达，篇幅随问题而定，不要求遍历九宫、固定字数或列满步骤。通常无需内部编号或来源表；用户要求研究说明时，再展开理论出处和口径。合理推论与已知事实分别表达。

按项查原表、小节或回读全文，可用 `scripts/qimen_tools.py` 的 `lookup`、`twelve-state` 和 `theory`，见 [精确读取](references/retrieval.md)。结果保留原文条件与顺逆依赖；需要时继续扩读，不要求每题遍历查表。
