"""
Askr Framework - A middleware framework for QQ chatbot development
Version: Beta 0.98
License: GPL v3

Main package that exports key components for external use.
"""

from . import config
from . import database
from . import plugin
from . import server

__version__ = "Beta 0.98"
__all__ = ['config', 'database', 'plugin', 'server']
