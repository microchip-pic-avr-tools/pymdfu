"""MCP2221A MAC layers"""
from logging import getLogger
from EasyMCP2221.exceptions import NotAckError, LowSDAError, LowSCLError
from EasyMCP2221.exceptions import TimeoutError as Mcp2221TimeoutError
from pymdfu.drivers.mcp2221a import MCP2221A
from pymdfu.mac.mac import Mac
from pymdfu.mac.exceptions import MacError, MacI2cNackError
from pymdfu.timeout import Timer

class MacMcp2221a(Mac):
    """MAC layer for MCP2221A I2C interface
    """

    def __init__(self, clock_speed, address, system_latency=0.01, clock_stretch_delay=0.01,
                inter_transaction_delay=0.01):
        """Class initialization

        :param clock_speed: I2C clock speed in Hz
        :type clock_speed: int
        :param address: I2C address
        :type address: int
        :param system_latency: Time it takes to get a response back from MCP2221A when
        asking for current status. This is an estimate and can vary depending on machine, OS...
        Default is 10 ms (0.01)
        :type system_latency: float
        :parm clock_stretch_delay: Estimated time in seconds for a client to process a byte before
        it acks/nacks the transfer. Default is 10 ms (0.01 seconds)
        :type clock_stretch_delay: float
        :param inter_transaction_delay: Delay in seconds between I2C transactions. This is a minimum requested time
        and the actual time will be longer due to the time it takes to send the next transaction request to the kernel
        after the delay expired. Default delay is 10 ms (0.01 seconds).
        :type inter_transaction_delay: float 
        """
        self.clock_speed = clock_speed
        self.address = address
        timeout = self._calculate_timeout(clock_speed, system_latency=system_latency,
                                          clock_stretch_delay=clock_stretch_delay)
        self.timeout_ms = timeout * 1000
        self.dev = MCP2221A()
        self.dev.I2C_speed(self.clock_speed)
        self._inter_transaction_delay = inter_transaction_delay
        self.itd_timer = Timer(0)
        self.logger = getLogger(__name__)

    def _calculate_timeout(self, clock_speed, system_latency=0.01, clock_stretch_delay=0.001):
        """Calculate a reasonable timeout for getting back a transfer response

        Each I2C read/write transaction command to the MCP2221A results in
        one byte with address and read/write flag, and up to 60 bytes of data.
        (the up to 60 bytes are a result of the FS USB HID transfer that allows up to
        64 bytes, but the first 4 bytes are used for control data).
        This results in a total max transfer of 61 bytes on I2C bus per issued
        transaction command to the MCP2221A.

        Each byte requires 9 clock toggles (8 data and one ACK). Combining clock
        speed, max number of bytes to transfer and number of clock cycles per byte
        results in an approx. timeout for the raw data transfer.

        At this point it would be the ideal transfer rate, however, the client might
        clock stretch in each byte transfer until it is able to ack/nack. To take this
        into account a clock stretching delay is added for each byte transfer 

        In addition to the raw data transfer time it is necessary to add a system
        dependend latency e.g. how long it takes to poll the MCP2221A for a status
        of the current transaction.

        :param clock_speed: I2C clock speed
        :type clock_speed: int
        :param system_latency: Time it takes to get a response back from MCP2221A when
        asking for current status. This is an estimate and can vary depending on machine, OS...
        Default is 10 ms
        :type system_latency: float
        :parm clock_stretch_delay: Estimated time in seconds for a client to process a byte
        before it acks/nacks the transfer.
        :type clock_stretch_delay: float
        :returns: Calculated I2C transaction timeout in seconds
        :rtype: float
        """
        clock_cycle_per_byte = 9
        max_bytes_per_transfer = 60 + 1
        clock_stretching = max_bytes_per_transfer * clock_stretch_delay
        timeout = 1/clock_speed * clock_cycle_per_byte * max_bytes_per_transfer
        timeout += clock_stretching
        timeout += system_latency
        return timeout

    def open(self):
        """Open MCP2221A MAC layer"""

    @property
    def inter_transaction_delay(self):
        """Getter function for inter transaction delay

        :return: Delay in seconds between I2C transactions
        :rtype: float
        """
        return self._inter_transaction_delay

    @inter_transaction_delay.setter
    def inter_transaction_delay(self, delay):
        """Setter function for inter transaction delay

        :param delay: Delay in seconds between I2C transactions
        :type delay: float
        """
        self._inter_transaction_delay = delay

    def write(self, data):
        """I2C write transaction

        :param data: Data to send
        :type data: bytes like object
        :raises MacError: When transfer encounters an error
        """
        try:
            # Do not start a new transaction before the delay between this and
            # the last transaction has expired
            while not self.itd_timer.expired():
                pass
            self.dev.I2C_write(self.address, data, kind="regular", timeout_ms=self.timeout_ms)
        # ValueError: if any parameter is not valid.
        # NotAckError: if the I2C slave didn't acknowledge.
        # TimeoutError: if the writing timeout is exceeded.
        # LowSDAError: if I2C engine detects the **SCL** line does not go up (read exception description).
        # LowSCLError: if I2C engine detects the **SDA** line does not go up (read exception description).
        # RuntimeError: if some other error occurs.
        except (ValueError,
                Mcp2221TimeoutError,
                TimeoutError,
                LowSDAError,
                LowSCLError,
                RuntimeError) as exc:
            raise MacError(exc) from exc
        except NotAckError as exc: # According to specification this error is handled by fetching the response
            raise MacI2cNackError("Client NACKed the I2C write transaction") from exc
        finally:
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)

    def read(self, size):
        """I2C read transaction

        :param size: Number of bytes to read
        :type size: int
        :raises MacError: When a transfer error occurs
        :raises MacI2cNackError: When client NACKs the read request
        :return: Data read from client
        :rtype: Bytes like object
        """
        try:
            # Do not start a new transaction before the delay between this and
            # the last transaction has expired
            while not self.itd_timer.expired():
                pass
            data = self.dev.I2C_read(self.address, size, kind="regular", timeout_ms=self.timeout_ms)
        # ValueError: if any parameter is not valid.
        # NotAckError: if the I2C slave didn't acknowledge.
        # TimeoutError: if the writing timeout is exceeded.
        # LowSDAError: if I2C engine detects the **SCL** line does not go up (read exception description).
        # LowSCLError: if I2C engine detects the **SDA** line does not go up (read exception description).
        # RuntimeError: if some other error occurs.
        except (ValueError, Mcp2221TimeoutError, TimeoutError, LowSDAError, LowSCLError, RuntimeError) as exc:
            raise MacError(exc) from exc
        except NotAckError as exc:
            raise MacI2cNackError(exc) from exc
        finally:
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)
        return data
