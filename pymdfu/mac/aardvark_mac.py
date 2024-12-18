"""MAC layer for Aardvark tool

This MAC layer wraps the pyaardvark library
"""
from logging import getLogger
import pyaardvark
from pymdfu.mac.mac import Mac
from pymdfu.mac.exceptions import MacError, MacI2cNackError
from pymdfu.timeout import Timer

class MacAardvark(Mac):
    """Aardvark MAC layer base class"""

    def __init__(self, device_id=None):
        """Base class initialization

        :param device_id: Either serial number as string or device index as integer, defaults to None
        :type device_id: str or int, optional
        """
        self.dev = None
        if device_id is not None and not isinstance(device_id, (int, str)):
            raise ValueError("Device ID for Aardvark MAC layer must be a serial number string or integer value")
        self.device_id = device_id
        self.logger = getLogger("mac.aardvark_mac")

    def _connect_to_aardvark(self):
        """Open Aardvark MAC layer"""
        devices = pyaardvark.find_devices()
        self.logger.debug("Found %d Aardvark devices", len(devices))
        for dev in devices:
            self.logger.debug("Device %d: %s", dev['port'], dev['serial_number'])
        if 0 == len(devices):
            raise MacError("No Aardvark tool found")
        try:
            if self.device_id is None:
                if len(devices) > 1:
                    self.logger.info("Multiple Aardvark devices found selecting first one in the list")
                self.dev = pyaardvark.open()
            elif isinstance(self.device_id, int):
                self.dev = pyaardvark.open(port=self.device_id)
            else:
                self.dev = pyaardvark.open(serial_number=self.device_id)
        except IOError as exc:
            errno, *_ =  exc.args
            if pyaardvark.ERR_UNABLE_TO_OPEN == errno:
                raise MacError("Unable to open Aardvark device") from exc
            raise MacError() from exc

