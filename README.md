# qimen-skill — 奇门遁甲排盘与解盘 Skill

将奇门排盘引擎、解盘理论资料和辅助工具整合到一个 Skill 中。通过统一的 [SKILL.md](SKILL.md) 入口，按需求排盘、解读已有盘、排盘后解盘，或查询奇门理论。

## 功能

- **排盘**：支持时家、日家、月家共 16 种已实现的 profile，默认使用时家转盘拆补。具体组合与设置见 [流派与设置](modules/paipan/references/settings.md)。
- **多种输出**：一次计算生成同一快照的 JSON、可交互 HTML 和 Markdown；具备浏览器环境时可另行生成九宫 PNG。
- **解盘**：按当前问事查阅取用、格局、应期和事项专题；已有盘面可直接读取，无需重新排盘。
- **理论查阅**：提供星、门、神、宫、干支关系及十二状态等查询工具，返回对应原文与出处位置。

排盘由确定性脚本执行；解盘由使用本 Skill 的助手结合盘面和理论资料完成。解盘模块采用纯理论资料，不附带历史问事或案例反馈库。

## 安装

本仓库根目录就是完整的 Skill 内容。下载或克隆后，将整个目录以 **`qimen`** 为名放入宿主支持的 skills 目录，不要只复制 `SKILL.md`。

可以从 [GitHub 仓库](https://github.com/DuShifang/qimen-skill) 下载 ZIP，或克隆到名为 `qimen` 的目录：

```text
git clone https://github.com/DuShifang/qimen-skill.git qimen
```

例如，下载后的目录可能叫 `qimen-skill-main`，安装时改名为 `qimen`。安装后的结构应为：

```text
<宿主的 skills 目录>/
└── qimen/
    ├── SKILL.md
    ├── README.md
    ├── bundle-version.json
    ├── references/
    └── modules/
```

只注册这一个 Skill；`modules/paipan/` 和 `modules/jiepan/` 是随包携带的内部模块，无需另外安装旧版 `qimen-paipan` 或 `qimen-jiepan`。

各宿主的安装位置与触发方式见 [跨宿主使用说明](references/host-usage.md)。

## 运行环境

| 用途 | 依赖 |
|---|---|
| 排盘，生成 JSON、HTML、Markdown | Node.js，需支持全局 `structuredClone`；排盘脚本只使用 Node 内置模块 |
| 盘面辅助查询与理论查表 | Python 3.10+ 标准库 |
| 生成 PNG（可选） | Python Playwright，以及现成的 Chrome、Edge 或 Chromium |

只生成 JSON、HTML 和 Markdown 不需要 Playwright。脚本不会自动下载浏览器。当前仓库副本已在 Node.js 24.18.0、Python 3.14.5 下完成基本运行检查；其他版本未在此次整理中逐一验证。

## 使用示例

安装后，可以向助手提出：

- “用奇门排一局，2026 年 11 月 9 日 10:26，北京时间，默认时家转盘拆补，给我九宫图。”
- “读取这份奇门盘 JSON，看看工作调动的问题，不要重新起盘。”
- “讲一下六仪击刑，并给出相关理论原文。”

也可以在仓库根目录手动运行以下命令。这里的日期仅为演示输入。

```text
node modules/paipan/scripts/paipan.cjs --datetime "2026-11-09T10:26" --profile shijia-zhuanpan-chaibu --outdir ./outputs
python modules/jiepan/scripts/qimen_tools.py lookup --kind star --item "天心"
```

macOS/Linux 按实际环境将 `python` 替换为 `python3`。排盘命令向终端返回真实的 `json`、`html`、`markdown` 路径；需要 PNG 时，把同一次排盘返回的三个路径传给包装器：

```text
python modules/jiepan/scripts/render_snapshot.py --html "实际HTML路径" --json "实际JSON路径" --markdown "实际Markdown路径" --outdir ./outputs
```

包装器会定位随包的渲染器，并返回实际 PNG 路径。完整操作约定见 [SKILL.md](SKILL.md)。

## 仓库结构

```text
.
├── README.md
├── SKILL.md                      # 唯一对外入口
├── LICENSE                       # MIT 许可证
├── .gitignore
├── bundle-version.json           # 总包与模块版本信息
├── references/
│   └── host-usage.md              # 跨宿主使用说明
└── modules/
    ├── paipan/
    │   ├── MODULE.md             # 排盘模块说明
    │   ├── assets/               # HTML 模板与 JSON Schema
    │   ├── references/           # 规则、设置、接口与导出说明
    │   └── scripts/              # 排盘引擎、节气数据与输出工具
    └── jiepan/
        ├── MODULE.md             # 解盘模块说明
        ├── version.json
        ├── references/           # 理论、查表资料与事项专题
        └── scripts/              # 盘面查询、理论查表与出图包装器
```

内部模块文档中的 `scripts/`、`references/` 短路径，以对应的 `modules/paipan/` 或 `modules/jiepan/` 目录为基准；总入口及本 README 的命令以仓库根目录为基准。

## 范围与版本

输入采用公历日期和北京时间（UTC+8），年份范围为 1900—2100。未实现的盘式与字段，以及分钟节气、日界和寄宫等规则，见 [排盘规则](modules/paipan/references/rules.md) 和 [设置说明](modules/paipan/references/settings.md)。

当前整合包为 **1.0.0**，排盘引擎为 **0.4.1**、输出工具为 **0.5.0**、解盘模块为 **0.2.3**。详细记录见 [bundle-version.json](bundle-version.json)。

本仓库来自统一运行包，未包含原始研发测试脚本、回归 fixtures 或案例档案。[测试与回归说明](modules/paipan/references/testing.md) 保留了原模块的研发验证记录；其中的历史测试命令需要原始工程测试文件。

所有术数判断属于传统知识的解释性应用，不代表结果已通过科学方法验证；涉及现实重大决策时应结合可核实事实和专业意见。

## 许可证

本项目采用 [MIT License](LICENSE)。Copyright (c) 2026 DuShifang。
