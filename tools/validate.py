"""Read-only AEF structure and run-record validation (standard library only)."""
import argparse
import json
from pathlib import Path
import sys

REQUIRED_FILES = ('AGENTS.md', 'README.md', 'orchestration.md', 'control.md',
                  'patterns.md', 'templates/task.md', 'tools/validate.py')
STATES = {'QUEUED', 'RUNNING', 'TESTING', 'DONE', 'BLOCKED', 'FAILED', 'CANCELLED'}
ACTIVE = {'RUNNING', 'TESTING'}


def validate(root):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    for name in REQUIRED_FILES:
        try:
            require(bool((root / name).read_text(encoding='utf-8-sig').strip()), f'Empty: {name}')
        except (OSError, UnicodeError) as exc:
            errors.append(f'Unreadable {name}: {exc}')
    require((root / 'runs').is_dir(), 'Missing runs/')
    count = 0
    for run in sorted((root / 'runs').iterdir()) if (root / 'runs').is_dir() else []:
        if not run.is_dir():
            continue
        count += 1
        try:
            data = json.loads((run / 'status.json').read_text(encoding='utf-8-sig'))
            check_run(data, run, require)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f'{run.name}: invalid record: {exc}')
    return errors, count


def check_run(data, run, require):
    def check(ok, message):
        require(ok, f'{run.name}: {message}')
    if not isinstance(data, dict):
        raise ValueError('status must be an object')
    for key in ('run_id', 'project_root', 'version', 'next_step'):
        check(isinstance(data.get(key), str) and bool(data[key].strip()), f'missing {key}')
    project = Path(data.get('project_root', '.'))
    check(project.is_absolute(), 'project_root must be absolute')
    tasks = data.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('tasks must be a nonempty list')
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError('task must be an object')
        tid = task.get('task_id')
        if not isinstance(tid, str) or not tid:
            raise ValueError('task_id must be nonempty string')
        check(tid not in by_id, f'duplicate task {tid}')
        by_id[tid] = task
        for key in ('goal', 'owner', 'agent_id', 'next_step'):
            check(isinstance(task.get(key), str) and bool(task[key].strip()), f'{tid}: missing {key}')
        for key in ('dependencies', 'writable_paths', 'readonly_paths', 'constraints',
                    'deliverables', 'acceptance', 'checkpoints', 'tests'):
            if not isinstance(task.get(key), list):
                raise ValueError(f'{tid}: {key} must be list')
        for key in ('dependencies', 'writable_paths', 'readonly_paths', 'constraints', 'deliverables'):
            if not all(isinstance(item, str) and item.strip() for item in task[key]):
                raise ValueError(f'{tid}: {key} must contain nonempty strings')
        check(task.get('status') in STATES, f'{tid}: invalid status')
        check(bool(task.get('acceptance')), f'{tid}: acceptance required')
        for checkpoint in task.get('checkpoints', []):
            check(isinstance(checkpoint, dict) and all(checkpoint.get(k) for k in
                  ('time', 'status', 'summary')), f'{tid}: invalid checkpoint')
            if isinstance(checkpoint, dict):
                check(checkpoint.get('status') in STATES, f'{tid}: invalid checkpoint status')
        def evidence(path):
            if not isinstance(path, str) or not path:
                return False
            p = Path(path)
            p = p if p.is_absolute() else run / p
            return p.is_file() and p.stat().st_size > 0
        for test in task.get('tests', []):
            if not isinstance(test, dict):
                raise ValueError('test must be object')
            check(all(test.get(k) for k in ('command', 'version', 'summary')), f'{tid}: incomplete test')
            check(type(test.get('exit_code')) is int, f'{tid}: test exit_code required')
            check(test.get('result') in ('PASSED', 'FAILED', 'SKIPPED'), f'{tid}: invalid test result')
            if test.get('result') == 'PASSED':
                check(test.get('exit_code') == 0 and evidence(test.get('evidence')),
                      f'{tid}: passed test lacks successful evidence')
        for criterion in task.get('acceptance', []):
            if not isinstance(criterion, dict):
                raise ValueError('acceptance must contain objects')
            check(bool(criterion.get('criterion')), f'{tid}: empty criterion')
            check(criterion.get('status') in ('PENDING', 'PASSED', 'FAILED'), f'{tid}: invalid acceptance status')
            if criterion.get('status') == 'PASSED':
                check(evidence(criterion.get('evidence')), f'{tid}: acceptance evidence missing')
        if task.get('status') == 'DONE':
            check(all(c.get('status') == 'PASSED' for c in task.get('acceptance', [])),
                  f'{tid}: DONE before acceptance passed')
            check(bool(task.get('deliverables')), f'{tid}: DONE without deliverables')
            for name in task.get('deliverables', []):
                p = Path(name)
                check((p if p.is_absolute() else project / p).exists(), f'{tid}: missing deliverable {name}')
            check(not any(t.get('result') == 'FAILED' for t in task.get('tests', [])),
                  f'{tid}: unresolved failed test')
    visiting, visited = set(), set()
    def visit(tid):
        if tid in visiting:
            check(False, f'dependency cycle at {tid}')
            return
        if tid in visited:
            return
        visiting.add(tid)
        for dep in by_id[tid].get('dependencies', []):
            check(isinstance(dep, str) and dep in by_id, f'{tid}: unknown dependency {dep}')
            if isinstance(dep, str) and dep in by_id:
                if by_id[tid].get('status') in ACTIVE | {'DONE'}:
                    check(by_id[dep].get('status') == 'DONE', f'{tid}: dependency {dep} not DONE')
                visit(dep)
        visiting.remove(tid)
        visited.add(tid)
    for tid in by_id:
        visit(tid)
    def normalized(name):
        # Paths are literal files/directories, not globs. Ancestor paths overlap.
        p = Path(name)
        return (p if p.is_absolute() else project / p).resolve()
    active = [t for t in tasks if t.get('status') in ACTIVE]
    for i, a in enumerate(active):
        for b in active[i + 1:]:
            if a.get('agent_id') == b.get('agent_id'):
                continue
            for x in a.get('writable_paths', []):
                for y in b.get('writable_paths', []):
                    px, py = normalized(x), normalized(y)
                    check(not (px == py or px in py.parents or py in px.parents),
                          f'write conflict: {a["task_id"]} / {b["task_id"]}: {x} / {y}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        errors, count = validate(args.root.resolve())
    except (OSError, TypeError, ValueError) as exc:
        errors, count = [f'Invalid input: {exc}'], 0
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    if errors:
        return 1
    print(f'PASS: {len(REQUIRED_FILES)} required files; {count} run record(s) checked.')
    print('Checks records and evidence presence; does not prove their truth or business correctness.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
