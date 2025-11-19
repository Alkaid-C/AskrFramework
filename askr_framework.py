#!/usr/bin/env python3
"""
Askr Framework - QQ Bot Framework based on NapCat
A beginner-friendly framework with process isolation for stability

Version: Beta 0.3-rc1
License: GPL v3
"""

# ==================== IMPORTS ====================
import json
import os
import logging
import threading
import sys
import sqlite3
import time
import datetime
import importlib
import inspect
import multiprocessing
import queue
import requests
import resource  # type: ignore
import psutil  # type: ignore
from flask import Flask, request
from typing import Dict, List, Union, Optional, Any, Callable, Set


# ==================== CONSTANTS & GLOBALS ====================

# Global initialization control
INIT_LOCK = threading.Lock()
INITIALIZED = False

# Event types definition
EVENT_TYPES_ = [
    "MESSAGE_PRIVATE", "MESSAGE_GROUP", "MESSAGE_GROUP_MENTION", "MESSAGE_GROUP_BOT",
    "MESSAGE_SENT_PRIVATE", "MESSAGE_SENT_GROUP",
    "NOTICE_FRIEND_ADD", "NOTICE_FRIEND_RECALL", "NOTICE_GROUP_RECALL",
    "NOTICE_GROUP_INCREASE", "NOTICE_GROUP_DECREASE", "NOTICE_GROUP_ADMIN",
    "NOTICE_GROUP_BAN", "NOTICE_GROUP_UPLOAD", "NOTICE_GROUP_CARD",
    "NOTICE_GROUP_NAME", "NOTICE_GROUP_TITLE", "NOTICE_POKE", "NOTICE_PROFILE_LIKE",
    "NOTICE_INPUT_STATUS", "NOTICE_ESSENCE", "NOTICE_GROUP_MSG_EMOJI_LIKE",
    "NOTICE_BOT_OFFLINE",
    "REQUEST_FRIEND", "REQUEST_GROUP",
    "META_HEARTBEAT", "META_LIFECYCLE",
    "UNCONDITIONAL",
]

# Event inheritance relationships
EVENT_INHERITANCE = {
    "MESSAGE_GROUP_MENTION": ["MESSAGE_GROUP"],
    "MESSAGE_GROUP_BOT": ["MESSAGE_GROUP"],
}

# Plugin registries
PLUGIN_REGISTRY = {}  # type: Dict[str, list]

# Default configuration with sensible values for production use
CONFIG = {
    'NAPCAT_SERVER': {'api_url': 'http://localhost:19218'},
    'NAPCAT_LISTEN': {'host': 'localhost', 'port': 19219},
    'PATHS': {
        'plugins_dir': './plugins',
        'database_file': './EventHistory.db',
        'access_control': './PluginsAccessControl.json'
    },
    'HTTP': {
        'max_retries': 3,
        'timeout_seconds': 10,
        'status_check_timeout': 5
    },
    'PLUGIN_EXECUTION': {
        'max_cpu_time_seconds': 3.0,
        'max_wall_time_seconds': 30.0,
        'memory_limit_mb': 1024,
        'monitor_interval_seconds': 0.1,
        'process_creation_method': 'spawn'
    },
    'ADMIN_NOTIFICATION': {
        'enabled': True,
        'admin_qq': 0,
        'notify_level': 'WARNING',
        'message_format': 'Askr Alert \n[{level}] {time}\n{message}'
    },
    'REMOVE_FAILED_PLUGIN': {
        'enabled': True,
        'remove_by_consecutive_or_total_failure': 'consecutive',
        'count_to_remove': 5
    }
}

