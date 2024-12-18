"""Tests for MDFU packet classes MdfuCmdPacket and MdfuStatusPacket"""
import unittest
import pytest
from ..mdfu import MdfuCmdPacket, MdfuStatusPacket, MdfuCmd, MdfuStatus,\
                    MdfuCmdNotSupportedError, MdfuStatusInvalidError

class TestMdfuPacket(unittest.TestCase):
    """
    Integration tests for CLI
    """
    def setUp(self):
        pass

    def test_cmd_packet_from_binary(self):
        """Instantiate MdfuCmdPacket from binary data.
        """
        test_packet = bytes([0x81, 0x01, 0x11, 0x22, 0x33, 0x44])
        packet = MdfuCmdPacket.from_binary(test_packet)

        self.assertTrue(packet.sync)
        self.assertEqual(packet.sequence_number, 1)
        self.assertEqual(packet.command, 0x01)
        self.assertEqual(packet.data, bytes([0x11, 0x22, 0x33, 0x44]))

    def test_cmd_packet_to_binary(self):
        """Build MDFU binary packet from MdfuCmd class"""
        data = bytes([1,2,3,4])
        packet_bin_expected = bytes([0x81, MdfuCmd.GET_CLIENT_INFO.value]) + data
        packet = MdfuCmdPacket(1, MdfuCmd.GET_CLIENT_INFO.value, data, sync=True)
        packet_bin = packet.to_binary()
        self.assertEqual(packet_bin, packet_bin_expected)

    def test_invalid_cmd_packet(self):
        """Test MdfuCmdPacket related exceptions
        """
        # Test sequence number out of range exception (valid values are [0..31])
        with pytest.raises(ValueError):
            MdfuCmdPacket(32, MdfuCmd.GET_CLIENT_INFO.value, None)
        with pytest.raises(ValueError):
            MdfuCmdPacket(-1, MdfuCmd.GET_CLIENT_INFO.value, None)
        # Test if not supported command is detected (0 is not allowed and 0xff is not defined)
        with pytest.raises(MdfuCmdNotSupportedError):
            MdfuCmdPacket(1,  0, None)
        with pytest.raises(MdfuCmdNotSupportedError):
            MdfuCmdPacket(1, 0xff, None)

    def test_status_packet_from_binary(self):
        """Create MdfuStatusPacket from binary data.
        """
        data = bytes([0x80, 0x00, 0x01, 0x00])
        test_packet = bytes([0x00, 0x01]) + data
        packet = MdfuStatusPacket.from_binary(test_packet)

        self.assertEqual(packet.sequence_number, 0)
        self.assertEqual(packet.status, MdfuStatus.SUCCESS.value)
        self.assertEqual(packet.data, data)
        self.assertFalse(packet.resend)

        data = bytes([])
        test_packet = bytes([0x42, 0x04]) + data
        packet = MdfuStatusPacket.from_binary(test_packet)

        self.assertEqual(packet.sequence_number, 2)
        self.assertEqual(packet.status, MdfuStatus.COMMAND_NOT_EXECUTED.value)
        self.assertEqual(packet.data, bytes())
        self.assertTrue(packet.resend)

    def test_invalid_status_packet(self):
        """Test MdfuCmdPacket related exceptions
        """
        # Test sequence number out of range exception (valid values are [0..31])
        with pytest.raises(ValueError):
            MdfuStatusPacket(32, MdfuStatus.SUCCESS.value, None)
        with pytest.raises(ValueError):
            MdfuStatusPacket(-1, MdfuStatus.SUCCESS.value, None)
        # Test if not supported status is detected (0 is not allowed and 0xff is not defined)
        with pytest.raises(MdfuStatusInvalidError):
            MdfuStatusPacket(1,  0, None)
        with pytest.raises(MdfuStatusInvalidError):
            MdfuStatusPacket(1, 0xff, None)
