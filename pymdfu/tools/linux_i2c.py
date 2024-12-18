"""Linux I2C subsystem tool"""
import logging
import textwrap
from pymdfu.mac.linux_i2c_mac import MacLinuxI2c
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.transport.i2c_transport import I2cTransport

class LinuxI2cTool(Tool, Transport):
    """Linux I2C subsystem tool interface"""
    def __init__(self, tool_args):
        self.logger = logging.getLogger(__name__)
        args = self._parse_args(tool_args)

        mac = MacLinuxI2c(args.dev_path, args.address)
        self.transport = I2cTransport(mac=mac)

    @staticmethod
    def _parse_args(tool_args):

        parser_i2c = ToolArgumentParser()
        parser_i2c.add_argument("--address",
            type=int,
            required=True
        )
        parser_i2c.add_argument("--dev-path",
            type=str,
            required=True
        )
        args = parser_i2c.parse_args(tool_args)

        if args.address > 0x7F:
            raise ValueError("Only 7-bit I2C address is supported")
        return args

    @classmethod
    def usage_help(cls):
        return "--dev-path <path to I2C device> --address <address>"

    @classmethod
    def tool_help(cls):
        return "Linux I2C subsystem"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        Linux I2C interface options
            --address <address>
                            I2C address
            --dev-path <path to I2C device>
                            E.g. /dev/i2c-1
        """)

    def list_connected(self):
        self.logger.info("Listing of available I2C bus interfaces not supported")

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
    tool = LinuxI2cTool(["--dev-path", "/dev/i2c-1", "--address", "85"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(LinuxI2cTool.usage_help)
