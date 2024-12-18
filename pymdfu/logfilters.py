"""
Filters used in logging handlers
"""
from logging import Filter

#pylint: disable=too-few-public-methods
class NoInfoFilter(Filter):
    """Logging filter removing all INFO level log records"""
    def filter(self, record):
        return not record.levelname == "INFO"

#pylint: disable=too-few-public-methods
class OnlyInfoFilter(Filter):
    """Logging filter removing all log records except INFO level records"""
    def filter(self, record):
        return record.levelname == "INFO"
