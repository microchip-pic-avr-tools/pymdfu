"""MDFU protocol
"""
from enum import Enum
from logging import getLogger
from packaging.version import Version
from pymdfu.utils import EnumDescription
from .transport import Transport, TransportError


mdfu_protocol_version = Version("1.2.0")

class MdfuStatus(Enum):
    """MDFU status codes
    """
    SUCCESS = 1
    COMMAND_NOT_SUPPORTED = 2
    NOT_AUTHORIZED = 3
    COMMAND_NOT_EXECUTED = 4
    ABORT_FILE_TRANSFER = 5

class MdfuCmd(Enum):
    """MDFU command codes
    """
    GET_CLIENT_INFO = 1
    START_TRANSFER = 2
    WRITE_CHUNK = 3
    GET_IMAGE_STATE = 4
    END_TRANSFER = 5

class ClientInfoType(Enum):
    """MDFU data types for GetClientInfo command response"""
    PROTOCOL_VERSION = 1
    BUFFER_INFO = 2
    COMMAND_TIMEOUTS = 3
    INTER_TRANSACTION_DELAY = 4

class ImageState(Enum):
    """MDFU firmware image states for GetImageState command response"""
    VALID = 1
    INVALID = 2

class FileTransferAbortCause(EnumDescription):
    """Error codes and description for file transfer abort causes"""
    GENERIC_CLIENT_ERROR = (0, "Generic problem encountered by client")
    INVALID_FILE = (1, "Generic problem with the update file")
    INVALID_CLIENT_DEVICE_ID = (2, "The update file is not compatible with the client device ID")
    ADDRESS_ERROR = (3, "An invalid address is present in the update file")
    ERASE_ERROR = (4, "Client memory did not properly erase")
    WRITE_ERROR = (5, "Client memory did not properly write")
    READ_ERROR = (6, "Client memory did not properly read")
    APPLICATION_VERSION_ERROR = (7, "Client did not allow changing to the application version " \
    "in the update file")

class CmdNotExecutedCause(EnumDescription):
    """Transport error causes"""
    TRANSPORT_INTEGRITY_CHECK_ERROR = (0, "Command received failed the Transport Integrity Check "\
    "indicating that the command was corrupted during transportation from the host to the client")
    COMMAND_TOO_LONG = (1, "Received command exceeded the size of the client buffer")
    COMMAND_TOO_SHORT = (2, "Received command was too short")
    SEQUENCE_NUMBER_INVALID = (3, "Sequence number of the received command is invalid")

def chunkify(data: bytes, chunk_size: int, padding=None):
    """Split data up into chunks

    :param data: Data for chunking.
    :type data: Bytes like object
    :param chunk_size: Chunks size
    :type chunk_size: int
    :param padding: Byte value to pad in last chunk if data is not a multiple
    of chunk_size, optional, default None = do not pad
    :type padding: int
    :return: Chunks of data
    :rtype: List object with chunks of data
    """
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    if padding:
        padding_byte_count = len(data) % chunk_size
        chunks[-1] += bytes([padding] * padding_byte_count)
    return chunks

class MdfuProtocolError(Exception):
    """Generic MDFU exception
    """

class MdfuCmdNotSupportedError(MdfuProtocolError):
    """MDFU exception if command is not supported on client
    """

class MdfuClientInfoError(MdfuProtocolError):
    """MDFU exception if client informatino is invalid
    """
class MdfuStatusInvalidError(MdfuProtocolError):
    """MDFU exception for an invalid MDFU packet status
    """

class MdfuUpdateError(MdfuProtocolError):
    """MDFU exception for a failed firmware update
    """
# pylint: disable-next=too-few-public-methods
class MdfuPacket():
    """MDFU packet class
    """

