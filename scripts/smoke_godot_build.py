#!/usr/bin/env python3
"""Bounded startup smoke; fail on missing C# scene startup or engine errors."""
import argparse
from pathlib import Path
import subprocess


def check_output(returncode: int, output: str) -> None:
    if returncode or 'LUNAVALE_SCENIC survey=ready' not in output:
        raise RuntimeError(f'Player failed to reach scenic survey startup (exit={returncode})')
    if any(message in output for message in ('ERROR:', 'SCRIPT ERROR:', 'Unhandled exception', 'Failed to load')):
        raise RuntimeError('Player logged a runtime error')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    result = subprocess.run([str(args.executable.resolve()), '--headless', '--quit-after', '120'],
                            capture_output=True, text=True, timeout=90)
    output = result.stdout + result.stderr
    print(output, end='')
    check_output(result.returncode, output)
