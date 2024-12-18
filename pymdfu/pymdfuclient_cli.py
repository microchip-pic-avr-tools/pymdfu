"""Command line interface for MDFU client"""
import logging
import os
import sys
import argparse
import textwrap
import time
from logging.config import dictConfig
from appdirs import user_log_dir
try:
    # When Python 3.11 becomes the minimum supported version for this tool
    # we can remove the tomli fallback solution here since this version
    # will have tomllib in its standard library.
    import tomllib as toml_reader
except ModuleNotFoundError:
    import tomli as toml_reader #pylint: disable=import-error
from pymdfu.pymdfuclient import MdfuClient
from pymdfu.tools.tools import ToolFactory, supported_client_tools

try:
    from . import __version__ as VERSION
    from . import BUILD_DATE, COMMIT_ID
except ImportError:
    print("Version info not found!")
    VERSION = "0.0.0"
    COMMIT_ID = "N/A"
    BUILD_DATE = "N/A"

def run_mdfu_client(transport):
    """Run MDFU client

    Terminate the client with CTRL-C

    :param transport: Initialized transport layer stack
    :type transport: Transport
    """
    client = MdfuClient(transport)
    client.start()
    try:
        while client.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        client.stop()

class CliHelp():
    """CLI help"""
    USAGE = textwrap.dedent("""\
    pymdfuclient [-h | --help] [-v <level> | --verbose <level>] [-V | --version] [-R | --release-info] \
 --tool <tool> [<tools-args>...]

    """)
    COMMON_OPTIONS = textwrap.dedent("""\
            -v <level>, --verbose <level>
                            Logging verbosity/severity level. Valid levels are
                            [debug, info, warning, error, critical].
                            Default is info.
    """)
    USAGE_EXAMPLES = textwrap.dedent("""\
    Usage examples
        Start client with networking tool on localhost port 5558

            pymdfuclient --tool network --host localhost --port 5558
    """)

    @classmethod
    def cli_help(cls):
        """Create help text for main CLI entrypoint

        :return: CLI help text
        :rtype: str
        """
        cli_help_txt = cls.USAGE + textwrap.dedent('''\
        Microchip Device Firmware Update (MDFU) client command line interface.
        
        Actions
            -h, --help      Show this help message and exit
        
            -V, --version   Print pymdfu version number and exit
        
            -R, --release-info
                            help=Print pymdfu release details and exit
            
            -t <tool>, --tool <tool>
                            Tool to use for connecting to a MDFU host. Each tool has
                            its own configuration parameters that are described in
                            the tools help section.
        
        Optional arguments
        ''') \
        + textwrap.indent(cls.COMMON_OPTIONS,"    ") \
        + "Tools Options\n" \
        + cls.tools_parameter_help() \
        + cls.USAGE_EXAMPLES

        return cli_help_txt

    @classmethod
    def tools_parameter_help(cls):
        """Create help text for tools specific parameters

        Text for
            pymdfu tools-help
        
        :return: Help text
        :rtype: str
        """
        tools_help_txt = ""
        for tool_name in supported_client_tools:
            tool = ToolFactory.get_client_tool_class(tool_name)
            tools_help_txt += f"{tool.parameter_help()}\n"
        return tools_help_txt

    @classmethod
    def tool_usage_help(cls, cli_usage, tool_name, msg=None):
        """Create tool specific CLI usage help

        :param cli_usage: CLI usage text that contains '<tool>'
        and '[<tools-args>...]'. Both of them will be replaced with
        tool specific parameters based on tool_name input.
        :type cli_usage: str
        :param tool_name: Tool name
        :type tool_name: str
        :param msg: Error message, defaults to None
        :type msg: str, optional
        :return: CLI usage with optional error message
        :rtype: str
        """
        tool = ToolFactory.get_client_tool_class(tool_name)
        usage_tool = tool.usage_help()
        usage = cli_usage.replace("<tool>", tool_name)
        usage = usage.replace("[<tools-args>...]", usage_tool)
        if msg:
            usage = usage + "\n" + "Tool parameter error: " + str(msg)
        return usage