class MacAardvarkI2c(MacAardvark):
    """MAC wrapper for Aardvark library I2C interface
    """

    def __init__(self, clock_speed, address, pull_ups=True, timeout=200, device_id=None, inter_transaction_delay=0.01):
        """Aardvark I2C MAC layer initialization

        :param clock_speed: I2C clock speed in Hz
        :type clock_speed: int
        :param address: I2C address
        :type address: int
        :param pull_ups: Enable/disable internal pull-ups (2.2k), defaults to True
        :type pull_ups: bool, optional
        :param timeout: I2C bus timeout in milliseconds, defaults to 200 ms. Minimum value is 10 ms
        and the maximum value is 450 ms. Not every value can be set and will be rounded to the
        next possible number. This is handled in the Aardvark and is reset by events like ACKs,
        start condition, stop condition or repeated start.
        :type timeout: int, optional
        :param device_id: Either serial number as string or device index as integer, defaults to None
        :type device_id: str or int, optional
        :param inter_transaction_delay: Delay in seconds between I2C transactions. This is a minimum requested time
        and the actual time will be longer due to the time it takes to send the next transaction request to the tool
        after the delay expired. Default delay is 10 ms (0.01 seconds).
        :type inter_transaction_delay: float 
        :raises ValueError: If device_id is not a string or integer type
        """
        self.clock_speed = clock_speed
        self._inter_transaction_delay = inter_transaction_delay
        self.itd_timer = Timer(0)
        self.address = address
        self.pull_ups = pull_ups
        self.timeout_ms = timeout
        super().__init__(device_id=device_id)

    def open(self):
        """Open Aardvark MAC layer"""
        if self.dev is not None:
            return
        self._connect_to_aardvark()

        self.dev.enable_i2c = True
        self.dev.i2c_bitrate = self.clock_speed // 1000
        self.dev.i2c_pullups = self.pull_ups
        self.dev.i2c_bus_timeout = self.timeout_ms

    def close(self):
        """Close Aardvark MAC layer"""
        if self.dev is None:
            return
        try:
            self.dev.close()
        except IOError as exc:
            raise MacError() from exc

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
        :raises MacI2cNackError: When client NACKs address or data
        """
        try:
            # Do not start a new transaction before the delay between this and
            # the last transaction has expired
            while not self.itd_timer.expired():
                pass
            self.dev.i2c_master_write(self.address, data)
        except (IOError) as exc:
            errno, *_ =  exc.args
            if pyaardvark.I2C_STATUS_SLA_NACK == errno:
                raise MacI2cNackError("Client NACK on address") from exc
            if pyaardvark.I2C_STATUS_DATA_NACK == errno:
                raise MacI2cNackError("Client NACK on data") from exc
            raise MacError(exc) from exc
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
            data = self.dev.i2c_master_read(self.address, size)
        except IOError as exc:
            errno, *_ =  exc.args
            if pyaardvark.I2C_STATUS_SLA_NACK == errno:
                raise MacI2cNackError("Client NACK on address") from exc
            if pyaardvark.I2C_STATUS_DATA_NACK == errno:
                raise MacI2cNackError("Client NACK on data") from exc
            raise MacError(exc) from exc
        finally:
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)
        return data

class MacAardvarkSpi(MacAardvark):
    """MAC wrapper for Aardvark library SPI interface
    """

    def __init__(self, clock_speed, mode=0, cs_polarity="low", device_id=None, inter_transaction_delay=10e-3):
        """Aardvark SPI MAC layer initialization

        :param clock_speed: SPI clock speed in Hz
        :type clock_speed: int
        :param mode: SPI mode, either 0 or 3 (limitation is in pyaardvark library). Default is 0.
        :type mode: int
        :param cs_polarity: Chip select polarity, either active "low" or "high". Default is active "low".
        :type cs_polarity: str
        :param device_id: Either serial number as string or device index as integer, defaults to None
        :type device_id: str or int, optional
        :param inter_transaction_delay: Delay in seconds between SPI transactions (time between chip select deassert
        and next chip select assert). This is a minimum requested time and the actual time will be longer due
        to the time it takes to send the next transaction request to the tool after the delay expired. Default delay
        is 10 ms.
        :type inter_transaction_delay: float
        :raises ValueError: If device_id is not a string or integer type
        """
        self.clock_speed = clock_speed
        self._inter_transaction_delay = inter_transaction_delay
        self.itd_timer = Timer(0)
        if mode not in (0,3):
            raise ValueError(f"SPI mode {mode} not supported, use 0 or 3.")
        if cs_polarity == "low":
            self.cs_polarity = pyaardvark.SPI_SS_ACTIVE_LOW
        elif cs_polarity == "high":
            self.cs_polarity = pyaardvark.SPI_SS_ACTIVE_HIGH
        else:
            raise ValueError(f'Invalid SPI chip select polarity {cs_polarity}, select "low" or "high"')
        self.mode = mode
        self.rx_data_buf = []
        super().__init__(device_id=device_id)

    def open(self):
        """Open Aardvark MAC layer"""
        if self.dev is not None:
            return
        self._connect_to_aardvark()

        self.dev.enable_spi = True
        self.dev.spi_bitrate = self.clock_speed // 1000
        self.dev.spi_configure_mode(self.mode)

    def close(self):
        """Close Aardvark MAC layer"""
        if self.dev is None:
            return
        try:
            self.dev.close()
        except IOError as exc:
            raise MacError() from exc

    @property
    def inter_transaction_delay(self):
        """Getter function for inter transaction delay

        :return: Delay in seconds between SPI transactions
        :rtype: float
        """
        return self._inter_transaction_delay

    @inter_transaction_delay.setter
    def inter_transaction_delay(self, delay):
        """Setter function for inter transaction delay

        :param delay: Delay in seconds between SPI transactions
        :type delay: float
        """
        self._inter_transaction_delay = delay

    def write(self, data):
        """Initiate a SPI transaction

        The received data of a write operation must be obtained
        with the read function before a new write operation is initiated
        unless the received data is not needed.

        :param data: Data to send via SPI
        :type data: bytes, bytearray
        :raises MacError: When an error occurs
        """
        try:
            # Do not start a new transaction before the delay between this and
            # the last transaction has expired
            while not self.itd_timer.expired():
                pass
            self.rx_data_buf = self.dev.spi_write(data)
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)
        except (IOError) as exc:
            raise MacError(exc) from exc

    def read(self, size=0): # pylint: disable=unused-argument
        """Read data returned from SPI transaction

        :param size: Length of data to read
        :type size: Size is for compatibility reason here and is ignored
        :return: Data received during SPI transaction
        :rtype: bytes
        """
        data = self.rx_data_buf
        self.rx_data_buf = []
        return data
