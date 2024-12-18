"""Test MDFU firmware update"""
import unittest
import mock
import pytest
from packaging.version import Version
from pymdfu.transport.uart_transport import UartTransport
from ..mdfu import Mdfu, ClientInfo, MdfuUpdateError
from ..pymdfuclient import MdfuClient
from ..mac import MacFactory


class TestMdfuUpdate(unittest.TestCase):
    """
    Integration tests for CLI
    """
    def setUp(self):
        pass

    def test_simulate_update(self):
        """Simulate a firmware update
        """
        upgrade_image = bytes(512 * [0xff])
        # Thread termination is shorter with short timeout so the test finishes faster
        mac_host, mac_client = MacFactory.get_bytes_based_mac(timeout=1)
        transport_client = UartTransport(mac=mac_client, timeout=1)
        client = MdfuClient(transport_client)

        transport_host = UartTransport(mac=mac_host)
        host = Mdfu(transport_host)

        client.start()
        host.run_upgrade(upgrade_image)
        client.stop()

    def test_update_protocol_version_error(self):
        """Test update abort when client version is higher than host version
        """
        with mock.patch.object(Mdfu, '_get_client_info', mock.MagicMock()):
            transport = mock.MagicMock()
            host = Mdfu(transport)
            host.client = ClientInfo(Version("99.99.99"), 1, 256, 1)
            with pytest.raises(MdfuUpdateError):
                host.run_upgrade(bytes(1))
