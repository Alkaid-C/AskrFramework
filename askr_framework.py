#!/usr/bin/env python3

import json
import os
import importlib
import inspect
import requests
import logging
import sqlite3
import time
import datetime
import threading
import multiprocessing
import signal
import resource
import psutil
import queue
import hashlib
from flask import Flask, request
from typing import List, Dict, Optional, Union, Any, Callable
import threading

INIT_LOCK = threading.Lock()
INITIALIZED = False

EVENT_TYPES_: List[str] = [
    "MESSAGE_PRIVATE", "MESSAGE_GROUP", "MESSAGE_GROUP_MENTION", "MESSAGE_GROUP_BOT",
    "MESSAGE_SENT_PRIVATE", "MESSAGE_SENT_GROUP",
    "NOTICE_FRIEND_ADD", "NOTICE_FRIEND_RECALL", "NOTICE_GROUP_RECALL", 
    "NOTICE_GROUP_INCREASE", "NOTICE_GROUP_DECREASE", "NOTICE_GROUP_ADMIN", 
    "NOTICE_GROUP_BAN", "NOTICE_GROUP_UPLOAD", "NOTICE_GROUP_CARD", 
    "NOTICE_GROUP_NAME", "NOTICE_GROUP_TITLE", "NOTICE_POKE", "NOTICE_PROFILE_LIKE", 
    "NOTICE_INPUT_STATUS", "NOTICE_ESSENCE", "NOTICE_GROUP_MSG_EMOJI_LIKE", 
    "NOTICE_BOT_OFFLINE",
    "REQUEST_FRIEND", "REQUEST_GROUP",
    "META_HEARTBEAT", "META_LIFECYCLE"
]

EVENT_INHERITANCE = {
    "MESSAGE_GROUP_MENTION": ["MESSAGE_GROUP"],
    "MESSAGE_GROUP_BOT": ["MESSAGE_GROUP"],
}

PLUGIN_REGISTRY = {}  # type: Dict[str, List[callable]]
UNCONDITIONAL_REGISTRY = []  # type: List[tuple[callable, int]]
INITIALIZER_REGISTRY = []  # type: List[tuple[callable, str]]

CONFIG = {
    'NAPCAT_SERVER': {'api_url': 'http://localhost:29217'},
    'NAPCAT_LISTEN': {'host': '0.0.0.0', 'port': 29218},
    'PATHS': {
        'plugins_dir': './plugins',
        'history_dir': './MessageHistory',  # Legacy
        'database_file': './EventHistory.db'
    },
    'HTTP': {
        'max_retries': 3,
        'timeout_seconds': 10,
        'status_check_timeout': 5
    },
    'PLUGIN_EXECUTION': {
        'max_cpu_time_seconds': 3.0,
        'max_wall_time_seconds': 30.0,
        'memory_limit_mb': 100,
        'monitor_interval_seconds': 0.1,
        'process_creation_method': 'spawn'
    },
    'ADMIN_NOTIFICATION': {
        'enabled': False,
        'admin_qq': 999999999,
        'notify_level': 'WARNING',
        'rate_limit_seconds': 300,
        'message_format': 'Alert \n[{level}] {time}\n{message}'
    }
}

logging.basicConfig(level=logging.INFO)

IS_MUTED = False

LOGGING_LEVELS = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}
AdminNotificationInProgress = False
AdminNotificationLast = {}  # Rate limiting: {messageHash: timestamp}

def MessageHasher(message: str) -> str:
    return hashlib.md5(message.encode('utf-8')).hexdigest()[:8]

def NotificationEligibilityChecker(recordLevelName: str) -> bool:
    if not CONFIG['ADMIN_NOTIFICATION']['enabled']:
        return False
    if not CONFIG['ADMIN_NOTIFICATION']['admin_qq']:
        return False
    
    configLevel = CONFIG['ADMIN_NOTIFICATION']['notify_level']
    configLevelNum = LOGGING_LEVELS.get(configLevel, 40)
    recordLevelNum = LOGGING_LEVELS.get(recordLevelName, 0)
    
    return recordLevelNum >= configLevelNum

def QQNotificationSender(level: str, message: str) -> None:
    def _sendNotification():
        global AdminNotificationInProgress
        
        if AdminNotificationInProgress:
            return
        
        # Rate limiting based on message content hash
        currentTime = time.time()
        rateLimit = CONFIG['ADMIN_NOTIFICATION']['rate_limit_seconds']
        messageHash = MessageHasher(message)
        lastTime = AdminNotificationLast.get(messageHash, 0)
        
        if currentTime - lastTime < rateLimit:
            return
        
        AdminNotificationInProgress = True
        try:
            formattedTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            notificationText = CONFIG['ADMIN_NOTIFICATION']['message_format'].format(
                level=level, time=formattedTime, message=message
            )
            
            adminQQ = CONFIG['ADMIN_NOTIFICATION']['admin_qq']
            requestBody = {
                "user_id": adminQQ,
                "message": [{"type": "text", "data": {"text": notificationText}}]
            }
            
            baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
            fullUrl = f"{baseUrl}/send_private_msg"
            
            response = requests.post(fullUrl, json=requestBody, timeout=5.0)
            
            if response.status_code == 200:
                AdminNotificationLast[messageHash] = currentTime
                
        except Exception:
            # Silent failure to avoid recursion
            pass
        finally:
            AdminNotificationInProgress = False
    
    # Background thread to avoid blocking
    thread = threading.Thread(target=_sendNotification, daemon=True)
    thread.start()

