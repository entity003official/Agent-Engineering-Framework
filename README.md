# AEF · Agent Engineering Framework

**选择一个文件夹，写下目标，让 Agent 按可检查、可恢复的流程工作。**

AEF 是轻量的 Agent 工程方法库与项目接入工具。已有项目保留原文件，新项目从清晰的目标开始；核心依赖仅为 Python 标准库。

[下载最新版本](https://github.com/entity003official/Agent-Engineering-Framework/releases/latest) · [行为规范](AGENTS.md) · [调度流程](orchestration.md) · [运行记录格式](docs/RUN-RECORDS.md)

## 三步开始

1. 下载 Release 中的 `AEF-v1.0.0-portable.zip`，解压到普通目录。安装环境需 **Python 3.10+，含 Tkinter**；Windows 官方 Python 通常包含 Tkinter。
2. 双击 `AEF-Start.cmd`，点击 **选择文件夹**。也可手动填写新项目路径。
3. 填写多行 **初始 Prompt**，或导入 UTF-8 `.txt` / `.md` 文件，选择平台，点击 **预览接入 → 接入项目**。

在你的 Agent 中发送：

> 读取 AGENTS.md 和 .aef/PROJECT.md，检查项目现状，按 AEF 的 P0–P3 执行任务。

图形界面负责生成项目规范与初始任务，不会启动模型、训练、发布或常驻监控。Release 为源码便携包，**需要已有 Python，不是独立 EXE**。macOS/Linux 可运行 `python3 aef_gui.py`；本版本实际验证环境为 Windows，其他系统未实测。

## 初始 Prompt 示例

```text
目标：为这个项目补齐可运行的最小功能与使用说明。
先调查：已有实现、环境、依赖、用户修改和未完成项。
范围：只修改目标项目，不安装额外依赖，不发布。
验收：运行必要测试，提供真实命令、退出码和交付文件。
遇到重要需求冲突时先说明影响并确认。
```

重复接入不会覆盖文件，也不会更新已有 Prompt；初始 Prompt 用于首次接入。已接入项目可点击“检查已有接入”，修改目标应明确更新项目目标和任务记录，并同步管理清单；本版本尚无自动升级/目标编辑命令。

## 接入后项目中有什么

```text
my-project/
├── AGENTS.md                 # 原文保留，追加 AEF 入口
├── CLAUDE.md                 # claude / both 模式下生成
└── .aef/
    ├── PROJECT.md            # 初始 Prompt 与项目范围
    ├── manifest.json         # 固定快照 SHA256 与文件归属
    ├── backups/              # 已有入口的原始字节备份（如有）
    ├── aef.py                # 可携带的命令行检查工具
    └── framework/
        ├── AGENTS.md         # 核心规则与配套文档
        ├── templates/task.md
        ├── tools/validate.py
        └── runs/bootstrap/   # 初始任务 QUEUED，执行后记录证据
```

- 保留用户修改：只新增 `.aef/` 并追加入口，已有入口按原字节备份。
- 固定方法库快照：不把开发者的历史运行记录复制进项目。
- 冲突保护：未知 `.aef/`、管理文件篡改、重复未归属标记及链接路径会拒绝接入。
- 幂等接入：已经接入且检查通过时，重复执行不写文件。
- 无隐式环境改动：不安装依赖、不修改全局 Agent 配置、不自动初始化 Git。

`check` 检查管理文件完整性、任务状态、依赖、并行写路径及证据存在；不证明证据真实性或业务正确性。运行记录可随任务推进；核心快照和入口变更需要人工核对。备份是恢复依据，不提供自动删除/回滚命令。

## Agent 如何协作

```text
P0 调查 → P1 规划 → P2 执行 → P3 验收与交付
```

Controller、Researcher、Architect、Implementer、Reviewer、Integrator 是六种职责，可以兼任。简单任务单 Agent 执行，大型任务按依赖和文件归属并行；并发数取决于平台实际能力，无子代理时串行执行。

| 使用环境 | 接入方式 | 能力边界 |
| --- | --- | --- |
| Codex | 选择 codex / both，读取 AGENTS.md | 子 Agent 与状态查询须由运行平台提供 |
| Claude Code | 选择 claude / both，读取 CLAUDE.md | 入口已测试，Claude Code 本身未实测 |
| 其他 Agent | 显式读取项目入口与 `.aef/PROJECT.md` | 没有调度工具时手工或串行执行 |

## 命令行

```sh
python -B aef.py init --project "path/to/project" --goal "具体目标" --platform both --dry-run
python -B aef.py init --project "path/to/project" --prompt-file "prompt.md" --platform both
python -B aef.py check --project "path/to/project"
```

长 Prompt 推荐 `--prompt-file`。图形界面与命令行调用同一接入逻辑。源码用户也可运行 `python aef_gui.py`；控制台交互入口保留在 `tools/start.ps1`。

## 开发与验证

```sh
python -B -m unittest discover -s tools -p "test_*.py" -v
python -B tools/validate.py
python -B tools/build_release.py
```

真实项目接入已测试：原有文件全量哈希保持一致、重复注入字节一致；新项目完成了一个标准库 CLI 及业务测试。公开仓库不包含这些项目的文件清单、私人路径或原始运行记录。图形界面的自动测试覆盖文件夹选择、Prompt 导入、预览门禁与实际接入流程。

更多：[监控与恢复](control.md) · [模式库](patterns.md) · [任务模板](templates/task.md)。候选模式的实际适用性仍需在各项目中验证。
