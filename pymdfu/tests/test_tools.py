"""Tests for tools layer"""
import unittest
import pytest
from mock import patch
from pymdfu.mdfu import Mdfu
from pymdfu.pymdfuclient import MdfuClient
from pymdfu.tools.tools import ToolFactory
from pymdfu.transport.uart_transport import UartTransport
from pymdfu.transport.i2c_transport import I2cTransportClient
from pymdfu.transport.spi_transport import SpiTransportClient
from pymdfu.mac import MacFactory

class TestTools(unittest.TestCase):
    """Tool tests"""

    def test_serial_tool(self):
        """Test serial tool
        Creates a linked MAC layer
        Initializes the serial tool with a patched MAC layer.
        Initializes a MDFU client with the linked MAC layer.
        Executes a MDFU update with a dummy image.
        """
        # Thread termination is shorter with short timeout so the test finishes faster
        host_mac, local_client_mac = MacFactory.get_bytes_based_mac(timeout=1)
        patcher = patch("pymdfu.tools.serial_generic.MacSerialPort")
        self.addCleanup(patcher.stop)
        mock_mcp2221a_mac = patcher.start()
        # Return our linked host MAC from mock object during instantiation
        mock_mcp2221a_mac.return_value = host_mac
        args = ["--port", "COMx", "--baudrate", "115200"]
        tool = ToolFactory.get_tool("serial", args)

        upgrade_image = bytes(512 * [0xff])

        transport_client = UartTransport(mac=local_client_mac)
        client = MdfuClient(transport_client)

        host = Mdfu(tool)

        client.start()
        host.run_upgrade(upgrade_image)
        client.stop()

    def test_mcp2221a_tool(self):
        """Test mcp2221a tool"""
        # Thread termination is shorter with short timeout so the test finishes faster
        host_mac, local_client_mac = MacFactory.get_packet_based_mac(timeout=1)
        patcher = patch("pymdfu.tools.mcp2221a.MacMcp2221a")
        self.addCleanup(patcher.stop)
        mock_mcp2221a_mac = patcher.start()
        # Return our linked host MAC from mock object during instantiation
        mock_mcp2221a_mac.return_value = host_mac

        args = ["--interface", "i2c", "--clk-speed", "100k", "--address", "15"]
        tool = ToolFactory.get_tool("mcp2221a", args)

        upgrade_image = bytes(512 * [0xff])

        transport_client = I2cTransportClient(mac=local_client_mac)
        client = MdfuClient(transport_client)

        host = Mdfu(tool)

        client.start()
        host.run_upgrade(upgrade_image)
        client.stop()

    def test_mcp2210_tool(self):
        """Test Aardvark tool"""
        # Thread termination is shorter with short timeout so the test finishes faster
        host_mac, local_client_mac = MacFactory.get_packet_based_mac(timeout=1)
        # We need to patch the MacMcp2210 class which is in pymdfu.mac.mcp2210_mac but since
        # this class is already imported in the mcp2210 tool during module initialization, that is
        # triggered by the imports in our test module here, we have to patch the class directly
        # in the mcp2210 tool.
        patcher = patch("pymdfu.tools.mcp2210.MacMcp2210")
        self.addCleanup(patcher.stop)
        mock_mcp2210_mac = patcher.start()
        # Return our linked host MAC from mock object during instantiation. In other words
        # when mac=MacMcp2210(...) is run in mcp2210 tool it will instead do mac=mock_mcp2210_mac()
        # which will return the host_mac that is connected to the client_mac.
        mock_mcp2210_mac.return_value = host_mac

        args = ["--clk-speed", "1M", "--chip-select", "1"]
        tool = ToolFactory.get_tool("mcp2210", args)

        upgrade_image = bytes(512 * [0xff])

        transport_client = SpiTransportClient(mac=local_client_mac)
        client = MdfuClient(transport_client)

        host = Mdfu(tool)

        client.start()
        host.run_upgrade(upgrade_image)
        client.stop()

    def test_simulator_tool(self):
        """Test the simulator tool"""
        # Test some valid configurations for the simulator tool
        args = ["--transport", "serial", "--mac", "bytes"]
        ToolFactory.get_tool("simulator", args)
        args = ["--transport", "i2c", "--mac", "packet"]
        ToolFactory.get_tool("simulator", args)
        args = ["--transport", "spi", "--mac", "packet"]
        ToolFactory.get_tool("simulator", args)
        args = ["--transport", "serial", "--mac", "socketpair"]
        ToolFactory.get_tool("simulator", args)

        # Test that instantiating a tool with an incompatible transport
        # and MAC layer will raise an error
        # In this case the SPI transport requires a packet MAC layer but
        # a bytes MAC is requested.
        with pytest.raises(ValueError):
            args = ["--transport", "spi", "--mac", "bytes"]
            ToolFactory.get_tool("simulator", args)
        # Try to create a tool with uart transport that requires
        # a bytes MAC
        with pytest.raises(ValueError):
            args = ["--transport", "uart", "--mac", "packet"]
            ToolFactory.get_tool("simulator", args)

        # Test instantiating with invalid MAC layer
        with pytest.raises(ValueError):
            args = ["--transport", "uart", "--mac", "invalid-MAC"]
            ToolFactory.get_tool("simulator", args)

        # Test instantiating with invalid transport layer
        with pytest.raises(ValueError):
            args = ["--transport", "invalid-tranport", "--mac", "bytes"]
            ToolFactory.get_tool("simulator", args)

        # Run an update with simulator tool
        args = ["--transport", "serial", "--mac", "bytes"]
        tool = ToolFactory.get_tool("simulator", args)
        mdfu_host = Mdfu(tool)
        upgrade_image = bytes(512 * [0xff])
        mdfu_host.run_upgrade(upgrade_image)
