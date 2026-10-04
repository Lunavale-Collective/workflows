#!/usr/bin/env python3
"""Reject incomplete C# desktop exports before packaging."""
from pathlib import Path
import argparse


def verify(root: Path, platform: str) -> None:
    executable = root / {'windows': 'Lunavale.exe', 'linux': 'Lunavale.x86_64',
                         'macos': 'Lunavale.app/Contents/MacOS/Lunavale'}[platform]
    magic = {'windows': b'MZ', 'linux': b'\x7fELF', 'macos': b'\xca\xfe\xba\xbe'}[platform]
    with executable.open('rb') as stream:
        if stream.read(len(magic)) != magic:
            raise RuntimeError(f'Invalid {platform} executable: {executable}')
    if not list(root.rglob('*.pck')):
        raise RuntimeError('Missing resource pack')
    rids = {'windows': ['windows_x86_64'], 'linux': ['linuxbsd_x86_64'],
            'macos': ['macos_arm64', 'macos_x86_64']}[platform]
    runtime = {'windows': 'coreclr.dll', 'linux': 'libcoreclr.so', 'macos': 'libcoreclr.dylib'}[platform]
    for rid in rids:
        directories = list(root.rglob(f'data_Lunavale_{rid}'))
        if len(directories) != 1:
            raise RuntimeError(f'Missing/ambiguous managed directory: {rid}')
        for filename in ('Lunavale.dll', 'Lunavale.runtimeconfig.json', 'GodotSharp.dll', runtime):
            target = directories[0] / filename
            if not target.is_file() or not target.stat().st_size:
                raise RuntimeError(f'Missing managed runtime file: {target}')
    print(f'Validated {platform} executable, resource pack, and self-contained managed runtimes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('platform', choices=['windows', 'linux', 'macos'])
    args = parser.parse_args()
    verify(args.root, args.platform)
