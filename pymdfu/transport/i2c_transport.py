"""I2C transport layer
"""
from logging import getLogger
from pymdfu.transport import Transport, TransportError
from pymdfu.timeout import Timer
from pymdfu.mac.exceptions import MacError, MacI2cNackError
from pymdfu.utils import calculate_checksum

class I2cTransport(Transport):
    """ Transport layer for I2C
    """
    RSP_FRAME_TYPE_LENGTH = bytes([ord("L")])
    RSP_FRAME_TYPE_RESPONSE = bytes([ord("R")])
    RSP_FRAME_TYPE_BUSY = bytes([0xff])
    FRAME_TYPE_LENGTH = 1
    RSP_LENGTH_FRAME_LENGTH = 5

    def __init__(self, mac, timeout=5):
        """ Class initialization

        :param mac: MAC layer for i2c bus access
        :type mac: Classes that implement the MAC layer interface
        :param timeout: Communication timeout in seconds, defaults to 5
        :type timeout: int, optional
        """
        self.timeout = timeout
        self.com = mac
        self.logger = getLogger(__name__)

    # Support 'with ... as ...' construct
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.com:
            self.com.close()

    def create_frame(self, packet):
        """Create a transport frame

        :param packet: MDFU packet
        :type packet: Bytes
        :return: Transport frame
        :rtype: Bytes
        """
        check_sequence = calculate_checksum(packet)
        check_sequence = check_sequence.to_bytes(2, byteorder="little")
        frame = packet + check_sequence
        return frame

    def open(self):
        """Open transport
        """
        try:
            self.com.open()
        except MacError as exc:
            self.logger.error("Opening Mac failed: %s", exc)
            raise TransportError(exc) from exc

    def close(self):
        """Close transport
        """
        self.com.close()

    @property
    def mac(self):
        """MAC layer

        :return: MAC layer used in the transport layer
        :rtype: Mac
        """
        return self.com

    def write(self, data):
        """Send MDFU command packet to client

        :param data: MDFU packet
        :type data: bytes
        """
        frame = self.create_frame(data)
        self.logger.debug("Sending frame -> 0x%s", frame.hex())
        try:
            self.com.write(frame)
        except MacError as exc:
            raise TransportError(exc) from exc
        except MacI2cNackError as exc:
            # A NACK on write is treated as a recoverable error according to MDFU specification
            # The error will be detected during response polling and a new write attempt can be
            # started on MDFU protocol layer
            self.logger.debug("I2C Transport: %s", exc)

    def read(self, timeout=None):
        """Receive a MDFU status packet

        :param timeout: Timeout for the read operation in seconds
        timeout = 0 -> Non-blocking read
        timeout = None -> Use default timeout set during class initialization.
        timeout any other value -> The value is used as timeout
        :type timeout: Float
        :raises TransportError: For CRC checksum mismatch
        :raises TransportError: When MAC returns unexpected number of bytes
        :raises TransportError: When a MAC error was raised
        :return: MDFU status packet
        :rtype: bytes
        """
        timer = Timer(timeout if timeout else self.timeout)
        buf = None
        # Poll for response length
        while True:
            try:
                buf = self.com.read(self.RSP_LENGTH_FRAME_LENGTH)
                if buf:
                    if self.RSP_LENGTH_FRAME_LENGTH != len(buf):
                        raise TransportError("Unexpected frame returned while polling for " +
                            f"client response size. Got frame with length {len(buf)} but" +
                            f"expected {self.RSP_LENGTH_FRAME_LENGTH}")
                    if self.RSP_FRAME_TYPE_LENGTH[0] == buf[0]:
                        self.logger.debug("Received response length frame <- 0x%s", buf.hex())
                        size = int.from_bytes(buf[1:3], byteorder="little")
                        checksum = int.from_bytes(buf[3:5], byteorder="little")
                        calculated_checksum = calculate_checksum(buf[1:3])
                        if checksum != calculated_checksum:
                            raise TransportError("I2C transport checksum mismatch")
                        break
                    else:
                        self.logger.debug("Received client busy frame <- 0x%s", buf.hex())
            except MacI2cNackError:
                pass # Continue polling when client NACKs
            except MacError as exc:
                raise TransportError(exc) from exc

            if timer.expired():
                raise TransportError("Timeout while waiting for response from client.")

        # Poll for response
        while True:
            try:
                frame_size = size + self.FRAME_TYPE_LENGTH
                frame = self.com.read(frame_size)
                if frame is not None and frame_size == len(frame):
                    if self.RSP_FRAME_TYPE_RESPONSE[0] == frame[0]:
                        self.logger.debug("Received response <- 0x%s", frame.hex())
                        frame = frame[self.FRAME_TYPE_LENGTH:] # remove frame type code
                        frame_checksum = int.from_bytes(frame[-2:], byteorder="little")
                        packet = frame[:-2]

                        calculated_checksum = calculate_checksum(packet)

                        if frame_checksum != calculated_checksum:
                            self.logger.error("I2C transport checksum mismatch")
                            raise TransportError("I2C transport checksum mismatch")
                        break
                    else:
                        self.logger.debug("Received client busy frame <- 0x%s", frame.hex())
                else:
                    if frame:
                        raise TransportError("Unexpected response frame returned from client with frame size" +
                            f"{len(frame)} (expected {frame_size}) and frame type {hex(frame[0])} " +
                            f"(expected 0x{self.RSP_FRAME_TYPE_RESPONSE.hex()})")
                    raise TransportError("No response frame returned from MAC layer")
            except MacI2cNackError:
                pass # Continue polling when client NACKs
            except MacError as exc:
                raise TransportError(exc) from exc
            if timer.expired():
                raise TransportError("Timeout while waiting for response from client.")
        return packet

