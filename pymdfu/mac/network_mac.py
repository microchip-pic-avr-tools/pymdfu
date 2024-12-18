"""Networking MAC layer"""
import socket
import selectors
import types
import threading
from logging import getLogger
from collections import deque
from pymdfu.mac.mac import Mac
from pymdfu.mac.exceptions import MacError
from pymdfu.timeout import Timer

class MacSocketHost(threading.Thread):
    """Host MAC layer for a network connection"""
    def __init__(self, host, port, timeout=3):
        """Class initialization

        :param host: Host interface to listen on
        :type host: str
        :param port: Port to listen on for connections
        :type port: int
        :param timeout:
        timeout = None -> blocking read without timeout
        timeout = 0 -> non-blocking read, return immediately with up to the requested number of bytes
        timeout > 0 -> blocking read with timeout, return with requested number of bytes or less in
        case of timeout.
        :type timeout: int or None, optional
        :type timeout: int
        """
        self.logger = getLogger("mac.MacSocketHost")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.rx_buf = deque()
        self.tx_buf = deque()
        self.stop_event = threading.Event()
        self.sel = selectors.DefaultSelector()
        self.conn = None
        self.opened = False
        self.sock = None

        super().__init__(name="Socket connection manager")

    def run(self):
        """Thread main loop
        """
        while True:
            # Timeout is to check for thread stop event every second
            # otherwise this will block until a socket event happens
            events = self.sel.select(timeout=1)
            for key, mask in events:
                # if we have not attached any data to this thread it is
                # a new thread
                if key.data is None:
                    self.accept()
                else:
                    self.service_connection(key, mask)
            if self.stop_event.is_set():
                break

    def accept(self):
        """Accept and initialize new connection
        """
        self.conn, addr = self.sock.accept()
        self.logger.debug("Accepted connection from %s", addr)
        self.conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, connected=False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(self.conn, events, data=data)

    def service_connection(self, key, mask):
        """Service connected client

        :param key: Selector key
        :type key: SelectorKey
        :param mask: Events bitmask
        :type mask: int
        """
        data = key.data
        if mask & selectors.EVENT_READ:
            try:
                recv_data = self.conn.recv(1024)
            except ConnectionError:
                recv_data = 0

            if recv_data:
                self.logger.debug("Received data %s from %s", str(recv_data), data.addr)
                self.rx_buf.extendleft(recv_data)
            else:
                self.logger.debug("Closing connection to %s", data.addr)
                self.sel.unregister(self.conn)
                self.conn.close()
        if mask & selectors.EVENT_WRITE:
            if len(self.tx_buf):
                buf = bytearray()
                for _ in range(len(self.tx_buf)):
                    buf.append(self.tx_buf.pop())
                self.logger.debug("Sending %s to %s", str(bytes(buf)), data.addr)
                self.conn.sendall(buf)

    def open(self):
        """Open MAC layer
        """
        if not self.opened:
            self.rx_buf.clear()
            self.tx_buf.clear()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            self.sock.listen()
            self.sock.setblocking(False)
            # Register selector for listening socket
            self.sel.register(self.sock, selectors.EVENT_READ, data=None)
            self.start()
            self.opened = True
            self.logger.debug("Socket MAC started")

    def close(self):
        """Close MAC layer
        """
        if self.opened:
            self.stop_event.set()
            self.join()
            self.sel.unregister(self.sock)
            self.sock.close()
            self.logger.debug("Socket MAC stopped")
            self.opened = False

    def read(self, size):
        """Read received data

        Read size bytes from the MAC layer. If no timeout is set (None) it is a blocking
        read. Non-blocking operation (timeout > 0 or timeout = 0) can return
        less bytes than requested.

        :param size: Number of bytes to read
        :type size: int
        :return: Read data
        :rtype: bytearray
        """
        return_size = size
        if size > len(self.rx_buf):
            if self.timeout is None:
                while size > len(self.rx_buf):
                    pass
            elif self.timeout == 0:
                return_size = len(self.rx_buf)
            else:
                timer = Timer(self.timeout)
                while not timer.expired() and (size > len(self.rx_buf)):
                    pass
                if timer.expired():
                    return_size = len(self.rx_buf)

        data = bytearray()
        for _ in range(return_size):
            data.append(self.rx_buf.pop())
        return data

    def write(self, data):
        """Write data to MAC

        :param data: Data to write
        :type data: Bytes like object
        """
        self.tx_buf.extendleft(data)

