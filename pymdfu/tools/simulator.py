"""Simulator tool"""
import textwrap
from pymdfu.mac import MacFactory
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.pymdfuclient import MdfuClient
from pymdfu.transport import Transport
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.transport.i2c_transport import I2cTransport, I2cTransportClient
from pymdfu.transport.spi_transport import SpiTransport, SpiTransportClient

transport_mac_support = {
    "serial": ["bytes", "socketpair"],
    "i2c": ["packet"],
    "spi": ["packet"]
}

class SimulatorTool(Tool, Transport):
    """Simulator Tool"""
    def __init__(self, tool_args):
        args = self._parse_args(tool_args)

        if args.mac == "bytes":
            mac_host, mac_client = MacFactory.get_bytes_based_mac(timeout=0)
        elif args.mac == "socketpair":
            mac_host, mac_client = MacFactory.get_socketpair_based_mac(timeout=0)
        elif args.mac == "packet":
            # Since host and client run on different threads data is not immediately available
            # and we don't want to do blocking read in the client simulator. Therefore we add
            # a timeout when creating the MAC for SPI. I2C does not need it but we keep it simple
            # and add it for both.
            mac_host, mac_client = MacFactory.get_packet_based_mac(timeout=1)
        else:
            raise ValueError(f"Invalid MAC layer: {args.mac}")

        if "serial" == args.transport:
            if args.mac not in transport_mac_support["serial"]:
                raise ValueError("The serial transport does not support {args.mac} MAC layer")
            transport_client = UartTransport(mac=mac_client, timeout=1)
            self.transport = UartTransport(mac=mac_host, timeout=1)
        elif "i2c" == args.transport:
            if args.mac not in transport_mac_support["i2c"]:
                raise ValueError("The I2C transport does not support {args.mac} MAC layer")
            transport_client = I2cTransportClient(mac=mac_client, timeout=1)
            self.transport = I2cTransport(mac=mac_host, timeout=1)
        elif "spi" == args.transport:
            if args.mac not in transport_mac_support["spi"]:
                raise ValueError("The SPI transport does not support {args.mac} MAC layer")
            transport_client = SpiTransportClient(mac=mac_client, timeout=1)
            self.transport = SpiTransport(mac=mac_host, timeout=1)
        else:
            raise ValueError(f"Invalid transport layer {args.transport}")

        self.client = MdfuClient(transport_client)

    @staticmethod
    def _parse_args(tool_args):
        parser = ToolArgumentParser()
        parser.add_argument("-m", "--mac",
            type=str,
            help="Mac layer",
            choices=["socketpair", "bytes", "packet"],
            default="bytes"
        )
        parser.add_argument("--transport",
            type=str,
            help="Transport layer",
            choices=["serial", "i2c", "spi"],
            default="serial"
        )
        return parser.parse_args(tool_args)

    @classmethod
    def usage_help(cls):
        return "[--transport <transport] [--mac <mac>]"

    @classmethod
    def tool_help(cls):
        return "Microchip MDFU client simulator"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        Simulator tool options
        
            --transport <transport>
                            Transport protocol. Valid options are serial, i2c and spi.
                            Default is serial.
            --mac <mac>
                            MAC layer slection. Valid options are socketpair, bytes and packet.
                            The packet based MAC layer must be used for i2c and spi transport.
                            Default is bytes.
        """)

    def list_connected(self):
        print("List network interface not implemented")

    def open(self):
        self.client.start()
        self.transport.open()

    def close(self):
        self.transport.close()
        self.client.stop()

    @property
    def mac(self):
        """MAC layer

        :return: MAC layer used in the transport layer
        :rtype: Mac
        """
        return self.transport.mac

    def write(self, data):
        self.transport.write(data)

    def read(self,timeout):
        return self.transport.read(timeout)
