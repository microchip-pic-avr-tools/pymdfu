"""Networking tool"""
import logging
import textwrap
from pymdfu.mac import MacFactory
from pymdfu.mac.network_mac import MacSocketPacketClient, MacSocketPacketHost
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.transport.spi_transport import SpiTransport, SpiTransportClient
from pymdfu.transport.i2c_transport import I2cTransportClient, I2cTransport

class NetworkTool(Tool, Transport):
    """Network tool"""
    def __init__(self, tool_args):
        """Network tool initialization

        :param tool_args: Tool arguments
        :type tool_args: list
        """
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        if args.transport == "serial":
            mac = MacFactory.get_socket_client_mac(host=args.host, port=args.port, timeout=1)
            self.transport = UartTransport(mac=mac)
        elif args.transport == "spi":
            mac = MacSocketPacketClient(args.host, args.port, timeout=2)
            self.transport = SpiTransport(mac=mac)
        elif args.transport == "i2c":
            mac = MacSocketPacketClient(args.host, args.port, timeout=2)
            self.transport = I2cTransport(mac=mac)
        else:
            raise ValueError(f"Invalid transport {args.transport}")

    @staticmethod
    def _parse_args(tool_args):
        parser = ToolArgumentParser()
        parser.add_argument("--transport",
            type=str,
            choices=["serial", "spi", "i2c"],
            default="serial"
        )
        parser.add_argument("--port",
            type=int,
            default=5559
        )
        parser.add_argument("--host",
            type=str,
            default="localhost"
        )
        return parser.parse_args(tool_args)

    @classmethod
    def usage_help(cls):
        return "[--host <host>] [--port <port] [--transport <transport>]"

    @classmethod
    def tool_help(cls):
        return "Network tool"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        Networking tool options
            --port <port>   Port number, default is 5559
            
            --host <host>   Host name or IP address e.g. localhost or 127.0.0.1
            
            --transport <transport>
                            Transport protocol one of [serial, spi], default is serial
        """)

    def list_connected(self):
        self.logger.info("List connected tools not implemented for network tool")

    def open(self):
        self.transport.open()

    def close(self):
        self.transport.close()

    @property
    def mac(self):
        """MAC layer

        :return: MAC layer used in the transport layer
        :rtype: Mac
        """
        return self.transport.mac

    def write(self, data):
        self.transport.write(data)

    def read(self, timeout=None):
        return self.transport.read(timeout)

class NetworkClientTool(NetworkTool):
    """Network client tool"""
    def __init__(self, tool_args): #pylint: disable=super-init-not-called
        """Network client tool initialization

        :param tool_args: Tool arguments
        :type tool_args: list
        """
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        if args.transport == "serial":
            mac = MacFactory.get_socket_host_mac(host=args.host, port=args.port, timeout=1)
            self.transport = UartTransport(mac=mac)
        elif args.transport == "spi":
            mac = MacSocketPacketHost(args.host, args.port, timeout=2)
            self.transport = SpiTransportClient(mac=mac)
        elif args.transport == "i2c":
            mac = MacSocketPacketHost(args.host, args.port, timeout=2)
            self.transport = I2cTransportClient(mac=mac)
        else:
            raise ValueError(f"Invalid transport {args.transport}")

if __name__ == "__main__":
    tool = NetworkTool(["--host", "localhost", "--port", "5558", "--transport", "serial"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(NetworkTool.usage_help)
