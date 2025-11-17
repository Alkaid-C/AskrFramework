"""
Configuration module for Askr Framework
Handles all configuration loading and constants
"""
import json
import os
import logging
import threading
import sys
from typing import Dict, Set

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
        'admin_qq': 1804326288,
        'notify_level': 'WARNING',
        'message_format': 'Askr Alert \n[{level}] {time}\n{message}'
    },
    'REMOVE_FAILED_PLUGIN':{
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


def AdminNotifier(messageLevel: str, message: str) -> None:
    """
    Send notification to administrator via QQ message.
    Note: Import is delayed to avoid circular dependency.
    """
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
            import datetime
            import requests

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

        if 'REMOVE_FAILED_PLUGIN' in fileConfig and isinstance(fileConfig['REMOVE_FAILED_PLUGIN'], dict):
            if 'enabled' in fileConfig['REMOVE_FAILED_PLUGIN']:
                if isinstance(fileConfig['REMOVE_FAILED_PLUGIN']['enabled'], bool):
                    CONFIG['REMOVE_FAILED_PLUGIN']['enabled'] = fileConfig['REMOVE_FAILED_PLUGIN']['enabled']
                else:
                    logger.warning(f"Invalid type for REMOVE_FAILED_PLUGIN.enabled, expected bool")
                    AdminNotifier('WARNING', f"Invalid type for REMOVE_FAILED_PLUGIN.enabled, expected bool")
            if 'remove_by_consecutive_or_total_failure' in fileConfig['REMOVE_FAILED_PLUGIN']:
                if fileConfig['REMOVE_FAILED_PLUGIN']['remove_by_consecutive_or_total_failure'] == 'consecutive' or fileConfig['REMOVE_FAILED_PLUGIN']['remove_by_consecutive_or_total_failure'] == 'total':
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
