"""Check all bundled Mach-O files against the advertised macOS baseline."""
import re
import subprocess
import sys
from pathlib import Path

MAGIC = {bytes.fromhex(v) for v in ('feedface','cefaedfe','feedfacf','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca')}
seen=set()
count=0
for path in Path(sys.argv[1]).rglob('*'):
    if not path.is_file() or path.resolve() in seen:
        continue
    seen.add(path.resolve())
    with path.open('rb') as stream:
        if stream.read(4) not in MAGIC:
            continue
    output=subprocess.check_output(['xcrun','otool','-l',str(path)],text=True)
    versions=re.findall(r'^\s*minos\s+([\d.]+)',output,re.M)
    versions+=re.findall(r'cmd LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version ([\d.]+)',output)
    if not versions or any(tuple(map(int,v.split('.')))>(15,0,0) for v in versions):
        raise SystemExit(f'{path}: unsupported deployment target {versions}')
    arches=subprocess.check_output(['lipo','-archs',str(path)],text=True).split()
    if 'arm64' not in arches:
        raise SystemExit(f'{path}: missing arm64 architecture')
    count+=1
print(f'Checked {count} Mach-O files: arm64, macOS deployment targets <= 15.0.')
