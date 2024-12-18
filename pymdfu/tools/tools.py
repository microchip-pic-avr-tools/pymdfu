"""Tools manager for MDFU host application
"""
import platform
from pymdfu.tools.nedbg import NedbgTool
from pymdfu.tools.serial_generic import SerialTool
from pymdfu.tools.mcp2221a import Mcp2221aTool
from pymdfu.tools.network import NetworkTool, NetworkClientTool
from pymdfu.tools.simulator import SimulatorTool
from pymdfu.tools.mcp2210 import Mcp2210Tool
from pymdfu.tools.aardvark import AardvarkTool

supported_tools = {'serial': SerialTool, 'simulator': SimulatorTool, 'network': NetworkTool,
                    'mcp2221a': Mcp2221aTool, 'nedbg': NedbgTool, 'mcp2210': Mcp2210Tool,
                    'aardvark': AardvarkTool}

supported_client_tools = {'serial': SerialTool, 'network': NetworkClientTool}

os_type = platform.system()
if os_type == "Windows":
    pass
if os_type == "Linux":
    from pymdfu.tools.linux_i2c import LinuxI2cTool
    from pymdfu.tools.linux_spi import LinuxSpiTool
    supported_tools['linux-i2c'] = LinuxI2cTool
    supported_tools['linux-spi'] = LinuxSpiTool
elif os_type == "Darwin":
    pass

class ToolFactory():
    """Tools manager"""
    @staticmethod
    def get_tool(tool_name, tool_args=None):
        """Tools factory

        Returns a tool based on tool name.

        :param tool: Tool name
        :type tool: str
        :param tool_args: Tool specific parameters, defaults to None
        :type tool_args: dict, optional
        :raises ValueError: When tool is not supported
        :raises MacError: When tool initialization failed
        :return: Tool object
        :rtype: Object inherited from Transport class
        """
        try:
            tool = supported_tools[tool_name](tool_args)
        except KeyError as exc:
            tool_list = ""
            for name,_ in supported_tools.items():
                tool_list += f", {name}"
            raise ValueError(f'Tool "{tool_name}" is not in supported tools list {tool_list} ') from exc
        return tool

    @staticmethod
    def get_client_tool(tool_name, tool_args=None):
        """MDFU client tools factory

        Returns a client tool based on tool name.

        :param tool: Tool name
        :type tool: str
        :param tool_args: Tool specific parameters, defaults to None
        :type tool_args: dict, optional
        :raises ValueError: When tool is not supported
        :raises MacError: When tool initialization failed
        :return: Tool object
        :rtype: Object inherited from Transport class
        """
        try:
            tool = supported_client_tools[tool_name](tool_args)
        except KeyError as exc:
            tool_list = ""
            for name,_ in supported_client_tools.items():
                tool_list += f", {name}"
            raise ValueError(f'Tool "{tool_name}" is not in supported tools list {tool_list} ') from exc
        return tool

    @staticmethod
    def get_tool_class(tool_name):
        """Get tool class

        :param tool_name: Tool name
        :type tool_name: str
        :raises ValueError: If tool is not in supported list
        :return: Tool class
        :rtype: Implementation of Tool abstract class
        """
        try:
            tool = supported_tools[tool_name]
        except KeyError as exc:
            tool_list = ""
            for name,_ in supported_tools.items():
                tool_list += f", {name}"
            raise ValueError(f'Tool "{tool_name}" is not in supported tools list {tool_list} ') from exc
        return tool

    @staticmethod
    def get_client_tool_class(tool_name):
        """Get client tool class

        :param tool_name: Tool name
        :type tool_name: str
        :raises ValueError: If tool is not in supported list
        :return: Tool class
        :rtype: Implementation of Tool abstract class
        """
        try:
            tool = supported_client_tools[tool_name]
        except KeyError as exc:
            tool_list = ""
            for name,_ in supported_client_tools.items():
                tool_list += f", {name}"
            raise ValueError(f'Tool "{tool_name}" is not in supported tools list {tool_list} ') from exc
        return tool