class InterTransactionDelay(object):
    """
    Represents a delay between transactions in seconds.

    The delay is stored internally as nanoseconds for precision.

    :ivar value: The delay value in nanoseconds.
    :vartype value: int

    :cvar MAX_INTER_TRANSACTION_DELAY_SECONDS: The maximum delay allowed in seconds.
    :cvartype MAX_INTER_TRANSACTION_DELAY_SECONDS: float
    """
    MAX_INTER_TRANSACTION_DELAY_SECONDS = 0xffff_ffff * 1e-9
    def __init__(self, value):
        """
        Initialize the InterTransactionDelay object with a delay value in seconds.

        :param value: The delay value in seconds. Must be in the range of 0 to 4.294967295 seconds
        :type value: float
        """
        if value > self.MAX_INTER_TRANSACTION_DELAY_SECONDS:
            raise ValueError("Inter transaction delay is too long. Valid values are 0 <= delay < 4.295 seconds")
        if value < 0:
            raise ValueError("Inter transaction delay must be a positive value")
        # store as ns value
        self.value = int(value * 1e9)

    @property
    def seconds(self):
        """
        Get the delay value in seconds.

        :return: The delay value in seconds, rounded to 9 decimal places.
        :rtype: float
        """
        return round(self.value * 1e-9, 9)

    @property
    def ns(self):
        """
        Get the delay value in nanoseconds.

        :return: The delay value in nanoseconds.
        :rtype: int
        """
        return self.value

    @classmethod
    def from_bytes(cls, data):
        """
        Create an InterTransactionDelay object from a 4-byte representation.

        :param data: A 4-byte representation of the delay.
        :type data: bytes
        :return: An instance of InterTransactionDelay.
        :rtype: InterTransactionDelay
        :raises ValueError: If the provided data is not 4 bytes.
        """
        if len(data) != 4:
            raise ValueError(f"Expected 4 bytes for inter-transaction delay but got {len(data)}")
        itd_ns = int.from_bytes(data, byteorder="little")
        # Large/small number calculations can lead to a small rounding error. We correct this
        # here by rounding up to nano seconds (e.g. 50 * 1e-6 would lead to 4.9999999999999996e-05).
        # This small error is not relevant so we do the rounding to avoid confusion for the user.
        itd_seconds = round(itd_ns * 1e-9, 9)
        return cls(itd_seconds)

    def to_bytes(self):
        """
        Convert the InterTransactionDelay object to a 4-byte representation.

        :return: A 4-byte representation of the delay.
        :rtype: bytes
        """
        return self.value.to_bytes(4, byteorder="little")

class MdfuCmdPacket(MdfuPacket):
    """MDFU command packet
    """
    def __init__(self, sequence_number: int, command: int, data: bytes, sync=False):
        """MDFU command packet initialization

        :param sequence_number: Sequence number for this packet, valid numbers are from 0 to 31
        :type sequence_number: int
        :param command: Command to execute
        :type command: int
        :param data: Packet data
        :type data: bytes
        :param sync: Whether or not this packet should initiate a synchronization of
        the sequence number, defaults to False
        :type sync: bool, optional
        """
        self.sync = sync
        self.command = command
        self.data = data
        if sequence_number > 31 or sequence_number < 0:
            raise ValueError("Valid values for MDFU packet sequence number are 0...31", sequence_number)
        self.sequence_number = sequence_number
        cmd_values = set(item.value for item in MdfuCmd)
        if command not in cmd_values:
            raise MdfuCmdNotSupportedError(f"{hex(command)} is not a valid MDFU command")


    def __repr__(self) -> str:
        return f"""\
Command:         {MdfuCmd(self.command).name} ({hex(self.command)})
Sequence Number: {self.sequence_number}
Sync:            {self.sync}
Data:            {self.data}
"""

    @staticmethod
    def decode_packet(packet: bytes) -> tuple:
        """ Decode a MDFU packet

        :param packet: MDFU packet
        :type packet: Bytes
        :return: Fields of the packet (Sequence number, command, data, sync)
        :rtype: Tuple(Int, Int, Bytes, Bool)
        """
        sequence_field = packet[0]
        sequence_number = sequence_field & 0x1f
        sync = bool(sequence_field & 0x80)
        command = int.from_bytes(packet[1:2], byteorder="little")
        data = packet[2:]
        return sequence_number, command, data, sync

    @classmethod
    def from_binary(cls, packet: bytes):
        """Create MDFU command packet from binary data.

        :param packet: MDFU packet in binary form
        :type packet: Bytes like object
        :return: Command packet object
        :rtype: MdfuCmdPacket
        """
        sequence_number, command, data, sync = cls.decode_packet(packet)
        pack = cls(sequence_number, command, data, sync=sync)
        return pack

    def to_binary(self):
        """Create binary MDFU packet

        :return: MDFU packet in binary form
        :rtype: Bytes
        """
        sequence_field = self.sequence_number | ((1 << 7) if self.sync else 0x00)
        packet =  sequence_field.to_bytes(1, byteorder="little") \
            + self.command.to_bytes(1, byteorder="little") \
            + self.data
        return packet