def LoggingNotificationConfigurator() -> None:
    if not CONFIG['ADMIN_NOTIFICATION']['enabled']:
        return
    
    # Monkey patch logging functions
    originalFunctions = {
        'debug': logging.debug, 'info': logging.info, 'warning': logging.warning,
        'error': logging.error, 'critical': logging.critical
    }
    
    def EnhancedLoggingCreator(levelName: str, originalFunc):
        def enhancedLogging(msg, *args, **kwargs):
            originalFunc(msg, *args, **kwargs)
            
            if NotificationEligibilityChecker(levelName):
                try:
                    formattedMsg = msg % args if args else str(msg)
                    QQNotificationSender(levelName, formattedMsg)
                except:
                    pass
        return enhancedLogging
    
    for levelName, originalFunc in originalFunctions.items():
        enhancedFunc = EnhancedLoggingCreator(levelName.upper(), originalFunc)
        setattr(logging, levelName, enhancedFunc)

def AdminDispatcher(rawEvent: Dict) -> bool:
    global IS_MUTED
    
    adminQQ = CONFIG['ADMIN_NOTIFICATION']['admin_qq']
    if (rawEvent.get("post_type") == "message" and 
        rawEvent.get("message_type") == "private" and
        rawEvent.get("user_id") == adminQQ):
        
        command = rawEvent.get("raw_message", "").strip()
        
        if command == "mute":
            IS_MUTED = True
            logging.info(f"Admin {adminQQ} activated mute mode")
            return True
        elif command == "unmute":
            IS_MUTED = False
            logging.info(f"Admin {adminQQ} deactivated mute mode")
            return True
    
    return False

def DatabaseInitializer() -> None:
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
        
        logging.info(f"Database initialized successfully at {dbPath}")
        
    except Exception as e:
        logging.critical(f"Failed to initialize database: {e}")
        sys.exit(1)

def UnconditionalScheduler() -> None:
    logging.info("Starting UNCONDITIONAL scheduler")
    
    while True:
        now = datetime.datetime.now()
        secondsToNextMinute = 60 - now.second + 3  # +3s buffer to avoid rounding errors
        time.sleep(secondsToNextMinute)
        
        if IS_MUTED:
            continue
        
        currentMinute = datetime.datetime.now().minute
        
        # Collect handlers that should run this minute
        due_handlers = []
        for handler, interval in UNCONDITIONAL_REGISTRY:
            if currentMinute % interval == 0:
                due_handlers.append(handler)
        
        if due_handlers:
            emptyRawEvent = {"post_type": "unconditional", "time": int(time.time())}
            
            def response_callback(result, event):
                OutbondMessageParser(result, event)
            
            PluginCaller(due_handlers, None, emptyRawEvent, response_callback)

