"""Tk widget and real CLI workflow tests; use temporary projects only."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('aef_gui',ROOT/'aef_gui.py')
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='aef-gui-')
        self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name)/'中文 project'
        self.root=tk.Tk();self.root.withdraw()
        self.app=gui.App(self.root)
        self.addCleanup(self.app.close)
        self.root.update()

    def wait(self):
        end=time.monotonic()+20
        while self.app.busy and time.monotonic()<end:
            self.root.update();time.sleep(.02)
        self.assertFalse(self.app.busy,'GUI worker timed out')
        self.root.update()

    def test_folder_picker_and_prompt_import(self):
        with patch.object(gui.filedialog,'askdirectory',return_value=str(self.project)):
            self.app.choose_folder()
        self.assertEqual(self.app.path.get(),str(self.project))
        prompt=Path(self.temp.name)/'prompt.md';prompt.write_text('中文目标\n验收：测试通过',encoding='utf-8')
        with patch.object(gui.filedialog,'askopenfilename',return_value=str(prompt)):
            self.app.import_prompt()
        self.assertEqual(self.app.prompt.get('1.0','end-1c'),'中文目标\n验收：测试通过')

    def test_preview_apply_and_check(self):
        self.app.path.set(str(self.project));self.root.update()
        self.app.start('init',True);self.wait()
        self.assertFalse(self.project.exists())
        self.assertIsNotNone(self.app.previewed)
        self.app.start('init',False);self.wait()
        self.assertTrue((self.project/'.aef/manifest.json').exists())
        self.app.start('check');self.wait()
        self.assertIn('PASS',self.app.log.get('1.0','end'))

    def test_prompt_edit_invalidates_preview(self):
        self.app.path.set(str(self.project));self.root.update()
        self.app.start('init',True);self.wait()
        self.app.prompt.insert('end',' changed');self.root.update()
        self.assertIsNone(self.app.previewed)
        self.assertEqual(str(self.app.apply_button['state']),'disabled')

    def test_missing_input_blocks_write(self):
        with patch.object(gui.messagebox,'showerror') as error:
            self.app.start('init',True)
        error.assert_called_once();self.assertFalse(self.project.exists())


if __name__=='__main__':unittest.main()
