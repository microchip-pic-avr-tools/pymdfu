"""SPI transport layer
"""
from logging import getLogger
from pymdfu.transport import Transport, TransportError
from pymdfu.timeout import Timer
from pymdfu.mac.exceptions import MacError
from pymdfu.utils import calculate_checksum

class SpiTransport(Transport):
    """Transport implementation for SPI
    """
    CLIENT_RSP_LEN_PREFIX = bytes("LEN", encoding="ascii")
    CLIENT_RSP_PREFIX = bytes("RSP", encoding="ascii")
    CLIENT_RSP_PREFIX_START = 1
    CLIENT_RESP_PREFIX_SIZE = 4
    FRAME_TYPE_CMD = 0x11
    FRAME_TYPE_RSP_RETRIEVAL = 0x55
    CHECKSUM_SIZE = 2
    CHECKSUM_START = 6
    RESPONSE_LENGTH_SIZE = 2
    RESPONSE_LENGTH_START = 4


    """ Transport layer for SPI
    """
    def __init__(self, mac, timeout=5, polling_interval=0.1):
        self.com = mac
        self.timeout = timeout
        self.polling_interval = polling_interval
        self.logger = getLogger(__name__)

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
        frame = self.create_write_frame(data)
        self.logger.debug("Sending write frame -> 0x%s", frame.hex())
        try:
            response = self.spi_transaction(frame)
            self.logger.debug("Received response 0x%s", response.hex())
        except MacError as exc:
            raise TransportError(exc) from exc

    def read(self, timeout=None):
        """Receive a MDFU status packet

        :param timeout: Timeout for the read operation in seconds
        :type timeout: Float
        :raises ValueError: Upon checksum error
        :return: MDFU status packet
        :rtype: bytes
        """
        timer = Timer(timeout if timeout else self.timeout)

        while True:
            try:
                frame = self.create_read_frame(self.RESPONSE_LENGTH_SIZE + self.CHECKSUM_SIZE)
                self.logger.debug("Sending read frame -> 0x%s", frame.hex())
                buf = self.spi_transaction(frame)

                if buf[self.CLIENT_RSP_PREFIX_START:self.CLIENT_RESP_PREFIX_SIZE] == self.CLIENT_RSP_LEN_PREFIX:
                    self.logger.debug("Received status response <- 0x%s", buf.hex())
                    data_size = int.from_bytes(buf[self.CLIENT_RESP_PREFIX_SIZE:self.CLIENT_RESP_PREFIX_SIZE +
                                                   self.RESPONSE_LENGTH_SIZE], byteorder="little")
                    checksum = int.from_bytes(buf[self.CHECKSUM_START:self.CHECKSUM_START + self.CHECKSUM_SIZE],
                                              byteorder="little")
                    calculated_checksum = calculate_checksum(
                        buf[self.CLIENT_RESP_PREFIX_SIZE:self.CLIENT_RESP_PREFIX_SIZE + self.CHECKSUM_SIZE])
                    if checksum != calculated_checksum:
                        self.logger.error("SPI transport checksum mismatch")
                        raise TransportError("SPI transport checksum mismatch")
                    break
                self.logger.debug("Received no response from client")
            except MacError as exc:
                raise TransportError(exc) from exc

            if timer.expired():
                raise TransportError("Timeout while waiting for response from client.")

        try:
            dummy_read = self.create_read_frame(data_size)
            self.logger.debug("Sending read frame -> 0x%s", dummy_read.hex())
            frame = self.spi_transaction(dummy_read)
            self.logger.debug("Received frame <- 0x%s", frame.hex())
            frame_checksum = int.from_bytes(frame[-self.CHECKSUM_SIZE:], byteorder="little")
            packet = frame[self.CLIENT_RESP_PREFIX_SIZE:-self.CHECKSUM_SIZE]
            if frame[self.CLIENT_RSP_PREFIX_START:self.CLIENT_RESP_PREFIX_SIZE] != self.CLIENT_RSP_PREFIX:
                raise TransportError("Received no response from client")

            calculated_checksum = calculate_checksum(packet)
            if frame_checksum != calculated_checksum:
                self.logger.error("SPI transport checksum mismatch")
                raise TransportError("SPI transport checksum mismatch")
        except MacError as exc:
            raise TransportError(exc) from exc
        return packet

    def spi_transaction(self, data):
        """Perform a SPI transaction

        :param data: Data to send
        :type data: bytes, bytearray
        :return: Data returned from SPI client
        :rtype: bytes, bytearray
        """
        self.com.write(data)
        response = self.com.read(len(data))
        assert(len(data) == len(response))
        return response

    def create_write_frame(self, packet):
        """Create a transport write frame

        :param packet: MDFU packet
        :type packet: bytes, bytearray
        :return: Transport frame
        :rtype: bytes
        """
        check_sequence = calculate_checksum(packet)
        check_sequence = check_sequence.to_bytes(self.CHECKSUM_SIZE, byteorder="little")

        frame = bytes([self.FRAME_TYPE_CMD]) + packet + check_sequence
        return frame

    def create_read_frame(self, data_size):
        """Create a transport read frame

        :param data_size: Length of the data to be read
        :type data_size: int
        :return: Encoded read transport frame
        :rtype: bytes
        """
        # Read command and three dummy bytes to get the four bytes "MDFU" prefix back,
        # then shift data_size dummy bytes to get response.
        frame = bytes([self.FRAME_TYPE_RSP_RETRIEVAL, 0, 0, 0]) + bytes(data_size )
        return frame

