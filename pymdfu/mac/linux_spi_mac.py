"""Linux SPI MAC layer module"""
import logging
import os
import ctypes
import array
import fcntl
from enum import Enum
from pymdfu.mac.mac import Mac
from pymdfu.mac.exceptions import MacError
from pymdfu.timeout import Timer

# pylint: disable=too-few-public-methods
class _CSpiIocTransfer(ctypes.Structure):
    _fields_ = [
        ('tx_buf', ctypes.c_ulonglong),
        ('rx_buf', ctypes.c_ulonglong),
        ('len', ctypes.c_uint),
        ('speed_hz', ctypes.c_uint),
        ('delay_usecs', ctypes.c_ushort),
        ('bits_per_word', ctypes.c_ubyte),
        ('cs_change', ctypes.c_ubyte),
        ('tx_nbits', ctypes.c_ubyte),
        ('rx_nbits', ctypes.c_ubyte),
        ('pad', ctypes.c_ushort),
    ]


class SpiIoctlRequest(Enum):
    """SPI IOCTL requests
    Corresponds to requests in <uapi/linux/spi/spidev.h>
    """
    SPI_IOC_MESSAGE_1        = 0x40206b00
    SPI_IOC_WR_MODE          = 0x40016b01
    SPI_IOC_RD_MODE          = 0x80016b01
    SPI_IOC_RD_LSB_FIRST     = 0x80016b02
    SPI_IOC_WR_LSB_FIRST     = 0x40016b02
    SPI_IOC_WR_BITS_PER_WORD = 0x40016b03
    SPI_IOC_RD_BITS_PER_WORD = 0x80016b03
    SPI_IOC_WR_MAX_SPEED_HZ  = 0x40046b04
    SPI_IOC_RD_MAX_SPEED_HZ  = 0x80046b04
    SPI_IOC_WR_MODE32        = 0x40046b05
    SPI_IOC_RD_MODE32        = 0x80046b05

