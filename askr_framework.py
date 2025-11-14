#!/usr/bin/env python3
"""
Askr Framework - Compatibility wrapper for backward compatibility
This file maintains the same interface as the original monolithic file
but now uses the modularized structure.

Version: Beta 0.98
License: GPL v3
"""

# Import all modules
from . import config
from . import database
from . import plugin
from . import server

# Re-export all constants from config
EVENT_TYPES_ = config.EVENT_TYPES_
EVENT_INHERITANCE = config.EVENT_INHERITANCE
PLUGIN_REGISTRY = config.PLUGIN_REGISTRY
CONFIG = config.CONFIG
PLUGIN_ACCESS_RULES = config.PLUGIN_ACCESS_RULES
IS_MUTED = config.IS_MUTED
LOGGING_LEVELS = config.LOGGING_LEVELS
PLUGIN_FAILURE_COUNT = config.PLUGIN_FAILURE_COUNT
INIT_LOCK = config.INIT_LOCK
INITIALIZED = config.INITIALIZED
FRAMEWORK_CONFIG_FILE = config.FRAMEWORK_CONFIG_FILE
logger = config.logger

# Re-export functions from config
FrameworkConfigReader = config.FrameworkConfigReader
PluginsAccessControlLoader = config.PluginsAccessControlLoader
AdminNotifier = config.AdminNotifier

# Re-export functions from database
DatabaseInitializer = database.DatabaseInitializer
Historian = database.Historian
HistoryParser = database.HistoryParser
SubprocessLibrarian = database.SubprocessLibrarian
SubprocessConfigReader = database.SubprocessConfigReader
SubprocessConfigWriter = database.SubprocessConfigWriter

# Re-export functions from plugin
CheckPluginAccess = plugin.CheckPluginAccess
CheckPluginPrivilege = plugin.CheckPluginPrivilege
SubprocessCrossOriginConfigReader = plugin.SubprocessCrossOriginConfigReader
SubprocessCrossOriginConfigWriter = plugin.SubprocessCrossOriginConfigWriter
SubprocessApiCaller = plugin.SubprocessApiCaller
PluginWorker = plugin.PluginWorker
PluginMonitor = plugin.PluginMonitor
PluginCallerSingle = plugin.PluginCallerSingle
PluginCaller = plugin.PluginCaller
RegistryInitializer = plugin.RegistryInitializer

# Re-export functions and Flask app from server
NAPCAT_LISTENER = server.NAPCAT_LISTENER
NapCatListener = server.NapCatListener
HealthCheck = server.HealthCheck
Initializer = server.Initializer
ActualInitializer = server.ActualInitializer
UnconditionalEventInitializer = server.UnconditionalEventInitializer
UnconditionalEventGenerator = server.UnconditionalEventGenerator
AdminDispatcher = server.AdminDispatcher
EventTypeParser = server.EventTypeParser
InbondMessageParser = server.InbondMessageParser
NapCatSender = server.NapCatSender
OutbondMessageParser = server.OutbondMessageParser
MainDispatcher = server.MainDispatcher

# If this file is run directly, start the server
if __name__ == '__main__':
    import sys
    try:
        logger.info(f"Starting Askr Framework on {config.CONFIG['NAPCAT_LISTEN']['host']}:{config.CONFIG['NAPCAT_LISTEN']['port']}")
        config.AdminNotifier('INFO', f"Starting Askr Framework on {config.CONFIG['NAPCAT_LISTEN']['host']}:{config.CONFIG['NAPCAT_LISTEN']['port']}")
        NAPCAT_LISTENER.run(host=config.CONFIG['NAPCAT_LISTEN']['host'], port=config.CONFIG['NAPCAT_LISTEN']['port'])
    except Exception as e:
        logger.critical(f"Failed to start HTTP server: {e}")
        config.AdminNotifier('CRITICAL', f"Failed to start HTTP server: {e}")
        sys.exit(1)
