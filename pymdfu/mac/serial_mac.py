"""Serial MAC layer"""
from serial import Serial, SerialException
from pymdfu.mac.exceptions import MacError

class MacSerialPort(Serial):
    """MAC wrapper for a serial port based on pySerial
    """
    def __init__(self, port, baudrate, timeout=1, bytesize=8, parity='N', stopbits=1):
        """Class initialization

        :param port: Serial port e.g. COM11 or /dev/ttyACMS0
        :type port: str
        :param baudrate: Baudrate
        :type baudrate: int
        :param timeout: Read timeout for MAC in seconds, defaults to 1
        timeout = None -> blocking read without timeout
        timeout = 0 -> non-blocking read, return immediately with zero or up to the requested number of bytes
        timeout > 0 -> set timeout to the specified number of seconds
        :type timeout: int or None, optional
        """
        # Initialize serial port but don't open yet (=we do not pass port as argument)
        super().__init__(baudrate=baudrate, timeout=timeout, bytesize=bytesize, parity=parity, stopbits=stopbits)
        # store port in instance for opening the port later
        self.port = port

    def open(self):
        try:
            super().open()
        except SerialException as exc:
            raise MacError(exc) from exc