def setup_logging(user_requested_level=logging.WARNING, default_path='logging.toml',
                  env_key='MICROCHIP_PYTHONTOOLS_CONFIG'):
    """
    Setup logging configuration for this CLI
    """
    # Logging config TOML file can be specified via environment variable
    value = os.getenv(env_key, None)
    if value:
        path = value
    else:
        # Otherwise use the one shipped with this application
        path = os.path.join(os.path.dirname(__file__), default_path)
    # Load the TOML if possible
    if os.path.exists(path):
        try:
            with open(path, 'rb') as file:
                # Load logging configfile from toml
                configfile = toml_reader.load(file)
                # File logging goes to user log directory under Microchip/modulename
                logdir = user_log_dir(__name__, "Microchip")
                # Look through all handlers, and prepend log directory to redirect all file loggers
                num_file_handlers = 0
                for handler in configfile['handlers'].keys():
                    # A filename key
                    if 'filename' in configfile['handlers'][handler].keys():
                        configfile['handlers'][handler]['filename'] = os.path.join(
                            logdir, configfile['handlers'][handler]['filename'])
                        num_file_handlers += 1
                if num_file_handlers > 0:
                    # Create it if it does not exist
                    os.makedirs(logdir, exist_ok=True)

                if user_requested_level <= logging.DEBUG:
                    # Using a different handler for DEBUG level logging to be able to have a more detailed formatter
                    configfile['root']['handlers'].append('console_detailed')
                    # Remove the original console handlers
                    try:
                        configfile['root']['handlers'].remove('console_only_info')
                    except ValueError:
                        # The toml file might have been customized and the console_only_info handler might
                        # already have been removed
                        pass
                    try:
                        configfile['root']['handlers'].remove('console_not_info')
                    except ValueError:
                        # The toml file might have been customized and the console_only_info handler might
                        # already have been removed
                        pass
                else:
                    # Console logging takes granularity argument from CLI user
                    configfile['handlers']['console_only_info']['level'] = user_requested_level
                    configfile['handlers']['console_not_info']['level'] = user_requested_level

                # Root logger must be the most verbose of the ALL TOML configurations and the CLI user argument
                most_verbose_logging = min(user_requested_level, getattr(logging, configfile['root']['level']))
                for handler in configfile['handlers'].keys():
                    # A filename key
                    if 'filename' in configfile['handlers'][handler].keys():
                        level = getattr(logging, configfile['handlers'][handler]['level'])
                        most_verbose_logging = min(most_verbose_logging, level)
                configfile['root']['level'] = most_verbose_logging
            dictConfig(configfile)
            return
        except toml_reader.TOMLDecodeError:
            # Error while parsing TOML
            print(f"Error parsing logging config file '{path}'")
        except KeyError as keyerror:
            # Error looking for custom fields in TOML
            print(f"Key {keyerror} not found in logging config file")
    else:
        # Config specified by environment variable not found
        print(f"Unable to open logging config file '{path}'")

    # If all else fails, revert to basic logging at specified level for this application
    print("Reverting to basic logging.")
    logging.basicConfig(level=user_requested_level)

def main():
    """
    Entrypoint for installable CLI

    Configures the CLI and parses the arguments
    """
    # Shared switches.  These are inherited by subcommands (and root) using parents=[]
    common_argument_parser = argparse.ArgumentParser(add_help=False)
    common_argument_parser.add_argument("-v", "--verbose",
                                        default="info",
                                        choices=['debug', 'info', 'warning', 'error', 'critical'],
                                        help="Logging verbosity/severity level")
    common_argument_parser.add_argument("-h", "--help", action="store_true")

    parser = argparse.ArgumentParser(
        add_help=False,
        parents=[common_argument_parser],
        formatter_class=argparse.RawTextHelpFormatter)

    # Action-less switches.  These are all "do X and exit"
    parser.add_argument("-V", "--version", action="store_true",
                        help="Print pymdfuclient version number and exit")
    parser.add_argument("-R", "--release-info", action="store_true",
                        help="Print pymdfuclient release details and exit")

    parser.add_argument("--tool", choices=["serial", "network"],
                required = not any(arg in ["-V", "--version", "-R", "--release-info", "-h", "--help"]
                                   for arg in sys.argv))

    args, tool_args = parser.parse_known_args()

    # Setup logging
    setup_logging(user_requested_level=getattr(logging, args.verbose.upper()))
    logger = logging.getLogger(__name__)

    if args.help:
        txt = CliHelp.cli_help()
        print(txt)
        return 0

    if args.version or args.release_info:
        print(f"pymdfuclient version {VERSION}")
        if args.release_info:
            print(f"Build date:  {BUILD_DATE}")
            print(f"Commit ID:   {COMMIT_ID}")
            print(f"Installed in {os.path.abspath(os.path.dirname(__file__))}")
        return 0

    try:
        tool = ToolFactory.get_client_tool(args.tool, tool_args)
    except ValueError as exc:
        help_txt = CliHelp.tool_usage_help(CliHelp.USAGE, args.tool, msg=exc)
        print(help_txt, file=sys.stderr)
        return 1
    try:
        run_mdfu_client(tool)
    # pylint: disable-next=broad-exception-caught
    except Exception as exc:
        logger.error("Operation failed with %s: %s", type(exc).__name__, exc)
        if args.verbose != "debug":
            logger.error("For more information run with -v debug")
        logger.debug(exc, exc_info=True)    # get traceback if debug loglevel
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