def Initializer() -> None:
    global PLUGIN_REGISTRY
    
    LoggingNotificationConfigurator()
    DatabaseInitializer()
    
    PLUGIN_REGISTRY = {eventType: [] for eventType in EVENT_TYPES_}
    
    pluginsDir = CONFIG['PATHS']['plugins_dir']
    if not os.path.exists(pluginsDir):
        os.makedirs(pluginsDir)
        logging.info(f"Created plugins directory: {pluginsDir}")
    
    if not os.path.isdir(pluginsDir):
        logging.critical(f"Plugins path is not a directory: {pluginsDir}")
        sys.exit(1)
        
    pluginFiles_ = [f for f in os.listdir(pluginsDir) if f.endswith('.py') and not f.startswith('__')]
    
    if not pluginFiles_:
        logging.critical(f"No plugin files found in {pluginsDir}")
        sys.exit(1)
    
    logging.info(f"Found {len(pluginFiles_)} plugin files: {pluginFiles_}")
    
    # Load each plugin file
    for pluginFile in pluginFiles_:
        try:
            moduleName = pluginFile[:-3]
            
            import sys
            if pluginsDir not in sys.path:
                sys.path.insert(0, pluginsDir)
            
            pluginModule = importlib.import_module(moduleName)
            
            if not hasattr(pluginModule, 'MANIFEST'):
                logging.error(f"Plugin {moduleName} has no MANIFEST, skipping")
                continue
                
            manifest = getattr(pluginModule, 'MANIFEST')
            if not isinstance(manifest, dict):
                logging.error(f"Plugin {moduleName} MANIFEST is not a dict, skipping")
                continue
            
            for eventType, functionName in manifest.items():
                if eventType == "INITIALIZER":
                    if not isinstance(functionName, str):
                        logging.error(f"Plugin {moduleName} INITIALIZER must be string, skipping")
                        continue
                    
                    if not hasattr(pluginModule, functionName):
                        logging.error(f"Plugin {moduleName} declares INITIALIZER function '{functionName}' but it doesn't exist")
                        continue
                        
                    handlerFunction = getattr(pluginModule, functionName)
                    if not callable(handlerFunction):
                        logging.error(f"Plugin {moduleName}.{functionName} is not callable")
                        continue
                    
                    sig = inspect.signature(handlerFunction)
                    allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                    actualParams = set(sig.parameters.keys())
                    
                    unknownParams = actualParams - allowedParams
                    if unknownParams:
                        logging.error(f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                      f"Allowed parameters are: {allowedParams}")
                        continue
                    
                    INITIALIZER_REGISTRY.append((handlerFunction, moduleName))
                    logging.info(f"Registered {moduleName}.{functionName} for INITIALIZER event")
                    continue
                
                if eventType == "UNCONDITIONAL":
                    interval = 1  # Default: every minute
                    handlerName = functionName
                    
                    if isinstance(functionName, list):
                        if len(functionName) == 2:
                            handlerName, interval = functionName
                        else:
                            logging.error(f"Plugin {moduleName} UNCONDITIONAL has invalid format, skipping")
                            continue
                    elif not isinstance(functionName, str):
                        logging.error(f"Plugin {moduleName} UNCONDITIONAL must be string or list, skipping")
                        continue
                    
                    if not hasattr(pluginModule, handlerName):
                        logging.error(f"Plugin {moduleName} declares UNCONDITIONAL function '{handlerName}' but it doesn't exist")
                        continue
                        
                    handlerFunction = getattr(pluginModule, handlerName)
                    if not callable(handlerFunction):
                        logging.error(f"Plugin {moduleName}.{handlerName} is not callable")
                        continue
                    
                    if not isinstance(interval, int) or interval <= 0 or interval > 60:
                        logging.error(f"Plugin {moduleName} UNCONDITIONAL interval must be integer 1-60, got {interval}")
                        continue
                    
                    sig = inspect.signature(handlerFunction)
                    allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                    actualParams = set(sig.parameters.keys())
                    
                    unknownParams = actualParams - allowedParams
                    if unknownParams:
                        logging.error(f"Plugin {moduleName}.{handlerName} has unknown parameters: {unknownParams}. "
                                      f"Allowed parameters are: {allowedParams}")
                        continue
                    
                    UNCONDITIONAL_REGISTRY.append((handlerFunction, interval))
                    logging.info(f"Registered {moduleName}.{handlerName} for UNCONDITIONAL event (interval: {interval})")
                    continue
                
                # Regular event types
                if eventType not in EVENT_TYPES_:
                    logging.error(f"Plugin {moduleName} declares invalid event type '{eventType}'. Valid types: {EVENT_TYPES_}")
                    continue
                    
                if not hasattr(pluginModule, functionName):
                    logging.error(f"Plugin {moduleName} declares function '{functionName}' but it doesn't exist")
                    continue
                    
                handlerFunction = getattr(pluginModule, functionName)
                if not callable(handlerFunction):
                    logging.error(f"Plugin {moduleName}.{functionName} is not callable")
                    continue
                
                sig = inspect.signature(handlerFunction)
                allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                actualParams = set(sig.parameters.keys())
                
                unknownParams = actualParams - allowedParams
                if unknownParams:
                    logging.error(f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                  f"Allowed parameters are: {allowedParams}")
                    continue
                
                PLUGIN_REGISTRY[eventType].append(handlerFunction)
                logging.info(f"Registered {moduleName}.{functionName} for event '{eventType}'")
                
        except Exception as e:
            logging.error(f"Failed to load plugin {pluginFile}: {e}")
            continue
    
    # Execute INITIALIZER functions serially
    failedPlugins_ = []
    if INITIALIZER_REGISTRY:
        logging.info(f"Executing {len(INITIALIZER_REGISTRY)} INITIALIZER plugins")
        
        for handlerFunction, pluginName in INITIALIZER_REGISTRY:
            try:
                emptyRawEvent = {"post_type": "initializer", "time": int(time.time())}
                result = PluginCallerSingle(handlerFunction, None, emptyRawEvent)
                
                if isinstance(result, dict) and "_error" in result:
                    logging.error(f"INITIALIZER for plugin {pluginName} failed: {result['_error']}")
                    failedPlugins_.append(pluginName)
                elif result is None:
                    logging.info(f"INITIALIZER for plugin {pluginName} completed successfully")
                else:
                    logging.error(f"INITIALIZER for plugin {pluginName} returned unexpected result: {result}")
                    
            except Exception as e:
                logging.error(f"INITIALIZER for plugin {pluginName} failed with exception: {e}")
                failedPlugins_.append(pluginName)
    
    # Remove failed plugins from all registries
    for pluginName in failedPlugins_:
        for eventType in PLUGIN_REGISTRY:
            PLUGIN_REGISTRY[eventType] = [
                handler for handler in PLUGIN_REGISTRY[eventType]
                if handler.__module__ != pluginName
            ]
        
        UNCONDITIONAL_REGISTRY[:] = [
            (handler, interval) for handler, interval in UNCONDITIONAL_REGISTRY
            if handler.__module__ != pluginName
        ]
        
        logging.error(f"Removed all functions for failed plugin: {pluginName}")
    
    totalHandlers = sum(len(handlerList_) for handlerList_ in PLUGIN_REGISTRY.values())
    totalUnconditional = len(UNCONDITIONAL_REGISTRY)
    totalInitializers = len(INITIALIZER_REGISTRY)
    totalFailed = len(failedPlugins_)
    
    logging.info(f"Plugin initialization complete. {totalHandlers} handlers registered for {len(PLUGIN_REGISTRY)} event types")
    logging.info(f"UNCONDITIONAL plugins: {totalUnconditional}")
    logging.info(f"INITIALIZER plugins: {totalInitializers} executed, {totalFailed} failed")
    
    if failedPlugins_:
        logging.error(f"Failed plugins removed: {', '.join(failedPlugins_)}")
    
    for eventType, handlerList_ in PLUGIN_REGISTRY.items():
        if handlerList_:
            logging.info(f"  {eventType}: {len(handlerList_)} handlers")
    
    # Start scheduler if needed
    if UNCONDITIONAL_REGISTRY:
        schedulerThread = threading.Thread(target=UnconditionalScheduler, daemon=True)
        schedulerThread.start()
        logging.info("Started UNCONDITIONAL scheduler thread")

