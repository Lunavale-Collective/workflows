import hashlib
import tempfile
import unittest
from pathlib import Path
from godot_release import prepare_presets
from install_godot import verify as verify_checksum
from smoke_godot_build import check_output
from verify_godot_build import verify as verify_build


class ExportTests(unittest.TestCase):
    def test_prepare_desktop_presets_preserves_resource_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'export_presets.cfg').write_text('[preset.0]\ninclude_filter="Credits.txt"\nexclude_filter="Tests/**"\n')
            prepare_presets(root, '0.2.0-alpha')
            text = (root/'export_presets.cfg').read_text()
            for name in ('CI Windows', 'CI Linux', 'CI macOS'):
                self.assertIn(name, text)
            for setting in ('Data/**/*.json', 'Credits.txt', 'Tests/**',
                            'dotnet/include_scripts_content=false', 'codesign/codesign=3',
                            'binary_format/architecture="universal"', 'application/version="0.2.0"'):
                self.assertIn(setting, text)
            self.assertNotIn('Android', text)

    def test_missing_presets_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'export_presets.cfg').write_text('[preset.0]\n')
            with self.assertRaises(RuntimeError):
                prepare_presets(root, '0.2.0')

    def test_checksum_accepts_exact_bytes_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'asset'
            path.write_bytes(b'fixture')
            verify_checksum(path, hashlib.sha256(b'fixture').hexdigest())
            with self.assertRaises(RuntimeError):
                verify_checksum(path, '0'*64)

    def test_smoke_requires_managed_startup(self):
        with self.assertRaises(RuntimeError):
            check_output(0, 'Godot Engine')
        check_output(0, 'LUNAVALE_SCENIC survey=ready tiles=220')

    def test_smoke_rejects_errors_and_crashes(self):
        for code, suffix in [(1, ''), (0, 'ERROR: missing resource'), (0, 'Unhandled exception')]:
            with self.subTest(code=code, suffix=suffix), self.assertRaises(RuntimeError):
                check_output(code, 'LUNAVALE_SCENIC survey=ready '+suffix)

    def test_missing_managed_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Lunavale.exe').write_bytes(b'MZfixture')
            (root/'Lunavale.pck').write_bytes(b'fixture')
            with self.assertRaisesRegex(RuntimeError, 'managed directory'):
                verify_build(root, 'windows')

    def test_wrong_executable_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Lunavale.exe').write_bytes(b'not executable')
            with self.assertRaisesRegex(RuntimeError, 'Invalid windows executable'):
                verify_build(root, 'windows')


if __name__ == '__main__':
    unittest.main()
