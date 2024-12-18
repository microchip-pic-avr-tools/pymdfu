"""Tests GetClientInfo command"""
import unittest
import pytest
from packaging.version import Version
from ..mdfu import ClientInfo, ClientInfoType, MdfuCmd, MdfuClientInfoError


mandatory_parameters = bytes([
    ClientInfoType.BUFFER_INFO.value, 3, 128, 128 >> 8, 2, # size=3, buffer size=0x8000 (128), buffers=2
    ClientInfoType.PROTOCOL_VERSION.value, 3, 1, 2, 3, # size=3, 1=major, 2=minor, 3=patch
    ClientInfoType.COMMAND_TIMEOUTS.value, 3, 0, 10, 0 # size=3, 0=default timeout, timeout = 0x000A (10)
])

mandatory_parameters_and_some_command_timeouts = bytes([
    ClientInfoType.BUFFER_INFO.value, 3, 128, 128 >> 8, 2, # size=3, buffer size=0x8000 (128), buffers=2
    ClientInfoType.PROTOCOL_VERSION.value, 3, 1, 2, 3, # size=3, 1=major, 2=minor, 3=patch
    ClientInfoType.COMMAND_TIMEOUTS.value, 9, 0, 10, 0, # size=9, 0=default timeout, timeout = 0x000A (10)
    MdfuCmd.WRITE_CHUNK.value, 10, 0, # Write chunk command with timeout of 10
    MdfuCmd.GET_IMAGE_STATE.value, 500 & 0xff, 500 >> 8, # Get image state command with timeout of 500
    ClientInfoType.INTER_TRANSACTION_DELAY.value, 4, 100, 0, 0, 0 # size 2, 100 ns inter transaction delay
])

# Test client info with invalid size for buffer info parameter
# Correct size would be 3 but we have 2 here
invalid_parameter_size = bytes([
    ClientInfoType.BUFFER_INFO.value, 2, 2, 0, 3, # wrong size 2 for this parameter
    ClientInfoType.PROTOCOL_VERSION.value, 3, 1, 2, 3, # size=3, 1=major, 2=minor, 3=patch
    ClientInfoType.COMMAND_TIMEOUTS.value, 3, 0, 10, 0 # size=3, 0=default timeout, timeout = 0x000A (10)
])

# Test client info with an invalid parameter type
# Invalid parameter type used here is 0
invalid_info_type = bytes([
    0, 3, 128, 128 >> 8, 2, # Invalid info type = 0, size=3, buffer size=0x8000 (128), buffers=2
    ClientInfoType.PROTOCOL_VERSION.value, 3, 1, 2, 3, # size=3, 1=major, 2=minor, 3=patch
    ClientInfoType.COMMAND_TIMEOUTS.value, 3, 0, 10, 0] # size=3, 0=default timeout, timeout = 0x000A (10)
)

# The client info with missing mandatory parameter
# version parameter is mandatory but in this case we dont have it
missing_version_parameter = bytes([
    ClientInfoType.BUFFER_INFO.value, 3, 128, 128 >> 8, 2, # size=3, buffer size=0x8000 (128), buffers=2
    ClientInfoType.COMMAND_TIMEOUTS.value, 3, 0, 10, 0] # size=3, 0=default timeout, timeout = 0x000A (10)
)

class TestMdfuGetClientInfo(unittest.TestCase):
    """
    Integration tests for MDFU GetClientInfo command
    """
    def test_client_info_instantiation(self):
        """Instantiate ClientInfo class with different parameters
        """
        # Instantiate class with mandatory parameters from both, bytes and parameters.
        # Check that both end up with the same results
        client1 = ClientInfo.from_bytes(mandatory_parameters)
        client2 = ClientInfo(Version("1.2.3"), 2, 128, 1.0, {})
        self.assertEqual(client1.protocol_version, client2.protocol_version)
        self.assertEqual(client1.buffer_count, client2.buffer_count)
        self.assertEqual(client1.buffer_size, client2.buffer_size)
        self.assertEqual(client1.default_timeout, client2.default_timeout)
        self.assertEqual(client1.timeouts, client2.timeouts)

        # Instantiate class with mandatory parameters and optional command timings.
        # Do this based on bytes and parameters input, then check that both end up with the same results.
        client1 = ClientInfo.from_bytes(mandatory_parameters_and_some_command_timeouts)
        client2 = ClientInfo(Version("1.2.3"), 2, 128, 1.0, {MdfuCmd.WRITE_CHUNK: 1, MdfuCmd.GET_IMAGE_STATE: 50},
                             inter_transaction_delay=100e-9)
        self.assertEqual(client1.protocol_version, client2.protocol_version)
        self.assertEqual(client1.buffer_count, client2.buffer_count)
        self.assertEqual(client1.buffer_size, client2.buffer_size)
        self.assertEqual(client1.default_timeout, client2.default_timeout)
        self.assertEqual(client1.timeouts, client2.timeouts)
        self.assertEqual(client1.inter_transaction_delay, client2.inter_transaction_delay)

        # Convert to bytes and back again, then look if input and output match
        client1 = ClientInfo(Version("1.0.0"), 1, 512, 1, {MdfuCmd.GET_IMAGE_STATE: 5, MdfuCmd.WRITE_CHUNK: 0.2},
                             inter_transaction_delay=100e-9)
        client_bytes = client1.to_bytes()
        client2 = ClientInfo.from_bytes(client_bytes)
        self.assertEqual(client1.protocol_version, client2.protocol_version)
        self.assertEqual(client1.buffer_count, client2.buffer_count)
        self.assertEqual(client1.buffer_size, client2.buffer_size)
        self.assertEqual(client1.default_timeout, client2.default_timeout)
        self.assertEqual(client1.timeouts, client2.timeouts)
        self.assertEqual(client1.inter_transaction_delay, client2.inter_transaction_delay)

    def test_client_info_instantiation_with_invalid_data(self):
        """Instantiate ClientInfo class with invalid parameters
        """
        with pytest.raises(MdfuClientInfoError):
            ClientInfo.from_bytes(invalid_parameter_size)
        with pytest.raises(MdfuClientInfoError):
            ClientInfo.from_bytes(invalid_info_type)
        with pytest.raises(MdfuClientInfoError):
            ClientInfo.from_bytes(missing_version_parameter)
