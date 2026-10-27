#!/usr/bin/env python3
"""Generate local RRO sources only. No device access or installation."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--side', choices=('left', 'right'), required=True,
               help='Damaged physical edge in ROTATION_0')
p.add_argument('--width', type=int, required=True, help='Measured physical pixels')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
if not 0 < a.width < 1264:
    p.error('width must be between 1 and 1263 pixels')
if a.output.exists():
    p.error('output must be a new directory')
a.output.mkdir(parents=True)
(a.output / 'res/values').mkdir(parents=True)
w = a.width
path = (f'M -{w},0 L 0,0 L 0,1680 L -{w},1680 Z @right @bind_right_cutout'
        if a.side == 'right' else
        f'M 0,0 L {w},0 L {w},1680 L 0,1680 Z @left @bind_left_cutout')
(a.output / 'AndroidManifest.xml').write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="local.leaf2.edgeavoidance" android:versionCode="1" android:versionName="1.0">
  <uses-sdk android:minSdkVersion="30" android:targetSdkVersion="30" />
  <overlay android:targetPackage="android" android:isStatic="false"
      android:priority="1" android:category="com.android.internal.display_cutout_emulation" />
  <application android:hasCode="false" android:label="Leaf2 physical edge avoidance" />
</manifest>
''')
(a.output / 'res/values/config.xml').write_text(f'''<resources>
  <bool name="config_maskMainBuiltInDisplayCutout">true</bool>
  <bool name="config_fillMainBuiltInDisplayCutout">false</bool>
  <string name="config_mainBuiltInDisplayCutout" translatable="false">{path}</string>
  <string name="config_mainBuiltInDisplayCutoutRectApproximation" translatable="false">{path}</string>
</resources>
''')
(a.output / 'parameters.json').write_text(json.dumps({
    'model': 'Leaf2_P', 'firmware': '2025-11-26_19-25_4.0.2-rel_0621_da686c4b1',
    'side_at_rotation_0': a.side, 'width_px': w, 'path': path,
    'expected_logical_size': [1264-w, 1680],
    'status': 'generated configuration; verify on the target device',
    'deployment_requirement': 'system-trusted overlay or manufacturer signature',
    'acceptance': 'No content on damaged edge; full remaining good area; system and WeRead; 0/180 rotation',
    'appearance': 'Black margin or e-ink ghosting is an observation, not a pure-white requirement'
}, ensure_ascii=False, indent=2)+'\n')
print(a.output)
