"""Independent validator regression checks; fixtures never touch real run records."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import validate


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in validate.REQUIRED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture', encoding='utf-8')
        self.run = self.root / 'runs' / 'fixture'
        self.run.mkdir(parents=True)
        (self.run / 'proof.txt').write_text('verified', encoding='utf-8')
        (self.root / 'result.txt').write_text('result', encoding='utf-8')
        self.task = dict(task_id='T1', goal='fixture', owner='Reviewer',
                         agent_id='agent-1', next_step='none', status='DONE',
                         dependencies=[], writable_paths=['result.txt'],
                         readonly_paths=[], constraints=[], deliverables=['result.txt'],
                         acceptance=[dict(criterion='result exists', status='PASSED',
                                          evidence='proof.txt')], checkpoints=[], tests=[])
        self.record = dict(run_id='fixture', project_root=str(self.root),
                           version='fixture snapshot', next_step='none', tasks=[self.task])

    def check_record(self):
        (self.run / 'status.json').write_text(json.dumps(self.record), encoding='utf-8')
        return validate.validate(self.root)

    def assert_invalid(self, fragment):
        errors, count = self.check_record()
        self.assertEqual(count, 1)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def add_task(self, **changes):
        task = copy.deepcopy(self.task)
        task.update(task_id='T2', agent_id='agent-2')
        task.update(changes)
        self.record['tasks'].append(task)
        return task

    def test_valid_record(self):
        self.assertEqual(self.check_record(), ([], 1))

    def test_missing_required_file(self):
        (self.root / 'README.md').unlink()
        self.assert_invalid('Unreadable README.md')

    def test_invalid_status(self):
        self.task['status'] = 'FINISHED'
        self.assert_invalid('invalid status')

    def test_unknown_dependency(self):
        self.task['dependencies'] = ['missing']
        self.assert_invalid('unknown dependency')

    def test_dependency_cycle(self):
        self.task.update(status='QUEUED', dependencies=['T2'])
        self.add_task(status='QUEUED', dependencies=['T1'])
        self.assert_invalid('dependency cycle')

    def test_unsatisfied_dependency(self):
        self.task.update(status='RUNNING', dependencies=['T2'])
        self.add_task(status='QUEUED')
        self.assert_invalid('not DONE')

    def test_parent_child_write_conflict(self):
        self.task.update(status='RUNNING', writable_paths=['src'])
        self.add_task(status='TESTING', writable_paths=['src/module.py'])
        self.assert_invalid('write conflict')

    def test_isolated_write_paths(self):
        self.task.update(status='RUNNING', writable_paths=['worktree-a/src'])
        self.add_task(status='RUNNING', writable_paths=['worktree-b/src'])
        self.assertEqual(self.check_record(), ([], 1))

    def test_passed_test_without_evidence(self):
        self.task['tests'] = [dict(command='fixture command', version='fixture',
                                   summary='passed', exit_code=0, result='PASSED')]
        self.assert_invalid('passed test lacks')

    def test_done_before_acceptance(self):
        self.task['acceptance'][0]['status'] = 'PENDING'
        self.assert_invalid('DONE before acceptance')

    def test_missing_deliverable(self):
        self.task['deliverables'] = ['absent.txt']
        self.assert_invalid('missing deliverable')

    def test_malformed_json(self):
        (self.run / 'status.json').write_text('{bad', encoding='utf-8')
        errors, count = validate.validate(self.root)
        self.assertEqual(count, 1)
        self.assertTrue(any('invalid record' in e for e in errors))

    def test_schema_missing_list(self):
        del self.task['dependencies']
        self.assert_invalid('dependencies must be list')

    def test_schema_nonstring_paths(self):
        for field in ('writable_paths', 'readonly_paths', 'deliverables'):
            with self.subTest(field=field):
                self.task[field] = [42]
                self.assertTrue(self.check_record()[0])
                self.task[field] = []

    def test_schema_nonstring_dependency(self):
        self.task['dependencies'] = [{}]
        self.assertTrue(self.check_record()[0])


if __name__ == '__main__':
    unittest.main()