def GroupMessageAnalyzer(rawEvent: Dict) -> str:
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

def EventTypeParser(rawEvent: Dict) -> str:
    match rawEvent.get("post_type"):
        case "message":
            match rawEvent.get("message_type"):
                case "private":
                    return "MESSAGE_PRIVATE"
                case "group":
                    return GroupMessageAnalyzer(rawEvent)
        
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
    
    logging.warning(f"Unrecognized event structure: post_type='{rawEvent.get('post_type')}', "
                   f"sub_type='{rawEvent.get('message_type', rawEvent.get('notice_type', rawEvent.get('request_type', rawEvent.get('meta_event_type'))))}', "
                   f"sub_sub_type='{rawEvent.get('sub_type')}'")
    return "UNEXPECTED"

def InbondMessageParser(rawEvent: Dict) -> Union[Dict, None]:
    eventType = EventTypeParser(rawEvent)
    
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

def SubprocessConfigReader(pluginName: str) -> Dict:
    dbPath = CONFIG['PATHS']['database_file']
    
    try:
        databaseConnect = sqlite3.connect(dbPath, timeout=5.0)
        databaseConnect.execute("PRAGMA query_only = ON")  # Read-only mode for safety
        cursor = databaseConnect.cursor()
        
        cursor.execute("""
            SELECT CONFIG_DATA FROM PLUGIN_CONFIGS 
            WHERE PLUGIN_NAME = ?
        """, (pluginName,))
        
        row = cursor.fetchone()
        databaseConnect.close()
        
        if row:
            try:
                config = json.loads(row[0])
                return config
            except json.JSONDecodeError as e:
                logging.error(f"ConfigReader: Invalid JSON for plugin {pluginName}: {e}")
                return {}
        else:
            return {}
            
    except Exception as e:
        logging.error(f"SubprocessConfigReader error for plugin {pluginName}: {e}")
        return {}

