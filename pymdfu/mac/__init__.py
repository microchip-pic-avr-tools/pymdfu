"""Common MAC layer functions"""
import socket
from collections import deque
from .network_mac import MacSocketPair, MacSocketClient, MacSocketHost
from .packet_mac import MacPacket
from .bytes_mac import MacBytes

class MacFactory():
    """MAC layer factory
    """
    def __init__(self):
        pass

    @classmethod
    def get_packet_based_mac(cls, timeout=5):
        """Create a packet based MAC layer

        :param timeout: Read timeout for MAC, defaults to 5 seconds
        :type timeout: int, optional
        :return: Linked MAC objects that can be injected into host/client transport layer
        :rtype: (MacPacket, MacPacket)
        """
        host_in = deque()
        client_in = deque()
        host = MacPacket(host_in, client_in, timeout=timeout)
        client = MacPacket(client_in, host_in, timeout=timeout)
        return host, client

    @classmethod
    def get_bytes_based_mac(cls, timeout=5):
        """Create a bytes based MAC layer

        :param timeout:  Read timeout for MAC, defaults to 5 seconds
        :type timeout: int, optional
        :return: Linked MAC objects that can be injected into host/client transport layer
        :rtype: (MacPacket, MacPacket)
        """
        host_in = deque()
        client_in = deque()
        host = MacBytes(host_in, client_in, timeout=timeout)
        client = MacBytes(client_in, host_in, timeout=timeout)
        return host, client

    @classmethod
    def get_socketpair_based_mac(cls, timeout=5):
        """Create a socket based MAC layer where the sockets are already connected

        :param timeout: Read timeout for MAC, defaults to 5 seconds
        :type timeout: int, optional
        :return: Tuple of MacSocketPair instances that are connected to each other.
        :rtype: tuple(MacSocketPair, MacSocketpair)
        """
        if hasattr(socket, "AF_UNIX"):
            family = socket.AF_UNIX
        else:
            family = socket.AF_INET
        sock1, sock2 = socket.socketpair(family, type=socket.SOCK_STREAM)

        host = MacSocketPair(sock1, timeout=timeout)
        client = MacSocketPair(sock2, timeout=timeout)
        return host, client

    @classmethod
    def get_socket_client_mac(cls, timeout=5, host="localhost", port=5557):
        """Create a client socket based MAC (MDFU host)

        From a socket connection point of view this is a client socket but
        for the MDFU protocol it is the MAC layer for the host application.

        :param timeout: Read timeout on MAC layer, defaults to 5 seconds
        :type timeout: int, optional
        :param host: Socket host to connect to, defaults to "localhost"
        :type host: str, optional
        :param port: Host port, defaults to 5557
        :type port: int, optional
        :return: MAC layer
        :rtype: MacSocketClient
        """
        client = MacSocketClient(port, host=host, timeout=timeout)
        return client

    @classmethod
    def get_socket_host_mac(cls, host="localhost", port=5557, timeout=3):
        """Create a host socket based MAC (MDFU client)

        From a socket connection point of view this is a host socket but
        for the MDFU protocol it is the MAC layer for the client.

        :param timeout: Timeout for host socket read, defaults to 3 seconds.
        A value of None or zero will be a blocking read.
        :type timeout: int, optional
        :param host: Host interface, defaults to "localhost"
        :type host: str, optional
        :param port: Port to listen on for connections, defaults to 5557
        :type port: int, optional
        :return: Mac layer
        :rtype: MacSocketHost
        """
        server = MacSocketHost(host, port, timeout=timeout)
        return server
