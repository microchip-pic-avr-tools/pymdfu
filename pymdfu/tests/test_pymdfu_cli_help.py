"""Tests for MDFU client"""
import unittest
import sys
import io
from mock import patch
from pymdfu.pymdfu import main, CliHelp
from pymdfu import __version__ as VERSION
from pymdfu import BUILD_DATE


class TestPymdfuCliHelp(unittest.TestCase):
    """Tests for pymdfu CLI help"""
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

    def test_get_version(self):
        """Test that pymdfu CLI returns a version"""
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfu", "--version"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(f'pymdfu version {VERSION}' in mock_stdout.getvalue())

        testargs = ["pymdfu", "-V"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(f'pymdfu version {VERSION}' in mock_stdout.getvalue())

    def test_get_release_info(self):
        """Test that pymdfu CLI returns the release info"""
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfu", "--release-info"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(f"pymdfu version {VERSION}" in mock_stdout.getvalue())
        self.assertTrue(f"Build date:  {BUILD_DATE}" in mock_stdout.getvalue())

        testargs = ["pymdfu", "-R"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(f"pymdfu version {VERSION}" in mock_stdout.getvalue())
        self.assertTrue(f"Build date:  {BUILD_DATE}" in mock_stdout.getvalue())

    def test_get_help(self):
        """Test that pymdfu CLI returns help text"""
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfu", "--help"]
        with patch.object(sys, 'argv', testargs):
            # In pymdfu we create the help separately from configargparse so we exit program execution without
            # the SystemExit exception
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue('pymdfu [--help | -h]' in mock_stdout.getvalue())

        testargs = ["pymdfu"]
        with patch.object(sys, 'argv', testargs):
            # In pymdfu we create the help separately from configargparse so we exit program execution without
            # the SystemExit exception
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue('pymdfu [--help | -h]' in mock_stdout.getvalue())

    def test_usage_error(self):
        """Test CLI help with invalid action
        """
        mock_stderr = self._mock_stderr()
        testargs = ["pymdfu", "invalid_argument"]
        with patch.object(sys, 'argv', testargs):
            # configargparse will throw a SystemExit exception for invalid parameters
            with self.assertRaises(SystemExit) as system_exit:
                main()
        # The system exit code is most likely OS dependent so we check ony that it is not 0=success.
        # On Windows it returns 2
        self.assertNotEqual(system_exit.exception.code, 0)
        self.assertTrue(CliHelp.USAGE.strip() in mock_stderr.getvalue())

    def test_update_cmd_help(self):
        """Test CLI help for update action
        """
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfu", "update", "--help"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(CliHelp.update_cmd_help() in mock_stdout.getvalue())

    def test_update_usage_error(self):
        """Test CLI help with invalid action
        """
        mock_stderr = self._mock_stderr()
        testargs = ["pymdfu", "update", "invalid_argument"]
        with patch.object(sys, 'argv', testargs):
            # configargparse will throw a SystemExit exception for invalid parameters
            with self.assertRaises(SystemExit) as system_exit:
                main()
        # The system exit code is most likely OS dependent so we check ony that it is not 0=success.
        # On Windows it returns 2
        self.assertNotEqual(system_exit.exception.code, 0)
        self.assertTrue(CliHelp.USAGE_UPDATE_CMD.strip() in mock_stderr.getvalue())

    def test_client_info_cmd_help(self):
        """Test CLI help for client-info action
        """
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfu", "client-info", "--help"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(CliHelp.client_info_cmd_help() in mock_stdout.getvalue())

    def test_client_info_usage_error(self):
        """Test CLI help with invalid parameter for client-info action
        """
        mock_stderr = self._mock_stderr()
        testargs = ["pymdfu", "client-info", "invalid_argument"]
        with patch.object(sys, 'argv', testargs):
            # configargparse will throw a SystemExit exception for invalid parameters
            with self.assertRaises(SystemExit) as system_exit:
                main()
        # The system exit code is most likely OS dependent so we check ony that it is not 0=success.
        # On Windows it returns 2
        self.assertNotEqual(system_exit.exception.code, 0)
        self.assertTrue(CliHelp.USAGE_CLIENT_INFO_CMD.strip() in mock_stderr.getvalue())

    def test_tools_help_cmd_help(self):
        """Test CLI help for tools-help action
        """
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfu", "tools-help", "--help"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(CliHelp.tools_help_cmd_help() in mock_stdout.getvalue())

    def test_tools_help_usage_error(self):
        """Test CLI help with invalid parameter for tools-help action
        """
        mock_stderr = self._mock_stderr()
        testargs = ["pymdfu", "tools-help", "invalid_argument"]
        with patch.object(sys, 'argv', testargs):
            status = main()
        # The system exit code is most likely OS dependent so we check ony that it is not 0=success.
        self.assertNotEqual(status, 0)
        self.assertTrue(CliHelp.USAGE_TOOLS_HELP_CMD.strip() in mock_stderr.getvalue())
