"""Bytes based MAC"""
from collections import deque
from pymdfu.mac.mac import Mac
from pymdfu.timeout import Timer

class MacBytes(Mac):
    """Bytes based MAC
    """
    def __init__(self, buffer_in: deque, buffer_out: deque, timeout=1):
        """Class initialization

        :param buffer_in: MAC layer input buffer
        :type buffer_in: deque
        :param buffer_out: MAC layer output buffer
        :type buffer_out: deque
        :param timeout: Read timeout in seconds, defaults to 1
        timeout = None -> blocking read without timeout
        timeout = 0 -> non-blocking read, return immediately with up to the requested number of bytes
        timeout > 0 -> blocking read with timeout, return with requested number of bytes or less in
        case of timeout.
        :type timeout: int or None, optional
        """
        self.buffer_in = buffer_in
        self.buffer_out = buffer_out
        self.timeout = timeout

    def write(self, data):
        """Write to MAC layer

        :param data: Data to write.
        :type data: bytes, bytearray
        """
        for byte in data:
            self.buffer_in.appendleft(byte)

    def read(self, size):
        """Read from MAC layer
        
        Read size bytes from the MAC layer. If no timeout is set (None) it is a blocking
        read. Non-blocking operation (timeout > 0 or timeout = 0) can return
        less bytes than requested.
        
        :param size: Number of bytes to read
        :type size: int
        :return: Bytearray with bytes read.
        :rtype: Bytearray
        """
        return_size = size
        available = len(self.buffer_out)
        if size > available:
            if self.timeout is None:
                while size > len(self.buffer_out):
                    pass
            elif self.timeout == 0:
                return_size = available
            else:
                timer = Timer(self.timeout)
                while not timer.expired() and (size > len(self.buffer_out)):
                    pass
                if timer.expired():
                    available = len(self.buffer_out)
                    return_size = size if available > size else available

        data = bytearray()
        for _ in range(return_size):
            data.append(self.buffer_out.pop())
        return data

    def __len__(self):
        """Get number of bytes available to read from MAC

        :return: Number of bytes
        :rtype: int
        """
        return len(self.buffer_out)
