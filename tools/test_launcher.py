"""Independent portable-launcher regression tests; standard library only."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'aef.py'


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()} if root.exists() else {}


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aef-launcher-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'

    def call(self, *args, expected=0, launcher=LAUNCHER):
        result = subprocess.run([sys.executable, '-B', str(launcher), *args,
                                 '--project', str(self.project)],
                                capture_output=True, text=True, encoding='utf-8',
                                errors='replace')
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def init(self, *extra):
        return self.call('init', '--goal', 'Produce verified project results', *extra)

    def test_dry_run_writes_nothing(self):
        self.init('--dry-run')
        self.assertFalse(self.project.exists())

    def test_missing_project_created(self):
        self.init()
        self.assertTrue((self.project / '.aef/manifest.json').is_file())
        self.assertTrue((self.project / 'AGENTS.md').is_file())

    def test_existing_entries_preserved_and_backed_up(self):
        self.project.mkdir()
        old = b'\xef\xbb\xbfOriginal\r\n\x80\xff'
        for name in ('AGENTS.md', 'CLAUDE.md'):
            (self.project / name).write_bytes(old)
        self.init('--platform', 'both')
        for name in ('AGENTS.md', 'CLAUDE.md'):
            self.assertTrue((self.project / name).read_bytes().startswith(old))
            self.assertEqual((self.project / '.aef/backups' / name).read_bytes(), old)

    def test_repeat_is_byte_identical(self):
        self.init()
        before = snapshot(self.project)
        self.init()
        self.assertEqual(before, snapshot(self.project))

    def test_check_passes(self):
        self.init()
        self.call('check')

    def test_tampering_fails_check(self):
        self.init()
        (self.project / '.aef/framework/control.md').write_text('tampered', encoding='utf-8')
        self.call('check', expected=1)

    def test_unowned_aef_rejected_without_writes(self):
        (self.project / '.aef').mkdir(parents=True)
        (self.project / '.aef/user.txt').write_bytes(b'keep')
        before = snapshot(self.project)
        self.call('init', '--goal', 'test', expected=1)
        self.assertEqual(before, snapshot(self.project))

    def test_conflicting_marker_rejected_without_writes(self):
        self.project.mkdir()
        (self.project / 'AGENTS.md').write_bytes(b'old\n<!-- AEF:BEGIN -->\n')
        before = snapshot(self.project)
        self.call('init', '--goal', 'test', expected=1)
        self.assertEqual(before, snapshot(self.project))
        self.assertFalse((self.project / '.aef').exists())

    def test_missing_goal_rejected(self):
        self.call('init', expected=1)
        self.assertFalse(self.project.exists())

    def test_chinese_and_spaced_path(self):
        self.project = Path(self.temp.name) / '中文 项目'
        self.init()
        self.call('check')

    def test_installed_copy_checks_project(self):
        self.init()
        self.call('check', launcher=self.project / '.aef/aef.py')


if __name__ == '__main__':
    unittest.main(verbosity=2)
