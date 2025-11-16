#!/usr/bin/env python3
"""
Askr Framework - Server module
Handles Flask app, event routing, API communication, and main entry point
Version: Beta 0.2.1
License: GPL v3
"""
import json
import requests
import time
import datetime
import threading
import multiprocessing
import sys
from flask import Flask, request
from typing import Dict, Union, Any
import config
import database
import plugin


# Flask application
NAPCAT_LISTENER = Flask(__name__)


@NAPCAT_LISTENER.route('/', methods=['POST'])
def NapCatListener() -> str:
    """Handle incoming events from NapCat."""
    try:
        rawEvent = request.get_json()

        # Validate we received JSON data
        if rawEvent is None:
            config.logger.warning("Received POST request with no JSON body or invalid Content-Type")
            return 'OK'  # Return OK to avoid NapCat retry storms

        # Handle admin commands first
        if AdminDispatcher(rawEvent):
            return 'OK'

        # Check mute status
        if config.IS_MUTED:
            return 'OK'

        # Dispatch to main handler
        MainDispatcher(rawEvent)
        return 'OK'

    except Exception as e:
        # Log the error with full traceback
        config.logger.error(f"Fatal error in NapCatListener: {e}", exc_info=True)
        config.AdminNotifier('ERROR', f"Fatal error in NapCatListener: {e}")

        # Still return 'OK' to prevent NapCat from retrying
        # (retrying a broken request will just cause more errors)
        return 'OK'


@NAPCAT_LISTENER.route('/health', methods=['GET'])
def HealthCheck() -> dict:
    """Health check endpoint for monitoring."""
    NapCatServerStatus = 'Unreachable'
    try:
        baseUrl = config.CONFIG['NAPCAT_SERVER']['api_url']
        statusUrl = f"{baseUrl}/get_status"
        statusResponse = requests.get(statusUrl, timeout=config.CONFIG['HTTP']['status_check_timeout'])
        if statusResponse.status_code == 200:
            statusData = statusResponse.json()
            if statusData.get('status', '') == 'ok':
                NapCatServerStatus = 'OK'
    except Exception as e:
        config.logger.error(f"Failed to check NapCat server status: {e}")
        config.AdminNotifier('ERROR', f"Failed to check NapCat server status: {e}")

    health_status = {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'is_muted': config.IS_MUTED,
        'version': 'Beta 0.2.1',
        'NapCatServerStatus': NapCatServerStatus
    }

    return health_status


def Initializer():
    """Ensure framework is initialized exactly once."""
    if config.INITIALIZED:
        return

    with config.INIT_LOCK:
        if not config.INITIALIZED:
            try:
                # Only set multiprocessing start method if not already set
                if multiprocessing.get_start_method(allow_none=True) is None:
                    multiprocessing.set_start_method(config.CONFIG['PLUGIN_EXECUTION']['process_creation_method'])
                    config.logger.info(f"Set multiprocessing start method to {config.CONFIG['PLUGIN_EXECUTION']['process_creation_method']}")
                    config.AdminNotifier('INFO', f"Set multiprocessing start method to {config.CONFIG['PLUGIN_EXECUTION']['process_creation_method']}")
            except Exception as e:
                config.logger.warning(f"Could not set multiprocessing start method: {e}")
                config.AdminNotifier('WARNING', f"Could not set multiprocessing start method: {e}")
                # This is not critical, continue with default

            ActualInitializer()
            config.INITIALIZED = True


def ActualInitializer() -> None:
    """Initialize the framework, load plugins, and start background services."""
    # Load configurations first
    config.FrameworkConfigReader()
    config.PluginsAccessControlLoader()

    # Initialize database
    database.DatabaseInitializer()

    # Initialize plugin registry
    plugin.RegistryInitializer()

    # Start unconditional event generator
    UnconditionalEventInitializer()


def UnconditionalEventInitializer() -> None:
    """Initialize the unconditional event generator."""
    thread = threading.Thread(target=UnconditionalEventGenerator, daemon=True)
    thread.start()
    config.logger.info("Unconditional event generator started")
    config.AdminNotifier('INFO', "Unconditional event generator started")


