"""Timeout helper functions
"""
import time

class Timer():
    """Simple timeout timer
    """

    def __init__(self, timeout):
        """Class initialzation

        :param timeout: Timeout in seconds
        :type timeout: int
        """
        self.set(timeout)

    def set(self, timeout):
        """Set a timeout

        :param timeout: Timeout in seconds
        :type timeout: int
        """
        self.timeout = time.time() + timeout

    def expired(self):
        """Checks if timeout has expired

        :return: True if timeout has expired otherwise False
        :rtype: bool
        """
        return time.time() > self.timeout
