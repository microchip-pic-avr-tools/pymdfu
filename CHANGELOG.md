# Changelog
## [2.5.1] - December 2024
- pymdfu CLI and library
  - MDFU specification 1.2.0 support
  - Position independent common CLI arguments
  - Common checksum library
  - Configurable number of retries
  - I2C transport
  - I2C transport over network
- pymdfuclient
  - I2C transport support
  - Inter transaction delay support

### Added
- PYTOOLS-12 As a user I want to list supported hardware tools/adapters
- PYTOOLS-36 pymdfu simulator target tests
- PYTOOLS-272 Move padding and CRC creation from transport layers to utils
- PYTOOLS-309 Allow common arguments anywhere on the command line
- PYTOOLS-311 I2C transport specification updates

## [2.4.0] - August 2024
- pymdfu CLI and library
  - SPI transport layer
  - Packet based networking layer
  - Linux SPI subsystem support
  - Linux I2C subsystem support
  - Transport and MAC layers refactored into their own sub-modules
  - Aardvark tool support with SPI and I2C interfaces
  - MCP2221A tool support
  - MCP2210 tool support
  - Logging configuration through TOML file
  - Support MDFU protocol specfication version 1.1
  - Checks for client MDFU version and exits if not supported by host
  - CLI help for tool specific options
  - CLI configuration by file
- pymdfuclient
  - Support for serial port.

### Added
- PYTOOLS-278 Packet based networking MAC
- PYTOOLS-277 Serial interface support in pymdfuclient
- PYTOOLS-275 Linux SPI and I2C subsystem support
- PYTOOLS-274 SPI transport layer spec update
- PYTOOLS-271 Transport and MAC layer restructuring
- PYTOOLS-270 Aardvark tool support
- PYTOOLS-269 Replace yaml logging configuration with TOML
- PYTOOLS-267 Update pymdfu excludes
- PYTOOLS-257 Remove @property from classmethods since it will not be supported in Python 3.13
- PYTOOLS-254 SPI transport layer
- PYTOOLS-253 MCP2210 tool
- PYTOOLS-243 MCP2221A tool
- PYTOOLS-242 I2C transport layer prototype
- PYTOOLS-191 Add supported MDFU protocol version and verify client version
- PYTOOLS-160 Tools API rework
- PYTOOLS-111 Specification for CLI configuration file
- PYTOOLS-17 Support for reading configuration file
- PYTOOLS-14 CLI help for tool specific options
- PYTOOLS-258 Document new CLI commands and options
### Fixed
- PYTOOLS-265 Handle file transfer abort response when no additional data is present
- PYTOOLS-210 Code in pymdfu break binary building

## [1.0.2] - December 2023
### Added
- PYTOOLS-211 Add missing packaging dependency

## [1.0.1] - December 2023

- Support MDFU get client info command
  - Read client command timeouts
  - Read client MDFU protocol version
- Support individual command timeouts
- Decode transport and file transfer abort error causes
- Check image state command response
- Bugfixes

### Added
- PYTOOLS-156 New get client information command with version and command timeouts
- PYTOOLS-91  Decode transport and file transfer abort error causes
- PYTOOLS-90  Check "get image state" command response packet payload for image status

### Fixed
- PYTOOLS-155 PyMDFU tool usage guideline is incorrect
- PYTOOLS-84  Document link between pymdfu and pyfwimagebuilder

## [0.1.4] - October 2023

Initial public beta release.

### Initial beta release

## [0.0.1] - October 2023

- Placeholder release
