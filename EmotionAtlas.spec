# PyInstaller specification. Run from the repository root on macOS.
from pathlib import Path
import os
import sysconfig
root = Path(SPECPATH)
version = (root/'VERSION').read_text().strip()
signing_identity = os.environ.get('DEVELOPER_ID_APPLICATION')
# Some Python distributions load additional trust-policy data during SSLContext
# construction. Preserve that runtime file beside the frozen ssl module.
ssl_policy = Path(sysconfig.get_path('stdlib'))/'codex-rejected-cas.pem'
ssl_data = [(str(ssl_policy), '.')] if ssl_policy.is_file() else []
a = Analysis([str(root/'app.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root/'assets/emotion-atlas-icon-small.png'), 'assets'), (str(root/'LICENSE'), '.'),
                        (str(root/'THIRD_PARTY_NOTICES.md'), '.'), (str(root/'VERSION'), '.'), (str(root/'licenses'), 'licenses')] + ssl_data,
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Emotional Atlas', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          target_arch='arm64', codesign_identity=signing_identity, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Emotional Atlas')
app = BUNDLE(coll, name='Emotional Atlas.app', icon=str(root/'assets/emotion-atlas.icns'),
    bundle_identifier='com.github.FL2744.emotion-atlas', version=version,
    info_plist={'CFBundleDisplayName':'Emotional Atlas', 'CFBundleShortVersionString':version,
                'CFBundleVersion':version, 'LSMinimumSystemVersion':'15.0',
                'NSHighResolutionCapable':True, 'NSHumanReadableCopyright':'Copyright 2026 Emotional Atlas contributors'})
