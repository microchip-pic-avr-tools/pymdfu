"""Transport interface for MDFU
"""
import abc

class TransportError(Exception):
    """Generic transport exception"""

class Transport(object, metaclass=abc.ABCMeta):
    """Abstract class for transport interface definition

    :raises NotImplementedError: Exception when interface implementation does not
    follow interface specification
    """
    @abc.abstractmethod
    def open(self):
        """Open transport"""
        raise NotImplementedError('users must define open to use this base class')
    @abc.abstractmethod
    def close(self):
        """Close transport"""
        raise NotImplementedError('users must define close to use this base class')
    @abc.abstractmethod
    def read(self, timeout):
        """Read from transport layer"""
        raise NotImplementedError('users must define read to use this base class')
    @abc.abstractmethod
    def write(self, data):
        """Write to transport layer"""
        raise NotImplementedError('users must define write to use this base class')
    @property
    @abc.abstractmethod
    def mac(self):
        """MAC layer"""
        raise NotImplementedError('To use this base class the mac property must be implemented')
