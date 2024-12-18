"""MCP2221A tool"""
import logging
import textwrap
from pymdfu.utils import si_postfix_unit_to_int
from pymdfu.mac.serial_mac import MacSerialPort
from pymdfu.mac.mcp2221a_mac import MacMcp2221a
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.transport.i2c_transport import I2cTransport

class Mcp2221aTool(Tool, Transport):
    """MCP2221A Tool"""
    def __init__(self, tool_args):
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        if args.interface == "uart":
            mac = MacSerialPort(args.port, args.baudrate)
            self.transport = UartTransport(mac=mac)
        else:
            mac = MacMcp2221a(args.clk_speed, args.address, system_latency=0.1)
            self.transport = I2cTransport(mac=mac)

    @staticmethod
    def _parse_args(tool_args):
        parser_common = ToolArgumentParser()
        parser_common.add_argument("--interface",
            type=str,
            choices=["uart", "i2c"],
            default="uart",
            required=False
        )

        parser_uart = ToolArgumentParser()
        parser_uart.add_argument("--baudrate",
            type=si_postfix_unit_to_int,
            required=True,
        )
        parser_uart.add_argument("--port",
            type=str,
            required=True
        )

        parser_i2c = ToolArgumentParser()
        parser_i2c.add_argument("--address",
            type=int,
            required=True
        )
        parser_i2c.add_argument("--clk-speed",
            type=si_postfix_unit_to_int,
            required=True
        )
        args, unparsed_iface_args = parser_common.parse_known_args(tool_args)

        if args.interface == "uart":
            iface_args = parser_uart.parse_args(unparsed_iface_args)
            if iface_args.baudrate > 2_000_000:
                raise ValueError("This tool supports only baudrates up to 2M baud")
            iface_args.interface = "uart"
        else:
            iface_args = parser_i2c.parse_args(unparsed_iface_args)
            iface_args.interface = "i2c"
            if iface_args.clk_speed > 400_000:
                raise ValueError("This tool supports only I2C clock speeds up to 400kHz")
        return iface_args

    @classmethod
    def usage_help(cls):
        return "[--interface uart --baudrate <baudrate> --port <port> | " + \
            "--interface i2c --address <address> --clk-speed <clk-speed>]"

    @classmethod
    def tool_help(cls):
        return "Microchip MCP2221A USB to UART/I2C bridge"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        MCP2221A tool options
            --interface <interface>
                            Interface selection. Valid interfaces are uart and i2c.

        MCP2221A tool UART interface options
            --baudrate <baudrate> 
                            Baudrate (max 2M baud)
            --port <port>
                            Serial port e.g. COM1 on Windows or /dev/ttyACM0 on Linux.

        MCP2221A tool I2C interface options
            --address <address>
                            I2C address
            --clk-speed <clk-speed>
                            I2C clock speed
        """)

    def list_connected(self):
        self.logger.info("List connected tools for nEDBG not supported")

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

    def read(self, timeout):
        return self.transport.read(timeout)

if __name__ == "__main__":
    tool = Mcp2221aTool(["--interface", "uart", "--port", "COM12", "--baudrate", "115200"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(Mcp2221aTool.usage_help)