class I2cTransportClient(Transport):
    """ Transport layer for I2C
    """
    RSP_FRAME_TYPE_LENGTH = bytes([ord("L")])
    RSP_FRAME_TYPE_RESPONSE = bytes([ord("R")])
    CHECKSUM_SIZE = 2
    def __init__(self, mac, timeout=5):
        """ Class initialization

        :param mac: MAC layer for i2c bus access
        :type mac: Classes that implement the MAC layer interface
        :param timeout: Communication timeout in seconds, defaults to 5
        :type timeout: int, optional
        """
        self.timeout = timeout
        self.com = mac
        self.logger = getLogger(__name__)

    def __del__(self):
        if self.com:
            self.com.close()

    # Support 'with ... as ...' construct
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.com:
            self.com.close()

    def create_response_frame(self, packet):
        """Create a response frame

        The frame created here consists of
        - I2C transport frame type (1 byte)
        - MDFU packet (MDFU packet size bytes)
        - I2C transport frame checksum (2 bytes)

        :param packet: MDFU packet
        :type packet: Bytes
        :return: Transport frame
        :rtype: Bytes
        """
        check_sequence = calculate_checksum(packet)
        check_sequence_bytes = check_sequence.to_bytes(2, byteorder="little")
        frame = self.RSP_FRAME_TYPE_RESPONSE + packet + check_sequence_bytes
        return frame

    def create_response_length_frame(self, size: int):
        """Create a response length frame

        :param size: Size of the MDFU packet
        :type size: int
        :return: Encoded frame for I2C transport
        :rtype: bytes
        """
        response_length = size + self.CHECKSUM_SIZE
        response_length_bytes = response_length.to_bytes(2, byteorder="little")
        check_sequence_bytes = calculate_checksum(response_length_bytes).to_bytes(2, "little")
        frame = self.RSP_FRAME_TYPE_LENGTH + response_length_bytes + check_sequence_bytes
        return frame

    def open(self):
        """Open transport
        """
        try:
            self.com.open()
        except MacError as exc:
            self.logger.error("Opening Mac failed: %s", exc)
            raise TransportError(exc) from exc

    def close(self):
        """Close transport
        """
        self.com.close()

    @property
    def mac(self):
        """MAC layer

        :return: MAC layer used in the transport layer
        :rtype: Mac
        """
        return self.com

    def write(self, data):
        """Send MDFU response packet to host

        :param data: MDFU packet
        :type data: bytes
        """
        # We have two I2C transactions for a response
        # 1) Response length frame
        # 2) Response frame
        # so we issue two writes here
        frame = self.create_response_length_frame(len(data))
        self.logger.debug("Sending response length frame -> 0x%s", frame.hex())
        self.com.write(frame)
        frame = self.create_response_frame(data)
        self.logger.debug("Sending response frame -> 0x%s", frame.hex())
        self.com.write(frame)

    def read(self, timeout=None):
        """Receive a MDFU packet

        :param timeout: Timeout for the read operation in seconds.
        timeout = 0 -> Non-blocking read
        timeout = None -> Use default timeout set during class initialization.
        timeout any other value -> The value is used as timeout
        :type timeout: Float
        :raises TransportError: For frame checksum error, MacError and TimeoutError
        :return: MDFU command packet
        :rtype: bytes
        """
        packet = None
        timer = Timer(timeout if timeout else self.timeout)

        while True:
            try:
                frame = self.com.read()
                if frame:
                    packet = frame[:-2]
                    checksum = int.from_bytes(frame[-2:], byteorder="little")
                    calc_checksum = calculate_checksum(packet)

                    if checksum != calc_checksum:
                        raise TransportError("Frame checksum error detected")
                    break
            except MacError as exc:
                raise TransportError(exc) from exc

            if timer.expired():
                raise TransportError("Timeout while waiting for command from host.")
        return packet
