"""Utilities"""
from enum import Enum

def si_postfix_unit_to_int(si_unit):
    """
    Converts a postfixed SI unit into an int
    Supports k, M and G postfix.

    :param si_unit: SI unit with postfix e.g. 1M, 11k
    :type si_unit: str
    :return: int representation SI unit
    """
    if si_unit[-1] == 'k':
        value = float(si_unit.strip('k')) * 1000
    elif si_unit[-1] == 'M':
        value = float(si_unit.strip('M')) * 1_000_000
    elif si_unit[-1] == 'G':
        value = float(si_unit.strip('G')) * 1e9
    else:
        value = float(si_unit)
    return int(value)

class EnumDescription(int, Enum):
    """Subclass of Enum to support descriptions for Enum members
    
    Example:

    class MyEnum(EnumDescription):
        VAR1 = (0, "Description of VAR1")
        VAR2 = (1, "Desctiption of VAR2")

    MyEnum.VAR1.description
    MyEnum.VAR1.value
    MyEnum.VAR1.name

    Instantiation of MyEnum can be done with its value.
    y = MyEnum(0)
    y.description
    y.value
    y.name
    """
    def __new__(cls, value, description=None):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._description_ = description
        return obj

    @property
    def description(self):
        """Enum description property"""
        return self._description_

def calculate_checksum(data):
    """Calculate checksum

    The checksum is a two's complement addition (integer addition)
    of 16-bit values in little-endian byte order. If the data is an
    uneven number of bytes a padding zero byte is added at the end before
    calculating the checksum. Data passed into this function will not
    be modified when adding the padding byte.

    :param data: Input data for checksum calculation
    :type data: Bytes like object
    :return: 16bit checksum
    :rtype: int
    """
    checksum = 0
    # add padding byte at the end if we have an uneven number of bytes
    padded_payload = data + bytes(1) if len(data) % 2 else data
    for i in range(0, len(padded_payload), 2):
        checksum += (padded_payload[i + 1] << 8) | padded_payload[i]
    return (~checksum) & 0xffff
