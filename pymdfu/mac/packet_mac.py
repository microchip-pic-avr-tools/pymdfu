"""Packet based MAC layer"""
from collections import deque
from pymdfu.mac.mac import Mac
from pymdfu.timeout import Timer

class MacPacket(Mac):
    """Packet based MAC
    """
    def __init__(self, buffer_in: deque, buffer_out: deque, timeout=1):
        """Class initialization

        :param buffer_in: Buffer for storing incoming packets
        :type buffer_in: deque
        :param buffer_out: Buffer for storing outgoing packets
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

    def write(self, packet):
        """Write a packet to MAC layer

        :param packet: Packet to send to MAC layer
        :type packet: any
        """
        self.buffer_in.appendleft(packet)

    def read(self, size=0):#pylint: disable=unused-argument
        """Read a packet from MAC layer

        :param size: For compatibility with other MAC layers. Size will be ignored in the
                     read function and a full packet will be returned.
        :type size: int
        :return: Packet from MAC layer or None if no packet was received or timeout expired
        :rtype: any
        """
        if self.timeout is None:
            while len(self.buffer_out) == 0:
                pass
            packet = self.buffer_out.pop()
        elif self.timeout == 0:
            if len(self.buffer_out):
                packet = self.buffer_out.pop()
            else:
                packet = None
        else:
            timer = Timer(self.timeout)
            while len(self.buffer_out) == 0 and not timer.expired():
                pass
            if timer.expired():
                packet = None
            else:
                packet = self.buffer_out.pop()
        return packet


    def __len__(self):
        """Number of packets in read queue"""
        return len(self.buffer_out)
