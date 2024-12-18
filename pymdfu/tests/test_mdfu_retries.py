"""Test MDFU firmware update"""
import unittest
import mock
import pytest
from ..mdfu import Mdfu, MdfuProtocolError, TransportError

class TestMdfuRetries(unittest.TestCase):
    """
    Integration tests for CLI
    """
    def setUp(self):
        pass

    def test_mdfu_retries(self):
        """Test MDFU command retries
        """
        transport = mock.MagicMock()
        # We want the MDFU command to fail so we raise a TransportError in the
        # transport write function. A transport error is a recoverable error so the
        # MDFU protocol will retry sending the command if number of retries is larger than 0.
        transport.write.side_effect = TransportError("Intentional mock timeout exception")

        host = Mdfu(transport, retries=0)
        host.open()
        with pytest.raises(MdfuProtocolError):
            host.get_client_info()
        # Check that the transport write function was called
        transport.write.assert_called()
        # For 0 retries we expect the transport write function to be called once
        self.assertEqual(transport.write.call_count, 1)

        transport.reset_mock()
        transport.write.side_effect = TransportError("Intentional mock timeout exception")
        host.retries = 3
        with pytest.raises(MdfuProtocolError):
            host.get_client_info()
        transport.write.assert_called()
        # For 3 retries we expect the transport write function to be called four times
        # Once for the initial attempt and then 3 times for the 3 retries.
        self.assertEqual(transport.write.call_count, 4)
