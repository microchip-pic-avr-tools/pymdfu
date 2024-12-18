"""MCP2210 tool"""
import logging
import textwrap
from pymdfu.utils import si_postfix_unit_to_int
from pymdfu.transport.spi_transport import SpiTransport
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.mac.mcp2210_mac import MacMcp2210

class Mcp2210Tool(Tool, Transport):
    """MCP2210 Tool"""
    def __init__(self, tool_args):
        """Class initialization

        :param tool_args: Tool arguments list
        :type tool_args: list
        """
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        mac = MacMcp2210(args.clk_speed, args.chip_select)
        self.transport = SpiTransport(mac=mac)

    @staticmethod
    def _parse_args(tool_args):
        """Parse tool command line arguments

        :param tool_args: Command line arguments for the tool
        :type tool_args: list
        :raises ValueError: When SPI clock speed exceeds limit
        :raises ValueError: When chip select pin is outside allowed range
        :return: Validated tool configuration parameters
        :rtype: Namespace
        """
        parser_spi = ToolArgumentParser()
        parser_spi.add_argument("--clk-speed",
            type=si_postfix_unit_to_int,
            required=True
        )
        parser_spi.add_argument("--chip-select",
            type=int,
            required=True
        )
        args = parser_spi.parse_args(tool_args)

        if not 3_000_000 >= args.clk_speed >= 1500:
            raise ValueError("This tool supports only SPI clock speeds between 1500 bps and 3 Mbps")

        if not 8 >= args.chip_select >= 0:
            raise ValueError("Valid chip select pins are 0 to 8")
        return args

    @classmethod
    def usage_help(cls):
        return "--clk-speed <clk-speed> --chip-select <chip-select-pin>"

    @classmethod
    def tool_help(cls):
        return "Microchip MCP2210 USB to SPI bridge"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        MCP2210 tool options
            --clk-speed <clk-speed>
                            SPI clock speed
            --chip-select <chip-select-pin>
                            SPI chip select pin
        """)

    def list_connected(self):
        self.logger.info("List connected tools for MCP2210 not supported")

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
    tool = Mcp2210Tool(["--clk-speed", "1M", "--chip-select", "1"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(Mcp2210Tool.usage_help)
