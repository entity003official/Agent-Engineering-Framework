"""Build a portable source ZIP from an explicit public-file allowlist."""
from pathlib import Path
import hashlib
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.0.0'
FILES=['AEF-Start.cmd','AEF-Desktop.pyw','aef.py','aef_gui.py','README.md',
       'AGENTS.md','orchestration.md','control.md','patterns.md','templates/task.md',
       'docs/RUN-RECORDS.md','tools/validate.py','tools/start.ps1',
       'tools/build_release.py','tools/test_validate.py','tools/test_launcher.py','tools/test_gui.py']


def main():
    output=ROOT/'dist';output.mkdir(exist_ok=True)
    package=output/f'AEF-v{VERSION}-portable.zip'
    prefix=f'AEF-v{VERSION}/'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT/name,prefix+name)
        archive.writestr(prefix+'runs/.gitkeep','')
    checksum=output/'SHA256SUMS.txt'
    checksum.write_text(hashlib.sha256(package.read_bytes()).hexdigest()+'  '+package.name+'\n',encoding='utf-8')
    print(package);print(checksum)


if __name__=='__main__':main()
