"""Tests for MDFU client"""
import unittest
import sys
import io
import time
from mock import patch
from pymdfu.mac import MacFactory
from pymdfu.pymdfuclient_cli import main
from pymdfu.pymdfuclient import MdfuClient
from pymdfu import __version__ as VERSION
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.mdfu import Mdfu
from pymdfu.tools.tools import ToolFactory

class TestMdfuClient(unittest.TestCase):
    """Tests for MDFU client"""
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
        """Test that MDFU client CLI returns a version"""
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfuclient", "--version"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)
        self.assertTrue(f'pymdfuclient version {VERSION}' in mock_stdout.getvalue())

    def test_get_help(self):
        """Test that MDFU client CLI returns help text"""
        mock_stdout = self._mock_stdout()
        testargs = ["pymdfuclient", "--help"]
        with patch.object(sys, 'argv', testargs):
            # The --help argument is a built-in part of argparse so it will result in a SystemExit exception instead of
            #  a normal return code
            #with self.assertRaises(SystemExit) as system_exit:
            retval = main()
        self.assertEqual(retval, 0)
        #self.assertEqual(system_exit.exception.code, 0)
        self.assertTrue('pymdfuclient' in mock_stdout.getvalue())

    def test_network_client_parameters(self):
        """Test that MDFU client CLI verifies host and port correctly"""
        client_run_patch = patch("pymdfu.pymdfuclient_cli.run_mdfu_client")
        self.addCleanup(client_run_patch.stop)
        client_run_patch.start()
        self._mock_stdout()
        testargs = ["pymdfuclient", "--tool", "network", "--port", "5559", "--host", "localhost"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)

        testargs = ["pymdfuclient", "--tool", "network"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 0)

        mock_stderr = self._mock_stderr()

        testargs = ["pymdfuclient", "--tool", "network", "--port", "abc"]
        with patch.object(sys, 'argv', testargs):
            #with self.assertRaises(SystemExit) as system_exit:
            retval = main()
            #self.assertEqual(system_exit.exception.code, 0)
        self.assertNotEqual(retval, 0)
        self.assertTrue('argument --port: invalid int value' in mock_stderr.getvalue())

    def test_error_during_execution(self):
        """Test exception handling in main

        Throw an exception in the client processing loop and make sure the
        application handles it correctly.
        """
        client_run_patch = patch("pymdfu.pymdfuclient_cli.run_mdfu_client")
        self.addCleanup(client_run_patch.stop)
        mock_client_run = client_run_patch.start()
        # We catch any exception during client execution so the exception base class is just fine here
        mock_client_run.side_effect = Exception("Exception injected by pymdfu run client mock")
        mock_stdout = self._mock_stdout()

        testargs = ["pymdfuclient", "--tool", "network", "--port", "5559", "--host", "localhost"]
        with patch.object(sys, 'argv', testargs):
            retval = main()
        self.assertEqual(retval, 1)
        self.assertTrue('Operation failed with' in mock_stdout.getvalue())

    def test_host_connect(self):
        """Test connection between client and host

        Open and close connection at MAC layer.
        """
        host = "localhost"
        port = 5559
        mdfu_client_mac = MacFactory.get_socket_host_mac(host, port)
        mdfu_client_transport = UartTransport(mdfu_client_mac)
        mdfu_client = MdfuClient(mdfu_client_transport)
        mdfu_client.start()

        # We need to give the client some time to start up before we connect
        # otherwise the port will not be opened in time and we get a
        # connection refused error from the OS.
        time.sleep(1)
        mdfu_host = MacFactory.get_socket_client_mac(3, "localhost", 5559)
        mdfu_host.open()
        mdfu_host.close()

        mdfu_client.stop()

    def test_update(self):
        """Run MDFU session between client and host
        """
        args = ["--host", "localhost", "--port", "5559"]
        mdfu_client_tool = ToolFactory.get_client_tool("network", args)
        #mdfu_client_mac = MacFactory.get_socket_host_mac(host, port)
        #mdfu_client_transport = UartTransport(mdfu_client_mac)
        mdfu_client = MdfuClient(mdfu_client_tool)
        mdfu_client.start()

        # We need to give the client some time to start up before we connect
        # otherwise the port will not be opened in time and we get a
        # connection refused error from the OS.
        time.sleep(1)
        #mdfu_host_mac = MacFactory.get_socket_client_mac(3, "localhost", 5559)
        #mdfu_host_transport = UartTransport(mac=mdfu_host_mac)
        mdfu_host_tool = ToolFactory.get_tool("network", args)
        mdfu_host = Mdfu(mdfu_host_tool)
        upgrade_image = bytes(512 * [0xff])
        mdfu_host.run_upgrade(upgrade_image)
        mdfu_client.stop()