class MacSocketClient(Mac):
    """Socket based transport
    """
    def __init__(self, port, host='localhost', timeout=5):
        """Class initialization

        :param buffer_in: MAC layer input buffer
        :type buffer_in: deque
        :param buffer_out: MAC layer output buffer
        :type buffer_out: deque
        :param timeout: Read timeout in seconds, defaults to 5
        timeout = None -> blocking read without timeout
        timeout = 0 -> non-blocking read, return immediately with up to the requested number of bytes
        timeout > 0 -> blocking read with timeout, return with requested number of bytes or less in
        case of timeout.
        :type timeout: int or None, optional
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connect_timeout = 5
        self.buf = bytearray()
        self.opened = False
        self.sock = None

    def open(self):
        """Open MAC layer
        """
        if not self.opened:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # TODO Timeouts are also valid for connect but the timeout requirements here
            # might be different
            # self.sock.settimeout(5)
            try:
                self.sock.connect((self.host, self.port))
            except ConnectionRefusedError as exc:
                raise MacError(f"{exc}") from exc
            # timeout = None -> blocking
            # timeout = 0 -> non-blocking
            # timeout > 0 -> blocking with timeout
            self.sock.settimeout(self.timeout)
            self.opened = True

    def close(self):
        """Close MAC layer
        """
        if self.opened:
            self.sock.close()
            self.opened = False

    def write(self, data):
        """Write to MAC layer

        :param data: Data to write.
        :type data: bytes, bytearray
        """
        self.sock.sendall(data)

    def read(self, size):
        """Read from MAC layer

        Read size bytes from the MAC layer. If no timeout is set (None) it is a blocking
        read. Non-blocking operation (timeout > 0 or timeout = 0) can return
        less bytes than requested.

        :param size: Number of bytes to read
        :type size: int
        """
        buf = bytearray()
        if self.timeout is None:
            while size > len(buf):
                buf.extend(self.sock.recv(size - len(buf)))
        elif self.timeout == 0:
            try:
                buf = self.sock.recv(size)
            except BlockingIOError:
                pass
        else:
            timer = Timer(self.timeout)
            while not timer.expired() and (size > len(buf)):
                buf.extend(self.sock.recv(size - len(buf)))
        return buf

class MacSocketPacketHost(threading.Thread):
    """Host MAC layer for a network connection"""
    FRAME_HEADER_SIZE = 4
    FRAME_LENGTH_SIZE = 4
    def __init__(self, host, port, timeout=3):
        """Class initialization

        :param host: Host interface to listen on
        :type host: str
        :param port: Port to listen on for connections
        :type port: int
        :param timeout:
        timeout = None -> blocking read without timeout
        timeout = 0 -> non-blocking read, return immediately with up to the requested number of bytes
        timeout > 0 -> blocking read with timeout, return with requested number of bytes or less in
        case of timeout.
        :type timeout: int or None, optional
        :type timeout: int
        """
        self.logger = getLogger("mac.MacSocketPacketHost")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.rx_buf = deque()
        self.tx_buf = deque()
        self.stop_event = threading.Event()
        self.sel = selectors.DefaultSelector()
        self.conn = None
        self.opened = False
        self.sock = None

        super().__init__(name="Socket connection manager")

    def run(self):
        """Thread main loop
        """
        while True:
            # Timeout is to check for thread stop event every second
            # otherwise this will block until a socket event happens
            events = self.sel.select(timeout=1)
            for key, mask in events:
                # if we have not attached any data to this thread it is
                # a new thread
                if key.data is None:
                    self.accept()
                else:
                    self.service_connection(key, mask)
            if self.stop_event.is_set():
                break

    def accept(self):
        """Accept and initialize new connection
        """
        self.conn, addr = self.sock.accept()
        self.logger.debug("Accepted connection from %s", addr)
        self.conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, connected=False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(self.conn, events, data=data)

    def service_connection(self, key, mask):
        """Service connected client

        :param key: Selector key
        :type key: SelectorKey
        :param mask: Events bitmask
        :type mask: int
        """
        data = key.data
        if mask & selectors.EVENT_READ:
            try:
                recv_data = self.conn.recv(1024)
            except ConnectionError:
                recv_data = 0

            if recv_data:
                self.logger.debug("Received data 0x%s from %s", recv_data.hex(), data.addr)
                self.rx_buf.extendleft(recv_data)
            else:
                self.logger.debug("Closing connection to %s", data.addr)
                self.sel.unregister(self.conn)
                self.conn.close()
        if mask & selectors.EVENT_WRITE:
            if len(self.tx_buf):
                frame = self.tx_buf.pop()
                self.logger.debug("Sending 0x%s to %s", bytes(frame).hex(), data.addr)
                self.conn.sendall(frame)

    def open(self):
        """Open MAC layer
        """
        if not self.opened:
            self.rx_buf.clear()
            self.tx_buf.clear()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            self.sock.listen()
            self.sock.setblocking(False)
            # Register selector for listening socket
            self.sel.register(self.sock, selectors.EVENT_READ, data=None)
            self.start()
            self.opened = True
            self.logger.debug("Socket MAC started")

    def close(self):
        """Close MAC layer
        """
        if self.opened:
            self.stop_event.set()
            self.join()
            self.sel.unregister(self.sock)
            self.sock.close()
            self.logger.debug("Socket MAC stopped")
            self.opened = False

    def _is_packet_complete(self):
        if len(self.rx_buf) >= 8:
            tmp = bytearray()
            # peek into the first 8 bytes of the queue to get header and frame size
            for i in range(1,9):
                tmp.append(self.rx_buf[-i])
            if tmp[0:self.FRAME_HEADER_SIZE] == b"MDFU":
                size = int.from_bytes(
                    tmp[self.FRAME_HEADER_SIZE:self.FRAME_HEADER_SIZE + self.FRAME_LENGTH_SIZE],
                    byteorder="little")
                if size <= (len(self.rx_buf) - (self.FRAME_HEADER_SIZE + self.FRAME_LENGTH_SIZE)):
                    return True
            else:
                raise ValueError("Packet MAC out of sync")
        return False

    def read(self, size=0): #pylint: disable=unused-argument
        """
        Reads a packet from MAC layer.

        This function waits until a complete packet is available in the MAC layer,
        then reads and returns the packet. If the packet is not available within
        the specified timeout period, a `MacError` is raised.

        :param int size: (Optional) The size of the packet to read. This parameter is ignored
        but kept for API compatibility with a stream based MAC layer.
        :raises MacError: If the packet is not available within the timeout period.
        :return: The packet read from the buffer.
        :rtype: bytearray
        """
        timer = Timer(self.timeout)
        while not self._is_packet_complete():
            if timer.expired():
                raise MacError("Timeout while waiting for packet")
        for _ in range(self.FRAME_HEADER_SIZE):
            self.rx_buf.pop()
        packet_size = bytearray()
        for _ in range(self.FRAME_LENGTH_SIZE):
            packet_size.append(self.rx_buf.pop())
        packet_size = int.from_bytes(packet_size, byteorder="little")
        packet = bytearray()
        for _ in range(packet_size):
            packet.append(self.rx_buf.pop())
        return packet

    def write(self, data):
        """
        Write a packet to the MAC layer.

        This method frames the data with a header and size information before sending it over
        the socket.

        :param data: The data to be sent.
        :type data: bytes
        :return: None
        """
        frame = b"MDFU" + len(data).to_bytes(4, byteorder="little") + data
        self.tx_buf.appendleft(frame)

class MacSocketPacketClient(Mac):
    """
    Socket based transport with packet framing for MAC layer communication.

    This class provides a socket-based transport mechanism for the MAC layer,
    allowing for communication over TCP/IP. It handles packet framing and
    ensures that complete packets are read from the socket.

    """
    FRAME_HEADER_SIZE = 4
    FRAME_LENGTH_SIZE = 4
    def __init__(self, host='localhost', port=5559, timeout=5):
        """
        Initialize the MacSocketPacketClient.

        :param host: The hostname or IP address of the server to connect to.
        :type host: str
        :param port: The port number of the server to connect to.
        :type port: int
        :param timeout: Read timeout in seconds. Defaults to 5.
        :type timeout: int, optional
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.buf = bytearray()
        self.opened = False
        self.sock = None

    def open(self):
        """
        Open the MAC layer connection.

        This method establishes a TCP connection to the specified host and port.
        It sets the socket to non-blocking mode and initializes the internal buffer.

        :raises MacError: If the connection to the server is refused.
        """
        if not self.opened:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.connect((self.host, self.port))
            except ConnectionRefusedError as exc:
                raise MacError(f"{exc}") from exc
            self.sock.setblocking(False)
            self.opened = True
            self.buf = bytearray()

    def close(self):
        """
        Close the MAC layer connection.

        This method closes the TCP connection and marks the connection as closed.
        """
        if self.opened:
            self.sock.close()
            self.opened = False

    def _is_packet_complete(self):
        """
        Check if the current buffer contains a complete packet.

        A complete packet starts with the header 'MDFU' followed by the packet size (4 bytes in little endian format).
        The method checks if the buffer contains enough data to form a complete packet.

        :return: True if a complete packet is available, False otherwise.
        :rtype: bool
        :raises MacError: If the packet header is out of sync, meaning first bytes in buffer do not contain the
        header 'MDFU'.
        """
        if len(self.buf) >= self.FRAME_HEADER_SIZE:
            if self.buf[0:self.FRAME_HEADER_SIZE] == b"MDFU":
                size = int.from_bytes(
                    self.buf[self.FRAME_HEADER_SIZE:self.FRAME_HEADER_SIZE + self.FRAME_LENGTH_SIZE],
                    byteorder="little")
                if size == len(self.buf) - (self.FRAME_HEADER_SIZE + self.FRAME_LENGTH_SIZE):
                    return True
            else:
                raise MacError("Packet MAC out of sync")
        return False

    def write(self, data):
        """
        Write data to the socket.

        This method frames the data with a header and size information before sending it over
        the socket.

        :param data: The data to be sent.
        :type data: bytes
        :return: None
        """
        frame = b"MDFU" + len(data).to_bytes(4, byteorder="little") + data
        return self.sock.sendall(frame)

    def read(self, size=0): #pylint: disable=unused-argument
        """
        Read data from the socket.

        This method reads data from the socket based on the specified timeout.
        It ensures that a complete packet is read before returning the data.

        :param size: The number of bytes to read. This is ignored but kept here to keep
        a common API for all MAC layers.
        :type size: int, optional
        :return: The complete packet data.
        :rtype: bytes
        :raises MacError: If the read operation times out.
        """
        timer = Timer(self.timeout)
        while not self._is_packet_complete():
            try:
                self.buf.extend(self.sock.recv(256))
            except BlockingIOError:
                pass
            if timer.expired():
                raise MacError("Timeout while waiting for data")
        packet_size = int.from_bytes(self.buf[4:8], byteorder="little")
        packet = self.buf[8:8+packet_size]
        if len(self.buf) > 8 + packet_size:
            self.buf = self.buf[8+packet_size:]
        else:
            self.buf = bytearray()
        return packet

