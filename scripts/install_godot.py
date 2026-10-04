#!/usr/bin/env python3
"""Install official Godot 4.7.2 .NET assets, verifying pinned release SHA-256."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

VERSION = '4.7.2'
ASSETS = {
    'Linux': ('Godot_v4.7.2-stable_mono_linux_x86_64.zip', '129f82db7bafd54ae14bb5bb284041c73860e8c7a009a3a026ca5e946cbff247'),
    'macOS': ('Godot_v4.7.2-stable_mono_macos.universal.zip', '8af3977b60d2c59802f7c8ff1914b3ca02a5e294f7381fc1104ee777e33cbbd8'),
    'templates': ('Godot_v4.7.2-stable_mono_export_templates.tpz', '92f8681e349ef1f90891b792da95e3b2b0bd1ed610b78018c58feb2d87e15a9d'),
}


def verify(path, digest):
    with path.open('rb') as source:
        actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != digest:
        raise RuntimeError(f'Checksum mismatch for {path.name}: {actual}')


def install(host, destination):
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for kind in (host, 'templates'):
        filename, digest = ASSETS[kind]
        archive = destination / filename
        if not archive.exists():
            partial = archive.with_suffix('.download')
            subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--max-time', '900',
                            f'https://github.com/godotengine/godot-builds/releases/download/{VERSION}-stable/{filename}',
                            '--output', str(partial)], check=True, timeout=1000)
            partial.rename(archive)
        verify(archive, digest)
        if kind == 'templates':
            with zipfile.ZipFile(archive) as content:
                content.extractall(destination / 'unpacked-templates')
        elif host == 'macOS':
            subprocess.run(['ditto', '-x', '-k', str(archive), str(destination)], check=True)
        else:
            with zipfile.ZipFile(archive) as content:
                content.extractall(destination)
    editor = (destination / 'Godot_mono.app/Contents/MacOS/Godot' if host == 'macOS'
              else destination / f'Godot_v{VERSION}-stable_mono_linux_x86_64/Godot_v{VERSION}-stable_mono_linux.x86_64')
    editor.chmod(editor.stat().st_mode | 0o111)
    # Self-contained editor data keeps local verification out of the user's templates/cache.
    data_root = destination if host == 'macOS' else editor.parent
    (data_root / '_sc_').touch()
    templates = data_root / 'editor_data/export_templates' / f'{VERSION}.stable.mono'
    templates.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(destination / 'unpacked-templates/templates', templates, dirs_exist_ok=True)
    result = subprocess.run([str(editor), '--headless', '--version'], check=True, text=True, capture_output=True, timeout=60)
    if not result.stdout.strip().startswith(f'{VERSION}.stable.mono.'):
        raise RuntimeError(f'Unexpected editor: {result.stdout}')
    if os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'], 'a') as output:
            output.write(f'GODOT={editor}\n')
    print(editor)
    return editor


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=['macOS', 'Linux'], required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    install(args.host, args.destination)