def UnconditionalEventGenerator() -> None:
    """Generate UNCONDITIONAL events at scheduled intervals."""
    config.logger.info("Starting UNCONDITIONAL event generator")
    config.AdminNotifier('INFO', "Starting UNCONDITIONAL event generator")

    while True:
        now = datetime.datetime.now()
        secondsToNextMinute = 60 - now.second + 3  # +3s buffer to avoid rounding errors
        time.sleep(secondsToNextMinute)

        unconditional_event = {
            "post_type": "unconditional",
            "time": int(time.time())
        }

        try:
            url = f"http://localhost:{config.CONFIG['NAPCAT_LISTEN']['port']}/"
            response = requests.post(url, json=unconditional_event, timeout=5.0)
            if response.status_code != 200:
                config.logger.error(f"Failed to send unconditional event: HTTP {response.status_code}")
                config.AdminNotifier('ERROR', f"Failed to send unconditional event: HTTP {response.status_code}")
        except Exception as e:
            config.logger.error(f"Failed to send unconditional event: {e}")
            config.AdminNotifier('ERROR', f"Failed to send unconditional event: {e}")


def AdminDispatcher(rawEvent: Dict) -> bool:
    """Handle admin control commands (mute/unmute)."""
    adminQQ = config.CONFIG['ADMIN_NOTIFICATION']['admin_qq']
    if (rawEvent.get("post_type") == "message" and
        rawEvent.get("message_type") == "private" and
        rawEvent.get("user_id") == adminQQ and adminQQ != 0):

        command = rawEvent.get("raw_message", "").strip()

        if command == "mute":
            config.IS_MUTED = True
            config.logger.info(f"Admin {adminQQ} activated mute mode")
            config.AdminNotifier('INFO', f"Admin {adminQQ} activated mute mode")
            return True
        elif command == "unmute":
            config.IS_MUTED = False
            config.logger.info(f"Admin {adminQQ} deactivated mute mode")
            config.AdminNotifier('INFO', f"Admin {adminQQ} deactivated mute mode")
            return True

    return False


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

    config.logger.warning(f"Unrecognized event structure: post_type='{rawEvent.get('post_type')}',full event ={rawEvent}")
    config.AdminNotifier('WARNING', f"Unrecognized event structure: post_type='{rawEvent.get('post_type')}',full event ={rawEvent}")
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
    baseUrl = config.CONFIG['NAPCAT_SERVER']['api_url']
    fullUrl = f"{baseUrl}/{actionEndpoint}"

    for attempt in range(config.CONFIG['HTTP']['max_retries']):
        try:
            response = requests.post(
                fullUrl,
                json=requestBody,
                timeout=config.CONFIG['HTTP']['timeout_seconds']
            )

            if 400 <= response.status_code < 500:
                config.logger.warning(f"Client error {response.status_code} for {actionEndpoint}")
                config.AdminNotifier('WARNING', f"Client error {response.status_code} for {actionEndpoint}")
                return

            if response.status_code == 200:
                try:
                    responseData = response.json()
                    status = responseData.get('status', '').lower()
                    if status in ['ok', 'async']:
                        return
                    else:
                        config.logger.error(f"API returned status '{status}' for {actionEndpoint}")
                        config.AdminNotifier('ERROR', f"API returned status '{status}' for {actionEndpoint}")
                        break
                except (json.JSONDecodeError, KeyError) as e:
                    config.logger.error(f"Invalid JSON response from {actionEndpoint}: {e}")
                    config.AdminNotifier('ERROR', f"Invalid JSON response from {actionEndpoint}: {e}")
                    break

            config.logger.warning(f"HTTP {response.status_code} from {actionEndpoint}, attempt {attempt + 1}/{config.CONFIG['HTTP']['max_retries']}")
            config.AdminNotifier('WARNING', f"HTTP {response.status_code} from {actionEndpoint}, attempt {attempt + 1}/{config.CONFIG['HTTP']['max_retries']}")

        except requests.exceptions.Timeout:
            config.logger.warning(f"Timeout for {actionEndpoint}, attempt {attempt + 1}/{config.CONFIG['HTTP']['max_retries']}")
            config.AdminNotifier('WARNING', f"Timeout for {actionEndpoint}, attempt {attempt + 1}/{config.CONFIG['HTTP']['max_retries']}")

        except Exception as e:
            config.logger.error(f"Request error for {actionEndpoint}: {e}")
            config.AdminNotifier('ERROR', f"Request error for {actionEndpoint}: {e}")
            break

    # Diagnostic: check bot status
    try:
        statusUrl = f"{baseUrl}/get_status"
        statusResponse = requests.get(statusUrl, timeout=config.CONFIG['HTTP']['status_check_timeout'])
        if statusResponse.status_code == 200:
            statusData = statusResponse.json()
            config.logger.error(f"Failed to send {actionEndpoint}. Bot status: {statusData}")
            config.AdminNotifier('ERROR', f"Failed to send {actionEndpoint}. Bot status: {statusData}")
        else:
            config.logger.error(f"Failed to send {actionEndpoint}. Could not get bot status (HTTP {statusResponse.status_code})")
            config.AdminNotifier('ERROR', f"Failed to send {actionEndpoint}. Could not get bot status (HTTP {statusResponse.status_code})")
    except Exception as e:
        config.logger.error(f"Failed to send {actionEndpoint}. Could not get bot status: {e}")
        config.AdminNotifier('ERROR', f"Failed to send {actionEndpoint}. Could not get bot status: {e}")


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
            config.logger.warning(f"String response not supported for event {EventTypeParser(rawEvent)}")
            config.AdminNotifier('WARNING', f"String response not supported for event {EventTypeParser(rawEvent)}")

    elif isinstance(pluginResponse, dict):
        if ("action" not in pluginResponse) or ("data" not in pluginResponse):
            config.logger.warning("Plugin dict response missing 'action' key or 'data' key")
            config.AdminNotifier('WARNING', "Plugin dict response missing 'action' key or 'data' key")
            return

        action = pluginResponse["action"]
        data = pluginResponse["data"]

        if (not isinstance(action, str)) or (not isinstance(data, dict)):
            config.logger.warning(f"Plugin dict response wrong type: got {type(action)}")
            config.AdminNotifier('WARNING', f"Plugin dict response wrong type: got {type(action)}")
            return

        NapCatSender(action, data)

    elif isinstance(pluginResponse, list):
        for i, item in enumerate(pluginResponse):
            if not isinstance(item, (str, dict)):
                config.logger.warning(f"Plugin list response contains invalid item at index {i}: expected str or dict, got {type(item).__name__}.")
                config.AdminNotifier('WARNING', f"Plugin list response contains invalid item at index {i}: expected str or dict, got {type(item).__name__}.")
            else:
                OutbondMessageParser(item, rawEvent)

    else:
        config.logger.warning(f"Invalid plugin response type: {type(pluginResponse).__name__}. Expected str, dict, or list of str/dict, got {repr(pluginResponse)}")
        config.AdminNotifier('WARNING', f"Invalid plugin response type: {type(pluginResponse).__name__}. Expected str, dict, or list of str/dict, got {repr(pluginResponse)}")
        return


