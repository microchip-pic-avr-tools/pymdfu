"""Linux SPI subsystem tool"""
import logging
import textwrap
from pymdfu.mac.linux_spi_mac import MacLinuxSpi
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.transport.spi_transport import SpiTransport
from pymdfu.utils import si_postfix_unit_to_int

class LinuxSpiTool(Tool, Transport):
    """Linux SPI subsystem tool interface"""
    def __init__(self, tool_args):
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        mac = MacLinuxSpi(args.dev_path, args.mode, args.clk_speed)
        self.transport = SpiTransport(mac=mac)

    @staticmethod
    def _parse_args(tool_args):

        parser_spi = ToolArgumentParser()
        parser_spi.add_argument("--clk-speed",
            type=si_postfix_unit_to_int,
            required=True
        )
        parser_spi.add_argument("--dev-path",
            type=str,
            required=True
        )
        parser_spi.add_argument("--mode",
            type=int,
            default=0,
            required=True,
        )
        args = parser_spi.parse_args(tool_args)

        return args

    @classmethod
    def usage_help(cls):
        return "--dev-path <path to SPI device> --clk-speed <clock speed> --mode <mode>"

    @classmethod
    def tool_help(cls):
        return "Linux SPI subsystem"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        Linux SPI interface options
            --dev-path <path to SPI device>
                            E.g. /dev/spi0-0.
            --clk-speed <clk-speed> 
                            SPI clock speed in Hz.
            --mode <mode>
                            SPI mode one of [0,1,2,3], default is mode 0.
                            0: CPOL=0, CPHA=0
                            1: CPOL=0, CPHA=1
                            2: CPOL=1, CPHA=0
                            3: CPOL=1, CPHA=1
        """)

    def list_connected(self):
        self.logger.info("Listing of available SPI bus interfaces not supported")

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
    tool = LinuxSpiTool(["--dev-path", "/dev/spi0-1", "--clk-speed", "1M", "--mode", "0"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(LinuxSpiTool.usage_help)
