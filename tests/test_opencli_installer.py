from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from stock_master.opencli_installer import install_opencli_clis


class OpenCliInstallerTests(unittest.TestCase):
    def test_install_opencli_clis_creates_symlinks_and_replaces_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as src_tmp, tempfile.TemporaryDirectory() as dst_tmp:
            source_root = Path(src_tmp)
            target_root = Path(dst_tmp)
            nested = source_root / 'dc'
            nested.mkdir(parents=True, exist_ok=True)
            source_file = nested / 'quote.yaml'
            source_file.write_text('site: dc\nname: quote\n', encoding='utf-8')

            existing = target_root / 'dc' / 'quote.yaml'
            existing.parent.mkdir(parents=True, exist_ok=True)
            existing.write_text('old', encoding='utf-8')

            installed = install_opencli_clis(target_root, source_root)

            self.assertEqual([path.resolve() for path in installed], [existing.resolve()])
            self.assertTrue(existing.is_symlink())
            self.assertEqual(existing.resolve(), source_file.resolve())
            self.assertEqual(existing.read_text(encoding='utf-8'), 'site: dc\nname: quote\n')


if __name__ == '__main__':
    unittest.main()
