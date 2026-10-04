#!/usr/bin/env python3
"""Desktop-only CI presets. Never run preparation in a developer's working tree."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def prepare_presets(root: Path, version: str) -> None:
    original = (root / 'export_presets.cfg').read_text(encoding='utf-8')
    def value(key: str) -> str:
        match = re.search(r'^' + re.escape(key) + r'=("[^"\n]*")$', original, re.MULTILINE)
        if not match:
            raise RuntimeError(f'Missing {key} in source export presets')
        return json.loads(match.group(1))
    include = ','.join(filter(None, [value('include_filter'), 'Data/**/*.json']))
    exclude = value('exclude_filter')
    sections = []
    for index, (name, platform, arch) in enumerate([
        ('CI Windows', 'Windows Desktop', 'x86_64'),
        ('CI Linux', 'Linux', 'x86_64'),
        ('CI macOS', 'macOS', 'universal'),
    ]):
        sections.append(f'''[preset.{index}]
name="{name}"
platform="{platform}"
runnable=false
dedicated_server=false
export_filter="all_resources"
include_filter={json.dumps(include)}
exclude_filter={json.dumps(exclude)}
export_path=""
script_export_mode=2

[preset.{index}.options]
binary_format/architecture="{arch}"
binary_format/embed_pck=false
dotnet/include_scripts_content=false
dotnet/embed_build_outputs=false
shader_baker/enabled=false
''')
        if platform == 'macOS':
            numeric = version.split('-')[0].split('+')[0]
            sections.append(f'''application/bundle_identifier="com.lunavale.game"
application/short_version="{numeric}"
application/version="{numeric}"
application/icon="res://Assets/Resources/UI/Branding/app_icon.png"
codesign/codesign=3
codesign/entitlements/allow_jit_code_execution=true
codesign/entitlements/allow_unsigned_executable_memory=true
codesign/entitlements/disable_library_validation=true
notarization/notarization=0
''')
        elif platform == 'Windows Desktop':
            sections.append('codesign/enable=false\napplication/modify_resources=false\n')
    (root / 'export_presets.cfg').write_text('\n'.join(sections), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    prepare_presets(args.project, args.version)
