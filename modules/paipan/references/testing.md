> 统一总包说明：以下为原排盘模块的研发验收方法；原始测试脚本和大型基准fixture不随正常运行包发布。需重新执行工程测试时请使用原始排盘来源ZIP中的 `tests/`，不要在当前总Skill运行目录中假定存在该目录。

# 测试与回归说明

测试不需要APK、原生库、联网排盘或新的大型运行依赖。正常排盘和Node测试只用Node内置模块；浏览器测试使用现成Python Playwright及Chrome／Edge／Chromium，不下载浏览器。

## Node自动化测试

在skill目录运行：

```powershell
node --test 'tests/paipan.test.cjs'
```

覆盖修改前113组真实引擎结果、16种profile的完整CLI输出、Schema及语义拒绝项、JSON／内嵌HTML／MD一致性、完整九宫和寄干、状态标记、一次计算、重复和不同设置并存、并发生成、历史文件保护、同ID拒绝覆盖、模拟中途磁盘失败、确定性导出及旧记录转换。测试使用系统临时目录，结束仅移除本次创建的目录。

`tests/fixtures/engine-before.json`在P0修改前直接从原0.4.1引擎保存，覆盖时日月家／四种盘式、拆补置闰、七项设置、阴阳遁、各寄宫方式、23点日界、交节前后及1900／2100边界。**这些回归基准只证明本次改动保留原有计算行为，不独立证明原算法正确。** 不应在看到差异后自动重录覆盖基准；先定位改动并按任务授权处理。

既有原生核对数量与限制继续保存在 [rules.md](rules.md)。本测试包没有把APK库或其实现作为依赖，也未新增未经来源核验的“准确性标准盘”。

## 独立完整Schema验证

```powershell
python 'tests/validate_schema.py'
```

需已有Python `jsonschema`（本次用4.26.0）以及PATH上的Node。该库仅用于独立测试，不是skill排盘的运行依赖；缺少时明确失败，不自动安装。测试先验证正式Schema自身符合Draft 2020-12，再检查113份由原样例生成的新快照和4种非法对照。

本次独立依赖放在工作区`work/p0p2-test-deps`，未安装到系统或打包进skill。复现本任务的测试可以先将该目录加入本次命令的PYTHONPATH；其他环境可使用自己已有的jsonschema。

## 浏览器与PNG验证

```powershell
python 'tests/browser_test.py' --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe'
```

验证16种profile真实页面初始JSON／DOM、初始零次重算、原快照冻结、48个桌面／中等／手机布局、交互后当前TXT、16次重新打开恢复、保存文件不变、无页面错误／网络计算、实际PNG输出与拒绝覆盖已有PNG。无需更改已安装skill；测试读取同包的脚本和模板。

PNG是三文件快照提交之后的独立可选产物。测试验证正常渲染和拒绝覆盖；没有模拟浏览器所有异常、所有硬盘／网络盘故障或断电。布局测量不等同于全部浏览器和字体的兼容性证明。

## 维护范围

输出工具、Schema和MD格式有各自版本；原引擎版本不因测试或文档改动而改变。新增profile或计算规则属于后续明确授权任务，需另行说明正确性核对。文档校验与运行测试都应执行，不能用frontmatter校验代替功能测试。
