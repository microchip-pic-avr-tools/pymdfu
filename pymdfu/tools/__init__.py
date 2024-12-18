"""Tools module"""
import abc
import argparse

class Tool(object, metaclass=abc.ABCMeta):
    """Tool API definition"""
    @abc.abstractmethod
    def list_connected(self):
        """List connected tools"""
        raise NotImplementedError('users must define write to use this base class')

    @classmethod
    @abc.abstractmethod
    def usage_help(cls):
        """CLI parameters usage
        """
        raise NotImplementedError('This property must be implemented to use this base class')

    @classmethod
    @abc.abstractmethod
    def tool_help(cls):
        """Tool help
        """
        raise NotImplementedError('This property must be implemented to use this base class')

    @classmethod
    @abc.abstractmethod
    def parameter_help(cls):
        """Tool CLI parameters help
        """
        raise NotImplementedError('This property must mbe implemented to use this base class')

class ToolArgumentParser(argparse.ArgumentParser):
    """Tool specific argument parser inherited from configargparse Argument parser

    We need to override the error method in this class to provide custom error
    messages and raise an exception that can be caught.
    """
    def error(self, message):
        """Function to handle argument parsing errors

        :raises ValueError: Raises alwas this exception here 
        :param message: Error message
        :type message: str
        """
        raise ValueError(message)
