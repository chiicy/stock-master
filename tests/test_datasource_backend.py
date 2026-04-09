from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from stock_master.datasource.backend import CommandBackend


class CommandBackendTests(unittest.TestCase):
    def test_check_module_uses_runtime_python_bin(self) -> None:
        backend = CommandBackend('/tmp/fake-venv/bin/python', command_exists_fn=lambda _: False)

        with patch('stock_master.datasource.backend.os.path.exists', return_value=True):
            with patch('stock_master.datasource.backend.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run_mock:
                self.assertTrue(backend.check_module('demo.module'))

        args = run_mock.call_args.args[0]
        self.assertEqual(args[0], '/tmp/fake-venv/bin/python')
        self.assertEqual(args[1], '-c')
        self.assertIn("importlib.import_module('demo.module')", args[2])

    def test_check_module_returns_false_when_import_fails(self) -> None:
        backend = CommandBackend('/tmp/fake-venv/bin/python', command_exists_fn=lambda _: False)

        with patch('stock_master.datasource.backend.os.path.exists', return_value=True):
            with patch('stock_master.datasource.backend.subprocess.run', side_effect=RuntimeError('boom')):
                self.assertFalse(backend.check_module('akshare'))


if __name__ == '__main__':
    unittest.main()