class SpiTransportClient(Transport):
    """Transport for SPI client
    """
    CLIENT_RSP_LEN_PREFIX = bytes("LEN", encoding="ascii")
    CLIENT_RSP_PREFIX = bytes("RSP", encoding="ascii")
    CLIENT_RSP_PREFIX_SIZE = 4
    CLIENT_RSP_PREFIX_START = 1
    FRAME_TYPE_CMD = 0x11
    FRAME_TYPE_RSP_RETRIEVAL = 0x55
    CHECKSUM_SIZE = 2
    RESPONSE_LENGTH_SIZE = 2
    # The minimal SPI frame length is:
    # 1 byte SPI frame type code + 1 byte MDFU sequence + 1 byte MDFU command code + 2 bytes frame checksum
    MIN_SPI_FRAME_SIZE = 1 + 1 + 1 + 2

    """ Transport layer for SPI
    """
    def __init__(self, mac, timeout=5):
        self.com = mac
        self.timeout = timeout
        self.logger = getLogger(__name__)

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
        """Send MDFU response to host

        :param data: MDFU packet
        :type data: bytes
        """
        # Create frame length (data + checksum size)
        length = (len(data) + self.CHECKSUM_SIZE).to_bytes(self.RESPONSE_LENGTH_SIZE, byteorder="little")
        checksum = calculate_checksum(length).to_bytes(self.CHECKSUM_SIZE, byteorder="little")
        frame = bytes(1) + self.CLIENT_RSP_LEN_PREFIX + length + checksum

        cmd = self.com.read()
        self.logger.debug("Client received frame <- 0x%s", cmd.hex())

        # If transaction length is not what we expect just return the requested length with zero bytes
        # and raise an error later.
        if len(cmd) != len(frame):
            dummy_data = bytes(len(cmd))
            self.com.write(dummy_data)
        else:
            self.com.write(frame)

        self.logger.debug("Client sent frame -> 0x%s", frame.hex())

        # TODO according to the spec, if a command was received instead of response retrieval
        # we would need to store this frame here, abort, and later provide the frame to the client through the
        # read function instead of fetching from MAC layer.
        if cmd[0] != self.FRAME_TYPE_RSP_RETRIEVAL:
            raise TransportError(f"Expected read transaction but got {cmd[0]}")
        if len(cmd) != len(frame):
            raise TransportError("Expected read transaction was too short for getting the response length")

        check_sequence = calculate_checksum(data)
        check_sequence = check_sequence.to_bytes(self.CHECKSUM_SIZE, byteorder="little")

        frame = bytes(1) + self.CLIENT_RSP_PREFIX + data + check_sequence
        cmd = self.com.read()
        self.com.write(frame)
        self.logger.debug("Client sent frame -> 0x%s", frame.hex())
        self.logger.debug("Client received frame <- 0x%s", cmd.hex())

        if cmd[0] != self.FRAME_TYPE_RSP_RETRIEVAL:
            raise TransportError(f"Expected read transaction but got {cmd[0]}")

    def read(self, timeout=None):
        """Receive a MDFU command packet

        :param timeout: Timeout for the read operation in seconds
        :type timeout: Float
        :raises TransportError: Upon checksum error
        :return: MDFU status packet
        :rtype: bytes
        """
        packet = None
        timer = Timer(timeout if timeout else self.timeout)

        while True:
            try:
                frame = self.com.read()
                if frame and len(frame) > 0:
                    response = bytearray(len(frame))
                    self.com.write(response) # send back dummy bytes
                    self.logger.debug("Client received frame <- 0x%s", frame.hex())
                    self.logger.debug("Client sent frame -> 0x%s", response.hex())
                    if len(frame) < (self.MIN_SPI_FRAME_SIZE):
                        raise TransportError("SPI frame is too small. Should contain at least 5 bytes.")
                    if frame[0] == self.FRAME_TYPE_CMD:
                        packet = frame[1:-self.CHECKSUM_SIZE]
                        checksum = int.from_bytes(frame[-self.CHECKSUM_SIZE:], byteorder="little")
                        calc_checksum = calculate_checksum(packet)

                        if checksum != calc_checksum:
                            raise TransportError("Client detected frame checksum error")
                        break
            except MacError as exc:
                raise TransportError(exc) from exc

            if timer.expired():
                raise TransportError("Timeout while waiting for response from host.")
        return packet