class MacLinuxSpi(Mac):
    """MAC layer for Linux SPI subsystem
    """
    # SPI configuration bits for MODE32 (and partly MODE) IOCTLs
    SPI_CPHA        = 0b01  # clock phase
    SPI_CPOL        = 0b10 # clock polarity
    SPI_MODE_0      = 0b00
    SPI_MODE_1      = 0b01 # (0|SPI_CPHA)
    SPI_MODE_2      = 0b10 # (SPI_CPOL|0)
    SPI_MODE_3      = 0b11 # (SPI_CPOL|SPI_CPHA)
    SPI_MODE_X_MASK	= 0b11
    SPI_CS_HIGH     = 0b100	# chipselect active high
    SPI_LSB_FIRST   = 1 << 3 # per-word bits-on-wire
    SPI_CS_WORD     = 1 << 12 # toggle cs after each word

    def __init__(self, dev_path, mode, max_speed, bit_order="msb", extra_flags=0, inter_transaction_delay=10e-3):
        """Linux SPI MAC layer initialization

        :param dev_path: Path to SPI device
        :type dev_path: string
        :param mode: SPI mode, one of [0, 1, 2, 3].
        :type mode: int
        :param max_speed: SPI clock speed in Hz.
        :type max_speed: int
        :param bit_order: Tran, defaults to "msb"
        :type bit_order: str, optional
        :param extra_flags: _description_, defaults to 0
        :type extra_flags: int, optional
        :param inter_transaction_delay: Delay in seconds between SPI transactions (time between chip select deassert
        and next chip select assert). This is a minimum requested time and the actual time will be longer due
        to the time it takes to send the next transaction request to the tool after the delay expired. Default
        delay is 10 ms.
        :type inter_transaction_delay: float
        :raises TypeError: For parameters that are passed during initialization with wrong type.
        :raises ValueError: For parameters that do not match requirements e.g. max/min value.
        """
        self.logger = logging.getLogger(__name__)
        self._fd = None
        self._fs = None
        self.rx_data = bytearray()
        if not isinstance(dev_path, str):
            raise TypeError("Invalid devpath type, must be str.")
        if not isinstance(mode, int):
            raise TypeError("Invalid mode type, must be int.")
        if not isinstance(max_speed, (int, float)):
            raise TypeError("Invalid max_speed type, must be int or float.")
        if not isinstance(bit_order, str):
            raise TypeError("Invalid bit_order type, must be str.")
        if not isinstance(extra_flags, int):
            raise TypeError("Invalid extra_flags type, must be int.")

        if mode not in [0, 1, 2, 3]:
            raise ValueError("Invalid mode, can be 0, 1, 2, 3.")
        if bit_order.lower() not in ["msb", "lsb"]:
            raise ValueError("Invalid bit_order, can be \"msb\" or \"lsb\".")
        if extra_flags < 0 or extra_flags > 255:
            raise ValueError("Invalid extra_flags, must be 0-255.")

        self._devpath = dev_path
        self.mode = mode
        self.max_speed = max_speed
        self.bit_order = bit_order.lower()
        self.extra_flags = extra_flags
        self._inter_transaction_delay = inter_transaction_delay
        # Create timer for inter transaction delay and set initial value to zero so
        # that there is no delay for the first transaction
        self.itd_timer = Timer(0)

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

    def __del__(self):
        self.close()

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()

    def open(self):
        """Open Linux SPI MAC layer"""
        try:
            self._fd = os.open(self._devpath, os.O_RDWR)

            # Set mode, bit order, extra flags
            # Chip select active low
            # 8-bits per word
            # Do not toggle chip select after each word
            mode32 = self.mode | (MacLinuxSpi.SPI_LSB_FIRST if self.bit_order == "lsb" else 0) \
                | self.extra_flags

            buf = array.array("I", [mode32])
            fcntl.ioctl(self._fd, SpiIoctlRequest.SPI_IOC_WR_MODE32.value, buf, False)

            # Set max speed
            buf = array.array("I", [int(self.max_speed)])
            fcntl.ioctl(self._fd, SpiIoctlRequest.SPI_IOC_WR_MAX_SPEED_HZ.value, buf, False)

            # Set bits per word
            buf = array.array("B", [8])
            fcntl.ioctl(self._fd, SpiIoctlRequest.SPI_IOC_WR_BITS_PER_WORD.value, buf, False)

        except OSError as exc:
            self.logger.debug("ioctl returned error code %d - %s", exc.args[0], exc.args[1])
            self.close()
            raise MacError(exc) from exc

    def close(self):
        """Close Linux SPI MAC layer"""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def write(self, data):
        """SPI transaction

        :param data: SPI data to send. The received data must be obtained after the write with the read function.
        :type data: bytes, bytearray
        :raises MacError: When transfer does not finish successfully
        """
        # Create mutable array
        buf = array.array('B', data)
        buf_addr, buf_len = buf.buffer_info()

        # Prepare transfer structure
        #pylint: disable=attribute-defined-outside-init
        spi_xfer = _CSpiIocTransfer()
        spi_xfer.tx_buf = buf_addr
        spi_xfer.rx_buf = buf_addr
        spi_xfer.len = buf_len

        try:
            while not self.itd_timer.expired():
                pass
            fcntl.ioctl(self._fd, SpiIoctlRequest.SPI_IOC_MESSAGE_1.value, spi_xfer)
            self.itd_timer.set(self._inter_transaction_delay)
        except OSError as exc:
            raise MacError(f"ioctl returned error code {exc.args[0]} - {exc.args[1]}") from exc
        self.rx_data = bytearray(buf)

    def read(self, size): #pylint: disable=unused-argument
        """SPI read transaction

        A SPI transfer needs to finish first by calling the write function before this
        function will return any data. If write function was not called before no bytes
        will be returned here.

        :param size: This is ignored but kept for API compliance
        :type size: int
        :return: Data read from SPI client
        :rtype: bytearray
        """
        data = self.rx_data
        self.rx_data = bytearray()
        return data
