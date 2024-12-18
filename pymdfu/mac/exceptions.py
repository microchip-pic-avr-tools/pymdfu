"""Exceptions for MAC layer"""

class MacError(Exception):
    """Generic MAC error"""

class MacI2cNackError(Exception):
    """I2C client NACK error"""
