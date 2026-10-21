# 任务：<名称>

```yaml
task_id: TASK-001
goal: 具体交付目标
owner: Controller
agent_id: local-controller
dependencies: []
writable_paths: []
readonly_paths: []
constraints: []
deliverables: []
acceptance:
  - criterion: 可检查的验收条件
    status: PENDING
    evidence: null
status: QUEUED
```

## P0 调查

记录需求来源、已验证事实、项目文件、已有实现、环境与依赖、Git 状态、用户修改、风险与未知项。无 Git 时记录无仓库，不自行初始化。

## P1 规划

明确最终交付、范围、共享接口、输入输出、不变量、任务依赖、文件归属与验收条件。简单任务每阶段一句即可，避免额外管理文档。将机器检查字段同步到本次运行唯一的 status.json；该文件是当前状态的权威记录。

## P2 执行

按依赖推进最小可运行成果，记录检查点、实际 Agent ID、有效产物和异常。未满足前置任务不得开工；并行写入路径必须独占。

## P3 验收与交付

记录实际测试命令、退出码、关键结果、对应版本、证据路径及交付物。分别说明已实现、已测试、已集成、已交付、用户已验收；不得以 DONE 推断用户已验收。

## 恢复入口

记录已完成成果和版本、未完成任务与阻塞、Agent 最后确认状态、有效测试证据、下一步及已执行的有副作用操作。恢复前核对真实状态。
