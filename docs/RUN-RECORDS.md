# 运行记录与验证

## 每次运行的最小记录

每次真实任务建立 runs/<run-id>/status.json，复制 templates/task.md 为 task.md（多任务可为各任务分别复制）。简单任务用一份模板和一个单任务状态记录即可。状态文件集中维护，避免多个 Agent 同写。现有历史 smoketest 先前没有持久记录，不补造历史证据。

status.json 结构如下（示例为排队状态，不是成功执行证据）：

```json
{
  "run_id": "example-001",
  "project_root": "E:/work/your-project",
  "version": "git commit + dirty diff证据；无Git时填文件快照证据路径",
  "next_step": "P0 检查项目",
  "tasks": [{
    "task_id": "TASK-001",
    "goal": "具体交付",
    "owner": "Controller/Implementer",
    "agent_id": "local-controller",
    "dependencies": [],
    "writable_paths": ["src/component.py"],
    "readonly_paths": ["README.md"],
    "constraints": ["不安装依赖"],
    "deliverables": ["src/component.py"],
    "acceptance": [{"criterion": "必要测试通过", "status": "PENDING", "evidence": null}],
    "status": "QUEUED",
    "checkpoints": [],
    "tests": [],
    "next_step": "核对现状"
  }]
}
```

路径约定：可写/只读路径与交付物相对于 project_root，证据路径相对于 status.json 所在目录，也可用绝对路径；文件所有权使用明确文件或目录，不使用通配符。目录授权包含全部子路径。worktree 使用各自绝对路径。checkpoints 每项包含 time（带时区）、status、summary，可附 evidence。tests 每项包含 command、exit_code（整数）、result（PASSED/FAILED/SKIPPED）、summary、version、evidence。通过的测试及验收必须关联非空证据文件。重测保留旧失败到检查点和日志，tests 表示当前有效验证集合。

状态为 QUEUED、RUNNING、TESTING、DONE，另外允许 BLOCKED、FAILED、CANCELLED。正常顺序 QUEUED → RUNNING → TESTING → DONE；修复后可从 TESTING 回 RUNNING，解除阻塞/重试时记录原因和检查点，取消任务需显式重新授权才恢复。DONE 只表示约定验收通过，不代表用户已验收。

## 验证工具

在方法库目录执行：

```text
python -B tools/validate.py
python -B -m unittest discover -s tools -p test_validate.py -v
```

验证器只读，退出码0通过、1失败；可用 --root 指定另一方法库根目录。检查必需文件非空、每个运行目录的 status.json、状态枚举、依赖引用及环、活动/完成任务的前置门禁、跨 Agent 活动任务写路径相同或祖先冲突、通过测试的退出码与证据、DONE 的验收与交付物。

边界：静态记录检查不证明日志真实性、测试充分性、业务正确性或实际写入未越界；不能从当前快照证明完整状态转换历史。Controller/Reviewer 必须核实实际工具状态、文件差异和版本。串行共享路径在前任务退出 RUNNING/TESTING 后可复用；并行共享文件须改为单一写者或隔离路径，不能以文字豁免绕过冲突检查。
