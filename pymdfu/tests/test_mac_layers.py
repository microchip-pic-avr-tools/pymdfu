"""Tests for MAC socket layer"""
import unittest
import io
from mock import patch
from pymdfu.mac import MacFactory
from pymdfu.mac.network_mac import MacSocketPacketHost, MacSocketPacketClient

class TestMacLayers(unittest.TestCase):
    """Tests for MAC layers"""
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

    def _run_connection_test(self, host, client):
        host.open()
        client.open()
        msg = "Hello".encode("utf-8")

        client.write(msg)
        data = host.read(len(msg))
        self.assertEqual(msg, data)

        host.write(msg)
        data = client.read(len(msg))
        self.assertEqual(msg, data)

        client.close()
        host.close()

    def _run_package_size_test(self, host, client):
        host.open()
        client.open()
        messages = []
        messages.append(bytes([i % 256 for i in range(257)]))
        messages.append(bytes([i % 256 for i in range(1025)]))
        messages.append(bytes([i % 256 for i in range(1600)]))

        for msg in messages:
            client.write(msg)
            data = host.read(len(msg))
            self.assertEqual(msg, data)

            host.write(msg)
            data = client.read(len(msg))
            self.assertEqual(msg, data)

        client.close()
        host.close()

    def _run_non_blocking_read_test(self, host, client):
        host.open()
        client.open()
        msg = "Hello".encode("utf-8")

        # Try to read when host has not sent anything yet
        data = client.read(len(msg))
        self.assertEqual(data, bytes())

        host.write(msg)
        # Do a partial read
        data = client.read(len(msg) - 2)
        self.assertEqual(data, msg[:-2])
        data += client.read(2)
        self.assertEqual(data, msg)

        data = host.read(len(msg))
        self.assertEqual(data, bytes())

        client.write(msg)
        data = host.read(len(msg) - 2)
        self.assertEqual(data, msg[:-2])
        data += host.read(2)
        self.assertEqual(data, msg)

    def test_socket_mac(self):
        """ Test socket MAC.

        Create host and client MAC socket layers, connect them
        and send some data back and forth.
        """
        host = MacFactory.get_socket_host_mac()
        client = MacFactory.get_socket_client_mac()
        self._run_connection_test(host, client)

    def test_socket_packet_mac(self):
        host = MacSocketPacketHost("localhost", 5559)
        client = MacSocketPacketClient(host="localhost", port=5559)
        self._run_connection_test(host, client)
        # A new host object is required here since it is based on a thread and the
        # start method of the thread can only be initiated once
        host = MacSocketPacketHost("localhost", 5559)
        self._run_package_size_test(host, client)

    def test_socketpair_mac(self):
        """ Test socketpair MAC.

        Create host and client socketpair MACs, connect them
        and send some data back and forth.
        """
        host, client = MacFactory.get_socketpair_based_mac(timeout=1)
        self._run_connection_test(host, client)
        host, client = MacFactory.get_socketpair_based_mac(timeout=0)
        self._run_non_blocking_read_test(host, client)
        host, client = MacFactory.get_socketpair_based_mac(timeout=None)
        self._run_connection_test(host, client)

    def test_bytes_mac(self):
        """ Test bytes MAC.

        Create host and client bytes MACs, connect them
        and send some data back and forth.
        """
        host, client = MacFactory.get_bytes_based_mac(timeout=1)
        self._run_connection_test(host, client)
        host, client = MacFactory.get_bytes_based_mac(timeout=0)
        self._run_non_blocking_read_test(host, client)
        host, client = MacFactory.get_bytes_based_mac(timeout=None)
        self._run_connection_test(host, client)

    def test_packet_mac(self):
        """ Test packet MAC.

        Create host and client packet MACs, connect them
        and send some data back and forth.
        """
        host, client = MacFactory.get_packet_based_mac(timeout=1)
        host.open()
        client.open()
        msg = "Hello".encode("utf-8")

        client.write(msg)
        data = host.read()
        self.assertEqual(msg, data)

        host.write(msg)
        data = client.read()
        self.assertEqual(msg, data)

        client.close()
        host.close()
