"""Totalphase Aardvark I2C/SPI bridge tool"""
import logging
import textwrap
from pymdfu.utils import si_postfix_unit_to_int
from pymdfu.mac.aardvark_mac import MacAardvarkI2c, MacAardvarkSpi
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.transport.i2c_transport import I2cTransport
from pymdfu.transport.spi_transport import SpiTransport

class AardvarkTool(Tool, Transport):
    """Aardvark Tool"""
    def __init__(self, tool_args):
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        if args.interface == "spi":
            mac = MacAardvarkSpi(args.clk_speed, mode=args.mode, cs_polarity=args.cs_polarity, device_id=args.device_id)
            self.transport = SpiTransport(mac=mac)
        else:
            mac = MacAardvarkI2c(args.clk_speed, args.address, args.enable_pull_ups, device_id=args.device_id)
            self.transport = I2cTransport(mac=mac)

    @staticmethod
    def _parse_args(tool_args):
        parser_common = ToolArgumentParser()
        parser_common.add_argument("--interface",
            type=str,
            choices=["spi", "i2c"],
            default="i2c",
            required=False
        )
        parser_common.add_argument("--serial-number",
            type=str,
            dest="device_id",
            default=None,
            required=False
        )

        parser_spi = ToolArgumentParser()
        parser_spi.add_argument("--clk-speed",
            type=si_postfix_unit_to_int,
            required=True,
        )

        parser_spi.add_argument("--mode",
            type=int,
            default=0,
            required=True,
        )

        parser_spi.add_argument("--cs-polarity",
            type=str,
            choices=["low", "high"],
            default="low",
            required=False
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
        parser_i2c.add_argument("--enable-pull-ups",
            action='store_true',
            required=False
        )
        args, unparsed_iface_args = parser_common.parse_known_args(tool_args)

        if args.interface == "spi":
            iface_args = parser_spi.parse_args(unparsed_iface_args)
            iface_args.interface = "spi"
            if iface_args.clk_speed > 8_000_000 or iface_args.clk_speed < 125_000:
                raise ValueError("This tool supports only SPI clock speeds 125 kHz - 8 MHz")
        else:
            iface_args = parser_i2c.parse_args(unparsed_iface_args)
            iface_args.interface = "i2c"
            if iface_args.clk_speed > 800_000 or iface_args.clk_speed < 1000:
                raise ValueError("This tool supports only I2C clock speeds 1 kHz - 800 kHz")
        iface_args.device_id = args.device_id
        return iface_args

    @classmethod
    def usage_help(cls):
        return "[--serial-number <serial-number>] " + \
            "[--interface spi --clk-speed <clk-speed> --mode <mode> --cs-polarity <polarity> | " + \
            "--interface i2c --address <address> --clk-speed <clk-speed> [--enable-pull-ups]]"

    @classmethod
    def tool_help(cls):
        return "Totalphase Aardvark USB to SPI/I2C bridge"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        Aardvark tool options
            --interface <interface>
                            Interface selection. Valid interfaces are spi and i2c.
            --serial-number <serial-number>
                            Serial number of Aardvark tool

        Aardvark tool SPI interface options
            --clk-speed <clk-speed> 
                            SPI clock speed (125 kHz - 8 MHz)
            --mode <mode>
                            SPI mode, either 0 or 3. Default is mode 0.
                            0: CPOL=0, CPHA=0
                            3: CPOL=1, CPHA=1
            --cs-polarity <polarity>
                            Chip select polarity. Default is active low.
                            low: Active low
                            high: Active high

        Aardvark tool I2C interface options
            --address <address>
                            I2C address
            --clk-speed <clk-speed>
                            I2C clock speed (1 kHz - 800 kHz)
            --enable-pull-ups
                            Enable built-in I2C pull-ups (2.2 kOhm)

        """)

    def list_connected(self):
        self.logger.info("Not supported")

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
    tool = AardvarkTool(["--interface", "i2c", "--clk-speed", "100k", "--address", "85"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(AardvarkTool.usage_help)
