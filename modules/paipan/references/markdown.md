# Markdown 导出规范 · 1.0.0

`scripts/markdown.cjs`消费一次已经计算完成的结构化结果。正常`paipan.cjs`自动保存MD；转换程序不调用`atTime`或`board`，不识图、不调用语言模型、不解释吉凶。

## 固定结构

1. 排盘基础信息：公历输入、时间约定、profile与盘式、定局、遁局、真实四柱、起盘柱、旬首、值符值使、寄宫及所用节气、旬空驿马、天禽和真实节气。
2. 九宫空间总览：固定按`4 9 2 / 3 5 7 / 8 1 6`的三列三行Markdown表格，包含星、门、天地神、天地干及寄干，不把1—9存储顺序当空间顺序。
3. 九宫逐宫详情：同一空间顺序，包含中五宫；每宫表格完整列出原引擎16个逐宫字段，保留代码字段名和可用状态。
4. 设置与计算说明：全部标准化settings、参与／未参与状态、原traces、layers、darkMode、notes和已知限制。
5. 数据来源与版本：snapshotId、schemaVersion、engineVersion、工具版本、Markdown格式版本、原生成时间与相对JSON链接。

空字符串和false保持原JSON值，正文按照`palaceStates`分别显示空值、不适用或“当前方法未实现”。尤其unavailable暗干层不能写“无暗干”。转盘中宫星干寄出与飞盘中门／弃用太常的中宫留空属于适用范围，不靠补造值填满表格。

输出采用UTF-8、LF换行；标题、字段名称、空间顺序稳定。文字中的竖线、尖括号和换行做Markdown表格转义。给定同一JSON、同一对应JSON链接和同一导出器版本，正文确定；独立快照的UUID和生成时间本来不同，不应误判为导出器随机改写正文。

## 独立转换

```powershell
node '<SKILL_ROOT>/modules/paipan/scripts/export_markdown.cjs' --json '<RECORDS_DIR>/已有盘.json' --markdown '<RECORDS_DIR>/新的记录.md'
```

`<SKILL_ROOT>` 替换为统一包根目录，`<RECORDS_DIR>` 替换为实际记录目录。

新格式先验证Schema和一致性，未知版本报错。旧0.4.1格式接受完整盘面事实、settings、layers、darkMode等原字段；缺新增元数据写“旧记录未提供”，不虚构snapshotId或生成时间。旧记录时间约定只报告记录中明确提供的内容。转换得到MD不会反向升级源JSON。

目标MD已存在即报错，不覆盖；临时文件生成完整内容后，使用同目录hard link独占发布，失败只清理本次临时文件。此方式需要支持hard link的本地文件系统；不支持时明确失败，没有不安全覆盖回退。

正常CLI的JSON与MD相邻同名；独立转换可以换目录，对应JSON链接据实际相对路径生成。stdout返回真实目标路径。原HTML保存TXT继续保留，TXT与MD用途不同：TXT记录当前页面显示的盘，自动MD绑定原始快照。
