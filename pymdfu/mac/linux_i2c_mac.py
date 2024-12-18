"""Linux I2C MAC layer module"""
import logging
import os
import errno
import ctypes
import array
import fcntl
from pymdfu.mac.mac import Mac
from pymdfu.mac.exceptions import MacError, MacI2cNackError
from pymdfu.timeout import Timer

class MacLinuxI2c(Mac): # pylint: disable=too-many-instance-attributes
    """MAC layer for Linux I2C subsystem
    """
    # Constants from <uapi/linux/i2c.h>
    # I2C message flags
    I2C_M_RD           = 0x0001	# guaranteed to be 0x0001!
    I2C_M_TEN          = 0x0010 # use only if I2C_FUNC_10BIT_ADDR
    I2C_M_DMA_SAFE     = 0x0200	# use only in kernel space
    I2C_M_RECV_LEN     = 0x0400	# use only if I2C_FUNC_SMBUS_READ_BLOCK_DATA
    I2C_M_NO_RD_ACK    = 0x0800	# use only if I2C_FUNC_PROTOCOL_MANGLING
    I2C_M_IGNORE_NAK   = 0x1000	# use only if I2C_FUNC_PROTOCOL_MANGLING
    I2C_M_REV_DIR_ADDR = 0x2000	# use only if I2C_FUNC_PROTOCOL_MANGLING
    I2C_M_NOSTART      = 0x4000	# use only if I2C_FUNC_NOSTART
    I2C_M_STOP         = 0x8000	# use only if I2C_FUNC_PROTOCOL_MANGLING

    # I2C adapter supported functionality bits
    I2C_FUNC_I2C               = 0x00000001
    I2C_FUNC_10BIT_ADDR        = 0x00000002 # required for I2C_M_TEN
    I2C_FUNC_PROTOCOL_MANGLING = 0x00000004 # required for I2C_M_IGNORE_NAK etc.
    I2C_FUNC_SMBUS_PEC         = 0x00000008
    I2C_FUNC_NOSTART           = 0x00000010 # required for I2C_M_NOSTART
    I2C_FUNC_SLAVE             = 0x00000020

    # IOCTL commands for /dev/i2c-xx
    I2C_RETRIES	    = 0x0701 # number of times a device address should be polled when not acknowledging
    I2C_TIMEOUT     = 0x0702 # set timeout in units of 10 ms
    I2C_SLAVE       = 0x0703 # Use this slave address
    I2C_TENBIT      = 0x0704 # 0 for 7 bit addrs, != 0 for 10 bit
    I2C_FUNCS       = 0x0705 # Get the adapter functionality mask
    I2C_SLAVE_FORCE = 0x0706 # Use this slave address, even if it is already in use by a driver!
    I2C_RDWR        = 0x0707 # Combined R/W transfer (one STOP only)
    I2C_PEC         = 0x0708 # != 0 to use PEC with SMBus
    I2C_SMBUS       = 0x0720 # SMBus transfer

    I2C_RDWR_IOCTL_MAX_MSGS	= 42

    def __init__(self, dev_path, address, timeout=0.2, inter_transaction_delay=0.01):
        """Linux I2C MAC layer initialization
    
        :param dev_path: Path to I2C device e.g. /dev/i2c-0
        :type dev_path: str
        :param address: I2C address
        :type address: int
        :param timeout: I2C bus timeout in seconds, defaults to 0.2 seconds.
        :type timeout: float, optional
        :param inter_transaction_delay: Delay in seconds between I2C transactions. This is a minimum requested time
        and the actual time will be longer due to the time it takes to send the next transaction request to the kernel
        after the delay expired. Default delay is 10 ms (0.01 seconds).
        :type inter_transaction_delay: float 
        """
        self.logger = logging.getLogger(__name__)
        self._fd = None
        self._fs = None
        self._devpath = dev_path
        self.address = address
        self.timeout = timeout
        self._inter_transaction_delay = inter_transaction_delay
        self.itd_timer = Timer(0)

    def __del__(self):
        self.close()

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()

    def open(self):
        """Open Linux I2C MAC layer"""
        try:
            #pylint: disable=consider-using-with
            self._fs = open(self._devpath, "rb+", buffering=0)
            self._fd = self._fs.fileno()
        except OSError as exc:
            raise MacError(exc) from exc
        try:
            # Get I2C adapter functionality
            buf = array.array('I', [0])
            fcntl.ioctl(self._fd, MacLinuxI2c.I2C_FUNCS, buf, True)

            # Set timeout is in units of 10 ms
            timeout = ctypes.c_ulong(int(self.timeout * 100))
            fcntl.ioctl(self._fd, MacLinuxI2c.I2C_TIMEOUT, timeout, False)

            # Set client address
            fcntl.ioctl(self._fd, MacLinuxI2c.I2C_SLAVE_FORCE, self.address)
        except OSError as exc:
            self.logger.debug("ioctl returned error code %d - %s", exc.args[0], exc.args[1])
            self.close()
            raise MacError(exc) from exc

    def close(self):
        """Close Linux I2C MAC layer"""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

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

        :param data: I2C data to send
        :type data: bytes, bytearray
        :raises MacError: When transfer does not finish successfully
        """
        try:
            # Do not start a new transaction before the delay between this and
            # the last transaction has expired
            while not self.itd_timer.expired():
                pass
            self._fs.write(data)
        except OSError as exc:
            # Most Linux I2C drivers seem to use -EREMOTEIO in the kernel space to indicate a device NACK. However,
            # this error code does not have an equivalent user space code so the syscall interface will translate
            # this to a more generic code that exists in user space, typically EIO.
            # In the MDFU I2C spec we should treat a NACK during sending a command not as error and detect the
            # problem during response polling, which eventually will then trigger a retry of the command when
            # client does not have a response available.
            if errno.EIO == exc.args[0]:
                self.logger.debug("ioctl returned error code EIO, potentially a client NACK")
            else:
                raise MacError(f"ioctl returned error code {exc.args[0]} - {exc.args[1]}") from exc
        finally:
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)

    def read(self, size):
        """I2C read transaction

        :param size: Number of bytes to read from I2C client
        :type size: int
        :raises MacError: When transfer encounters an error
        :return: Data read from I2C client
        :rtype: bytearray
        """
        try:
            data = self._fs.read(size)
        except OSError as exc:
            # Most Linux I2C drivers seem to use -EREMOTEIO in the kernel space to indicate a device NACK. However,
            # this error code does not have an equivalent user space code so the syscall interface will translate
            # this to a more generic code that exists in user space, typically EIO.
            # For a I2C read transaction we treat the EIO error as a client NACK so that the transport layer
            # will continue polling for a response.
            if errno.EIO == exc.args[0]:
                raise MacI2cNackError() from exc
            raise MacError(f"ioctl returned error code {exc.args[0]} - {exc.args[1]}") from exc
        finally:
            # Set inter transaction delay timer for next transaction
            self.itd_timer.set(self._inter_transaction_delay)
        return data
