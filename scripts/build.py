#!/usr/bin/env python3
"""Build locally with official Android SDK tools; never accesses a device."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--side', choices=['left', 'right'], required=True)
p.add_argument('--width', type=int, required=True)
p.add_argument('--sdk', type=Path, default=os.environ.get('ANDROID_HOME'))
p.add_argument('--build-tools', default='36.0.0')
p.add_argument('--platform', default='android-30')
p.add_argument('--keystore', type=Path, required=True)
p.add_argument('--alias', default='edge')
p.add_argument('--output', type=Path, default=ROOT / 'build')
a = p.parse_args()
if not 0 < a.width < 1264:
    p.error('Width must be between 1 and 1263 physical pixels')
if not a.sdk:
    p.error('Set ANDROID_HOME or provide --sdk')
sdk = Path(a.sdk).expanduser().resolve()
out = a.output.expanduser().resolve()
if out.exists():
    p.error('Output must not exist; choose a new --output directory')
key = a.keystore.expanduser().resolve()
if not key.is_file():
    p.error('Keystore does not exist; create your own private key as documented')
bt = sdk / 'build-tools' / a.build_tools
jar = sdk / 'platforms' / a.platform / 'android.jar'
for f in [bt/'aapt2', bt/'zipalign', bt/'apksigner', jar]:
    if not f.is_file():
        p.error(f'Missing required SDK file: {f}')
def run(*args):
    subprocess.run([str(x) for x in args], check=True)
out.mkdir(parents=True)
src = out / 'source'
run(sys.executable, ROOT/'scripts/generate.py', '--side', a.side,
    '--width', a.width, '--output', src)
run(bt/'aapt2', 'compile', '--dir', src/'res', '-o', out/'resources.zip')
run(bt/'aapt2', 'link', '-I', jar, '--manifest', src/'AndroidManifest.xml',
    '--auto-add-overlay', '-o', out/'unsigned.apk', out/'resources.zip')
run(bt/'zipalign', '-f', '4', out/'unsigned.apk', out/'aligned.apk')
apk = out / 'Leaf2EdgeAvoidance.apk'
# Password is entered through apksigner's prompt, never in command arguments.
run(bt/'apksigner', 'sign', '--ks', key, '--ks-key-alias', a.alias,
    '--v1-signing-enabled', 'false', '--v2-signing-enabled', 'true',
    '--out', apk, out/'aligned.apk')
run(bt/'apksigner', 'verify', '--verbose', '--print-certs', apk)
module = out / 'module'
overlay = module / 'system/product/overlay'
overlay.mkdir(parents=True)
(overlay/apk.name).write_bytes(apk.read_bytes())
(module/'module.prop').write_text(
    'id=leaf2_edge_avoidance\nname=Leaf2 Physical Edge Avoidance\n'
    'version=1.0\nversionCode=1\nauthor=Project contributors\n'
    f'description=Physical {a.side} edge at rotation 0; {a.width}px. Four resources only.\n')
(module/'disable').write_text('Initially disabled for recovery verification.\n')
# File payload only: deliberately no recovery installer or boot-time scripts.
with zipfile.ZipFile(out/'module-payload.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(module.rglob('*')):
        if f.is_file():
            z.write(f, f.relative_to(module))
(out/'build-info.json').write_text(json.dumps({
    'side': a.side, 'width_px': a.width, 'build_tools': a.build_tools,
    'platform': a.platform, 'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest(),
    'note': 'Locally signed build; not byte-identical to the original device trial.'
}, indent=2)+'\n')
print(f'Built and signature-verified: {apk}\nModule payload: {module}')