# Plugin access control rules
PLUGIN_ACCESS_RULES = {
    'version': '1.0',
    'default_policy': 'allow',
    'rules': {
        'global': {
            'private': {},
            'group': {},
            'privilege': False
        }
    }
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AskrFramework')

# Global state
IS_MUTED = False
LOGGING_LEVELS = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
PLUGIN_FAILURE_COUNT = {}
PLUGIN_FAILURE_LOCK = threading.Lock()  # Protects PLUGIN_FAILURE_COUNT updates

# Configuration file path
FRAMEWORK_CONFIG_FILE = './frameworkConfig.json'


# ==================== CONFIGURATION ====================

def AdminNotifier(messageLevel: str, message: str) -> None:
    """Send notification to administrator via QQ message."""
    if not CONFIG['ADMIN_NOTIFICATION']['enabled']:
        return

    if not CONFIG['ADMIN_NOTIFICATION']['admin_qq']:
        return

    # Check if message level meets threshold
    thresholdLevel = LOGGING_LEVELS[CONFIG['ADMIN_NOTIFICATION']['notify_level']]
    messageLevelNum = LOGGING_LEVELS[messageLevel]
    if messageLevelNum < thresholdLevel:
        return

    def AdminNotificationSender():
        """Send the actual notification."""
        try:
            formattedTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            notificationText = CONFIG['ADMIN_NOTIFICATION']['message_format'].format(
                level=messageLevel, time=formattedTime, message=message
            )
            adminQQ = CONFIG['ADMIN_NOTIFICATION']['admin_qq']
            requestBody = {
                "user_id": adminQQ,
                "message": [{"type": "text", "data": {"text": notificationText}}]
            }

            baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
            fullUrl = f"{baseUrl}/send_private_msg"

            response = requests.post(fullUrl, json=requestBody, timeout=5.0)
            success = (response.status_code == 200)

            if not success:
                logger.error(f"[AdminNotification] Failed to send notification: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"[AdminNotification] Exception while sending: {e}")

    # Execute in background thread
    thread = threading.Thread(target=AdminNotificationSender, daemon=True)
    thread.start()


def FrameworkConfigReader() -> None:
    """Read and validate framework configuration from JSON file."""
    global CONFIG

    configPath = FRAMEWORK_CONFIG_FILE
    if not os.path.exists(configPath) or not os.path.isfile(configPath):
        logger.warning(f"Configuration file {configPath} does not exist, using defaults")
        AdminNotifier('WARNING', f"Configuration file {configPath} does not exist, using defaults")
        return

    try:
        with open(configPath, 'r', encoding='utf-8') as configFile:
            fileConfig = json.load(configFile)

        logger.info(f"Loaded configuration from {configPath}")
        AdminNotifier('INFO', f"Loaded configuration from {configPath}")

        if 'version' in fileConfig:
            logger.info(f"Configuration version: {fileConfig['version']}")
            AdminNotifier('INFO', f"Configuration version: {fileConfig['version']}")

        # NAPCAT_SERVER section
        if 'NAPCAT_SERVER' in fileConfig and isinstance(fileConfig['NAPCAT_SERVER'], dict):
            if 'api_url' in fileConfig['NAPCAT_SERVER']:
                if isinstance(fileConfig['NAPCAT_SERVER']['api_url'], str):
                    CONFIG['NAPCAT_SERVER']['api_url'] = fileConfig['NAPCAT_SERVER']['api_url']
                else:
                    logger.critical(f"Configuration file contains invalid type for NAPCAT_SERVER.api_url, expected str")
                    AdminNotifier('CRITICAL', f"Configuration file contains invalid type for NAPCAT_SERVER.api_url, expected str")
                    sys.exit(1)

        # NAPCAT_LISTEN section
        if 'NAPCAT_LISTEN' in fileConfig and isinstance(fileConfig['NAPCAT_LISTEN'], dict):
            if 'host' in fileConfig['NAPCAT_LISTEN']:
                if isinstance(fileConfig['NAPCAT_LISTEN']['host'], str):
                    CONFIG['NAPCAT_LISTEN']['host'] = fileConfig['NAPCAT_LISTEN']['host']
                else:
                    logger.critical(f"Configuration file contains invalid type for NAPCAT_LISTEN.host, expected str")
                    AdminNotifier('CRITICAL', f"Configuration file contains invalid type for NAPCAT_LISTEN.host, expected str")
                    sys.exit(1)

            if 'port' in fileConfig['NAPCAT_LISTEN']:
                port = fileConfig['NAPCAT_LISTEN']['port']
                if isinstance(port, int) and 1 <= port <= 65535:
                    CONFIG['NAPCAT_LISTEN']['port'] = port
                else:
                    logger.critical(f"Configuration file contains invalid value for NAPCAT_LISTEN.port, must be int between 1-65535")
                    AdminNotifier('CRITICAL', f"Configuration file contains invalid value for NAPCAT_LISTEN.port, must be int between 1-65535")
                    sys.exit(1)

        # PATHS section
        if 'PATHS' in fileConfig and isinstance(fileConfig['PATHS'], dict):
            for key in ['plugins_dir', 'database_file', 'framework_config', 'access_control']:
                if key in fileConfig['PATHS']:
                    if isinstance(fileConfig['PATHS'][key], str):
                        CONFIG['PATHS'][key] = fileConfig['PATHS'][key]
                    else:
                        logger.critical(f"Configuration file contains invalid type for PATHS.{key}, expected str")
                        AdminNotifier('CRITICAL', f"Configuration file contains invalid type for PATHS.{key}, expected str")
                        sys.exit(1)

        # HTTP section
        if 'HTTP' in fileConfig and isinstance(fileConfig['HTTP'], dict):
            if 'max_retries' in fileConfig['HTTP']:
                if isinstance(fileConfig['HTTP']['max_retries'], int) and fileConfig['HTTP']['max_retries'] > 0:
                    CONFIG['HTTP']['max_retries'] = fileConfig['HTTP']['max_retries']
                else:
                    logger.error(f"Invalid value for HTTP.max_retries, must be positive int")
                    AdminNotifier('ERROR', f"Invalid value for HTTP.max_retries, must be positive int")

            for key in ['timeout_seconds', 'status_check_timeout']:
                if key in fileConfig['HTTP']:
                    value = fileConfig['HTTP'][key]
                    if isinstance(value, (int, float)) and value > 0:
                        CONFIG['HTTP'][key] = value
                    else:
                        logger.error(f"Invalid value for HTTP.{key}, must be positive number")
                        AdminNotifier('ERROR', f"Invalid value for HTTP.{key}, must be positive number")

        # PLUGIN_EXECUTION section
        if 'PLUGIN_EXECUTION' in fileConfig and isinstance(fileConfig['PLUGIN_EXECUTION'], dict):
            for key in ['max_cpu_time_seconds', 'max_wall_time_seconds', 'monitor_interval_seconds']:
                if key in fileConfig['PLUGIN_EXECUTION']:
                    value = fileConfig['PLUGIN_EXECUTION'][key]
                    if isinstance(value, (int, float)) and value > 0:
                        CONFIG['PLUGIN_EXECUTION'][key] = value
                        if value > 50:
                            logger.warning(f"PLUGIN_EXECUTION.{key} is set to more than 50 seconds, which may cause problems with UNCONDITIONAL events.")
                            AdminNotifier('WARNING', f"PLUGIN_EXECUTION.{key} is set to more than 50 seconds, which may cause problems with UNCONDITIONAL events.")
                    else:
                        logger.error(f"Invalid value for PLUGIN_EXECUTION.{key}, must be positive number")
                        AdminNotifier('ERROR', f"Invalid value for PLUGIN_EXECUTION.{key}, must be positive number")

            if 'memory_limit_mb' in fileConfig['PLUGIN_EXECUTION']:
                value = fileConfig['PLUGIN_EXECUTION']['memory_limit_mb']
                if isinstance(value, int) and value > 0:
                    CONFIG['PLUGIN_EXECUTION']['memory_limit_mb'] = value
                else:
                    logger.error(f"Invalid value for PLUGIN_EXECUTION.memory_limit_mb, must be positive int")
                    AdminNotifier('ERROR', f"Invalid value for PLUGIN_EXECUTION.memory_limit_mb, must be positive int")

            if 'process_creation_method' in fileConfig['PLUGIN_EXECUTION']:
                if isinstance(fileConfig['PLUGIN_EXECUTION']['process_creation_method'], str):
                    CONFIG['PLUGIN_EXECUTION']['process_creation_method'] = fileConfig['PLUGIN_EXECUTION']['process_creation_method']
                else:
                    logger.error(f"Invalid type for PLUGIN_EXECUTION.process_creation_method, expected str")
                    AdminNotifier('ERROR', f"Invalid type for PLUGIN_EXECUTION.process_creation_method, expected str")

        # ADMIN_NOTIFICATION section
        if 'ADMIN_NOTIFICATION' in fileConfig and isinstance(fileConfig['ADMIN_NOTIFICATION'], dict):
            if 'enabled' in fileConfig['ADMIN_NOTIFICATION']:
                if isinstance(fileConfig['ADMIN_NOTIFICATION']['enabled'], bool):
                    CONFIG['ADMIN_NOTIFICATION']['enabled'] = fileConfig['ADMIN_NOTIFICATION']['enabled']
                else:
                    logger.error(f"Invalid type for ADMIN_NOTIFICATION.enabled, expected bool")
                    AdminNotifier('ERROR', f"Invalid type for ADMIN_NOTIFICATION.enabled, expected bool")

            if 'admin_qq' in fileConfig['ADMIN_NOTIFICATION']:
                value = fileConfig['ADMIN_NOTIFICATION']['admin_qq']
                if isinstance(value, int) and value >= 0:
                    CONFIG['ADMIN_NOTIFICATION']['admin_qq'] = value
                elif isinstance(value, str) and value.isdigit() and int(value) >= 0:
                    CONFIG['ADMIN_NOTIFICATION']['admin_qq'] = int(value)
                else:
                    CONFIG['ADMIN_NOTIFICATION']['enabled'] = False
                    logger.error(f"Invalid value for ADMIN_NOTIFICATION.admin_qq, must be non-negative int or string representation")
                    AdminNotifier('ERROR', f"Invalid value for ADMIN_NOTIFICATION.admin_qq, must be non-negative int or string representation")

            if 'notify_level' in fileConfig['ADMIN_NOTIFICATION']:
                if isinstance(fileConfig['ADMIN_NOTIFICATION']['notify_level'], str):
                    CONFIG['ADMIN_NOTIFICATION']['notify_level'] = fileConfig['ADMIN_NOTIFICATION']['notify_level']
                else:
                    logger.warning(f"Invalid type for ADMIN_NOTIFICATION.notify_level, expected str")
                    AdminNotifier('WARNING', f"Invalid type for ADMIN_NOTIFICATION.notify_level, expected str")

            if 'rate_limit_seconds' in fileConfig['ADMIN_NOTIFICATION']:
                logger.warning(f"admin notification rate limit is deprecated. Use remove failed feature instead")
                AdminNotifier('WARNING', f"admin notification rate limit is deprecated. Use remove failed feature instead")

            if 'message_format' in fileConfig['ADMIN_NOTIFICATION']:
                if isinstance(fileConfig['ADMIN_NOTIFICATION']['message_format'], str):
                    CONFIG['ADMIN_NOTIFICATION']['message_format'] = fileConfig['ADMIN_NOTIFICATION']['message_format']
                else:
                    logger.warning(f"Invalid type for ADMIN_NOTIFICATION.message_format, expected str")
                    AdminNotifier('WARNING', f"Invalid type for ADMIN_NOTIFICATION.message_format, expected str")

        # REMOVE_FAILED_PLUGIN section
        if 'REMOVE_FAILED_PLUGIN' in fileConfig and isinstance(fileConfig['REMOVE_FAILED_PLUGIN'], dict):
            if 'enabled' in fileConfig['REMOVE_FAILED_PLUGIN']:
                if isinstance(fileConfig['REMOVE_FAILED_PLUGIN']['enabled'], bool):
                    CONFIG['REMOVE_FAILED_PLUGIN']['enabled'] = fileConfig['REMOVE_FAILED_PLUGIN']['enabled']
                else:
                    logger.warning(f"Invalid type for REMOVE_FAILED_PLUGIN.enabled, expected bool")
                    AdminNotifier('WARNING', f"Invalid type for REMOVE_FAILED_PLUGIN.enabled, expected bool")
            if 'remove_by_consecutive_or_total_failure' in fileConfig['REMOVE_FAILED_PLUGIN']:
                if fileConfig['REMOVE_FAILED_PLUGIN']['remove_by_consecutive_or_total_failure'] in ['consecutive', 'total']:
                    CONFIG['REMOVE_FAILED_PLUGIN']['remove_by_consecutive_or_total_failure'] = fileConfig['REMOVE_FAILED_PLUGIN']['remove_by_consecutive_or_total_failure']
                else:
                    logger.warning(f"Invalid type for REMOVE_FAILED_PLUGIN.remove_by_consecutive_or_total_failure, expected string 'consecutive' or 'total'")
                    AdminNotifier('WARNING', f"Invalid type for REMOVE_FAILED_PLUGIN.remove_by_consecutive_or_total_failure, expected string 'consecutive' or 'total'")
            if 'count_to_remove' in fileConfig['REMOVE_FAILED_PLUGIN']:
                if isinstance(fileConfig['REMOVE_FAILED_PLUGIN']['count_to_remove'], int) and fileConfig['REMOVE_FAILED_PLUGIN']['count_to_remove'] >= 1:
                    CONFIG['REMOVE_FAILED_PLUGIN']['count_to_remove'] = fileConfig['REMOVE_FAILED_PLUGIN']['count_to_remove']
                else:
                    logger.warning(f"Invalid type for REMOVE_FAILED_PLUGIN.count_to_remove, expected int >= 1")
                    AdminNotifier('WARNING', f"Invalid type for REMOVE_FAILED_PLUGIN.count_to_remove, expected int >= 1")

        # Ensure directories exist
        for key, value in CONFIG['PATHS'].items():
            if key.endswith('_dir') and not os.path.exists(value):
                os.makedirs(value)
                logger.info(f"Created directory: {value}")
                AdminNotifier('INFO', f"Created directory: {value}")

        logger.info("Configuration loading completed successfully")
        AdminNotifier('INFO', "Configuration loading completed successfully")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse configuration file: {e}\n Check if the file is valid JSON. Using default configuration due to parse error")
        AdminNotifier('ERROR', f"Failed to parse configuration file: {e}\n Check if the file is valid JSON. Using default configuration due to parse error")
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}\n Check file permissions and format. Using default configuration due to read error")
        AdminNotifier('ERROR', f"Error reading configuration file: {e}\n Check file permissions and format. Using default configuration due to read error")


def PluginsAccessControlLoader() -> None:
    """Load plugin access control rules from JSON file."""
    global PLUGIN_ACCESS_RULES

    configPath = CONFIG['PATHS']['access_control']

    if not os.path.exists(configPath):
        logger.info(f"No access control file found at {configPath}, using default (allow all)")
        AdminNotifier('INFO', f"No access control file found at {configPath}, using default (allow all)")
        return

    try:
        with open(configPath, 'r', encoding='utf-8') as ruleFile:
            fileRules = json.load(ruleFile)

        # Validate structure
        if not isinstance(fileRules, dict):
            logger.error("Access control file must be a JSON object, using defaults")
            AdminNotifier('ERROR', "Access control file must be a JSON object, using defaults")
            return

        if 'version' in fileRules:
            logger.info(f"Access control version: {fileRules['version']}")
            AdminNotifier('INFO', f"Access control version: {fileRules['version']}")

        # Validate default policy
        if 'default_policy' in fileRules:
            if fileRules['default_policy'] not in ['allow', 'deny']:
                logger.warning(f"Invalid default_policy '{fileRules['default_policy']}', using 'allow'")
                AdminNotifier('WARNING', f"Invalid default_policy '{fileRules['default_policy']}', using 'allow'")
                fileRules['default_policy'] = 'allow'

        # Validate rules
        if 'rules' in fileRules and isinstance(fileRules['rules'], dict):
            validatedRules = {}

            # Ensure global rule exists with defaults
            if 'global' not in fileRules['rules']:
                validatedRules['global'] = {
                    'private': {},
                    'group': {},
                    'privilege': False
                }

            for pluginName, localRules in fileRules['rules'].items():
                if not isinstance(localRules, dict):
                    logger.warning(f"Invalid rules for plugin '{pluginName}', skipping")
                    AdminNotifier('WARNING', f"Invalid rules for plugin '{pluginName}', skipping")
                    continue

                validatedLocalRules = {}

                # Validate private rules
                if 'private' in localRules and isinstance(localRules['private'], dict):
                    privateRules = {}
                    if 'WhiteList' in localRules['private'] and 'BlackList' in localRules['private']:
                        logger.warning(f"Plugin '{pluginName}' has both WhiteList and BlackList in private rules, using only WhiteList")
                        AdminNotifier('WARNING', f"Plugin '{pluginName}' has both WhiteList and BlackList in private rules, using only WhiteList")
                    if 'WhiteList' in localRules['private']:
                        if isinstance(localRules['private']['WhiteList'], list):
                            privateRules['WhiteList'] = set(
                                id for id in localRules['private']['WhiteList']
                                if isinstance(id, int) and id > 0
                            )
                    elif 'BlackList' in localRules['private']:
                        if isinstance(localRules['private']['BlackList'], list):
                            privateRules['BlackList'] = set(
                                id for id in localRules['private']['BlackList']
                                if isinstance(id, int) and id > 0
                            )
                    validatedLocalRules['private'] = privateRules
                else:
                    validatedLocalRules['private'] = {}

                # Validate group rules
                if 'group' in localRules and isinstance(localRules['group'], dict):
                    groupRules = {}
                    if 'WhiteList' in localRules['group'] and 'BlackList' in localRules['group']:
                        logger.warning(f"Plugin '{pluginName}' has both WhiteList and BlackList in group rules, using only WhiteList")
                        AdminNotifier('WARNING', f"Plugin '{pluginName}' has both WhiteList and BlackList in group rules, using only WhiteList")
                    if 'WhiteList' in localRules['group']:
                        if isinstance(localRules['group']['WhiteList'], list):
                            groupRules['WhiteList'] = set(
                                id for id in localRules['group']['WhiteList']
                                if isinstance(id, int) and id > 0
                            )
                    elif 'BlackList' in localRules['group']:
                        if isinstance(localRules['group']['BlackList'], list):
                            groupRules['BlackList'] = set(
                                id for id in localRules['group']['BlackList']
                                if isinstance(id, int) and id > 0
                            )
                    validatedLocalRules['group'] = groupRules
                else:
                    validatedLocalRules['group'] = {}

                # Validate privilege
                if 'privilege' in localRules:
                    if isinstance(localRules['privilege'], bool):
                        validatedLocalRules['privilege'] = localRules['privilege']
                    else:
                        logger.warning(f"Invalid privilege value for plugin '{pluginName}', expected bool")
                        AdminNotifier('WARNING', f"Invalid privilege value for plugin '{pluginName}', expected bool")

                validatedRules[pluginName] = validatedLocalRules

            fileRules['rules'] = validatedRules

        PLUGIN_ACCESS_RULES = fileRules
        logger.info(f"Loaded access control rules for {len(fileRules.get('rules', {}))} plugins")
        AdminNotifier('INFO', f"Loaded access control rules for {len(fileRules.get('rules', {}))} plugins")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse access control file: {e}")
        AdminNotifier('ERROR', f"Failed to parse access control file: {e}")
    except Exception as e:
        logger.error(f"Error reading access control file: {e}")
        AdminNotifier('ERROR', f"Error reading access control file: {e}")


# ==================== DATABASE ====================

def DatabaseInitializer() -> None:
    """Initialize SQLite database with required tables and indexes."""
    dbPath = CONFIG['PATHS']['database_file']

    try:
        databaseConnect = sqlite3.connect(dbPath, check_same_thread=False)
        databaseConnect.execute("PRAGMA journal_mode=WAL")  # Better concurrent access

        # Friend events table
        databaseConnect.execute("""
            CREATE TABLE IF NOT EXISTS FRIEND_EVENTS (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                USER_ID INTEGER NOT NULL,
                EVENT_TYPE TEXT NOT NULL,
                EVENT_DATA TEXT NOT NULL,
                TIMESTAMP INTEGER NOT NULL
            )
        """)
        databaseConnect.execute("""
            CREATE INDEX IF NOT EXISTS IDX_FRIEND_USER
            ON FRIEND_EVENTS(USER_ID, TIMESTAMP DESC)
        """)

        # Group events table
        databaseConnect.execute("""
            CREATE TABLE IF NOT EXISTS GROUP_EVENTS (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                GROUP_ID INTEGER NOT NULL,
                USER_ID INTEGER,
                EVENT_TYPE TEXT NOT NULL,
                EVENT_DATA TEXT NOT NULL,
                TIMESTAMP INTEGER NOT NULL
            )
        """)
        databaseConnect.execute("""
            CREATE INDEX IF NOT EXISTS IDX_GROUP_ID
            ON GROUP_EVENTS(GROUP_ID, TIMESTAMP DESC)
        """)
        databaseConnect.execute("""
            CREATE INDEX IF NOT EXISTS IDX_GROUP_USER
            ON GROUP_EVENTS(GROUP_ID, USER_ID, TIMESTAMP DESC)
        """)

        # Other events table
        databaseConnect.execute("""
            CREATE TABLE IF NOT EXISTS OTHER_EVENTS (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                EVENT_TYPE TEXT NOT NULL,
                EVENT_DATA TEXT NOT NULL,
                TIMESTAMP INTEGER NOT NULL
            )
        """)
        databaseConnect.execute("""
            CREATE INDEX IF NOT EXISTS IDX_OTHER_TYPE
            ON OTHER_EVENTS(EVENT_TYPE, TIMESTAMP DESC)
        """)

        # Plugin configs table
        databaseConnect.execute("""
            CREATE TABLE IF NOT EXISTS PLUGIN_CONFIGS (
                PLUGIN_NAME TEXT PRIMARY KEY,
                CONFIG_DATA TEXT NOT NULL,
                CREATED_AT INTEGER NOT NULL,
                UPDATED_AT INTEGER NOT NULL
            )
        """)

        databaseConnect.commit()
        databaseConnect.close()

        logger.info(f"Database initialized successfully at {dbPath}")
        AdminNotifier('INFO', f"Database initialized successfully at {dbPath}")

    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        AdminNotifier('CRITICAL', f"Failed to initialize database: {e}")
        sys.exit(1)


def Historian(rawEvent: Dict, eventType: str) -> None:
    """Save event to database for historical queries."""

    # Skip high-frequency useless events
    if eventType == "NOTICE_INPUT_STATUS":
        return

    timestamp = int(time.time())
    eventData = json.dumps(rawEvent, ensure_ascii=False)

    tableName = None
    insertSql = None
    insertParams = None

    # Classify events into appropriate tables
    if eventType in ["MESSAGE_PRIVATE", "NOTICE_FRIEND_RECALL", "NOTICE_FRIEND_ADD", "NOTICE_PROFILE_LIKE"]:
        userId = rawEvent.get("user_id")
        if userId:
            tableName = "FRIEND_EVENTS"
            insertSql = "INSERT INTO FRIEND_EVENTS (USER_ID, EVENT_TYPE, EVENT_DATA, TIMESTAMP) VALUES (?, ?, ?, ?)"
            insertParams = (userId, eventType, eventData, timestamp)

    elif eventType in ["MESSAGE_GROUP", "MESSAGE_GROUP_MENTION", "MESSAGE_GROUP_BOT",
                      "NOTICE_GROUP_RECALL", "NOTICE_GROUP_INCREASE",
                      "NOTICE_GROUP_DECREASE", "NOTICE_GROUP_ADMIN", "NOTICE_GROUP_BAN",
                      "NOTICE_GROUP_UPLOAD", "NOTICE_GROUP_CARD", "NOTICE_ESSENCE",
                      "NOTICE_GROUP_MSG_EMOJI_LIKE", "NOTICE_GROUP_NAME", "NOTICE_GROUP_TITLE"]:
        groupId = rawEvent.get("group_id")
        if groupId:
            userId = rawEvent.get("user_id")
            tableName = "GROUP_EVENTS"
            insertSql = "INSERT INTO GROUP_EVENTS (GROUP_ID, USER_ID, EVENT_TYPE, EVENT_DATA, TIMESTAMP) VALUES (?, ?, ?, ?, ?)"
            insertParams = (groupId, userId, eventType, eventData, timestamp)

    elif eventType == "NOTICE_POKE":
        # POKE can be in group or private
        groupId = rawEvent.get("group_id")
        userId = rawEvent.get("user_id")
        if groupId:
            tableName = "GROUP_EVENTS"
            insertSql = "INSERT INTO GROUP_EVENTS (GROUP_ID, USER_ID, EVENT_TYPE, EVENT_DATA, TIMESTAMP) VALUES (?, ?, ?, ?, ?)"
            insertParams = (groupId, userId, eventType, eventData, timestamp)
        elif userId:
            tableName = "FRIEND_EVENTS"
            insertSql = "INSERT INTO FRIEND_EVENTS (USER_ID, EVENT_TYPE, EVENT_DATA, TIMESTAMP) VALUES (?, ?, ?, ?)"
            insertParams = (userId, eventType, eventData, timestamp)

    # Default: OTHER_EVENTS
    else:
        tableName = "OTHER_EVENTS"
        insertSql = "INSERT INTO OTHER_EVENTS (EVENT_TYPE, EVENT_DATA, TIMESTAMP) VALUES (?, ?, ?)"
        insertParams = (eventType, eventData, timestamp)

    dbPath = CONFIG['PATHS']['database_file']
    maxRetries = 3

    for attempt in range(maxRetries):
        databaseConnect = None
        try:
            databaseConnect = sqlite3.connect(dbPath, timeout=10.0)
            databaseConnect.execute(insertSql, insertParams)
            databaseConnect.commit()
            return

        except sqlite3.OperationalError as e:
            logger.warning(f"Historian attempt {attempt + 1}/{maxRetries} failed for {tableName}: {e}")
            AdminNotifier('WARNING', f"Historian attempt {attempt + 1}/{maxRetries} failed for {tableName}: {e}")
            if attempt < maxRetries - 1:
                time.sleep(1)
            else:
                logger.error(f"Historian failed after {maxRetries} attempts for {tableName}: {e}")
                AdminNotifier('ERROR', f"Historian failed after {maxRetries} attempts for {tableName}: {e}")

        except Exception as e:
            logger.error(f"Historian database error for {tableName}: {e}")
            AdminNotifier('ERROR', f"Historian database error for {tableName}: {e}")
            return

        finally:
            if databaseConnect:
                try:
                    databaseConnect.close()
                except Exception as e:
                    logger.warning(f"Historian: Failed to close database connection: {e}")
                    AdminNotifier('WARNING', f"Historian: Failed to close database connection: {e}")


def HistoryParser(events: List[Dict]) -> str:
    """Parse event history into a formatted string."""
    lines = []
    for event in events:
        event_type = event.get('post_type', 'unknown')
        timestamp = event.get('time', 0)
        time_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        if event_type == 'message':
            userID = event.get('user_id', 'unknown')
            message = event.get('raw_message', '')
            lines.append(f"[{time_str}] User {userID}: {message}")
        else:
            lines.append(f"[{time_str}] Event: {event_type}")

    return '\n'.join(lines)


def SubprocessLibrarian(
    eventIdentifier: Dict,
    eventCount: int = 50,
    interval: Optional[int] = None,
    intervalMaxCount: int = 2047,
    stringOutput: bool = False
) -> Union[List[Dict], str]:
    """Query event history from database (subprocess version)."""
    dbPath = CONFIG['PATHS']['database_file']
    databaseConnect = None

    try:
        databaseConnect = sqlite3.connect(dbPath, timeout=5.0)
        databaseConnect.execute("PRAGMA query_only = ON")
        cursor = databaseConnect.cursor()

        identifierType = eventIdentifier.get("type")

        # Prepare base query based on identifier type
        base_query = None
        query_params = None

        match identifierType:
            case "private":
                userId = eventIdentifier.get("user_id")
                if not userId:
                    return [] if not stringOutput else ""
                base_query = "SELECT EVENT_DATA, TIMESTAMP FROM FRIEND_EVENTS WHERE USER_ID = ?"
                query_params = [userId]

            case "group":
                groupId = eventIdentifier.get("group_id")
                if not groupId:
                    return [] if not stringOutput else ""
                base_query = "SELECT EVENT_DATA, TIMESTAMP FROM GROUP_EVENTS WHERE GROUP_ID = ?"
                query_params = [groupId]

            case "other":
                eventType = eventIdentifier.get("event_type")
                if not eventType:
                    return [] if not stringOutput else ""
                base_query = "SELECT EVENT_DATA, TIMESTAMP FROM OTHER_EVENTS WHERE EVENT_TYPE = ?"
                query_params = [eventType]

            case _:
                return [] if not stringOutput else ""

        # Handle interval parameter with binary search
        if interval is not None:
            current_time = int(time.time())
            cutoff_time = current_time - interval

            # Binary search approach to avoid loading too much data at once
            fetch_count = 1
            events = []
            oldest_timestamp = current_time

            while fetch_count <= intervalMaxCount:
                # Query with limit
                query = f"{base_query} ORDER BY TIMESTAMP DESC LIMIT ?"
                cursor.execute(query, query_params + [fetch_count])
                rows = cursor.fetchall()

                if not rows:
                    break

                # Check oldest timestamp
                oldest_timestamp = rows[-1][1]  # TIMESTAMP is second column

                # If oldest message is within interval, we might need more
                if oldest_timestamp >= cutoff_time:
                    # Store current results
                    events = rows

                    # If we got fewer rows than requested, we have all messages
                    if len(rows) < fetch_count:
                        break

                    # Double the fetch count for next iteration
                    fetch_count = min(fetch_count * 2, intervalMaxCount)
                else:
                    # We've gone too far, use stored results and filter
                    if not events:
                        events = rows
                    break

            # Filter events by timestamp and apply count limit
            filtered_events = []
            for row in events:
                timestamp = row[1]
                if timestamp >= cutoff_time:
                    filtered_events.append(row)
                    if eventCount > 0 and len(filtered_events) >= eventCount:
                        break

            rows = filtered_events

        else:
            # Original behavior without interval
            if eventCount == 0:
                cursor.execute(f"{base_query} ORDER BY TIMESTAMP DESC", query_params)
            else:
                cursor.execute(f"{base_query} ORDER BY TIMESTAMP DESC LIMIT ?", query_params + [eventCount])
            rows = cursor.fetchall()

        # Parse events
        events = []
        for i, row in enumerate(rows):
            try:
                event = json.loads(row[0])  # EVENT_DATA is first column
                events.append(event)
            except json.JSONDecodeError as e:
                logger.warning(f"SubprocessLibrarian: Corrupted JSON data in database record {i+1}/{len(rows)}, skipping: {e}")
                AdminNotifier('WARNING', f"SubprocessLibrarian: Corrupted JSON data in database record {i+1}/{len(rows)}, skipping: {e}")
                continue

        events.reverse()  # Return chronological order

        if stringOutput:
            return HistoryParser(events)
        else:
            return events

    except Exception as e:
        logger.error(f"SubprocessLibrarian error: {e}")
        AdminNotifier('ERROR', f"SubprocessLibrarian error: {e}")
        return [] if not stringOutput else ""
    finally:
        if databaseConnect:
            try:
                databaseConnect.close()
            except Exception as e:
                logger.warning(f"SubprocessLibrarian: Failed to close database connection: {e}")
                AdminNotifier('WARNING', f"SubprocessLibrarian: Failed to close database connection: {e}")


def SubprocessConfigReader(pluginName: str) -> Dict:
    """Read plugin configuration from database (subprocess version)."""
    dbPath = CONFIG['PATHS']['database_file']
    databaseConnect = None

    try:
        databaseConnect = sqlite3.connect(dbPath, timeout=5.0)
        databaseConnect.execute("PRAGMA query_only = ON")  # Read-only mode for safety
        cursor = databaseConnect.cursor()

        cursor.execute("""
            SELECT CONFIG_DATA FROM PLUGIN_CONFIGS
            WHERE PLUGIN_NAME = ?
        """, (pluginName,))

        row = cursor.fetchone()

        if row:
            try:
                config_data = json.loads(row[0])
                return config_data
            except json.JSONDecodeError as e:
                logger.error(f"ConfigReader: Invalid JSON for plugin {pluginName}: {e}")
                AdminNotifier('ERROR', f"ConfigReader: Invalid JSON for plugin {pluginName}: {e}")
                return {}
        else:
            return {}

    except Exception as e:
        logger.error(f"SubprocessConfigReader error for plugin {pluginName}: {e}")
        AdminNotifier('ERROR', f"SubprocessConfigReader error for plugin {pluginName}: {e}")
        return {}

    finally:
        if databaseConnect:
            try:
                databaseConnect.close()
            except Exception as e:
                logger.warning(f"SubprocessConfigReader: Failed to close database connection: {e}")
                AdminNotifier('WARNING', f"SubprocessConfigReader: Failed to close database connection: {e}")


def SubprocessConfigWriter(pluginName: str, config_data: Dict) -> None:
    """Write plugin configuration to database (subprocess version)."""
    dbPath = CONFIG['PATHS']['database_file']

    if not isinstance(config_data, dict):
        logger.error(f"ConfigWriter: config must be a dict, got {type(config_data)} for plugin {pluginName}")
        AdminNotifier('ERROR', f"ConfigWriter: config must be a dict, got {type(config_data)} for plugin {pluginName}")
        return

    try:
        configDataJson = json.dumps(config_data, ensure_ascii=False)
        timestamp = int(time.time())

        maxRetries = 3
        for attempt in range(maxRetries):
            databaseConnect = None
            try:
                databaseConnect = sqlite3.connect(dbPath, timeout=10.0)

                # UPSERT: preserve created_at, update updated_at
                databaseConnect.execute("""
                    INSERT OR REPLACE INTO PLUGIN_CONFIGS
                    (PLUGIN_NAME, CONFIG_DATA, CREATED_AT, UPDATED_AT)
                    VALUES (
                        ?,
                        ?,
                        COALESCE((SELECT CREATED_AT FROM PLUGIN_CONFIGS WHERE PLUGIN_NAME = ?), ?),
                        ?
                    )
                """, (pluginName, configDataJson, pluginName, timestamp, timestamp))

                databaseConnect.commit()
                return

            except sqlite3.OperationalError as e:
                logger.warning(f"ConfigWriter attempt {attempt + 1}/{maxRetries} failed for plugin {pluginName}: {e}")
                AdminNotifier('WARNING', f"ConfigWriter attempt {attempt + 1}/{maxRetries} failed for plugin {pluginName}: {e}")
                if attempt < maxRetries - 1:
                    time.sleep(1)
                else:
                    logger.error(f"ConfigWriter failed after {maxRetries} attempts for plugin {pluginName}: {e}")
                    AdminNotifier('ERROR', f"ConfigWriter failed after {maxRetries} attempts for plugin {pluginName}: {e}")

            except Exception as e:
                logger.error(f"ConfigWriter database error for plugin {pluginName}: {e}")
                AdminNotifier('ERROR', f"ConfigWriter database error for plugin {pluginName}: {e}")
                return

            finally:
                if databaseConnect:
                    try:
                        databaseConnect.close()
                    except Exception as e:
                        logger.warning(f"SubprocessConfigWriter: Failed to close database connection: {e}")
                        AdminNotifier('WARNING', f"SubprocessConfigWriter: Failed to close database connection: {e}")

    except (TypeError, ValueError) as e:
        logger.error(f"ConfigWriter: Failed to serialize config for plugin {pluginName}: {e}")
        AdminNotifier('ERROR', f"ConfigWriter: Failed to serialize config for plugin {pluginName}: {e}")


# ==================== PLUGIN MANAGEMENT ====================

def CheckPluginAccess(handler: Callable, rawEvent: Dict) -> bool:
    """Check if a plugin handler has access to the event."""
    pluginName = handler.pluginName

    groupID = rawEvent.get('group_id')

    # Get rules
    default_policy = PLUGIN_ACCESS_RULES.get('default_policy', 'allow')
    all_rules = PLUGIN_ACCESS_RULES.get('rules', {})

    # Determine event context (private or group)
    if groupID:
        context = 'group'
        contextID = groupID
    else:
        context = 'private'
        contextID = rawEvent.get('user_id', 0)

    def ListChecker(rules: Dict, contextID: int) -> Optional[bool]:
        """Check whitelist/blacklist. Returns True=allow, False=deny, None=no match."""
        whitelist_ = rules.get('WhiteList', set())
        blacklist_ = rules.get('BlackList', set())

        # Whitelist takes precedence
        if whitelist_:
            if contextID in whitelist_:
                return True
            else:
                return False  # Not in whitelist
        elif blacklist_:
            if contextID in blacklist_:
                return False
            else:
                return True  # Not in blacklist
        else:
            return None  # No match

    # Check plugin-specific rules
    if pluginName in all_rules:
        localRules = all_rules[pluginName].get(context, {})
        result = ListChecker(localRules, contextID)
        if result is not None:
            if not result:
                logger.debug(f"Plugin {pluginName} is not activated by specific rules for {context} {contextID}")
                AdminNotifier('DEBUG', f"Plugin {pluginName} is not activated by specific rules for {context} {contextID}")
            return result

    # Then Check global rules
    if 'global' in all_rules:
        global_rules = all_rules['global'].get(context, {})
        result = ListChecker(global_rules, contextID)
        if result is not None:
            if not result:  # Explicitly denied by global rules
                logger.debug(f"Plugin {pluginName} is not activated by global rules for {context} {contextID}")
                AdminNotifier('DEBUG', f"Plugin {pluginName} is not activated by global rules for {context} {contextID}")
            return result

    # Apply default policy
    return default_policy == 'allow'


def CheckPluginPrivilege(pluginName: str) -> bool:
    """Check if a plugin has cross-origin config access privilege."""
    if not pluginName.endswith('.py'):
        pluginName += '.py'

    all_rules = PLUGIN_ACCESS_RULES.get('rules', {})

    # Check plugin-specific privilege
    if pluginName in all_rules:
        localRules = all_rules[pluginName]
        if 'privilege' in localRules:
            return localRules['privilege']

    # Fall back to global default
    global_rules = all_rules.get('global', {})
    return global_rules.get('privilege', False)


def UpdateFailureCount(pluginName: str, success: bool) -> None:
    """
    Update plugin failure count and remove plugin if threshold exceeded.

    Args:
        pluginName: Name of the plugin (e.g., "plugin.py")
        success: True if plugin succeeded, False if failed
    """
    # Fast exit if feature disabled
    if not CONFIG['REMOVE_FAILED_PLUGIN']['enabled']:
        return

    if success:
        # Fast path: Check if count exists and is non-zero (no lock needed)
        if pluginName not in PLUGIN_FAILURE_COUNT:
            return  # Never failed, nothing to reset

        if PLUGIN_FAILURE_COUNT[pluginName]["consecutive"] == 0:
            return  # Already at 0, nothing to do

        # Slow path: Reset consecutive count
        with PLUGIN_FAILURE_LOCK:
            if pluginName in PLUGIN_FAILURE_COUNT:
                PLUGIN_FAILURE_COUNT[pluginName]["consecutive"] = 0

    else:  # Failure
        with PLUGIN_FAILURE_LOCK:
            # Initialize if first failure
            if pluginName not in PLUGIN_FAILURE_COUNT:
                PLUGIN_FAILURE_COUNT[pluginName] = {"consecutive": 0, "total": 0}

            # Increment counters
            PLUGIN_FAILURE_COUNT[pluginName]["consecutive"] += 1
            PLUGIN_FAILURE_COUNT[pluginName]["total"] += 1

            # Check removal threshold
            mode = CONFIG['REMOVE_FAILED_PLUGIN']['remove_by_consecutive_or_total_failure']
            threshold = CONFIG['REMOVE_FAILED_PLUGIN']['count_to_remove']
            count = PLUGIN_FAILURE_COUNT[pluginName][mode]

            if count >= threshold:
                logger.error(f"Plugin {pluginName} reached {count} {mode} failures (threshold: {threshold}), removing all handlers")
                AdminNotifier('ERROR', f"Plugin {pluginName} reached {count} {mode} failures (threshold: {threshold}), removing all handlers")
                RemoveFailedPlugin(pluginName)


def RemoveFailedPlugin(pluginName: str) -> None:
    """
    Remove all handlers for a failed plugin from PLUGIN_REGISTRY.

    Note: Does NOT remove from PLUGIN_FAILURE_COUNT - that serves as historical record.
    Counter dict can be inspected to see which plugins have been removed and why.

    Args:
        pluginName: Name of the plugin to remove (e.g., "plugin.py")
    """
    removed_count = 0

    for eventType in list(PLUGIN_REGISTRY.keys()):
        oldList = PLUGIN_REGISTRY[eventType]
        newList = []

        for entry in oldList:
            # Handle both regular handlers and UNCONDITIONAL tuples (handler, interval)
            handler = entry[0] if isinstance(entry, tuple) else entry
            if getattr(handler, 'pluginName', None) != pluginName:
                newList.append(entry)
            else:
                removed_count += 1

        # Atomic list replacement - safe for concurrent reads
        PLUGIN_REGISTRY[eventType] = newList

    logger.error(f"Removed {removed_count} handlers for failed plugin: {pluginName}")
    AdminNotifier('ERROR', f"Removed {removed_count} handlers for failed plugin: {pluginName}")


def SubprocessCrossOriginConfigReader(caller_plugin: str, target_plugin: str) -> Union[Dict, None]:
    """Read another plugin's configuration with privilege check."""
    # Check if caller has privilege
    if not CheckPluginPrivilege(caller_plugin):
        logger.warning(f"Plugin {caller_plugin} attempted cross-origin config read without privilege")
        AdminNotifier('WARNING', f"Plugin {caller_plugin} attempted cross-origin config read without privilege")
        return None

    logger.info(f"Plugin {caller_plugin} is reading config of plugin {target_plugin}")
    AdminNotifier('INFO', f"Plugin {caller_plugin} is reading config of plugin {target_plugin}")

    return SubprocessConfigReader(target_plugin)


def SubprocessCrossOriginConfigWriter(caller_plugin: str, target_plugin: str, config_data: Dict) -> Union[bool, None]:
    """Write another plugin's configuration with privilege check."""
    # Check if caller has privilege
    if not CheckPluginPrivilege(caller_plugin):
        logger.warning(f"Plugin {caller_plugin} attempted cross-origin config write without privilege")
        AdminNotifier('WARNING', f"Plugin {caller_plugin} attempted cross-origin config write without privilege")
        return None

    logger.info(f"Plugin {caller_plugin} is writing config of plugin {target_plugin}")
    AdminNotifier('INFO', f"Plugin {caller_plugin} is writing config of plugin {target_plugin}")

    SubprocessConfigWriter(target_plugin, config_data)
    return True


def SubprocessApiCaller(caller_plugin: str, action: str, data: Dict) -> Union[Dict, None]:
    """Call NapCat API from subprocess with privilege check."""
    # Check if caller has privilege
    if not CheckPluginPrivilege(caller_plugin):
        logger.warning(f"Plugin {caller_plugin} attempted API call without privilege: {action}")
        AdminNotifier('WARNING', f"Plugin {caller_plugin} attempted API call without privilege: {action}")
        return None

    logger.info(f"Plugin {caller_plugin} is calling API: {action}")
    AdminNotifier('INFO', f"Plugin {caller_plugin} is calling API: {action}")

    if not isinstance(action, str) or not action:
        logger.error("ApiCaller: action must be non-empty string")
        AdminNotifier('ERROR', "ApiCaller: action must be non-empty string")
        return None

    if not isinstance(data, dict):
        logger.error("ApiCaller: data must be dict")
        AdminNotifier('ERROR', "ApiCaller: data must be dict")
        return None

    baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
    fullUrl = f"{baseUrl}/{action}"

    try:
        response = requests.post(fullUrl, json=data, timeout=5.0)

        if response.status_code == 200:
            try:
                responseData = response.json()
                return responseData
            except json.JSONDecodeError as e:
                logger.error(f"ApiCaller: Invalid JSON response from {action}: {e}")
                AdminNotifier('ERROR', f"ApiCaller: Invalid JSON response from {action}: {e}")
                return None
        else:
            logger.error(f"ApiCaller: HTTP {response.status_code} from {action}")
            AdminNotifier('ERROR', f"ApiCaller: HTTP {response.status_code} from {action}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"ApiCaller: Timeout for {action}")
        AdminNotifier('ERROR', f"ApiCaller: Timeout for {action}")
        return None

    except Exception as e:
        logger.error(f"ApiCaller: Request error for {action}: {e}")
        AdminNotifier('ERROR', f"ApiCaller: Request error for {action}: {e}")
        return None


def PluginWorker(handler, simpleEvent: Union[Dict, None], rawEvent: Dict, resultPipe, memoryLimit: int):
    """Worker function that runs in subprocess to execute plugin code."""
    try:
        # Set memory limit (Linux only)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memoryLimit, memoryLimit))
        except Exception as e:
            logger.warning(f"Failed to set memory limit: {e}")
            AdminNotifier('WARNING', f"Failed to set memory limit: {e}")

        pluginName = getattr(handler, '__module__', 'unknown_plugin')

        # Create plugin-specific config functions
        def ConfigReader() -> Dict:
            return SubprocessConfigReader(pluginName)

        def ConfigWriter(config_data: Dict) -> None:
            return SubprocessConfigWriter(pluginName, config_data)

        def CrossOriginConfigReader(target_plugin: str) -> Union[Dict, None]:
            return SubprocessCrossOriginConfigReader(pluginName, target_plugin)

        def CrossOriginConfigWriter(target_plugin: str, config_data: Dict) -> Union[bool, None]:
            return SubprocessCrossOriginConfigWriter(pluginName, target_plugin, config_data)

        def ApiCaller(action: str, data: Dict) -> Union[Dict, None]:
            return SubprocessApiCaller(pluginName, action, data)

        botContext = {
            "Librarian": SubprocessLibrarian,
            "ConfigReader": ConfigReader,
            "ConfigWriter": ConfigWriter,
            "CrossOriginConfigReader": CrossOriginConfigReader,
            "CrossOriginConfigWriter": CrossOriginConfigWriter,
            "ApiCaller": ApiCaller
        }

        sig = inspect.signature(handler)
        params = sig.parameters

        availableArgs = {
            'simpleEvent': simpleEvent,
            'rawEvent': rawEvent,
            'botContext': botContext
        }

        # Build call arguments based on function signature
        callArgs = {}
        for paramName in params:
            if paramName in availableArgs:
                callArgs[paramName] = availableArgs[paramName]

        result = handler(**callArgs)
        resultPipe.send(result)

    except Exception as e:
        resultPipe.send({"_error": str(e), "_type": type(e).__name__})
    finally:
        resultPipe.close()


def PluginMonitor(process, startTime, maxCpuTime: float, maxWallTime: float, memoryLimit: int):
    """Monitor plugin process resource usage."""
    try:
        pluginProcess = psutil.Process(process.pid)

        cpuTimes = pluginProcess.cpu_times()
        totalCpuTime = cpuTimes.user + cpuTimes.system

        if totalCpuTime > maxCpuTime:
            return f"cpu_time_exceeded ({totalCpuTime:.2f}s > {maxCpuTime}s)"

        wallTime = time.time() - startTime
        if wallTime > maxWallTime:
            return f"wall_time_exceeded ({wallTime:.2f}s > {maxWallTime}s)"

        try:
            memInfo = pluginProcess.memory_info()
            if memInfo.rss > memoryLimit:
                memUsageMB = memInfo.rss / (1024 * 1024)
                memLimitMB = memoryLimit / (1024 * 1024)
                return f"memory_exceeded ({memUsageMB:.1f}MB > {memLimitMB:.1f}MB)"
        except Exception:
            pass

        return None

    except psutil.NoSuchProcess:
        return None
    except Exception as e:
        logger.warning(f"Error monitoring process: {e}")
        AdminNotifier('WARNING', f"Error monitoring process: {e}")
        return None


def PluginCallerSingle(handler, simpleEvent: Union[Dict, None], rawEvent: Dict):
    """Execute a single plugin in an isolated subprocess."""
    parentConn = None
    process = None
    try:
        maxCpuTime = CONFIG['PLUGIN_EXECUTION']['max_cpu_time_seconds']
        maxWallTime = CONFIG['PLUGIN_EXECUTION']['max_wall_time_seconds']
        memoryLimit = CONFIG['PLUGIN_EXECUTION']['memory_limit_mb'] * 1024 * 1024

        parentConn, childConn = multiprocessing.Pipe()

        process = multiprocessing.Process(
            target=PluginWorker,
            args=(handler, simpleEvent, rawEvent, childConn, memoryLimit)
        )

        startTime = time.time()
        process.start()
        childConn.close()  # Parent doesn't need child end - prevent FD leak

        monitorInterval = CONFIG['PLUGIN_EXECUTION']['monitor_interval_seconds']

        while process.is_alive():
            if parentConn.poll(timeout=monitorInterval):
                try:
                    result = parentConn.recv()

                    # Clean up process
                    process.join(timeout=1)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=1)
                        if process.is_alive():
                            process.kill()

                    return result

                except Exception as e:
                    logger.error(f"Error receiving result from plugin {handler.__name__}: {e}")
                    AdminNotifier('ERROR', f"Error receiving result from plugin {handler.__name__}: {e}")
                    return None

            terminationReason = PluginMonitor(
                process, startTime, maxCpuTime, maxWallTime, memoryLimit
            )

            if terminationReason:
                logger.error(f"Plugin {handler.__name__} terminated: {terminationReason}")
                AdminNotifier('ERROR', f"Plugin {handler.__name__} terminated: {terminationReason}")

                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()

                return None

        exitCode = process.exitcode
        if exitCode != 0:
            logger.error(f"Plugin {handler.__name__} exited with code {exitCode}")
            AdminNotifier('ERROR', f"Plugin {handler.__name__} exited with code {exitCode}")

        return None

    except Exception as e:
        logger.error(f"Failed to execute plugin {handler.__name__} in subprocess: {e}")
        AdminNotifier('ERROR', f"Failed to execute plugin {handler.__name__} in subprocess: {e}")
        return None
    finally:
        # Ensure cleanup in all cases
        if parentConn:
            try:
                parentConn.close()
            except Exception as e:
                logger.error(f"Failed to close pipe for plugin {handler.__name__}: {e}")
                AdminNotifier('ERROR', f"Failed to close pipe for plugin {handler.__name__}: {e}")

        if process:
            try:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                    if process.is_alive():
                        process.kill()
                        process.join()
            except Exception as e:
                logger.error(f"Failed to cleanup process for plugin {handler.__name__}: {e}")
                AdminNotifier('ERROR', f"Failed to cleanup process for plugin {handler.__name__}: {e}")


def PluginCaller(
    handlers: List[Callable],
    simpleEvent: Union[Dict, None],
    rawEvent: Dict,
    resultCallback: Optional[Callable] = None
) -> List[Any]:
    """Execute multiple plugins in parallel with immediate result processing."""
    if not handlers:
        return []

    results = {}
    resultQueue = queue.Queue()

    def executePluginThread(handler, handlerIndex):
        """Execute plugin in thread and handle result."""
        pluginName = getattr(handler, 'pluginName', 'unknown')
        success = False

        try:
            result = PluginCallerSingle(handler, simpleEvent, rawEvent)

            # Convert errors to None for parallel execution
            if isinstance(result, dict) and "_error" in result:
                logger.error(f"Plugin {handler.__name__} raised {result['_type']}: {result['_error']}")
                AdminNotifier('ERROR', f"Plugin {handler.__name__} raised {result['_type']}: {result['_error']}")
                result = None
            else:
                success = True  # Plugin succeeded (returned non-error result)

            resultQueue.put((handlerIndex, handler, result))
        except Exception as e:
            logger.error(f"Thread execution error for plugin {handler.__name__}: {e}")
            AdminNotifier('ERROR', f"Thread execution error for plugin {handler.__name__}: {e}")
            resultQueue.put((handlerIndex, handler, None))
        finally:
            # Track failure regardless of exception path
            UpdateFailureCount(pluginName, success)

    # Start all plugin threads
    threads = []
    for i, handler in enumerate(handlers):
        thread = threading.Thread(target=executePluginThread, args=(handler, i))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    # Process results as they complete
    completedCount = 0
    maxWaitTime = CONFIG['PLUGIN_EXECUTION']['max_wall_time_seconds'] + 5  # +5s for cleanup

    while completedCount < len(handlers):
        try:
            handlerIndex, handler, result = resultQueue.get(timeout=maxWaitTime)
            completedCount += 1

            results[handlerIndex] = result

            # Immediate callback for successful results
            if resultCallback and result is not None:
                try:
                    resultCallback(result, rawEvent)
                except Exception as e:
                    logger.error(f"Error in result callback for plugin {handler.__name__}: {e}")
                    AdminNotifier('ERROR', f"Error in result callback for plugin {handler.__name__}: {e}")

        except queue.Empty:
            logger.warning(f"Timeout waiting for plugin results after {maxWaitTime} seconds")
            AdminNotifier('WARNING', f"Timeout waiting for plugin results after {maxWaitTime} seconds")
            break

    # Cleanup threads
    for thread in threads:
        thread.join(timeout=1)
        if thread.is_alive():
            logger.warning(f"Thread still alive after receiving its result - possible bug")
            AdminNotifier('WARNING', f"Thread still alive after receiving its result - possible bug")

    # Return results in original order
    orderedResults = []
    for i in range(len(handlers)):
        orderedResults.append(results.get(i, None))

    return orderedResults


def RegistryInitializer() -> None:
    """Scan and load plugins, register event handlers."""
    global PLUGIN_REGISTRY
    PLUGIN_REGISTRY = {eventType: [] for eventType in EVENT_TYPES_}
    INITIALIZER_REGISTRY = []  # type: List[tuple]

    pluginsDir = CONFIG['PATHS']['plugins_dir']
    if not os.path.exists(pluginsDir):
        os.makedirs(pluginsDir)
        logger.info(f"Created plugins directory: {pluginsDir}")
        AdminNotifier('INFO', f"Created plugins directory: {pluginsDir}")

    if not os.path.isdir(pluginsDir):
        logger.critical(f"Plugins path is not a directory: {pluginsDir}")
        AdminNotifier('CRITICAL', f"Plugins path is not a directory: {pluginsDir}")
        sys.exit(1)

    pluginFiles = [f for f in os.listdir(pluginsDir) if f.endswith('.py') and not f.startswith('__')]

    if not pluginFiles:
        logger.warning(f"No plugin files found in {pluginsDir}")
        AdminNotifier('WARNING', f"No plugin files found in {pluginsDir}")
    else:
        logger.info(f"Found {len(pluginFiles)} plugin files: {pluginFiles}")
        AdminNotifier('INFO', f"Found {len(pluginFiles)} plugin files: {pluginFiles}")

    # Load each plugin file
    for pluginFile in pluginFiles:
        try:
            moduleName = pluginFile[:-3]
            if pluginsDir not in sys.path:
                sys.path.insert(0, pluginsDir)

            pluginModule = importlib.import_module(moduleName)

            if not hasattr(pluginModule, 'MANIFEST'):
                logger.error(f"Plugin {moduleName} has no MANIFEST, skipping")
                AdminNotifier('ERROR', f"Plugin {moduleName} has no MANIFEST, skipping")
                continue

            manifest = getattr(pluginModule, 'MANIFEST')
            if not isinstance(manifest, dict):
                logger.error(f"Plugin {moduleName} MANIFEST is not a dict, skipping")
                AdminNotifier('ERROR', f"Plugin {moduleName} MANIFEST is not a dict, skipping")
                continue

            for eventType, functionName in manifest.items():
                if eventType == "INITIALIZER":
                    if not isinstance(functionName, str):
                        logger.error(f"Plugin {moduleName} INITIALIZER must be string, skipping")
                        AdminNotifier('ERROR', f"Plugin {moduleName} INITIALIZER must be string, skipping")
                        continue

                    if not hasattr(pluginModule, functionName):
                        logger.error(f"Plugin {moduleName} declares INITIALIZER function '{functionName}' but it doesn't exist")
                        AdminNotifier('ERROR', f"Plugin {moduleName} declares INITIALIZER function '{functionName}' but it doesn't exist")
                        continue

                    handlerFunction = getattr(pluginModule, functionName)
                    if not callable(handlerFunction):
                        logger.error(f"Plugin {moduleName}.{functionName} is not callable")
                        AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} is not callable")
                        continue

                    sig = inspect.signature(handlerFunction)
                    allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                    actualParams = set(sig.parameters.keys())

                    unknownParams = actualParams - allowedParams
                    if unknownParams:
                        logger.error(f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        continue

                    handlerFunction.pluginName = pluginFile
                    INITIALIZER_REGISTRY.append((handlerFunction, moduleName))
                    logger.info(f"Registered {moduleName}.{functionName} for INITIALIZER event")
                    AdminNotifier('INFO', f"Registered {moduleName}.{functionName} for INITIALIZER event")
                    continue

                if eventType == "UNCONDITIONAL":
                    interval = 1  # Default: every minute
                    handlerName = functionName

                    if isinstance(functionName, list):
                        if len(functionName) == 2:
                            handlerName, interval = functionName
                        else:
                            logger.error(f"Plugin {moduleName} UNCONDITIONAL has invalid format, skipping")
                            AdminNotifier('ERROR', f"Plugin {moduleName} UNCONDITIONAL has invalid format, skipping")
                            continue
                    elif not isinstance(functionName, str):
                        logger.error(f"Plugin {moduleName} UNCONDITIONAL must be string or list, skipping")
                        AdminNotifier('ERROR', f"Plugin {moduleName} UNCONDITIONAL must be string or list, skipping")
                        continue

                    if not hasattr(pluginModule, handlerName):
                        logger.error(f"Plugin {moduleName} declares UNCONDITIONAL function '{handlerName}' but it doesn't exist")
                        AdminNotifier('ERROR', f"Plugin {moduleName} declares UNCONDITIONAL function '{handlerName}' but it doesn't exist")
                        continue

                    handlerFunction = getattr(pluginModule, handlerName)
                    if not callable(handlerFunction):
                        logger.error(f"Plugin {moduleName}.{handlerName} is not callable")
                        AdminNotifier('ERROR', f"Plugin {moduleName}.{handlerName} is not callable")
                        continue

                    if not isinstance(interval, int) or interval <= 0 or interval > 60:
                        logger.error(f"Plugin {moduleName} UNCONDITIONAL interval must be integer 1-60, got {interval}")
                        AdminNotifier('ERROR', f"Plugin {moduleName} UNCONDITIONAL interval must be integer 1-60, got {interval}")
                        continue

                    sig = inspect.signature(handlerFunction)
                    allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                    actualParams = set(sig.parameters.keys())

                    unknownParams = actualParams - allowedParams
                    if unknownParams:
                        logger.error(f"Plugin {moduleName}.{handlerName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        AdminNotifier('ERROR', f"Plugin {moduleName}.{handlerName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        continue

                    # Register in both registries
                    handlerFunction.pluginName = pluginFile
                    PLUGIN_REGISTRY["UNCONDITIONAL"].append((handlerFunction, interval))
                    logger.info(f"Registered {moduleName}.{handlerName} for UNCONDITIONAL event (interval: {interval})")
                    AdminNotifier('INFO', f"Registered {moduleName}.{handlerName} for UNCONDITIONAL event (interval: {interval})")
                    continue

                # Regular event types
                if eventType not in EVENT_TYPES_:
                    logger.error(f"Plugin {moduleName} declares invalid event type '{eventType}'. Valid types: {EVENT_TYPES_}")
                    AdminNotifier('ERROR', f"Plugin {moduleName} declares invalid event type '{eventType}'. Valid types: {EVENT_TYPES_}")
                    continue

                if not hasattr(pluginModule, functionName):
                    logger.error(f"Plugin {moduleName} declares function '{functionName}' but it doesn't exist")
                    AdminNotifier('ERROR', f"Plugin {moduleName} declares function '{functionName}' but it doesn't exist")
                    continue

                handlerFunction = getattr(pluginModule, functionName)
                if not callable(handlerFunction):
                    logger.error(f"Plugin {moduleName}.{functionName} is not callable")
                    AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} is not callable")
                    continue

                sig = inspect.signature(handlerFunction)
                allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                actualParams = set(sig.parameters.keys())

                unknownParams = actualParams - allowedParams
                if unknownParams:
                    logger.error(f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                f"Allowed parameters are: {allowedParams}")
                    AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                f"Allowed parameters are: {allowedParams}")
                    continue

                handlerFunction.pluginName = pluginFile
                PLUGIN_REGISTRY[eventType].append(handlerFunction)
                logger.info(f"Registered {moduleName}.{functionName} for event '{eventType}'")
                AdminNotifier('INFO', f"Registered {moduleName}.{functionName} for event '{eventType}'")

        except Exception as e:
            logger.error(f"Failed to load plugin {pluginFile}: {e}")
            AdminNotifier('ERROR', f"Failed to load plugin {pluginFile}: {e}")
            continue

    # Execute INITIALIZER functions serially
    failedPlugins = []
    if INITIALIZER_REGISTRY:
        logger.info(f"Executing {len(INITIALIZER_REGISTRY)} INITIALIZER plugins")
        AdminNotifier('INFO', f"Executing {len(INITIALIZER_REGISTRY)} INITIALIZER plugins")

        for handlerFunction, pluginName in INITIALIZER_REGISTRY:
            try:
                emptyRawEvent = {"post_type": "initializer", "time": int(time.time())}
                result = PluginCallerSingle(handlerFunction, None, emptyRawEvent)

                if isinstance(result, dict) and "_error" in result:
                    logger.error(f"INITIALIZER for plugin {pluginName} failed: {result['_error']}")
                    AdminNotifier('ERROR', f"INITIALIZER for plugin {pluginName} failed: {result['_error']}")
                    failedPlugins.append(pluginName)
                elif result is None:
                    logger.info(f"INITIALIZER for plugin {pluginName} completed successfully")
                    AdminNotifier('INFO', f"INITIALIZER for plugin {pluginName} completed successfully")
                else:
                    logger.error(f"INITIALIZER for plugin {pluginName} returned unexpected result: {result}")
                    AdminNotifier('ERROR', f"INITIALIZER for plugin {pluginName} returned unexpected result: {result}")

            except Exception as e:
                logger.error(f"INITIALIZER for plugin {pluginName} failed with exception: {e}")
                AdminNotifier('ERROR', f"INITIALIZER for plugin {pluginName} failed with exception: {e}")
                failedPlugins.append(pluginName)

    # Remove failed plugins from all registries
    for pluginName in failedPlugins:
        for eventType in PLUGIN_REGISTRY:
            correctlyInitalizedHandlers_ = []
            for entry in PLUGIN_REGISTRY[eventType]:
                if isinstance(entry, tuple):
                    handlerFunction = entry[0]
                else:
                    handlerFunction = entry
                if getattr(handlerFunction, '__module__', None) != pluginName:
                    correctlyInitalizedHandlers_.append(entry)
            PLUGIN_REGISTRY[eventType] = correctlyInitalizedHandlers_

        logger.error(f"Removed all functions for failed plugin: {pluginName}")
        AdminNotifier('ERROR', f"Removed all functions for failed plugin: {pluginName}")

    totalHandlers = sum(len(handlerList) for handlerList in PLUGIN_REGISTRY.values())
    totalUnconditional = len(PLUGIN_REGISTRY.get("UNCONDITIONAL", []))
    totalInitializers = len(INITIALIZER_REGISTRY)
    totalFailed = len(failedPlugins)

    logger.info(f"Plugin initialization complete. {totalHandlers} handlers registered for {len(PLUGIN_REGISTRY)} event types")
    AdminNotifier('INFO', f"Plugin initialization complete. {totalHandlers} handlers registered for {len(PLUGIN_REGISTRY)} event types")
    logger.info(f"UNCONDITIONAL plugins: {totalUnconditional}")
    AdminNotifier('INFO', f"UNCONDITIONAL plugins: {totalUnconditional}")
    logger.info(f"INITIALIZER plugins: {totalInitializers} executed, {totalFailed} failed")
    AdminNotifier('INFO', f"INITIALIZER plugins: {totalInitializers} executed, {totalFailed} failed")

    if failedPlugins:
        logger.error(f"Failed plugins removed: {', '.join(failedPlugins)}")
        AdminNotifier('ERROR', f"Failed plugins removed: {', '.join(failedPlugins)}")

    for eventType, handlerList in PLUGIN_REGISTRY.items():
        if handlerList:
            logger.debug(f"  {eventType}: {len(handlerList)} handlers")
            AdminNotifier('DEBUG', f"  {eventType}: {len(handlerList)} handlers")


# ==================== EVENT HANDLING ====================

def EventTypeParser(rawEvent: Dict) -> str:
    """Parse raw event to determine its type."""
    match rawEvent.get("post_type"):
        case "message":
            match rawEvent.get("message_type"):
                case "private":
                    return "MESSAGE_PRIVATE"
                case "group":
                    selfId = str(rawEvent.get("self_id", ""))
                    messageSegments = rawEvent.get("message", [])
                    # @mention has highest priority
                    for segment in messageSegments:
                        if segment.get("type") == "at":
                            atQQ = segment.get("data", {}).get("qq", "")
                            if atQQ == selfId:
                                return "MESSAGE_GROUP_MENTION"
                    # Check command prefix in first text segment only
                    for segment in messageSegments:
                        if segment.get("type") == "text":
                            text = segment.get("data", {}).get("text", "")
                            trimmedText = text.lstrip()
                            if trimmedText and trimmedText[0] in ['.', '/', '\\']:
                                return "MESSAGE_GROUP_BOT"
                            break
                    return "MESSAGE_GROUP"

        case "message_sent":
            match rawEvent.get("message_type"):
                case "private":
                    return "MESSAGE_SENT_PRIVATE"
                case "group":
                    return "MESSAGE_SENT_GROUP"

        case "notice":
            match rawEvent.get("notice_type"):
                case "friend_add":
                    return "NOTICE_FRIEND_ADD"
                case "friend_recall":
                    return "NOTICE_FRIEND_RECALL"
                case "group_recall":
                    return "NOTICE_GROUP_RECALL"
                case "group_increase":
                    return "NOTICE_GROUP_INCREASE"
                case "group_decrease":
                    return "NOTICE_GROUP_DECREASE"
                case "group_admin":
                    return "NOTICE_GROUP_ADMIN"
                case "group_ban":
                    return "NOTICE_GROUP_BAN"
                case "group_upload":
                    return "NOTICE_GROUP_UPLOAD"
                case "group_card":
                    return "NOTICE_GROUP_CARD"
                case "essence":
                    return "NOTICE_ESSENCE"
                case "group_msg_emoji_like":
                    return "NOTICE_GROUP_MSG_EMOJI_LIKE"
                case "bot_offline":
                    return "NOTICE_BOT_OFFLINE"
                case "notify":
                    match rawEvent.get("sub_type"):
                        case "group_name":
                            return "NOTICE_GROUP_NAME"
                        case "title":
                            return "NOTICE_GROUP_TITLE"
                        case "poke":
                            return "NOTICE_POKE"
                        case "profile_like":
                            return "NOTICE_PROFILE_LIKE"
                        case "input_status":
                            return "NOTICE_INPUT_STATUS"

        case "request":
            match rawEvent.get("request_type"):
                case "friend":
                    return "REQUEST_FRIEND"
                case "group":
                    return "REQUEST_GROUP"

        case "meta_event":
            match rawEvent.get("meta_event_type"):
                case "heartbeat":
                    return "META_HEARTBEAT"
                case "lifecycle":
                    return "META_LIFECYCLE"
        case "unconditional":
                return "UNCONDITIONAL"

    logger.warning(f"Unrecognized event structure: post_type='{rawEvent.get('post_type')}',full event ={rawEvent}")
    AdminNotifier('WARNING', f"Unrecognized event structure: post_type='{rawEvent.get('post_type')}',full event ={rawEvent}")
    return "UNEXPECTED"


def InbondMessageParser(rawEvent: Dict, eventType: str) -> Union[Dict, None]:
    """Parse incoming message event to extract simple event data."""

    match eventType:
        case "MESSAGE_PRIVATE":
            messageSegments = rawEvent.get("message", [])
            textParts = []

            for segment in messageSegments:
                if segment.get("type") == "text":
                    textData = segment.get("data", {})
                    textContent = textData.get("text", "")
                    textParts.append(textContent)

            fullText = "".join(textParts)

            return {
                "user_id": rawEvent.get("user_id"),
                "text_message": fullText
            }

        case "MESSAGE_GROUP" | "MESSAGE_GROUP_MENTION" | "MESSAGE_GROUP_BOT":
            messageSegments = rawEvent.get("message", [])
            textParts = []

            for segment in messageSegments:
                if segment.get("type") == "text":
                    textData = segment.get("data", {})
                    textContent = textData.get("text", "")
                    textParts.append(textContent)

            fullText = "".join(textParts)

            return {
                "user_id": rawEvent.get("user_id"),
                "group_id": rawEvent.get("group_id"),
                "text_message": fullText
            }

        case _:
            return None


def NapCatSender(actionEndpoint: str, requestBody: Dict) -> None:
    """Send action request to NapCat API."""
    baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
    fullUrl = f"{baseUrl}/{actionEndpoint}"

    for attempt in range(CONFIG['HTTP']['max_retries']):
        try:
            response = requests.post(
                fullUrl,
                json=requestBody,
                timeout=CONFIG['HTTP']['timeout_seconds']
            )

            if 400 <= response.status_code < 500:
                logger.warning(f"Client error {response.status_code} for {actionEndpoint}")
                AdminNotifier('WARNING', f"Client error {response.status_code} for {actionEndpoint}")
                return

            if response.status_code == 200:
                try:
                    responseData = response.json()
                    status = responseData.get('status', '').lower()
                    if status in ['ok', 'async']:
                        return
                    else:
                        logger.error(f"API returned status '{status}' for {actionEndpoint}")
                        AdminNotifier('ERROR', f"API returned status '{status}' for {actionEndpoint}")
                        break
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Invalid JSON response from {actionEndpoint}: {e}")
                    AdminNotifier('ERROR', f"Invalid JSON response from {actionEndpoint}: {e}")
                    break

            logger.warning(f"HTTP {response.status_code} from {actionEndpoint}, attempt {attempt + 1}/{CONFIG['HTTP']['max_retries']}")
            AdminNotifier('WARNING', f"HTTP {response.status_code} from {actionEndpoint}, attempt {attempt + 1}/{CONFIG['HTTP']['max_retries']}")

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {actionEndpoint}, attempt {attempt + 1}/{CONFIG['HTTP']['max_retries']}")
            AdminNotifier('WARNING', f"Timeout for {actionEndpoint}, attempt {attempt + 1}/{CONFIG['HTTP']['max_retries']}")

        except Exception as e:
            logger.error(f"Request error for {actionEndpoint}: {e}")
            AdminNotifier('ERROR', f"Request error for {actionEndpoint}: {e}")
            break

    # Diagnostic: check bot status
    try:
        statusUrl = f"{baseUrl}/get_status"
        statusResponse = requests.get(statusUrl, timeout=CONFIG['HTTP']['status_check_timeout'])
        if statusResponse.status_code == 200:
            statusData = statusResponse.json()
            logger.error(f"Failed to send {actionEndpoint}. Bot status: {statusData}")
            AdminNotifier('ERROR', f"Failed to send {actionEndpoint}. Bot status: {statusData}")
        else:
            logger.error(f"Failed to send {actionEndpoint}. Could not get bot status (HTTP {statusResponse.status_code})")
            AdminNotifier('ERROR', f"Failed to send {actionEndpoint}. Could not get bot status (HTTP {statusResponse.status_code})")
    except Exception as e:
        logger.error(f"Failed to send {actionEndpoint}. Could not get bot status: {e}")
        AdminNotifier('ERROR', f"Failed to send {actionEndpoint}. Could not get bot status: {e}")


def OutbondMessageParser(pluginResponse: Any, rawEvent: Dict) -> None:
    """Parse plugin response and execute appropriate actions."""
    if isinstance(pluginResponse, str):
        postType = rawEvent.get("post_type")

        groupId = rawEvent.get("group_id")
        userId = rawEvent.get("user_id")

        if groupId:
            requestBody = {
                "group_id": groupId,
                "message": [{"type": "text", "data": {"text": pluginResponse}}]
            }
            NapCatSender("send_group_msg", requestBody)
        elif userId:
            requestBody = {
                "user_id": userId,
                "message": [{"type": "text", "data": {"text": pluginResponse}}]
            }
            NapCatSender("send_private_msg", requestBody)
        else:
            logger.warning(f"String response not supported for event {EventTypeParser(rawEvent)}")
            AdminNotifier('WARNING', f"String response not supported for event {EventTypeParser(rawEvent)}")

    elif isinstance(pluginResponse, dict):
        if ("action" not in pluginResponse) or ("data" not in pluginResponse):
            logger.warning("Plugin dict response missing 'action' key or 'data' key")
            AdminNotifier('WARNING', "Plugin dict response missing 'action' key or 'data' key")
            return

        action = pluginResponse["action"]
        data = pluginResponse["data"]

        if (not isinstance(action, str)) or (not isinstance(data, dict)):
            logger.warning(f"Plugin dict response wrong type: got {type(action)}")
            AdminNotifier('WARNING', f"Plugin dict response wrong type: got {type(action)}")
            return

        NapCatSender(action, data)

    elif isinstance(pluginResponse, list):
        for i, item in enumerate(pluginResponse):
            if not isinstance(item, (str, dict)):
                logger.warning(f"Plugin list response contains invalid item at index {i}: expected str or dict, got {type(item).__name__}.")
                AdminNotifier('WARNING', f"Plugin list response contains invalid item at index {i}: expected str or dict, got {type(item).__name__}.")
            else:
                OutbondMessageParser(item, rawEvent)

    else:
        logger.warning(f"Invalid plugin response type: {type(pluginResponse).__name__}. Expected str, dict, or list of str/dict, got {repr(pluginResponse)}")
        AdminNotifier('WARNING', f"Invalid plugin response type: {type(pluginResponse).__name__}. Expected str, dict, or list of str/dict, got {repr(pluginResponse)}")
        return


def AdminDispatcher(rawEvent: Dict) -> bool:
    """Handle admin control commands (mute/unmute)."""
    adminQQ = CONFIG['ADMIN_NOTIFICATION']['admin_qq']
    if (rawEvent.get("post_type") == "message" and
        rawEvent.get("message_type") == "private" and
        rawEvent.get("user_id") == adminQQ and adminQQ != 0):

        command = rawEvent.get("raw_message", "").strip()

        if command == "mute":
            global IS_MUTED
            IS_MUTED = True
            logger.info(f"Admin {adminQQ} activated mute mode")
            AdminNotifier('INFO', f"Admin {adminQQ} activated mute mode")
            return True
        elif command == "unmute":
            IS_MUTED = False
            logger.info(f"Admin {adminQQ} deactivated mute mode")
            AdminNotifier('INFO', f"Admin {adminQQ} deactivated mute mode")
            return True

    return False


def MainDispatcher(rawEvent: Dict) -> None:
    """Main event dispatcher that routes events to appropriate plugins."""
    eventType = EventTypeParser(rawEvent)
    HandlersToExecute_ = []
    simpleEvent = InbondMessageParser(rawEvent, eventType)
    if eventType == "UNEXPECTED":
        return

    elif eventType == "UNCONDITIONAL":
        currentMinute = datetime.datetime.fromtimestamp(rawEvent["time"]).minute
        for handler, interval in PLUGIN_REGISTRY.get("UNCONDITIONAL", []):
            if currentMinute % interval == 0:
                HandlersToExecute_.append(handler)
    else:
        Historian(rawEvent, eventType)
        eventTypesToTrigger_ = [eventType]
        if eventType in EVENT_INHERITANCE:
            eventTypesToTrigger_.extend(EVENT_INHERITANCE[eventType])

        # Deduplicate handlers
        matchedHandlers_ = set()

        for triggerType in eventTypesToTrigger_:
            handlerList_ = PLUGIN_REGISTRY.get(triggerType, [])
            matchedHandlers_.update(handlerList_)  # Atomic - add all at once

        # Apply access control filtering
        for handler in matchedHandlers_:
            if CheckPluginAccess(handler, rawEvent):
                HandlersToExecute_.append(handler)
            else:
                pluginName = getattr(handler, '__module__', 'unknown')
                logger.debug(f"Access denied for plugin {pluginName} on event {eventType}")
                AdminNotifier('DEBUG', f"Access denied for plugin {pluginName} on event {eventType}")

    # Execute filtered plugins in parallel with immediate response
    if HandlersToExecute_:
        def ResponseProcessor(result, event):
            OutbondMessageParser(result, event)

        PluginCaller(HandlersToExecute_, simpleEvent, rawEvent, ResponseProcessor)


# ==================== INITIALIZATION ====================

def Initializer():
    """Ensure framework is initialized exactly once."""
    global INITIALIZED
    if INITIALIZED:
        return

    with INIT_LOCK:
        if not INITIALIZED:
            try:
                # Only set multiprocessing start method if not already set
                if multiprocessing.get_start_method(allow_none=True) is None:
                    multiprocessing.set_start_method(CONFIG['PLUGIN_EXECUTION']['process_creation_method'])
                    logger.info(f"Set multiprocessing start method to {CONFIG['PLUGIN_EXECUTION']['process_creation_method']}")
                    AdminNotifier('INFO', f"Set multiprocessing start method to {CONFIG['PLUGIN_EXECUTION']['process_creation_method']}")
            except Exception as e:
                logger.warning(f"Could not set multiprocessing start method: {e}")
                AdminNotifier('WARNING', f"Could not set multiprocessing start method: {e}")
                # This is not critical, continue with default

            ActualInitializer()
            INITIALIZED = True


def ActualInitializer() -> None:
    """Initialize the framework, load plugins, and start background services."""
    # Load configurations first
    FrameworkConfigReader()
    PluginsAccessControlLoader()

    # Initialize database
    DatabaseInitializer()

    # Initialize plugin registry
    RegistryInitializer()

    # Start unconditional event generator
    UnconditionalEventInitializer()


def UnconditionalEventInitializer() -> None:
    """Initialize the unconditional event generator."""
    thread = threading.Thread(target=UnconditionalEventGenerator, daemon=True)
    thread.start()
    logger.info("Unconditional event generator started")
    AdminNotifier('INFO', "Unconditional event generator started")


def UnconditionalEventGenerator() -> None:
    """Generate UNCONDITIONAL events at scheduled intervals."""
    logger.info("Starting UNCONDITIONAL event generator")
    AdminNotifier('INFO', "Starting UNCONDITIONAL event generator")

    while True:
        now = datetime.datetime.now()
        secondsToNextMinute = 60 - now.second + 3  # +3s buffer to avoid rounding errors
        time.sleep(secondsToNextMinute)

        unconditional_event = {
            "post_type": "unconditional",
            "time": int(time.time())
        }

        try:
            url = f"http://localhost:{CONFIG['NAPCAT_LISTEN']['port']}/"
            response = requests.post(url, json=unconditional_event, timeout=5.0)
            if response.status_code != 200:
                logger.error(f"Failed to send unconditional event: HTTP {response.status_code}")
                AdminNotifier('ERROR', f"Failed to send unconditional event: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send unconditional event: {e}")
            AdminNotifier('ERROR', f"Failed to send unconditional event: {e}")


# ==================== FLASK APP ====================

# Flask application
NAPCAT_LISTENER = Flask(__name__)


@NAPCAT_LISTENER.route('/', methods=['POST'])
def NapCatListener() -> str:
    """Handle incoming events from NapCat."""
    try:
        rawEvent = request.get_json()

        # Validate we received JSON data
        if rawEvent is None:
            logger.warning("Received POST request with no JSON body or invalid Content-Type")
            return 'OK'  # Return OK to avoid NapCat retry storms

        # Handle admin commands first
        if AdminDispatcher(rawEvent):
            return 'OK'

        # Check mute status
        if IS_MUTED:
            return 'OK'

        # Dispatch to main handler
        MainDispatcher(rawEvent)
        return 'OK'

    except Exception as e:
        # Log the error with full traceback
        logger.error(f"Fatal error in NapCatListener: {e}", exc_info=True)
        AdminNotifier('ERROR', f"Fatal error in NapCatListener: {e}")

        # Still return 'OK' to prevent NapCat from retrying
        # (retrying a broken request will just cause more errors)
        return 'OK'


@NAPCAT_LISTENER.route('/health', methods=['GET'])
def HealthCheck() -> dict:
    """Health check endpoint for monitoring."""
    NapCatServerStatus = 'Unreachable'
    try:
        baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
        statusUrl = f"{baseUrl}/get_status"
        statusResponse = requests.get(statusUrl, timeout=CONFIG['HTTP']['status_check_timeout'])
        if statusResponse.status_code == 200:
            statusData = statusResponse.json()
            if statusData.get('status', '') == 'ok':
                NapCatServerStatus = 'OK'
    except Exception as e:
        logger.error(f"Failed to check NapCat server status: {e}")
        AdminNotifier('ERROR', f"Failed to check NapCat server status: {e}")

    health_status = {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'is_muted': IS_MUTED,
        'version': 'Beta 0.3-rc1',
        'NapCatServerStatus': NapCatServerStatus
    }

    return health_status


# Initialize framework when module is imported by Gunicorn/Uvicorn
# This ensures plugins are loaded and background services are started
Initializer()