def SubprocessConfigWriter(pluginName: str, config: Dict) -> None:
    dbPath = CONFIG['PATHS']['database_file']
    
    if not isinstance(config, dict):
        logging.error(f"ConfigWriter: config must be a dict, got {type(config)} for plugin {pluginName}")
        return
    
    try:
        configData = json.dumps(config, ensure_ascii=False)
        timestamp = int(time.time())
        
        maxRetries = 3
        for attempt in range(maxRetries):
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
                """, (pluginName, configData, pluginName, timestamp, timestamp))
                
                databaseConnect.commit()
                databaseConnect.close()
                return
                
            except sqlite3.OperationalError as e:
                logging.warning(f"ConfigWriter attempt {attempt + 1}/{maxRetries} failed for plugin {pluginName}: {e}")
                if attempt < maxRetries - 1:
                    time.sleep(1)
                else:
                    logging.error(f"ConfigWriter failed after {maxRetries} attempts for plugin {pluginName}: {e}")
                    
            except Exception as e:
                logging.error(f"ConfigWriter database error for plugin {pluginName}: {e}")
                return
                
    except (TypeError, ValueError) as e:
        logging.error(f"ConfigWriter: Failed to serialize config for plugin {pluginName}: {e}")

def SubprocessApiCaller(action: str, data: Dict) -> Union[Dict, None]:
    if not isinstance(action, str) or not action:
        logging.error("ApiCaller: action must be non-empty string")
        return None
        
    if not isinstance(data, dict):
        logging.error("ApiCaller: data must be dict")
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
                logging.error(f"ApiCaller: Invalid JSON response from {action}: {e}")
                return None
        else:
            logging.error(f"ApiCaller: HTTP {response.status_code} from {action}")
            return None
            
    except requests.exceptions.Timeout:
        logging.error(f"ApiCaller: Timeout for {action}")
        return None
        
    except Exception as e:
        logging.error(f"ApiCaller: Request error for {action}: {e}")
        return None

def SubprocessLibrarian(eventIdentifier: Dict, eventCount: int = 50) -> List[Dict]:
    dbPath = CONFIG['PATHS']['database_file']
    databaseConnect = None
    
    try:
        databaseConnect = sqlite3.connect(dbPath, timeout=5.0)
        databaseConnect.execute("PRAGMA query_only = ON")
        cursor = databaseConnect.cursor()
        
        identifierType = eventIdentifier.get("type")
        
        match identifierType:
            case "private":
                userId = eventIdentifier.get("user_id")
                if not userId:
                    return []
                
                # eventCount=0 means no limit
                if eventCount == 0:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM FRIEND_EVENTS 
                        WHERE USER_ID = ? 
                        ORDER BY TIMESTAMP DESC
                    """, (userId,))
                else:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM FRIEND_EVENTS 
                        WHERE USER_ID = ? 
                        ORDER BY TIMESTAMP DESC 
                        LIMIT ?
                    """, (userId, eventCount))
                
            case "group":
                groupId = eventIdentifier.get("group_id")
                if not groupId:
                    return []
                
                if eventCount == 0:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM GROUP_EVENTS 
                        WHERE GROUP_ID = ? 
                        ORDER BY TIMESTAMP DESC
                    """, (groupId,))
                else:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM GROUP_EVENTS 
                        WHERE GROUP_ID = ? 
                        ORDER BY TIMESTAMP DESC 
                        LIMIT ?
                    """, (groupId, eventCount))
                
            case "other":
                eventType = eventIdentifier.get("event_type")
                if not eventType:
                    return []
                
                if eventCount == 0:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM OTHER_EVENTS 
                        WHERE EVENT_TYPE = ? 
                        ORDER BY TIMESTAMP DESC
                    """, (eventType,))
                else:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM OTHER_EVENTS 
                        WHERE EVENT_TYPE = ? 
                        ORDER BY TIMESTAMP DESC 
                        LIMIT ?
                    """, (eventType, eventCount))
                
            case _:
                return []
        
        rows = cursor.fetchall()
        
        events = []
        for i, row in enumerate(rows):
            try:
                event = json.loads(row[0])
                events.append(event)
            except json.JSONDecodeError as e:
                logging.warning(f"SubprocessLibrarian: Corrupted JSON data in database record {i+1}/{len(rows)}, skipping: {e}")
                continue
        
        events.reverse()  # Return chronological order
        return events
        
    except Exception as e:
        logging.error(f"SubprocessLibrarian error: {e}")
        return []
    finally:
        if databaseConnect:
            try:
                databaseConnect.close()
            except Exception:
                pass

def PluginWorker(handler, simpleEvent: Union[Dict, None], rawEvent: Dict, resultPipe, memoryLimit: int):
    try:
        # Set memory limit (Linux only)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memoryLimit, memoryLimit))
        except Exception as e:
            logging.warning(f"Failed to set memory limit: {e}")
        
        pluginName = getattr(handler, '__module__', 'unknown_plugin')
        
        # Create plugin-specific config functions
        def ConfigReader() -> Dict:
            return SubprocessConfigReader(pluginName)
        
        def ConfigWriter(config: Dict) -> None:
            return SubprocessConfigWriter(pluginName, config)
        
        botContext = {
            "Librarian": SubprocessLibrarian,
            "ConfigReader": ConfigReader,
            "ConfigWriter": ConfigWriter,
            "ApiCaller": SubprocessApiCaller
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
        logging.warning(f"Error monitoring process: {e}")
        return None

def PluginCallerSingle(handler, simpleEvent: Union[Dict, None], rawEvent: Dict):
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
                    logging.error(f"Error receiving result from plugin {handler.__name__}: {e}")
                    return None
            
            terminationReason = PluginMonitor(
                process, startTime, maxCpuTime, maxWallTime, memoryLimit
            )
            
            if terminationReason:
                logging.error(f"Plugin {handler.__name__} terminated: {terminationReason}")
                
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()
                    
                return None
        
        exitCode = process.exitcode
        if exitCode != 0:
            logging.error(f"Plugin {handler.__name__} exited with code {exitCode}")
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to execute plugin {handler.__name__} in subprocess: {e}")
        return None

def PluginCaller(
    handlers_: List[Callable], 
    simpleEvent: Union[Dict, None], 
    rawEvent: Dict,
    resultCallback: Optional[Callable] = None
) -> List[Any]:
    
    if not handlers_:
        return []
    
    results = {}
    resultQueue = queue.Queue()
    
    def executePluginThread(handler, handlerIndex):
        try:
            result = PluginCallerSingle(handler, simpleEvent, rawEvent)
            
            # Convert errors to None for parallel execution
            if isinstance(result, dict) and "_error" in result:
                logging.error(f"Plugin {handler.__name__} raised {result['_type']}: {result['_error']}")
                result = None
            
            resultQueue.put((handlerIndex, handler, result))
        except Exception as e:
            logging.error(f"Thread execution error for plugin {handler.__name__}: {e}")
            resultQueue.put((handlerIndex, handler, None))
    
    # Start all plugin threads
    threads_ = []
    for i, handler in enumerate(handlers_):
        thread = threading.Thread(target=executePluginThread, args=(handler, i))
        thread.daemon = True
        thread.start()
        threads_.append(thread)
    
    # Process results as they complete
    completedCount = 0
    maxWaitTime = CONFIG['PLUGIN_EXECUTION']['max_wall_time_seconds'] + 5  # +5s for cleanup
    
    while completedCount < len(handlers_):
        try:
            handlerIndex, handler, result = resultQueue.get(timeout=maxWaitTime)
            completedCount += 1
            
            results[handlerIndex] = result
            
            # Immediate callback for successful results
            if resultCallback and result is not None:
                try:
                    resultCallback(result, rawEvent)
                except Exception as e:
                    logging.error(f"Error in result callback for plugin {handler.__name__}: {e}")
                    
        except queue.Empty:
            logging.warning(f"Timeout waiting for plugin results after {maxWaitTime} seconds")
            break
    
    # Cleanup threads
    for thread in threads_:
        thread.join(timeout=1)
        if thread.is_alive():
            logging.warning(f"Thread still alive after receiving its result - possible bug")
    
    # Return results in original order
    orderedResults = []
    for i in range(len(handlers_)):
        orderedResults.append(results.get(i, None))
    
    return orderedResults

def NapCatSender(actionEndpoint: str, requestBody: Dict) -> None:
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
                logging.warning(f"Client error {response.status_code} for {actionEndpoint}")
                return
            
            if response.status_code == 200:
                try:
                    responseData = response.json()
                    status = responseData.get('status', '').lower()
                    if status in ['ok', 'async']:
                        return
                    else:
                        logging.error(f"API returned status '{status}' for {actionEndpoint}")
                        break
                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Invalid JSON response from {actionEndpoint}: {e}")
                    break
            
            logging.warning(f"HTTP {response.status_code} from {actionEndpoint}, attempt {attempt + 1}/{CONFIG['HTTP']['max_retries']}")
            
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout for {actionEndpoint}, attempt {attempt + 1}/{CONFIG['HTTP']['max_retries']}")
            
        except Exception as e:
            logging.error(f"Request error for {actionEndpoint}: {e}")
            break
    
    # Diagnostic: check bot status
    try:
        statusUrl = f"{baseUrl}/get_status"
        statusResponse = requests.get(statusUrl, timeout=CONFIG['HTTP']['status_check_timeout'])
        if statusResponse.status_code == 200:
            statusData = statusResponse.json()
            logging.error(f"Failed to send {actionEndpoint}. Bot status: {statusData}")
        else:
            logging.error(f"Failed to send {actionEndpoint}. Could not get bot status (HTTP {statusResponse.status_code})")
    except Exception as e:
        logging.error(f"Failed to send {actionEndpoint}. Could not get bot status: {e}")

def OutbondMessageParser(pluginResponse: Any, rawEvent: Dict) -> None:
    if isinstance(pluginResponse, str):
        postType = rawEvent.get("post_type")
        
        if postType == "message":
            messageType = rawEvent.get("message_type")
            
            if messageType == "private":
                requestBody = {
                    "user_id": rawEvent.get("user_id"),
                    "message": [{"type": "text", "data": {"text": pluginResponse}}]
                }
                NapCatSender("send_private_msg", requestBody)
                
            elif messageType == "group":
                requestBody = {
                    "group_id": rawEvent.get("group_id"),
                    "message": [{"type": "text", "data": {"text": pluginResponse}}]
                }
                NapCatSender("send_group_msg", requestBody)
                
        elif postType == "notice":
            eventType = EventTypeParser(rawEvent)
            
            if eventType == "NOTICE_BOT_OFFLINE":
                logging.warning("Cannot send message for NOTICE_BOT_OFFLINE event")
                return
                
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
                logging.warning(f"Notice event {eventType} has neither group_id nor user_id")
                
        else:
            logging.warning(f"String response not supported for post_type '{postType}'")
            
    elif isinstance(pluginResponse, dict):
        if "action" not in pluginResponse:
            logging.warning("Plugin dict response missing 'action' key")
            return
            
        if "data" not in pluginResponse:
            logging.warning("Plugin dict response missing 'data' key")
            return
            
        action = pluginResponse["action"]
        data = pluginResponse["data"]
        
        if not isinstance(action, str):
            logging.warning(f"Plugin response 'action' field must be string, got {type(action)}")
            return
            
        if not isinstance(data, dict):
            logging.warning(f"Plugin response 'data' field must be dict, got {type(data)}")
            return
        
        NapCatSender(action, data)
            
    elif isinstance(pluginResponse, list):
        for i, item in enumerate(pluginResponse):
            if not isinstance(item, (str, dict)):
                logging.warning(f"Plugin list response contains invalid item at index {i}: "
                              f"expected str or dict, got {type(item).__name__}. "
                              f"Skipping invalid item: {repr(item)}")
                continue
            
            OutbondMessageParser(item, rawEvent)
            
    else:
        logging.warning(f"Invalid plugin response type: {type(pluginResponse).__name__}. "
                       f"Expected str, dict, or list of str/dict, got {repr(pluginResponse)}")
        return

def Historian(rawEvent: Dict) -> None:
    eventType = EventTypeParser(rawEvent)
    
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
    if not tableName:
        tableName = "OTHER_EVENTS"
        insertSql = "INSERT INTO OTHER_EVENTS (EVENT_TYPE, EVENT_DATA, TIMESTAMP) VALUES (?, ?, ?)"
        insertParams = (eventType, eventData, timestamp)
    
    dbPath = CONFIG['PATHS']['database_file']
    maxRetries = 3
    
    for attempt in range(maxRetries):
        try:
            databaseConnect = sqlite3.connect(dbPath, timeout=10.0)
            databaseConnect.execute(insertSql, insertParams)
            databaseConnect.commit()
            databaseConnect.close()
            return
            
        except sqlite3.OperationalError as e:
            logging.warning(f"Historian attempt {attempt + 1}/{maxRetries} failed for {tableName}: {e}")
            if attempt < maxRetries - 1:
                time.sleep(1)
            else:
                logging.error(f"Historian failed after {maxRetries} attempts for {tableName}: {e}")
                
        except Exception as e:
            logging.error(f"Historian database error for {tableName}: {e}")
            return

def ConfigReader(pluginName: str) -> Dict:
    dbPath = CONFIG['PATHS']['database_file']
    
    try:
        if not pluginName:
            logging.warning("ConfigReader: empty plugin name")
            return {}
            
        databaseConnect = sqlite3.connect(dbPath, timeout=5.0)
        cursor = databaseConnect.cursor()
        
        cursor.execute("""
            SELECT CONFIG_DATA FROM PLUGIN_CONFIGS 
            WHERE PLUGIN_NAME = ?
        """, (pluginName,))
        
        row = cursor.fetchone()
        databaseConnect.close()
        
        if row:
            try:
                config = json.loads(row[0])
                return config
            except json.JSONDecodeError as e:
                logging.error(f"ConfigReader: Invalid JSON for plugin {pluginName}: {e}")
                return {}
        else:
            return {}
            
    except Exception as e:
        logging.error(f"ConfigReader error for plugin {pluginName}: {e}")
        return {}

def ConfigWriter(pluginName: str, config: Dict) -> None:
    dbPath = CONFIG['PATHS']['database_file']
    
    if not pluginName:
        logging.error("ConfigWriter: empty plugin name")
        return
        
    if not isinstance(config, dict):
        logging.error(f"ConfigWriter: config must be a dict, got {type(config)} for plugin {pluginName}")
        return
    
    try:
        configData = json.dumps(config, ensure_ascii=False)
        timestamp = int(time.time())
        
        maxRetries = 3
        for attempt in range(maxRetries):
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
                """, (pluginName, configData, pluginName, timestamp, timestamp))
                
                databaseConnect.commit()
                databaseConnect.close()
                return
                
            except sqlite3.OperationalError as e:
                logging.warning(f"ConfigWriter attempt {attempt + 1}/{maxRetries} failed for plugin {pluginName}: {e}")
                if attempt < maxRetries - 1:
                    time.sleep(1)
                else:
                    logging.error(f"ConfigWriter failed after {maxRetries} attempts for plugin {pluginName}: {e}")
                    
            except Exception as e:
                logging.error(f"ConfigWriter database error for plugin {pluginName}: {e}")
                return
                
    except (TypeError, ValueError) as e:
        logging.error(f"ConfigWriter: Failed to serialize config for plugin {pluginName}: {e}")