def MainDispatcher(rawEvent: Dict) -> None:
    """Main event dispatcher that routes events to appropriate plugins."""
    eventType = EventTypeParser(rawEvent)
    HandlersToExecute_ = []
    simpleEvent = InbondMessageParser(rawEvent, eventType)
    if eventType == "UNEXPECTED":
        return

    elif eventType == "UNCONDITIONAL":
        currentMinute = datetime.datetime.fromtimestamp(rawEvent["time"]).minute
        for handler, interval in config.PLUGIN_REGISTRY.get("UNCONDITIONAL", []):
            if currentMinute % interval == 0:
                HandlersToExecute_.append(handler)
    else:
        database.Historian(rawEvent, eventType)
        eventTypesToTrigger_ = [eventType]
        if eventType in config.EVENT_INHERITANCE:
            eventTypesToTrigger_.extend(config.EVENT_INHERITANCE[eventType])

        # Deduplicate handlers
        matchedHandlers_ = set()

        for triggerType in eventTypesToTrigger_:
            handlerList_ = config.PLUGIN_REGISTRY.get(triggerType, [])
            for handler in handlerList_:
                matchedHandlers_.add(handler)

        # Apply access control filtering
        for handler in matchedHandlers_:
            if plugin.CheckPluginAccess(handler, rawEvent):
                HandlersToExecute_.append(handler)
            else:
                pluginName = getattr(handler, '__module__', 'unknown')
                config.logger.debug(f"Access denied for plugin {pluginName} on event {eventType}")
                config.AdminNotifier('DEBUG', f"Access denied for plugin {pluginName} on event {eventType}")

    # Execute filtered plugins in parallel with immediate response
    if HandlersToExecute_:
        def ResponseProcessor(result, event):
            OutbondMessageParser(result, event)

        plugin.PluginCaller(HandlersToExecute_, simpleEvent, rawEvent, ResponseProcessor)


# Initialize framework when module is imported by Gunicorn/Uvicorn
# This ensures plugins are loaded and background services are started
Initializer()
