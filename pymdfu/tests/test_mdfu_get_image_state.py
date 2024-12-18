"""Tests GetClientInfo command"""
import unittest
import pytest
from mock import patch
from ..mdfu import MdfuCmd, MdfuStatusPacket, ImageState, MdfuStatus, MdfuProtocolError,Mdfu

class TestMdfuGetImageState(unittest.TestCase):
    """
    Integration tests for MDFU GetImageState command
    """
    def setUp(self):
        self.status_packet = None

    def _mock_send_cmd(self, command: MdfuCmd, data=bytes(), sync=False):
        return self.status_packet

    def test_mdfu_get_image_state(self):
        """Test decoding of image state
        """
        with patch.object(Mdfu, 'send_cmd', self._mock_send_cmd):
            mdfu = Mdfu(None)
            self.status_packet = MdfuStatusPacket(1, MdfuStatus.SUCCESS.value, bytes([ImageState.VALID.value]), resend=False)
            state = mdfu._get_image_state()
            self.assertEqual(state, ImageState.VALID)

            # Test invalid image state
            with pytest.raises(MdfuProtocolError):
                self.status_packet = MdfuStatusPacket(1, MdfuStatus.SUCCESS.value, bytes([0xff]))
                state = mdfu._get_image_state()
            # Test too many payload bytes returned
            with pytest.raises(MdfuProtocolError):
                self.status_packet = MdfuStatusPacket(1, MdfuStatus.SUCCESS.value, bytes(2))
                state = mdfu._get_image_state()
            # Test no payload bytes returned
            with pytest.raises(MdfuProtocolError):
                self.status_packet = MdfuStatusPacket(1, MdfuStatus.SUCCESS.value)
                state = mdfu._get_image_state()
