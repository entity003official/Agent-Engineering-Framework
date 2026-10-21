"""AEF desktop project onboarding (Python standard library)."""
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent


def run_action(action, project, prompt, platform, preview=False):
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    # pythonw cannot capture child CLI output reliably; select sibling python.exe.
    executable = Path(sys.executable)
    if executable.name.lower() == 'pythonw.exe':
        executable = executable.with_name('python.exe')
    with tempfile.TemporaryDirectory(prefix='aef-prompt-') as temp:
        file = Path(temp)/'prompt.txt'
        file.write_text(prompt, encoding='utf-8')
        cmd = [str(executable), '-B', str(ROOT/'aef.py'), action, '--project', project]
        if action == 'init':
            cmd += ['--prompt-file', str(file), '--platform', platform]
            if preview:
                cmd += ['--dry-run']
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                                env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return result.returncode, result.stdout+result.stderr


class App:
    def __init__(self, root):
        self.root = root
        root.title('AEF · Agent Engineering Framework')
        root.geometry('840x740')
        root.minsize(700, 600)
        self.events = queue.Queue()
        self.previewed = None
        self.busy = False
        self.path = tk.StringVar()
        self.platform = tk.StringVar(value='both')
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='让项目按 AEF 开始工作', font=('Microsoft YaHei UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='选择项目、明确目标，先预览再接入。不会自动运行业务任务。').pack(anchor='w', pady=(6,18))
        ttk.Label(frame, text='项目文件夹（新项目也可直接填写尚不存在的路径）').pack(anchor='w')
        row = ttk.Frame(frame); row.pack(fill='x', pady=6)
        self.path_entry = ttk.Entry(row, textvariable=self.path)
        self.path_entry.pack(side='left', fill='x', expand=True)
        self.browse_button = ttk.Button(row, text='选择文件夹…', command=self.choose_folder)
        self.browse_button.pack(side='left', padx=(8,0))
        line = ttk.Frame(frame); line.pack(fill='x', pady=8)
        ttk.Label(line, text='平台').pack(side='left')
        self.combo = ttk.Combobox(line, textvariable=self.platform, values=['both','codex','claude'], state='readonly', width=12)
        self.combo.pack(side='left', padx=10)
        ttk.Label(line, text='both 同时生成 AGENTS.md 和 CLAUDE.md').pack(side='left')
        row = ttk.Frame(frame); row.pack(fill='x', pady=(10,6))
        ttk.Label(row, text='初始 Prompt · 最终目标、范围和验收要求').pack(side='left')
        self.import_button = ttk.Button(row, text='导入 UTF-8 文本…', command=self.import_prompt)
        self.import_button.pack(side='right')
        self.prompt = tk.Text(frame, height=7, wrap='word', font=('Microsoft YaHei UI',10), undo=True)
        self.prompt.pack(fill='both', expand=True)
        self.prompt.insert('1.0','先调查项目现状，保留已有文件和用户修改。\n目标：\n验收条件：\n约束：不安装依赖、不发布，遇到重要需求冲突先确认。')
        buttons = ttk.Frame(frame); buttons.pack(fill='x', pady=12)
        self.preview_button = ttk.Button(buttons, text='1. 预览接入', command=lambda:self.start('init', True))
        self.preview_button.pack(side='left')
        self.apply_button = ttk.Button(buttons, text='2. 接入项目', command=lambda:self.start('init', False), state='disabled')
        self.apply_button.pack(side='left', padx=8)
        self.check_button = ttk.Button(buttons, text='检查已有接入', command=lambda:self.start('check'))
        self.check_button.pack(side='left')
        self.status = tk.StringVar(value='就绪 · 已有入口保留并备份；重复接入不覆盖。')
        ttk.Label(frame, textvariable=self.status, wraplength=760).pack(anchor='w', pady=(0,6))
        self.log = tk.Text(frame, height=10, wrap='word', state='disabled', font=('Consolas',9))
        self.log.pack(fill='both', expand=True)
        ttk.Label(frame, text='接入后，在你的 Agent 中发送：读取 AGENTS.md 和 .aef/PROJECT.md，按 AEF 执行。',wraplength=760).pack(anchor='w',pady=(10,0))
        self.path.trace_add('write',self.invalidate)
        self.platform.trace_add('write',self.invalidate)
        self.prompt.bind('<<Modified>>',self.modified)
        self.prompt.edit_modified(False)
        self.after_id = root.after(100,self.poll)
        root.protocol('WM_DELETE_WINDOW',self.close)

    def close(self):
        if self.busy:
            messagebox.showinfo('正在处理','请等待当前操作完成后关闭窗口。')
            return
        self.root.after_cancel(self.after_id)
        self.root.destroy()

    def signature(self):
        return (self.path.get().strip(), self.prompt.get('1.0','end-1c').strip(), self.platform.get())

    def invalidate(self,*args):
        self.previewed=None
        self.apply_button.configure(state='disabled')

    def modified(self,event=None):
        if self.prompt.edit_modified():
            self.invalidate(); self.prompt.edit_modified(False)

    def choose_folder(self):
        folder=filedialog.askdirectory(title='选择要接入 AEF 的项目文件夹')
        if folder:self.path.set(folder)

    def import_prompt(self):
        file=filedialog.askopenfilename(title='导入初始 Prompt',filetypes=[('文本文件','*.txt *.md'),('所有文件','*.*')])
        if not file:return
        try:
            text=Path(file).read_text(encoding='utf-8-sig')
            self.prompt.delete('1.0','end'); self.prompt.insert('1.0',text); self.invalidate()
        except (OSError,UnicodeError) as exc:messagebox.showerror('无法读取 Prompt',str(exc))

    def set_busy(self, busy):
        self.busy=busy
        for widget in (self.preview_button,self.check_button,self.browse_button,self.import_button,self.path_entry):
            widget.configure(state='disabled' if busy else 'normal')
        self.combo.configure(state='disabled' if busy else 'readonly')
        self.prompt.configure(state='disabled' if busy else 'normal')
        self.apply_button.configure(state='disabled' if busy or self.previewed!=self.signature() else 'normal')

    def start(self, action, preview=False):
        if self.busy:return
        sig=self.signature()
        if not sig[0] or (action=='init' and not sig[1]):
            messagebox.showerror('缺少输入','请填写项目路径和初始 Prompt。');return
        if action=='init' and not preview and self.previewed!=sig:
            messagebox.showinfo('先预览','输入发生变化，请先重新预览。');return
        self.set_busy(True);self.status.set('正在预览…' if preview else '正在处理…')
        def worker():
            try:code,output=run_action(action,*sig,preview=preview)
            except Exception as exc:code,output=1,str(exc)
            self.events.put((action,preview,sig,code,output))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            while True:
                action,preview,sig,code,output=self.events.get_nowait()
                self.previewed=sig if code==0 and preview else None
                self.log.configure(state='normal');self.log.delete('1.0','end');self.log.insert('1.0',output);self.log.configure(state='disabled')
                self.status.set(('预览通过，可接入项目。' if preview else '完成，详见结果。') if code==0 else '未完成，请查看错误；不会自动覆盖冲突文件。')
                self.set_busy(False)
        except queue.Empty:pass
        self.after_id=self.root.after(100,self.poll)


def main():
    root=tk.Tk(); App(root);root.mainloop()


if __name__=='__main__':main()
