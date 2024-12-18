"""nEDBG tool"""
import textwrap
from pymdfu.utils import si_postfix_unit_to_int
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.mac.serial_mac import MacSerialPort

class NedbgTool(Tool, Transport):
    """Tool for nEDBG debugger

    Implementation of the API from abstract classes Tool and Transport.
    """
    def __init__(self, tool_args):
        """Class initialization

        :param tool_args: Tools specific parameters
        :type tool_args: list
        """
        args = self._parse_args(tool_args)
        mac = MacSerialPort(args.port, args.baudrate)
        self.transport = UartTransport(mac=mac)

    @staticmethod
    def _parse_args(tool_args):
        parser = ToolArgumentParser()
        parser.add_argument("--baudrate",
            type=si_postfix_unit_to_int,
            required=True
        )
        parser.add_argument("--port",
            type=str,
            required=True
        )
        args = parser.parse_args(tool_args)
        if args.baudrate > 500_000:
            raise ValueError("This tool supports only baudrates up to 500k baud")
        return args

    @classmethod
    def usage_help(cls):
        return "--baudrate <baudrate> --port <port>"

    @classmethod
    def tool_help(cls):
        return "nEDBG tool"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        nEDBG tool options
            --baudrate <baudrate>
                            Baudrate (max 500k baud)
            --port <port>   Serial port e.g. COM1 on Windows or /dev/ttyACM0 on Linux
        """)

    def list_connected(self):
        raise NotImplementedError("List connected tools for nEDBG not supported yet")

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
    tool = NedbgTool(["--port", "COM12", "--baudrate", "115200"])
    print(tool.usage_help)
    print(tool.tool_help)
    print(tool.parameter_help)
    print(NedbgTool.usage_help)