class MdfuStatusPacket(MdfuPacket):
    """MDFU status packet
    """
    def __init__(self, sequence_number, status, data=bytes(), resend=False):
        """MDFU packet initialization

        :param sequence_number: Sequence number for the packet, valid numbers are from 0 to 31
        :type sequence_number: Int
        :param status: Status code
        :type status: Int
        :param data: Data, defaults to bytes()
        :type data: Bytes like object, optional
        :param resend: Resend flag for the packet, defaults to False
        :type resend: bool, optional
        """
        if sequence_number > 31 or sequence_number < 0:
            raise ValueError("Valid values for MDFU packet sequence number are 0...31")
        self.sequence_number = sequence_number

        status_values = set(item.value for item in MdfuStatus)
        if status not in status_values:
            raise MdfuStatusInvalidError(f"{hex(status)} is not a valid MDFU status")
        self.status = status
        self.resend = resend
        self.data = data

    def __repr__(self) -> str:
        return f"""\
Sequence Number: {self.sequence_number}
Status:          {MdfuStatus(self.status).name} ({hex(self.status)})
Resend:          {self.resend}
Data:            0x{self.data.hex()}
"""
    @staticmethod
    def decode_packet(packet):
        """Decode a status packet

        :param packet: Packet
        :type packet: Bytes like object
        :return: packet sequence number (int), status (int), data (bytes), resend (bool)
        :rtype: tuple(int, int, bytes, bool)
        """
        sequence_field = packet[0]
        sequence_number = sequence_field & 0x1f
        resend = bool(sequence_field & 0x40)
        status = int.from_bytes(packet[1:2], byteorder="little")
        data = packet[2:]
        return sequence_number, status, data, resend

    @classmethod
    def from_binary(cls, packet):
        """Create MDFU status packet from binary data.

        :param packet: MDFU packet in binary form
        :type packet: Bytes like object
        :return: Status packet object
        :rtype: MdfuStatusPacket
        """
        sequence_number, status, data, resend = cls.decode_packet(packet)
        pack = cls(sequence_number, status, data, resend=resend)
        return pack

    def to_binary(self):
        """Create binary MDFU packet

        :return: MDFU packet in binary form
        :rtype: Bytes
        """
        sequence_field = self.sequence_number | ((1 << 6) if self.resend else 0x00)
        packet =  sequence_field.to_bytes(1, byteorder="little") \
            + self.status.to_bytes(1, byteorder="little") \
            + self.data
        return packet