def Librarian(eventIdentifier: Dict, eventCount: int = 50) -> List[Dict]:
    dbPath = CONFIG['PATHS']['database_file']
    databaseConnect = None
    
    try:
        databaseConnect = sqlite3.connect(dbPath, timeout=5.0)
        cursor = databaseConnect.cursor()
        
        identifierType = eventIdentifier.get("type")
        
        match identifierType:
            case "private":
                userId = eventIdentifier.get("user_id")
                if not userId:
                    logging.warning("Librarian: private type missing user_id")
                    return []
                
                # eventCount=0 means no limit
                if eventCount == 0:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM FRIEND_EVENTS 
                        WHERE USER_ID = ? 
                        ORDER BY TIMESTAMP DESC
                    """, (userId,))
                else:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM FRIEND_EVENTS 
                        WHERE USER_ID = ? 
                        ORDER BY TIMESTAMP DESC 
                        LIMIT ?
                    """, (userId, eventCount))
                
            case "group":
                groupId = eventIdentifier.get("group_id")
                if not groupId:
                    logging.warning("Librarian: group type missing group_id")
                    return []
                
                if eventCount == 0:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM GROUP_EVENTS 
                        WHERE GROUP_ID = ? 
                        ORDER BY TIMESTAMP DESC
                    """, (groupId,))
                else:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM GROUP_EVENTS 
                        WHERE GROUP_ID = ? 
                        ORDER BY TIMESTAMP DESC 
                        LIMIT ?
                    """, (groupId, eventCount))
                
            case "other":
                eventType = eventIdentifier.get("event_type")
                if not eventType:
                    logging.warning("Librarian: other type missing event_type")
                    return []
                
                if eventCount == 0:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM OTHER_EVENTS 
                        WHERE EVENT_TYPE = ? 
                        ORDER BY TIMESTAMP DESC
                    """, (eventType,))
                else:
                    cursor.execute("""
                        SELECT EVENT_DATA FROM OTHER_EVENTS 
                        WHERE EVENT_TYPE = ? 
                        ORDER BY TIMESTAMP DESC 
                        LIMIT ?
                    """, (eventType, eventCount))
                
            case _:
                logging.warning(f"Librarian: unknown identifier type '{identifierType}'")
                return []
        
        rows = cursor.fetchall()
        
        events = []
        for i, row in enumerate(rows):
            try:
                event = json.loads(row[0])
                events.append(event)
            except json.JSONDecodeError as e:
                logging.warning(f"Librarian: Corrupted JSON data in database record {i+1}/{len(rows)}, skipping: {e}")
                continue
        
        events.reverse()  # Return chronological order
        return events
        
    except sqlite3.OperationalError as e:
        logging.error(f"Librarian database error: {e}")
        return []
        
    except Exception as e:
        logging.error(f"Librarian failed to read history: {e}")
        return []
    finally:
        if databaseConnect:
            try:
                databaseConnect.close()
            except Exception:
                pass

def MainDispatcher(rawEvent: Dict) -> None:
    eventType = EventTypeParser(rawEvent)
    
    if eventType == "UNEXPECTED":
        return
        
    simpleEvent = InbondMessageParser(rawEvent)
    
    # Store history synchronously to ensure plugins can read it immediately
    Historian(rawEvent)
    
    # Collect handlers to trigger (including inherited events)
    eventTypesToTrigger = [eventType]
    if eventType in EVENT_INHERITANCE:
        eventTypesToTrigger.extend(EVENT_INHERITANCE[eventType])
    
    # Deduplicate handlers
    all_handlers = []
    processed_handlers = set()
    
    for triggerType in eventTypesToTrigger:
        handlerList_ = PLUGIN_REGISTRY.get(triggerType, [])
        for handler in handlerList_:
            if handler not in processed_handlers:
                processed_handlers.add(handler)
                all_handlers.append(handler)
    
    # Execute all plugins in parallel with immediate response
    if all_handlers:
        def response_callback(result, event):
            OutbondMessageParser(result, event)
        
        PluginCaller(all_handlers, simpleEvent, rawEvent, response_callback)

def InitializerGuard():
    global INITIALIZED
    if INITIALIZED:
        return
        
    with INIT_LOCK:
        if not INITIALIZED:
            try:
                multiprocessing.set_start_method(CONFIG['PLUGIN_EXECUTION']['process_creation_method'], force=True)
            except Exception as e:
                logging.critical(f"Failed to set multiprocessing start method: {e}")
                sys.exit(1)
            Initializer()
            INITIALIZED = True

NAPCAT_LISTENER = Flask(__name__)
@NAPCAT_LISTENER.route('/', methods=['POST'])
def NapCatListener() -> str:
    InitializerGuard()  # 懒加载初始化
    
    rawEvent = request.get_json()
    
    if AdminDispatcher(rawEvent):
        return 'OK'
    
    if IS_MUTED:
        return 'OK'
    
    MainDispatcher(rawEvent)
    return 'OK'



if __name__ == '__main__':
    InitializerGuard()
    try:
        NAPCAT_LISTENER.run(host=CONFIG['NAPCAT_LISTEN']['host'], port=CONFIG['NAPCAT_LISTEN']['port'])
    except Exception as e:
        logging.critical(f"Failed to start HTTP server: {e}")
        sys.exit(1)
