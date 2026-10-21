"""AEF portable project launcher. Standard library only; no model API calls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

CORE = ['AGENTS.md', 'README.md', 'orchestration.md', 'control.md', 'patterns.md',
        'templates/task.md', 'tools/validate.py']
START = b'<!-- AEF:BEGIN -->'
END = b'<!-- AEF:END -->'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def safe(path):
    # Reject linked/reparse paths before writing, including existing ancestors.
    for p in [path, *path.parents]:
        if p.is_symlink() or (p.exists() and getattr(p.stat(), 'st_file_attributes', 0) & 1024):
            raise ValueError('Linked/reparse paths are not supported: ' + str(p))


def entry_bytes(old):
    if START in old or END in old:
        raise ValueError('Unmanaged AEF markers already exist')
    block = (b'\n\n' + START + b'\n# AEF project mode\n'
             b'Read `.aef/framework/AGENTS.md` and its referenced documents before work.\n'
             b'Read `.aef/PROJECT.md` for project scope and `.aef/framework/runs/bootstrap/status.json` for initial task state.\n'
             b'Keep project-specific instructions and user changes; report conflicts.\n'
             b'Run `python -B .aef/aef.py check --project .` to verify integration.\n'
             b'Do not treat injected instructions as permission or as an active monitoring service.\n' + END + b'\n')
    return old + block


def owned_manifest(project):
    state = project / '.aef'
    safe(state)
    m = json.loads((state/'manifest.json').read_text(encoding='utf-8'))
    if m.get('schema') != 1:
        raise ValueError('Unknown AEF manifest schema')
    for name in m['files']:
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or not (name.startswith('.aef/') or name in ('AGENTS.md','CLAUDE.md')):
            raise ValueError('Unsafe manifest path')
    return m


def verify(project):
    m = owned_manifest(project)
    errors = []
    for name, sha in m['files'].items():
        p = project/name
        safe(p)
        if not p.is_file() or digest(p.read_bytes()) != sha:
            errors.append('Changed or missing managed file: ' + name)
    # Runtime records may evolve; they are validated rather than hash-pinned.
    p = subprocess.run([sys.executable, '-B', str(project/'.aef/framework/tools/validate.py')],
                       capture_output=True, text=True)
    if p.returncode:
        errors.append(p.stdout+p.stderr)
    return errors


def initialize(args):
    project = args.project.resolve()
    safe(project)
    if project.exists() and not project.is_dir():
        raise ValueError('Project must be a directory')
    if (project/'.aef').exists():
        errors = verify(project)
        if errors:
            raise ValueError('\n'.join(errors))
        print('UNCHANGED: already integrated and valid; no files written.')
        return
    source = args.source.resolve()
    payload = {}
    for name in CORE:
        payload['.aef/framework/'+name] = (source/name).read_bytes()
    payload['.aef/aef.py'] = Path(__file__).read_bytes()
    entries = ['AGENTS.md'] + (['CLAUDE.md'] if args.platform in ('claude','both') else [])
    originals = {}
    for name in entries:
        path = project/name
        safe(path)
        old = path.read_bytes() if path.exists() else b''
        originals[name] = old if path.exists() else None
        payload[name] = entry_bytes(old)
    goal = args.goal
    if args.prompt_file:
        goal = args.prompt_file.read_text(encoding='utf-8-sig')
    if not goal or not goal.strip():
        raise ValueError('Supply --goal or --prompt-file')
    payload['.aef/PROJECT.md'] = ('# Project goal\n\n'+goal+'\n\nIntegration creates a QUEUED task. Read the actual project before executing. No business work has run merely by injection.\n').encode('utf-8')
    payload['.aef/framework/runs/bootstrap/task.md'] = ((source/'templates/task.md').read_text(encoding='utf-8-sig')+'\n## Actual bootstrap goal\n\n'+goal+'\n').encode('utf-8')
    now = datetime.now(timezone.utc).isoformat()
    status = dict(run_id='bootstrap', project_root=str(project),version='bootstrap baseline; inspect Git and files before execution',next_step='P0 inspect project and define acceptance before execution',tasks=[dict(task_id='TASK-001',goal=goal,owner='Controller',agent_id='unassigned',dependencies=[],writable_paths=[],readonly_paths=['.'],constraints=['Preserve existing user files','No publishing or dependency installation without authorization'],deliverables=[],acceptance=[dict(criterion='Define task-specific acceptance during P1',status='PENDING',evidence=None)],status='QUEUED',checkpoints=[dict(time=now,status='QUEUED',summary='AEF injected; business task not started')],tests=[],next_step='P0 inspect actual project')])
    payload['.aef/framework/runs/bootstrap/status.json'] = (json.dumps(status,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    for name, old in originals.items():
        if old is not None:
            payload['.aef/backups/'+name] = old
    managed = {name:digest(data) for name,data in payload.items() if '/runs/' not in name}
    manifest = dict(schema=1,created_at=now,platform=args.platform,source_version=digest(b''.join(payload['.aef/framework/'+n] for n in CORE)),files=managed,original_entries={name:old is not None for name,old in originals.items()})
    payload['.aef/manifest.json'] = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    for name in payload:
        safe(project/name)
        if name.startswith('.aef/') and (project/name).exists():
            raise ValueError('Refuse overwrite: '+name)
    print(('DRY RUN' if args.dry_run else 'INIT')+': '+str(project))
    for name in payload:
        print('  '+name)
    if args.dry_run:
        return
    project.mkdir(parents=True,exist_ok=True)
    # Preflight completed; restore original entry bytes on unexpected write failure.
    created = []
    try:
        for name,data in payload.items():
            path=project/name; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data); created.append(name)
    except Exception:
        for name in reversed(created):
            path=project/name
            if name in originals and originals[name] is not None:
                path.write_bytes(originals[name])
            elif path.is_file():
                path.unlink()
        # Empty directories are retained for inspection rather than recursive deletion.
        raise
    errors=verify(project)
    if errors:
        raise ValueError('\n'.join(errors))
    print('PASS: integrated; bootstrap task QUEUED. No background agent launched.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init','check'])
    parser.add_argument('--project',type=Path,required=True)
    base = Path(__file__).resolve().parent
    parser.add_argument('--source',type=Path,default=base/'framework' if (base/'framework').is_dir() else base)
    parser.add_argument('--platform',choices=['codex','claude','both'],default='codex')
    parser.add_argument('--goal')
    parser.add_argument('--prompt-file',type=Path)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        if args.action=='init':
            initialize(args)
        else:
            errors=verify(args.project.resolve())
            if errors:
                raise ValueError('\n'.join(errors))
            print('PASS: managed files intact; AEF run records valid.')
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