class MacSocketPair(Mac):
    """Socket based MAC
    """
    def __init__(self, sock, timeout=5):
        """Class initialization

        :param sock: One of the sockets from the socket pair
        :type: socket
        :param timeout: Read timeout in seconds, defaults to 5
        timeout = None -> blocking read without timeout
        timeout = 0 -> non-blocking read, return immediately with up to the requested number of bytes
        timeout > 0 -> blocking read with timeout, return with requested number of bytes or less in
        case of timeout.
        :type timeout: int or None, optional
        """
        self.sock = sock
        self.timeout = timeout
        self.sock.settimeout(self.timeout)
        self.buf = bytearray()

    def write(self, data):
        """Write to MAC layer

        :param data: Data to write.
        :type data: bytes, bytearray
        """
        self.sock.sendall(data)

    def read(self, size):
        """Read from MAC layer

        Read size bytes from the MAC layer. If no timeout is set (None) it is a blocking
        read. Non-blocking operation (timeout > 0 or timeout = 0) can return
        less bytes than requested.

        :param size: Number of bytes to read
        :type size: int
        """
        if size > len(self.buf):
            try:
                self.buf.extend(self.sock.recv(size - len(self.buf)))
            except BlockingIOError:
                pass
            except (TimeoutError, socket.timeout):
                pass
        length = len(self.buf) if size > len(self.buf) else size
        data = self.buf[:length]
        self.buf = self.buf[length:]
        return data

    def __len__(self):
        """Get number of bytes available to read from MAC

        :return: Number of bytes
        :rtype: int
        """
        try:
            self.buf.extend(self.sock.recv(256))
        except BlockingIOError:
            pass
        return len(self.buf)
