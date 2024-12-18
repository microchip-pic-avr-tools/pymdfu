"""MCP2210 MAC layer"""
import hid
from mcp2210 import Mcp2210, Mcp2210GpioDesignation
from pymdfu.mac.mac import Mac
from pymdfu.mac.exceptions import MacError
from pymdfu.timeout import Timer

class MacMcp2210(Mac):
    """MAC wrapper for a SPI based on mcp2210-python library
    """
    def __init__(self, clock_speed, chip_select, inter_transaction_delay=10e-3, timeout=0):
        """Class initialization

        :param clock_speed: SPI clock speed in Hz
        :type clock_speed: int
        :param chip_select: SPI chip select pin
        :type chip_select: int
        :param inter_transaction_delay: Delay in seconds between SPI transactions (time between chip select deassert
        and next chip select assert). This is a minimum requested time and the actual time will be longer due
        to the time it takes to send the next transaction request to the tool after the delay expired. Default
        delay is 10ms.
        :type inter_transaction_delay: float
        timeout = 0 -> non-blocking read, return immediately with zero or up to the requested number of bytes
        :type timeout: int or None, optional
        """
        self.clock_speed = clock_speed
        self.chip_select = chip_select
        self.timeout_ms = timeout * 1000
        self._inter_transaction_delay = inter_transaction_delay
        self.itd_timer = Timer(0)
        self.vid = 0x04d8
        self.pid = 0x00de
        mcp2210_devices = []
        self.rx_data_buf = []
        devices = hid.enumerate()
        for device in devices:
            if device['vendor_id'] == self.vid and device['product_id'] == self.pid:
                mcp2210_devices.append(device)

        if len(mcp2210_devices) == 0:
            raise MacError("No MCP2210 device found")
        if len(mcp2210_devices) > 1:
            raise MacError("More than one MCP2210 device found. Please disconnect one.")
        mcp = mcp2210_devices[0]
        self.dev = Mcp2210(mcp['serial_number'], vendor_id=self.vid, product_id=self.pid)

        self.dev.configure_spi_timing(chip_select_to_data_delay=0,
                         last_data_byte_to_cs=0,
                         delay_between_bytes=0)
        self.dev.set_gpio_designation(self.chip_select, Mcp2210GpioDesignation.CHIP_SELECT)
        # This is a bit of a hack because the MCP2210 library does not offer a way to
        # set the SPI speed ... so we access this internal setting and then run
        # e.g. set_spi_mode which will update all SPI setting on the device that are stored in the
        # Mcp2210 instance implicitly
        self.dev._spi_settings.bit_rate = clock_speed
        self.dev.set_spi_mode(0)

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

    def open(self):
        pass

    def write(self, data):
        """Initiate a SPI transaction

        The received data of a write operation must be obtained
        with the read function before a new write operation is initiated
        unless the received data is not needed.

        :param data: Data to send via SPI
        :type data: bytes, bytearray
        :raises MacError: When write operation times out
        """
        try:
            # Do not start a new transaction before the delay between this and
            # the last transaction has expired
            while not self.itd_timer.expired():
                pass
            self.rx_data_buf = self.dev.spi_exchange(data, self.chip_select)
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)
        except TimeoutError as exc:
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
