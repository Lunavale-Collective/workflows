import tempfile
import unittest
from pathlib import Path
import game_release_metadata as metadata


class MetadataTests(unittest.TestCase):
    def test_godot_project_version_and_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'project.godot').write_text('[application]\nconfig/version="0.2.0-alpha"\n')
            (root / 'Lunavale.csproj').write_text('<Project Sdk="Godot.NET.Sdk/4.7.2"><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>')
            self.assertEqual(metadata.read_bundle_version(root), '0.2.0-alpha')
            self.assertEqual(metadata.read_editor_version(root), '4.7.2')

    def test_release_guards(self):
        release = metadata.GameRelease(metadata.Version.parse('0.2.0-alpha'), 'tag', 'name', None, 'a' * 64)
        with self.assertRaises(RuntimeError):
            metadata.enforce_release_order(metadata.Version.parse('0.1.0'), 'b' * 64, [release])
        with self.assertRaises(RuntimeError):
            metadata.enforce_release_order(metadata.Version.parse('0.2.0-alpha'), 'a' * 64, [release])
        metadata.enforce_release_order(metadata.Version.parse('0.2.0-alpha'), 'b' * 64, [release])


if __name__ == '__main__':
    unittest.main()
