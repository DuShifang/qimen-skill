# JSON 接口、快照与版本

正式接口为 [paipan.schema.json](../assets/paipan.schema.json)，采用 [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation)。此文件规定数据结构；结构合法不等于独立证明术数算法正确。

## 版本规则

| 标记 | 当前值 | 变更规则 |
|---|---|---|
| `engineVersion` | `0.4.1` | 原排盘引擎的规则／计算版本；本次未改动 |
| `schemaVersion` | `1.0.0` | JSON接口版本；不兼容变更升主版本，向后兼容字段扩展升次版本，说明修正升补丁 |
| `generator.version` | `0.5.0` | Skill输出工具版本；命名、文件生成、HTML模板或工具行为改变时更新 |
| `generator.markdownVersion` | `1.0.0` | Markdown导出格式版本；正文或字段布局改变时更新 |
| `timeConventions.calendarDataVersion` | `de440s-minute-1898-2101-v1` | 现有分钟节气表的资料版本；实际表改变时更新，不能只沿用旧标记 |

发布前同步工具常量、文档和测试；增加导出格式不单独改变排盘引擎版本。新版与未带`schemaVersion`的历史JSON分开识别，未知格式版本明确报错。本版语义校验只接受已支持的引擎及时间约定，不能把未来引擎数据默认为已兼容。

## 快照身份与写入

`snapshotId`格式为：`qimen_YYYY-MM-DD_HHMM_PROFILE_UUIDv4`。日期时间与profile便于归档检索，UUID作为每次生成记录的独立主键；设置不编码进冗长文件名，而完整绑定在对应JSON内。快照记录输入、UTC+8与23点日界、全部标准化settings（包括未参与项）、inactiveSettings、引擎／格式／工具／历法资料／Markdown版本及UTC生成时间。

此方案每次都建立新记录，不按输入去重；完全相同输入重复执行也产生新snapshotId。不同设置、未参与设置的变化、不同profile或版本都不会被错误合并。无需内容hash或缓存，UUID冲突／已有同ID记录明确报错，不复用或覆盖。

输出目录结构：

```text
用户输出目录/
  snapshotId/
    snapshotId.json
    snapshotId.html
    snapshotId.md
    snapshotId.png    # 随后成功出图才存在
```

名称只含ASCII字母、数字、连字符、下划线和扩展名；单文件名不足110字符，兼容Windows。输出目录本身过长时仍可能受宿主路径长度限制。CLI返回实际绝对路径，调用方不能猜旧文件名。

写入流程：一次原引擎计算→封装及Schema／一致性校验→独立临时目录→写入JSON／HTML／MD并读回核对→目录整体rename到正式ID。短期`.lock`目录保证相同ID写入的所有权；已有正式目录拒绝写入。普通失败清除本次临时目录和锁，不移除任何历史记录。硬中断可能留下`.qimen-stage-*`或`.lock`，它们不是已提交快照，不能当成盘文；不自动接管或删除其他生成任务的残留。PNG另行安全生成，失败不破坏已提交三文件组；缺PNG不能被报告为出图成功。

HTML、JSON、Markdown使用同一份已计算结果。HTML初始直接读内嵌快照；页面交互产生当前试算盘，提示不会回写原JSON／MD。TXT导出当前显示结果。记录的不可变性由生成工具不覆写来保证，不等同于防止用户手工编辑文件；未增加签名或防篡改数据库。目录rename只针对同一输出目录所在的本地文件系统，不承诺任意网络盘或硬件断电后的持久性。

## 字段定义

保留原引擎字段与含义，新增顶层元数据和`palaceStates`，不重命名`palaces`、不把空字符串转成null。

