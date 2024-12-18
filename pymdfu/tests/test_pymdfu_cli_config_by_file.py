"""Tests for MDFU client"""
import unittest
import sys
import io
import pathlib
from mock import patch
try:
    # When Python 3.11 becomes the minimum supported version for this tool
    # we can remove the tomli fallback solution here since this version
    # will have tomllib in its standard library.
    import tomllib as toml_reader
except ModuleNotFoundError:
    import tomli as toml_reader
import pymdfu
from pymdfu.pymdfu import main
from pymdfu.status_codes import STATUS_SUCCESS

class TestPymdfuCliConfig(unittest.TestCase):
    """Tests for pymdfu CLI configuration by file"""
    def _mock_stdout(self):
        """
        Returns stdout mock.

        Content sent to stdout can be fetched with mock_stdout.getvalue()
        """
        mock_stdout_patch = patch('sys.stdout', new_callable=io.StringIO)
        self.addCleanup(mock_stdout_patch.stop)
        return mock_stdout_patch.start()

    def _mock_stderr(self):
        """
        Returns stderr mock.

        Content sent to stderr can be fetched with mock_stderr.getvalue()
        """
        mock_stderr_patch = patch('sys.stderr', new_callable=io.StringIO)
        self.addCleanup(mock_stderr_patch.stop)
        return mock_stderr_patch.start()

    def _update_stub(self, args):
        """Mock function for pymdfu.update()

        :param args: Command line arguments
        :type args: Namespace
        :return: Status
        :rtype: int
        """
        # Load configuration file
        file = pathlib.Path(__file__).parent / "config.toml"
        with open(file, "rb") as file:
            config = toml_reader.load(file)

        # make sure all config file parameter values from common section
        # are present
        for key, value in config['common'].items():
            self.assertIn(key, args)
            # if param was also provided on cmd line make sure
            # it took precedence over config file
            if f"--{key}" in self.testargs:
                pos = self.testargs.index(f"--{key}")
                self.assertEqual(self.testargs[pos + 1], vars(args)[key])

        for key, value in config[args.tool].items():
            self.assertIn(f"--{key}", args.tool_args)
            self.assertIn(str(value), args.tool_args)
        return STATUS_SUCCESS


    def test_update_cmd_with_config(self):
        """Test that pymdfu CLI returns help text"""
        mock_stdout = self._mock_stdout()

        file = pathlib.Path(__file__).parent / "config.toml"
        self.testargs = ["pymdfu", "update", "-c", str(file)]
        with patch.object(sys, 'argv', self.testargs):
            with patch.object(pymdfu.pymdfu, 'update', self._update_stub):
                main()

        self.testargs = ["pymdfu", "update", "--tool", "serial", "-c", str(file), "--verbose", "debug"]
        with patch.object(sys, 'argv', self.testargs):
            with patch.object(pymdfu.pymdfu, 'update', self._update_stub):
                main()

