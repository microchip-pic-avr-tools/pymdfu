"""Serial port tool
"""
import textwrap
import serial.tools.list_ports
from pymdfu.utils import si_postfix_unit_to_int
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.tools import Tool, ToolArgumentParser
from pymdfu.transport import Transport
from pymdfu.mac.serial_mac import MacSerialPort

class SerialTool(Tool, Transport):
    """Tool for serial ports

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
        return parser.parse_args(tool_args)

    @classmethod
    def usage_help(cls):
        return "--baudrate <baudrate> --port <port>"

    @classmethod
    def tool_help(cls):
        return "Serial port tool"

    @classmethod
    def parameter_help(cls):
        return textwrap.dedent("""\
        Serial tool options
        
            --baudrate <baudrate>
                            Baudrate (max 2M baud).
            --port <port>
                            Serial port e.g. COM1 on Windows or /dev/ttyACM0 on Linux

        """)

    def list_connected(self):
        comports = serial.tools.list_ports.comports()
        print("Found serial ports:")
        for port in comports:
            print(f"{port}", end=None)
        print("")

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
