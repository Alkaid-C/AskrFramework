"""
Database module for Askr Framework
Handles all database operations including initialization, history storage, and queries
"""
import json
import sqlite3
import time
import datetime
import sys
from typing import Dict, List, Union, Optional
from . import config


def DatabaseInitializer() -> None:
    """Initialize SQLite database with required tables and indexes."""
    dbPath = config.CONFIG['PATHS']['database_file']

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

        config.logger.info(f"Database initialized successfully at {dbPath}")
        config.AdminNotifier('INFO', f"Database initialized successfully at {dbPath}")

    except Exception as e:
        config.logger.critical(f"Failed to initialize database: {e}")
        config.AdminNotifier('CRITICAL', f"Failed to initialize database: {e}")
        sys.exit(1)


def Historian(rawEvent: Dict) -> None:
    """Save event to database for historical queries."""
    from .server import EventTypeParser  # Import here to avoid circular dependency

    eventType = EventTypeParser(rawEvent)

    # Skip high-frequency useless events
    if eventType == "NOTICE_INPUT_STATUS":
        return

    # Don't store internal unconditional events
    if eventType == "UNCONDITIONAL":
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

    dbPath = config.CONFIG['PATHS']['database_file']
    maxRetries = 3

    for attempt in range(maxRetries):
        try:
            databaseConnect = sqlite3.connect(dbPath, timeout=10.0)
            databaseConnect.execute(insertSql, insertParams)
            databaseConnect.commit()
            databaseConnect.close()
            return

        except sqlite3.OperationalError as e:
            config.logger.warning(f"Historian attempt {attempt + 1}/{maxRetries} failed for {tableName}: {e}")
            config.AdminNotifier('WARNING', f"Historian attempt {attempt + 1}/{maxRetries} failed for {tableName}: {e}")
            if attempt < maxRetries - 1:
                time.sleep(1)
            else:
                config.logger.error(f"Historian failed after {maxRetries} attempts for {tableName}: {e}")
                config.AdminNotifier('ERROR', f"Historian failed after {maxRetries} attempts for {tableName}: {e}")

        except Exception as e:
            config.logger.error(f"Historian database error for {tableName}: {e}")
            config.AdminNotifier('ERROR', f"Historian database error for {tableName}: {e}")
            return


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
    dbPath = config.CONFIG['PATHS']['database_file']
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
                config.logger.warning(f"SubprocessLibrarian: Corrupted JSON data in database record {i+1}/{len(rows)}, skipping: {e}")
                config.AdminNotifier('WARNING', f"SubprocessLibrarian: Corrupted JSON data in database record {i+1}/{len(rows)}, skipping: {e}")
                continue

        events.reverse()  # Return chronological order

        if stringOutput:
            return HistoryParser(events)
        else:
            return events

    except Exception as e:
        config.logger.error(f"SubprocessLibrarian error: {e}")
        config.AdminNotifier('ERROR', f"SubprocessLibrarian error: {e}")
        return [] if not stringOutput else ""
    finally:
        if databaseConnect:
            try:
                databaseConnect.close()
            except Exception:
                pass


def SubprocessConfigReader(pluginName: str) -> Dict:
    """Read plugin configuration from database (subprocess version)."""
    dbPath = config.CONFIG['PATHS']['database_file']

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
                config_data = json.loads(row[0])
                return config_data
            except json.JSONDecodeError as e:
                config.logger.error(f"ConfigReader: Invalid JSON for plugin {pluginName}: {e}")
                config.AdminNotifier('ERROR', f"ConfigReader: Invalid JSON for plugin {pluginName}: {e}")
                return {}
        else:
            return {}

    except Exception as e:
        config.logger.error(f"SubprocessConfigReader error for plugin {pluginName}: {e}")
        config.AdminNotifier('ERROR', f"SubprocessConfigReader error for plugin {pluginName}: {e}")
        return {}


def SubprocessConfigWriter(pluginName: str, config_data: Dict) -> None:
    """Write plugin configuration to database (subprocess version)."""
    dbPath = config.CONFIG['PATHS']['database_file']

    if not isinstance(config_data, dict):
        config.logger.error(f"ConfigWriter: config must be a dict, got {type(config_data)} for plugin {pluginName}")
        config.AdminNotifier('ERROR', f"ConfigWriter: config must be a dict, got {type(config_data)} for plugin {pluginName}")
        return

    try:
        configDataJson = json.dumps(config_data, ensure_ascii=False)
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
                """, (pluginName, configDataJson, pluginName, timestamp, timestamp))

                databaseConnect.commit()
                databaseConnect.close()
                return

            except sqlite3.OperationalError as e:
                config.logger.warning(f"ConfigWriter attempt {attempt + 1}/{maxRetries} failed for plugin {pluginName}: {e}")
                config.AdminNotifier('WARNING', f"ConfigWriter attempt {attempt + 1}/{maxRetries} failed for plugin {pluginName}: {e}")
                if attempt < maxRetries - 1:
                    time.sleep(1)
                else:
                    config.logger.error(f"ConfigWriter failed after {maxRetries} attempts for plugin {pluginName}: {e}")
                    config.AdminNotifier('ERROR', f"ConfigWriter failed after {maxRetries} attempts for plugin {pluginName}: {e}")

            except Exception as e:
                config.logger.error(f"ConfigWriter database error for plugin {pluginName}: {e}")
                config.AdminNotifier('ERROR', f"ConfigWriter database error for plugin {pluginName}: {e}")
                return

    except (TypeError, ValueError) as e:
        config.logger.error(f"ConfigWriter: Failed to serialize config for plugin {pluginName}: {e}")
        config.AdminNotifier('ERROR', f"ConfigWriter: Failed to serialize config for plugin {pluginName}: {e}")
