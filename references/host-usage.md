# 跨宿主安装与触发（用户说明，不作为计算规则）

此总包只需安装一次完整 `qimen/` 目录。仓库根目录就是 Skill 内容；通过 GitHub 下载或克隆得到的目录，安装时命名为 `qimen`。不要把 `modules/` 的原始子模块再当作可独立发现的两个 Skill。对外只有 `qimen/SKILL.md` 一个 Skill 入口。保留完整目录结构；两个模块脚本按相对路径互相调用。

## 安装位置

| 宿主 | 工作区内安装位置 | 个人安装位置 | 典型显式触发 |
|---|---|---|---|
| Codex | `<project>/.agents/skills/qimen/` | `~/.agents/skills/qimen/`（旧版环境可能使用 `~/.codex/skills/qimen/`） | `$qimen`；也可自然语言 |
| Claude Code | `<project>/.claude/skills/qimen/` | `~/.claude/skills/qimen/` | `/qimen`；也可自然语言 |
| DeepSeek Harness | `<project>/.agents/skills/qimen/` 或 `.dsh/skills/qimen/` | `<dshHome>/skills/qimen/` 或 `<agentsHome>/skills/qimen/`（按实际安装环境） | `/qimen`（需启用Skill consumer）；也可自然语言 |
| Google Antigravity IDE | `<workspace>/.agents/skills/qimen/` | `~/.gemini/config/skills/qimen/` | 在支持的界面中使用 `/qimen` 或自然语言；也可明确指明SKILL.md |

不同安装版本、部署范围和权限可能改变自动发现行为。安装后新建会话验证当前宿主能否列出 `qimen`。若没有自动发现，明确说“读取并按 `<绝对路径>/qimen/SKILL.md` 处理”，前提是宿主具有文件读取工具。**不要假定这些宿主的 `/`、`$` 命令完全相同，或Skill会无条件自动调用。**

## 触发实例

- “用奇门排一局，按2026年11月9日10:26北京时间，默认时家转盘拆补，给九宫图” → 排盘。
- “这是我的奇门盘JSON，请看看工作调动前景” → 只解盘，不覆盖给定盘。
- “用奇门看看这次面试结果，按我提供的北京时间起局” → 排盘后解盘。
- “帮我讲一下六仪击刑是什么意思” → 理论解释。
- “请看看八字财运” → 不自动使用本Skill。
- “帮我起一卦” → 明确使用哪种术数，不自动假定奇门。

提示词中的示例公历时间仅为CLI测试格式，不是当前时刻或用户个人求测。

## 运行环境

必需：Node.js（实际奇门排盘，需支持全局 `structuredClone`）；Python 3.10+（理论/辅助查表和PNG包装器，按解盘模块声明统一最低版本）。**仅需要文本盘和JSON时不需要Playwright。** 需要PNG时另需可导入的Python Playwright、现成Chrome/Edge/Chromium浏览器，以及宿主允许运行本地进程和读写输出文件。`render_chart.py`只在渲染时导入Playwright。若受限宿主禁止读取本地 `file://`，在源HTML已通过同快照及无外部资源核验的前提下，随包渲染包装器可退回到浏览器内存加载HTML；不能推断所有沙盒均允许运行浏览器。未经用户许可不自动安装依赖、切换执行策略或改动系统全局配置。

Windows通常运行 `node`、`python` 或 `py -3`；macOS/Linux通常运行 `node` 和 `python3`。示例中的 `<SKILL_ROOT>` 使用当前实际安装的Skill根目录，并替换CLI命令的输出路径。CLI可用 `--help` 查询，设置和限制以本包原文为准。

运行时不联网寻找案例、不要读取用户其他目录中的历史问事库。排盘对UTC+8及1900—2100的适用范围、非默认profile逐层询问遵循原排盘模块。出图需要同一快照的HTML、JSON、Markdown三份原始文件；复制PNG等输出时不要覆盖旧文件。
