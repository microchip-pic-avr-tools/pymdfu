# Microchip Device Firmware Update Tools (pymdfu package)

The `pymdfu` Python package contains various tools to support firmware updates of clients that implement the Microchip Device Firmware Update (MDFU) protocol.

![PyPI - Format](https://img.shields.io/pypi/format/pymdfu)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pymdfu)
![PyPI - License](https://img.shields.io/pypi/l/pymdfu)

## Installation
Install using pip from [pypi](https://pypi.org/project/pymdfu):
```sh
pip install pymdfu
```

# MDFU host application command line interface pymdfu

`pymdfu` is a command line interface for the Microchip Device Firmware Update (MDFU) host application. It provides various actions to interact with MDFU clients, including updating firmware, retrieving client information, and getting help on tool-specific parameters.

## Usage
```sh
pymdfu [-h | --help] [-v <level> | --verbose <level>] [-V | --version] [-R | --release-info] [<action>]
```

### Actions

- `client-info`: Get MDFU client information.
- `tools-help`: Get help on tool-specific parameters.
- `update`: Perform a firmware update.

### Global Options

- `-h, --help`: Show help message and exit.
- `-v <level>, --verbose <level>`: Set logging verbosity/severity level. Valid levels are [debug, info, warning, error, critical]. Default is `info`.
- `-V, --version`: Print `pymdfu` version number and exit.
- `-R, --release-info`: Print `pymdfu` release details and exit.

## Examples

### Update Firmware

Update firmware through a serial port with `update_image.img`:

```sh
pymdfu update --tool serial --image update_image.img --port COM11 --baudrate 115200
```

### Get Client Information

Retrieve MDFU client information using a serial tool:

```sh
pymdfu client-info --tool serial --port COM11 --baudrate 115200
```

### Version and release information
To print the version of `pymdfu` command line tool and the supported MDFU protocol version:

```sh
pymdfu --version
```

To print release details:

```sh
pymdfu --release-info
```

### Help

For general help:

```sh
pymdfu --help
```

For help on a specific action:

```sh
pymdfu <action> --help
```

Get help on tool-specific parameters:

```sh
pymdfu tools-help
```

## Configuration File

For some actions like `update` and `client-info` it is possible to specify a configuration file using the `-c` or `--config-file` option. The configuration file should be in TOML format and can include common parameters and tool-specific parameters. Parameters provided on the command line will take precedence over parameters specified in the config file. Options in tool-specific section will only be applied if the corresponding tool is used e.g. if `--tool serial` is provided the parameters in the section `[serial]` will be applied.

### Example Configuration File

```toml
[common]
verbose = "debug"

[serial]
port = "COM11"
baudrate = 115200

[network]
host = "192.168.1.100"
port = 8080
```
# MDFU client command line interface pymdfuclient

The `pymdfuclient` is a MDFU client with a command line interface and can be used to test MDFU hosts. The client implements the MDFU protocol but not any firmware image specific functions like decoding or verifying the firmware image. This means the tool is firmware image file agnostic and any file can be transferred with the client returning an image state as success after the transfer.

Future versions of this tool might offer specific client implementations that can decode and verify FW images e.g. FW images for Microchip 8-bit microcontroller that use the pyfwimagebuilder tool: https://pypi.org/project/pyfwimagebuilder/

## Usage

```sh
pymdfuclient [-h | --help] [-v <level> | --verbose <level>] [-V | --version] [-R | --release-info]  --tool <tool> [<tools-args>...]
```
## Examples

Start MDFU client on localhost port 5558 and use the serial transport layer:
```sh
pymdfuclient --tool network --host localhost --port 5558 --transport serial
```

Start MDFU client on serial port COM11 with baudrate 115200:
```sh
pymdfuclient --tool serial --port COM11 --baudrate 115200
```