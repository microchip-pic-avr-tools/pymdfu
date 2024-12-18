"""Tests decoding and logging of MDFU error response codes"""
import io
import unittest
import pytest
from mock import patch
from pymdfu.mdfu import MdfuStatusPacket, Mdfu, MdfuStatus, \
        CmdNotExecutedCause, FileTransferAbortCause

class TestMdfuPacket(unittest.TestCase):
    """
    Integration tests for CLI
    """
    def setUp(self):
        pass

    def _mock_stderr(self):
        """
        Returns stderr mock.

        Content sent to stderr can be fetched with mock_stderr.getvalue()
        """
        mock_stderr_patch = patch('sys.stderr', new_callable=io.StringIO)
        self.addCleanup(mock_stderr_patch.stop)
        return mock_stderr_patch.start()

    def test_error_decoding(self):
        """Instantiate MdfuCmdPacket from binary data.
        """
        mdfu = Mdfu(None)

        # Test status packet with COMMAND_NOT_EXECUTED status and error cause TRANSPORT_INTEGRITY_CHECK_ERROR
        status_packet = MdfuStatusPacket(0, MdfuStatus.COMMAND_NOT_EXECUTED.value,
                                            data = bytes([CmdNotExecutedCause.TRANSPORT_INTEGRITY_CHECK_ERROR.value]))
        with self.assertLogs() as log:
            mdfu.log_error_cause(status_packet)
        self.assertTrue(any(CmdNotExecutedCause.TRANSPORT_INTEGRITY_CHECK_ERROR.description in x for x in log.output))

        # Test status packet with ABORT_FILE_TRANSFER and error cause GENERIC_CLIENT_ERROR
        status_packet = MdfuStatusPacket(0, MdfuStatus.ABORT_FILE_TRANSFER.value,
                                         data = bytes([FileTransferAbortCause.GENERIC_CLIENT_ERROR.value]))
        with self.assertLogs() as log:
            mdfu.log_error_cause(status_packet)
        self.assertTrue(any(FileTransferAbortCause.GENERIC_CLIENT_ERROR.description in x for x in log.output))

        # Test status packet with COMMAND_NOT_EXECUTED but no abort cause
        status_packet = MdfuStatusPacket(0, MdfuStatus.COMMAND_NOT_EXECUTED.value)
        with self.assertLogs() as log:
            mdfu.log_error_cause(status_packet)
        self.assertFalse(any("Command not executed cause" in x for x in log.output))
        self.assertFalse(any("Invalid command not executed cause" in x for x in log.output))
        
        # Test invalid response cause for COMMAND_NOT_EXECUTED status
        with self.assertLogs() as log:
            status_packet = MdfuStatusPacket(0, MdfuStatus.COMMAND_NOT_EXECUTED.value, data=bytes([0xff]))
            mdfu.log_error_cause(status_packet)
        self.assertTrue(any("Invalid command not executed cause" in x for x in log.output))

        # Test status packet with ABORT_FILE_TRANSFER but no abort cause
        status_packet = MdfuStatusPacket(0, MdfuStatus.ABORT_FILE_TRANSFER.value)
        with self.assertLogs() as log:
            mdfu.log_error_cause(status_packet)
        self.assertFalse(any("File transfer abort cause" in x for x in log.output))
        self.assertFalse(any("Invalid file abort cause" in x for x in log.output))
        
        # Test invalid response cause for ABORT_FILE_TRANSFER status
        with self.assertLogs() as log:
            status_packet = MdfuStatusPacket(0, MdfuStatus.ABORT_FILE_TRANSFER.value, data=bytes([0xff]))
            mdfu.log_error_cause(status_packet)
        self.assertTrue(any("Invalid file abort cause" in x for x in log.output))


