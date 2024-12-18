"""Tests for MDFU serial transport"""
import time
import unittest
import pytest
import mock
from ..transport.uart_transport import UartTransport, TransportError, Frame, \
    FRAME_END_ESC_SEQ, FRAME_START_ESC_SEQ, ESCAPE_SEQ_ESC_SEQ, FRAME_END_CODE, FRAME_START_CODE
from ..mac.mac import Mac

class TestMdfuPacket(unittest.TestCase):
    """
    Serial transport layer tests
    """
    def setUp(self):
        pass

    def test_mac_property(self):
        """Test that the transport returns the MAC layer through the mac property"""
        mac_mock = mock.MagicMock(Mac)
        transport = UartTransport(mac_mock)
        self.assertEqual(mac_mock, transport.mac)

    def test_read_until(self):
        """Test transport layer read_until function
        """
        data = bytes([0xCC, 0x55, 0x00, 0x00, 0xcc, 0x33])
        frame_with_end_seq = data + bytes([FRAME_END_CODE])

        mac_mock = mock.MagicMock()
        mac_mock.read.side_effect = [bytes([x]) for x in frame_with_end_seq]
        timer_mock = mock.MagicMock()
        timer_mock.expired.return_value = False
        transport = UartTransport(mac_mock)
        rsp = transport.read_until(bytes([FRAME_END_CODE]), timer_mock)
        # Should return the same frame that was provided through MAC layer
        # mock object
        self.assertEqual(frame_with_end_seq, rsp)

    def test_read(self):
        """Test serial transport read function
        """
        # Frame with some data and escape sequences to test reserved codes
        data = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55]) \
                + FRAME_START_ESC_SEQ + FRAME_END_ESC_SEQ \
                + ESCAPE_SEQ_ESC_SEQ

        # Invalid frame that does not contain a valid checksum
        frame = bytes([FRAME_START_CODE]) + data + bytes([FRAME_END_CODE])
        # Create a mock object for the MAC layer
        mac_mock = mock.MagicMock()
        # Add the frame as an iteratable object to return a byte each time the
        # read function of the MAC layer mock object is called
        mac_mock.read.side_effect = [bytes([x]) for x in frame]
        # Initialize serial transport layer with MAC layer mock object
        transport = UartTransport(mac_mock)
        # Since we have an invalid CRC in the frame we expect the transport layer
        # to raise a TransportError
        with pytest.raises(TransportError):
            rsp = transport.read()

        # Create a valid serial transport frame
        frame = Frame(data)
        # Add the frame as return value to the MAC layer read function
        mac_mock.read.side_effect = [bytes([x]) for x in frame.to_bytes()]
        rsp = transport.read()
        # The received data should match the data we put into the frame
        self.assertEqual(data, rsp)

        # Create MAC layer read function for MAC layer mock that returns nothing
        # to force a timeout to happen
        def read(size): #pylint: disable=unused-argument
            time.sleep(0.5)
            return bytes()

        mac_mock.read.side_effect = read
        # The transport layer read function should time out and raise a
        # TransportError
        with pytest.raises(TransportError):
            rsp = transport.read(timeout=1)
        mac_mock.read.assert_called()
        