class ClientInfo():
    """Class to handle MDFU client information
    """
    PARAM_TYPE_SIZE = 1
    PARAM_LENGTH_SIZE = 1
    BUFFER_INFO_SIZE = 3
    PROTOCOL_VERSION_SIZE = 3
    PROTOCOL_VERSION_INTERNAL_SIZE = 4
    COMMAND_TIMEOUT_SIZE = 3
    INTER_TRANSACTION_DELAY_SIZE = 4
    SECONDS_PER_LSB = 0.1
    LSBS_PER_SECOND = 10

    def __init__(self, version: Version, buffer_count: int, buffer_size: int,
                    default_timeout: float, timeouts: dict = None, inter_transaction_delay = None):
        """Class initialization

        :param version: Client MDFU protocol version 
        :type version: Version (from packaging.version)
        :param buffer_count: Number of command buffers on client
        :type buffer_count: int
        :param buffer_size: Maximum MDFU packet data length (=command buffer size)
        :type buffer_size: int
        :param default_timeout: Default command timeout that must be used when a command
        does not have a timeout specified in timeouts parameter. The timeout is specified
        in seconds. Allowed range is 0.1s - 6,553.5s (~109 minutes)).
        :type default_timeout: float
        :param timeouts: Client command timeouts.
        :type timeouts: dict(MdfuCmd: float)
        :param inter_transaction_delay: Delay in seconds between transactions on MAC layer (e.g. read/write calls)
        :type inter_transaction_delay: float
        """
        self.default_timeout = default_timeout
        if timeouts:
            self.timeouts = timeouts
        else:
            self.timeouts = {}
        self._verify_timeouts()
        self.protocol_version = version
        self.buffer_size = buffer_size
        self.buffer_count = buffer_count
        self.inter_transaction_delay = inter_transaction_delay

    def __str__(self):
        """Creates human readable representation of client information
        """
        if self.inter_transaction_delay is None:
            itd_txt = ""
        else:
            itd_txt = f"- Inter transaction delay: {self.inter_transaction_delay} seconds"
        txt =  f"""\
MDFU client information
--------------------------------
- MDFU protocol version: {self.protocol_version}
- Number of command buffers: {self.buffer_count} bytes
- Maximum packet data length: {self.buffer_size}
{itd_txt}
Command timeouts
- Default timeout: {self.default_timeout} seconds
"""
        for cmd, timeout in self.timeouts.items():
            txt += f"- {cmd.name}: {timeout} seconds\n"
        return txt

    def _verify_timeouts(self):
        """Verify command timeouts

        :raises ValueError: When timeout is above maximum supported value.
        :raises TypeError: When command is not of type MdfuCmd
        """
        if (self.default_timeout * self.LSBS_PER_SECOND) > 0xFFFF:
            raise ValueError(f"Maximum timeout is 6,553.5 seconds but got {self.default_timeout}")

        for cmd, timeout in self.timeouts.items():
            if not isinstance(cmd, MdfuCmd):
                raise TypeError(f"Invalid type. Expected MdfuCmd but got {type(cmd)}")
            if (timeout * self.LSBS_PER_SECOND) > 0xFFFF:
                raise ValueError(f"Maximum timeout is 6,553.5 seconds but got {timeout}")

    def to_bytes(self):
        """Encode client info

        :return: Bytes containing encoded client info
        :rtype: Bytes like object
        """
        data = ClientInfoType.BUFFER_INFO.value.to_bytes(self.PARAM_TYPE_SIZE, byteorder="little")
        data += self.BUFFER_INFO_SIZE.to_bytes(self.PARAM_LENGTH_SIZE, byteorder="little")
        data += self.buffer_size.to_bytes(2, byteorder="little")
        data += bytes([self.buffer_count])

        data += bytes([ClientInfoType.PROTOCOL_VERSION.value])
        data += self.PROTOCOL_VERSION_SIZE.to_bytes(self.PARAM_LENGTH_SIZE, byteorder="little")
        data += bytes([self.protocol_version.major, self.protocol_version.minor, self.protocol_version.micro])

        data += bytes([ClientInfoType.COMMAND_TIMEOUTS.value])
        # Total number of timeouts is: default timeout + timeouts specified in timeouts dict
        timeouts_count = 1 + len(self.timeouts)
        timeouts_size = timeouts_count * self.COMMAND_TIMEOUT_SIZE
        data += timeouts_size.to_bytes(self.PARAM_LENGTH_SIZE, "little")
        # Default timeout
        data += bytes([0])
        data += int(self.default_timeout * self.LSBS_PER_SECOND).to_bytes(2, "little")
        # Other command timeouts
        for cmd, value in self.timeouts.items():
            data += bytes([cmd.value])
            data += int(value * self.LSBS_PER_SECOND).to_bytes(2, byteorder="little")

        if self.inter_transaction_delay is not None:
            itd = InterTransactionDelay(self.inter_transaction_delay)
            data += bytes([ClientInfoType.INTER_TRANSACTION_DELAY.value])
            data += self.INTER_TRANSACTION_DELAY_SIZE.to_bytes(self.PARAM_LENGTH_SIZE, byteorder="little")
            data += itd.to_bytes()
        return data

    @classmethod
    def _decode_buffer_info(cls, length, data):
        """Decode buffer info parameter

        :param length: Length of the buffer info parameter
        :type length: int
        :param data: Buffer info parameter value
        :type data: Bytes
        :raises ValueError: If invalid data is detected during decoding
        :return: Tuple of (number of buffers, buffer size)
        :rtype: tuple(int, int)
        """
        if length != cls.BUFFER_INFO_SIZE:
            raise ValueError("Invalid parameter length for MDFU client buffer info." + \
                             f"Expected {cls.BUFFER_INFO_SIZE} but got {length}")
        buffer_size = int.from_bytes(data[0:2], byteorder="little")
        buffer_count = data[2]
        return buffer_count, buffer_size

    @classmethod
    def _decode_version(cls, length, data):
        """Decode version parameter

        :param length: Length of the version parameter
        :type length: int
        :param data: Version parameter value
        :type data: Bytes
        :raises ValueError: If invalid data is detected when decoding
        :return: MDFU client protocol version
        :rtype: Version (from packaging.version)
        """
        if length == cls.PROTOCOL_VERSION_SIZE:
            version = Version(f"{data[0]}.{data[1]}.{data[2]}")
        elif length == cls.PROTOCOL_VERSION_INTERNAL_SIZE:
            version = Version(f"{data[0]}.{data[1]}.{data[2]}-alpha{data[3]}")
        else:
            raise ValueError("Invalid parameter length for MDFU client protocol version" + \
                             f"Expected {cls.BUFFER_INFO_SIZE} but got {length}")
        return version

    @classmethod
    def _decode_command_timeouts(cls, length, data):
        """Decode command timeouts parameter

        :param length: Length of the command timeout parameter
        :type length: int
        :param data: Command timeout parameter value
        :type data: Bytes like object
        :raises ValueError: If invalid data is detected
        :return: Tuple of (default timeout, commands timeouts)
        :rtype: tuple(int, dict[MdfuCmd, float])
        """
        cmd_timeouts = {}
        default_timeout = None
        # Test if the parameter length is a multiple of (1 byte MDFU command, 2 bytes timeout value)
        if length % cls.COMMAND_TIMEOUT_SIZE:
            raise ValueError("Invalid parameter length for MDFU client command timeouts" + \
                             f"Expected length to be a multiple of 3 but got {length}")
        cmd_values = set(item.value for item in MdfuCmd)
        for _ in range(0, length // cls.COMMAND_TIMEOUT_SIZE):
            if data[0] == 0: #default timeout
                default_timeout = float(int.from_bytes(data[1:3], byteorder="little")) * cls.SECONDS_PER_LSB
            elif data[0] not in cmd_values:
                raise ValueError(f"Invalid command code {data[0]} in MDFU client command timeouts")
            else:
                timeout = float(int.from_bytes(data[1:3], byteorder="little")) * cls.SECONDS_PER_LSB
                cmd = MdfuCmd(data[0])
                cmd_timeouts[cmd] = timeout
            data = data[3:]
        if not default_timeout:
            raise ValueError("No required default timeout is present in client info")
        return default_timeout, cmd_timeouts

    @classmethod
    def from_bytes(cls, data):
        """Create ClientInfo object from bytes

        :param data: Bytes object containing encoded client information
        :type data: Bytes like object
        :raises ValueError: When an error occurs during client info decoding
        :return: Client information
        :rtype: ClientInfo
        """
        i = 0
        cmd_timeouts = {}
        version = None
        buffer_count = None
        buffer_size = None
        default_timeout = None
        inter_transaction_delay = None
        while i < len(data):
            try:
                try:
                    parameter_type = ClientInfoType(data[i])
                except ValueError as err:
                    raise MdfuClientInfoError(f"Invalid client info parameter type {data[i]}") from err
                parameter_length = data[i+1]
                parameter_value = data[i + 2:i + 2 + parameter_length]

                if parameter_type == ClientInfoType.BUFFER_INFO:
                    buffer_count, buffer_size = cls._decode_buffer_info(parameter_length, parameter_value)

                elif parameter_type == ClientInfoType.PROTOCOL_VERSION:
                    version = cls._decode_version(parameter_length, parameter_value)

                elif parameter_type == ClientInfoType.COMMAND_TIMEOUTS:
                    default_timeout, cmd_timeouts = cls._decode_command_timeouts(parameter_length, parameter_value)

                elif parameter_type == ClientInfoType.INTER_TRANSACTION_DELAY:
                    inter_transaction_delay = InterTransactionDelay.from_bytes(parameter_value).seconds
            except IndexError as err:
                raise MdfuClientInfoError("Not enough data to decode client information") from err
            except ValueError as err:
                raise MdfuClientInfoError(f"Error while decoding client information. {err}") from err
            i += cls.PARAM_TYPE_SIZE + cls.PARAM_LENGTH_SIZE + parameter_length
        # Test if mandatory parameters are present
        if version is None:
            raise MdfuClientInfoError("Mandatory client info parameter version is missing.")
        if buffer_count is None or buffer_size is None:
            raise MdfuClientInfoError("Mandatory client info parameter buffer info is missing.")
        if default_timeout is None:
            raise MdfuClientInfoError("Mandatory default timeout is missing in client info command timeouts.")
        return cls(version, buffer_count, buffer_size, default_timeout, cmd_timeouts,
                   inter_transaction_delay=inter_transaction_delay)

    def set_default_timeouts(self):
        """Set default timeout for commands that don't have a timeout set

        Update timeouts dictionary by adding a command timeout for commands
        that are not present in the dictionary.
        """
        for cmd in MdfuCmd:
            if cmd not in self.timeouts:
                self.timeouts[cmd] = self.default_timeout

class Mdfu():
    """MDFU protocol
    """
    def __init__(self, transport: Transport, retries=5):
        """Class initialization

        :param transport: Defines wich transport layer the MDFU protocol uses
        :type transport: Transport
        :param timeout: Communication timeout in seconds
        :type timeout: Int, defaults to 5
        :param retries: How often a failed command should be retried.
        :type retries: Int, defaults to 5
        """
        self.transport = transport
        self.sequence_number = 0
        self.retries = retries
        self.initial_default_command_timeout = 1
        self.client = None
        self.opened = False
        self.logger = getLogger("pymdfu.MdfuHost")

    def run_upgrade(self, image):
        """Executes the upgrade process

        :param image: File image
        :type image: Bytes like object
        :raises MdfuUpdateError: For an unsuccessful update
        """
        try:
            self.transport.open()
            # Start session by:
            # - resetting sequence number to zero
            # - sync sequence number with client
            # - getting client info
            self.sequence_number = 0
            self._get_client_info(sync=True)

            if self.client.protocol_version > mdfu_protocol_version:
                msg = f"MDFU client protocol version {self.client.protocol_version} not supported. " +\
                    f"This MDFU host implements MDFU protocol version {mdfu_protocol_version}. " +\
                    "Please update pymdfu to the latest version."
                raise MdfuProtocolError(msg)
            chunks = chunkify(image, self.client.buffer_size)

            self.start_transfer()
            for chunk in chunks:
                self.write_chunk(chunk)
            image_state = self._get_image_state()
            if image_state != ImageState.VALID:
                raise MdfuUpdateError(f"Get image state command returned with image state {image_state.name}.")
            self.end_transfer()

        except MdfuProtocolError as err:
            raise MdfuUpdateError(err) from err
        except TransportError as err:
            raise MdfuUpdateError(err) from err
        finally:
            self.transport.close()

    def open(self):
        """Open MDFU session.

        :raises MdfuProtocolError: When an error occurs on lower communication layers.
        """
        if not self.opened:
            try:
                self.transport.open()
            except TransportError as err:
                raise MdfuProtocolError(err) from err
            self.opened = True

    def close(self):
        """Close MDFU session.

        :raises MdfuProtocolError: When an error occurs on lower communication layers
        """
        if self.opened:
            try:
                self.transport.close()
            except TransportError as err:
                raise MdfuProtocolError(err) from err
            self.opened = False

    def get_client_info(self, sync=True):
        """Get MDFU client information

        Before calling this function start an MDFU session by calling open().

        :param sync: Synchronize packet sequence number with client. When set the client
        will set its sequence number to the one received in this command packet.
        :type sync: bool, optional
        :raises MdfuProtocolError: For failed command execution
        :return: Client information
        :rtype: ClientInfo
        """
        if not self.opened:
            raise MdfuProtocolError("Call open() before issuing any MDFU commands")

        self._get_client_info(sync=sync)
        return self.client

    def _get_client_info(self, sync=False):
        """Executes the GetClientInfo command

        :param sync: Synchronize packet sequence number with client. When set the client
        will set its sequence number to the one received in this command packet.
        :type sync: bool, optional
        :raises MdfuProtocolError: For failed command execution
        :return: Client information
        :rtype: ClientInfo
        """
        response = self.send_cmd(MdfuCmd.GET_CLIENT_INFO, sync=sync)
        try:
            self.client = ClientInfo.from_bytes(response.data)
            # If the client provides the inter transaction delay we apply it to the
            # MAC layer if it offers this feature
            if hasattr(self.transport.mac, "inter_transaction_delay"):
                if self.client.inter_transaction_delay is None:
                    raise MdfuClientInfoError("Client did not provide mandatory inter transaction delay parameter.")
                self.transport.mac.inter_transaction_delay = self.client.inter_transaction_delay

        except (ValueError, MdfuClientInfoError) as err:
            self.logger.error(err)
            self.logger.error("Received invalid MDFU Client Info")
            self.logger.debug("Raw Client Info 0x%s", response.data.hex())
            raise MdfuProtocolError from err

    def _get_image_state(self):
        """Executes Get Image State command

        :raises MdfuProtocolError: For invalid payload in command response.
        :return: Current client image state
        :rtype: ImageState
        """
        response = self.send_cmd(MdfuCmd.GET_IMAGE_STATE)
        payload_length = len(response.data)
        if payload_length > 1:
            raise MdfuProtocolError("Get image state command returned with more data than expected." +\
                                    f"Expected 1 byte but got {payload_length}")
        if payload_length < 1:
            raise MdfuProtocolError("Get image state command returned with less data than expected." + \
                                    f"Expected 1 byte but got {payload_length}.")
        try:
            image_state = ImageState(response.data[0])
        except ValueError as exc:
            raise MdfuProtocolError("Invalid image state {response.data[0]} received from client.") from exc
        return image_state

    def start_transfer(self, sync=False):
        """Executes Start Transfer command
        """
        self.logger.debug("Starting MDFU file transfer")
        self.send_cmd(MdfuCmd.START_TRANSFER, sync=sync)

    def write_chunk(self, chunk):
        """Executes Write Chunk command

        :param chunk: Piece of the upgrade image file
        :type chunk: Bytes like object
        """
        self.send_cmd(MdfuCmd.WRITE_CHUNK, data=chunk)

    def end_transfer(self):
        """Executes End Transfer command
        """
        self.logger.debug("Ending MDFU file transfer")
        self.send_cmd(MdfuCmd.END_TRANSFER)

    def send_cmd(self, command: MdfuCmd, data=bytes(), sync=False) -> MdfuStatusPacket:
        """Send a command packet to MDFU client

        :param command: Command to send
        :type command: MdfuCmd
        :param data: Data to send, defaults to None
        :type data: Bytes like object, optional
        :param sync: Synchronize packet sequence number with client. When set the client
        will set its sequence number to the one received in this command packet.
        :type sync: Bool
        :return: MDFU status packet
        :rtype: MdfuStatusPacket
        """
        cmd_packet = MdfuCmdPacket(self.sequence_number, command.value, data, sync=sync)
        self.logger.debug("Sending MDFU command packet:\n%s\n", cmd_packet)
        # We will try at least once plus the number of retries
        attempts = 1 + self.retries
        try:
            # Check if there is a specific timeout for the command
            timeout = self.client.timeouts[command]
        except KeyError:
            # No specific timeout found, use client default
            timeout = self.client.default_timeout
        except AttributeError:
            # No client provided timeouts found, use host default
            timeout = self.initial_default_command_timeout
        while attempts:
            try:
                self.transport.write(cmd_packet.to_binary())
                status_packet = self.transport.read(timeout=timeout)
                status_packet = MdfuStatusPacket.from_binary(status_packet)
                self.logger.debug("Received a MDFU status packet\n%s\n", status_packet)

                if status_packet.resend:
                    self.logger.debug("Resending MDFU packet. Packet status was %s",\
                            MdfuStatus(status_packet.status).name)
                    attempts -= 1
                    continue
                if status_packet.status == MdfuStatus.SUCCESS.value:
                    self._increment_sequence_number()
                    break

                self.log_error_cause(status_packet)
                self._increment_sequence_number()
                raise MdfuProtocolError()

            except TransportError as exc:
                self.logger.debug(exc)
                attempts -= 1
            except (MdfuStatusInvalidError, MdfuCmdNotSupportedError) as exc:
                self.logger.error(exc)
                raise MdfuProtocolError(exc) from exc
        if attempts == 0:
            msg = f"Tried {1 + self.retries} times to send command " + \
                    f"{MdfuCmd(cmd_packet.command).name} without success"
            self.logger.error(msg)
            raise MdfuProtocolError(msg)

        return status_packet

    def _increment_sequence_number(self):
        self.sequence_number = (self.sequence_number + 1) & 0x1f

    def log_error_cause(self, status_packet: MdfuStatusPacket):
        """Log MDFU client repsonse error cause

        :param status_packet: Mdfu status packet with error response status
        :type status_packet: MdfuStatusPacket
        """
        error = MdfuStatus(status_packet.status)
        self.logger.error("Received MDFU status packet with %s", error.name)

        error_cause = None
        if error == MdfuStatus.COMMAND_NOT_EXECUTED and len(status_packet.data):
            try:
                cause = CmdNotExecutedCause(status_packet.data[0])
                error_cause = f"Command not executed cause: {cause.description}"
            except ValueError:
                error_cause = f"Invalid command not executed cause {status_packet.data[0]}"
        elif error == MdfuStatus.ABORT_FILE_TRANSFER and len(status_packet.data):
            try:
                cause = FileTransferAbortCause(status_packet.data[0])
                error_cause = f"File transfer abort cause: {cause.description}"
            except ValueError:
                error_cause = f"Invalid file abort cause {status_packet.data[0]}"

        if error_cause:
            self.logger.error(error_cause)