| 字段组 | 定义 |
|---|---|
| `schemaVersion/engineVersion/snapshotId/generator/generatedAt` | 格式、引擎、记录身份、输出器版本、UTC生成时刻 |
| `input/profile/mode/date/timeConventions` | 原公历输入字符串、16种profile之一、calendar模式、原引擎公历分解及时间戳、时间和资料约定 |
| `settings/inactiveSettings` | 10个标准化设置字段：3个主要方法字段与7项可调项；未参与的7项设置名称列表 |
| `pillars/hour/hourIndex/activePillar/activeGanZhi/activeIndex` | 真实四柱和真实时柱；实际起盘柱、干支与60甲子序号。日／月家不能把真实时柱替换成起盘柱 |
| `yang/ju/dingJu/chaiBu` | 原阴阳遁、局数、实际定局；chaiBu仅原引擎拆补分支提供，保留条件出现的语义 |
| `solar/hostTerm` | 真实当前／下一天文节气、分钟精度、边界提示与来源；寄宫实际使用的节气。定局标签不代替真实天文节气 |
| `xun/hidden/original/source` | 旬首、六甲所遁仪、旬首原宮、原引擎星盘使用的起宫 |
| `chiefStar/targetRaw/target/targetStem` | 值符星、地盘起盘干原宫、实际值符落宫、所用天干 |
| `chiefDoor/doorRaw/doorTarget` | 值使记名、原落宫及最终落宫，保留中门特殊记名规则 |
| `hostPalace/birdPalace` | 所用寄宫，未调用时null；天禽实际宫位。飞星时天禽独立，bird布尔随星标记不适用 |
| `earth/sky/stars/doors/heavenGods/earthGods/dark/darkBranches` | 1—9宫顺序的九个原层数组，与逐宫对应字段一致 |
| `voidBranches/voidPalaces/horse/horsePalace` | 起盘柱旬空支、落宫与驿马支及宫位 |
| `layers/darkMode` | 各层是否飞布；暗干层为mingfa或unavailable。unavailable表示尚未实现，不表示本流派无暗干 |
| `notes/traces/rules` | 原引擎提示、步骤和既有CLI规则摘要；不含解盘推断 |

`palaces`必须有9项，固定按1—9存储，宫数各出现一次；空间展示另按4、9、2／3、5、7／8、1、6。每项保留：

| 逐宫字段 | 类型及含义 |
|---|---|
| `number/name/direction` | 宫数1—9、原宫名及方位 |
| `earth/sky` | 地盘干／天盘干原字符串 |
| `hostedEarth/hostedSky` | 地盘／天盘寄干原字符串，不能忽略 |
| `star/door/god/earthGod` | 九星、门、天神、地神原字符串 |
| `dark/darkBranch` | 暗干／暗支原字符串，以darkMode和状态识别未实现 |
| `bird/empty/horse` | 天禽随星、旬空、驿马原布尔标记；false仍是有效计算值 |

## 状态语义

`palaceStates`按1—9宫存储，每宫`fields`覆盖上述全部逐宫字段。状态仅解释已有数据与调用范围，不增添术数规则。

| 状态 | 含义 | 例子 |
|---|---|---|
| `present` | 可用并有值；包括已计算的false标记 | 地盘戊、空亡false |
| `empty` | 本层适用且计算结果为空字符串 | 转盘某宫没有额外寄干 |
| `notApplicable` | 本盘／本宫该字段不适用 | 星飞的寄干和随星禽标记；转盘中五未单独排列的星／天干 |
| `notImplemented` | 引擎当前方法尚未接入此层 | 混合盘、日月家暗干与暗支 |
| `missing/error` | 缺失或异常；保留诊断词汇 | 必需字段缺失、状态与原值矛盾 |

正常快照不得生成missing/error状态；Schema的字段类型／必需项与语义校验发现问题时拒绝交付。不能靠给异常字段标missing就绕过失败。false不是null或“没有计算”，空字符串不是“不存在”或统一的null。

Node运行时从正式Schema校验该接口所用的关键字，并验证层数组、profile、时间约定、起盘柱、状态及标记之间的一致性；该校验器只服务本Schema，不声称支持完整任意JSON Schema。另有Python jsonschema进行独立完整Draft验证，运行方法见 [testing.md](testing.md)。

## 兼容

原CLI参数保持不变，stdout保留原摘要字段并新增markdown路径及版本／身份字段。路径改为UUID快照子目录，这是修复覆盖所必需的接口变化；原来依据stdout路径的调用无需调整，猜旧名字的调用应改用返回路径。

旧JSON只可通过明确兼容的Markdown转换入口读取，不静默提升为v1快照。缺少新增元数据写“旧记录未提供”；缺少必需盘面事实、不可用标志或不支持的格式明确报错。现有历史HTML／JSON／PNG／TXT不会自动迁移、回写或重新计算。
