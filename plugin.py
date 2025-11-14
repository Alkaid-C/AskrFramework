"""
Plugin module for Askr Framework
Handles plugin loading, execution, access control, and resource monitoring
"""
import os
import sys
import importlib
import inspect
import multiprocessing
import threading
import queue
import time
import resource  # type: ignore
import psutil  # type: ignore
from typing import List, Dict, Optional, Union, Any, Callable
from . import config
from . import database


def CheckPluginAccess(handler: Callable, rawEvent: Dict) -> bool:
    """Check if a plugin handler has access to the event."""
    pluginName = getattr(handler, '__module__', 'unknown')
    if not pluginName.endswith('.py'):
        pluginName += '.py'

    groupID = rawEvent.get('group_id')

    # Get rules
    default_policy = config.PLUGIN_ACCESS_RULES.get('default_policy', 'allow')
    all_rules = config.PLUGIN_ACCESS_RULES.get('rules', {})

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
                config.logger.debug(f"Plugin {pluginName} is not activated by specific rules for {context} {contextID}")
                config.AdminNotifier('DEBUG', f"Plugin {pluginName} is not activated by specific rules for {context} {contextID}")
            return result

    # Then Check global rules
    if 'global' in all_rules:
        global_rules = all_rules['global'].get(context, {})
        result = ListChecker(global_rules, contextID)
        if result is not None:
            if not result:  # Explicitly denied by global rules
                config.logger.debug(f"Plugin {pluginName} is not activated by global rules for {context} {contextID}")
                config.AdminNotifier('DEBUG', f"Plugin {pluginName} is not activated by global rules for {context} {contextID}")
            return result

    # Apply default policy
    return default_policy == 'allow'


def CheckPluginPrivilege(pluginName: str) -> bool:
    """Check if a plugin has cross-origin config access privilege."""
    if not pluginName.endswith('.py'):
        pluginName += '.py'

    all_rules = config.PLUGIN_ACCESS_RULES.get('rules', {})

    # Check plugin-specific privilege
    if pluginName in all_rules:
        localRules = all_rules[pluginName]
        if 'privilege' in localRules:
            return localRules['privilege']

    # Fall back to global default
    global_rules = all_rules.get('global', {})
    return global_rules.get('privilege', False)


def SubprocessCrossOriginConfigReader(caller_plugin: str, target_plugin: str) -> Union[Dict, None]:
    """Read another plugin's configuration with privilege check."""
    # Check if caller has privilege
    if not CheckPluginPrivilege(caller_plugin):
        config.logger.warning(f"Plugin {caller_plugin} attempted cross-origin config read without privilege")
        config.AdminNotifier('WARNING', f"Plugin {caller_plugin} attempted cross-origin config read without privilege")
        return None

    config.logger.info(f"Plugin {caller_plugin} is reading config of plugin {target_plugin}")
    config.AdminNotifier('INFO', f"Plugin {caller_plugin} is reading config of plugin {target_plugin}")

    return database.SubprocessConfigReader(target_plugin)


def SubprocessCrossOriginConfigWriter(caller_plugin: str, target_plugin: str, config_data: Dict) -> Union[bool, None]:
    """Write another plugin's configuration with privilege check."""
    # Check if caller has privilege
    if not CheckPluginPrivilege(caller_plugin):
        config.logger.warning(f"Plugin {caller_plugin} attempted cross-origin config write without privilege")
        config.AdminNotifier('WARNING', f"Plugin {caller_plugin} attempted cross-origin config write without privilege")
        return None

    config.logger.info(f"Plugin {caller_plugin} is writing config of plugin {target_plugin}")
    config.AdminNotifier('INFO', f"Plugin {caller_plugin} is writing config of plugin {target_plugin}")

    database.SubprocessConfigWriter(target_plugin, config_data)
    return True


def SubprocessApiCaller(action: str, data: Dict) -> Union[Dict, None]:
    """Call NapCat API from subprocess."""
    import requests
    import json

    if not isinstance(action, str) or not action:
        config.logger.error("ApiCaller: action must be non-empty string")
        config.AdminNotifier('ERROR', "ApiCaller: action must be non-empty string")
        return None

    if not isinstance(data, dict):
        config.logger.error("ApiCaller: data must be dict")
        config.AdminNotifier('ERROR', "ApiCaller: data must be dict")
        return None

    baseUrl = config.CONFIG['NAPCAT_SERVER']['api_url']
    fullUrl = f"{baseUrl}/{action}"

    try:
        response = requests.post(fullUrl, json=data, timeout=5.0)

        if response.status_code == 200:
            try:
                responseData = response.json()
                return responseData
            except json.JSONDecodeError as e:
                config.logger.error(f"ApiCaller: Invalid JSON response from {action}: {e}")
                config.AdminNotifier('ERROR', f"ApiCaller: Invalid JSON response from {action}: {e}")
                return None
        else:
            config.logger.error(f"ApiCaller: HTTP {response.status_code} from {action}")
            config.AdminNotifier('ERROR', f"ApiCaller: HTTP {response.status_code} from {action}")
            return None

    except requests.exceptions.Timeout:
        config.logger.error(f"ApiCaller: Timeout for {action}")
        config.AdminNotifier('ERROR', f"ApiCaller: Timeout for {action}")
        return None

    except Exception as e:
        config.logger.error(f"ApiCaller: Request error for {action}: {e}")
        config.AdminNotifier('ERROR', f"ApiCaller: Request error for {action}: {e}")
        return None


def PluginWorker(handler, simpleEvent: Union[Dict, None], rawEvent: Dict, resultPipe, memoryLimit: int):
    """Worker function that runs in subprocess to execute plugin code."""
    try:
        # Set memory limit (Linux only)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memoryLimit, memoryLimit))
        except Exception as e:
            config.logger.warning(f"Failed to set memory limit: {e}")
            config.AdminNotifier('WARNING', f"Failed to set memory limit: {e}")

        pluginName = getattr(handler, '__module__', 'unknown_plugin')

        # Create plugin-specific config functions
        def ConfigReader() -> Dict:
            return database.SubprocessConfigReader(pluginName)

        def ConfigWriter(config_data: Dict) -> None:
            return database.SubprocessConfigWriter(pluginName, config_data)

        def CrossOriginConfigReader(target_plugin: str) -> Union[Dict, None]:
            return SubprocessCrossOriginConfigReader(pluginName, target_plugin)

        def CrossOriginConfigWriter(target_plugin: str, config_data: Dict) -> Union[bool, None]:
            return SubprocessCrossOriginConfigWriter(pluginName, target_plugin, config_data)

        botContext = {
            "Librarian": database.SubprocessLibrarian,
            "ConfigReader": ConfigReader,
            "ConfigWriter": ConfigWriter,
            "CrossOriginConfigReader": CrossOriginConfigReader,
            "CrossOriginConfigWriter": CrossOriginConfigWriter,
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
        config.logger.warning(f"Error monitoring process: {e}")
        config.AdminNotifier('WARNING', f"Error monitoring process: {e}")
        return None


def PluginCallerSingle(handler, simpleEvent: Union[Dict, None], rawEvent: Dict):
    """Execute a single plugin in an isolated subprocess."""
    parentConn = None
    process = None
    try:
        maxCpuTime = config.CONFIG['PLUGIN_EXECUTION']['max_cpu_time_seconds']
        maxWallTime = config.CONFIG['PLUGIN_EXECUTION']['max_wall_time_seconds']
        memoryLimit = config.CONFIG['PLUGIN_EXECUTION']['memory_limit_mb'] * 1024 * 1024

        parentConn, childConn = multiprocessing.Pipe()

        process = multiprocessing.Process(
            target=PluginWorker,
            args=(handler, simpleEvent, rawEvent, childConn, memoryLimit)
        )

        startTime = time.time()
        process.start()

        monitorInterval = config.CONFIG['PLUGIN_EXECUTION']['monitor_interval_seconds']

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
                    config.logger.error(f"Error receiving result from plugin {handler.__name__}: {e}")
                    config.AdminNotifier('ERROR', f"Error receiving result from plugin {handler.__name__}: {e}")
                    return None

            terminationReason = PluginMonitor(
                process, startTime, maxCpuTime, maxWallTime, memoryLimit
            )

            if terminationReason:
                config.logger.error(f"Plugin {handler.__name__} terminated: {terminationReason}")
                config.AdminNotifier('ERROR', f"Plugin {handler.__name__} terminated: {terminationReason}")

                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()

                return None

        exitCode = process.exitcode
        if exitCode != 0:
            config.logger.error(f"Plugin {handler.__name__} exited with code {exitCode}")
            config.AdminNotifier('ERROR', f"Plugin {handler.__name__} exited with code {exitCode}")

        return None

    except Exception as e:
        config.logger.error(f"Failed to execute plugin {handler.__name__} in subprocess: {e}")
        config.AdminNotifier('ERROR', f"Failed to execute plugin {handler.__name__} in subprocess: {e}")
        return None
    finally:
        # Ensure cleanup in all cases
        if parentConn:
            try:
                parentConn.close()
            except Exception as e:
                config.logger.error(f"Failed to close pipe for plugin {handler.__name__}: {e}")
                config.AdminNotifier('ERROR', f"Failed to close pipe for plugin {handler.__name__}: {e}")

        if process:
            try:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                    if process.is_alive():
                        process.kill()
                        process.join()
            except Exception as e:
                config.logger.error(f"Failed to cleanup process for plugin {handler.__name__}: {e}")
                config.AdminNotifier('ERROR', f"Failed to cleanup process for plugin {handler.__name__}: {e}")


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
        try:
            result = PluginCallerSingle(handler, simpleEvent, rawEvent)

            # Convert errors to None for parallel execution
            if isinstance(result, dict) and "_error" in result:
                config.logger.error(f"Plugin {handler.__name__} raised {result['_type']}: {result['_error']}")
                config.AdminNotifier('ERROR', f"Plugin {handler.__name__} raised {result['_type']}: {result['_error']}")
                result = None

            resultQueue.put((handlerIndex, handler, result))
        except Exception as e:
            config.logger.error(f"Thread execution error for plugin {handler.__name__}: {e}")
            config.AdminNotifier('ERROR', f"Thread execution error for plugin {handler.__name__}: {e}")
            resultQueue.put((handlerIndex, handler, None))

    # Start all plugin threads
    threads = []
    for i, handler in enumerate(handlers):
        thread = threading.Thread(target=executePluginThread, args=(handler, i))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    # Process results as they complete
    completedCount = 0
    maxWaitTime = config.CONFIG['PLUGIN_EXECUTION']['max_wall_time_seconds'] + 5  # +5s for cleanup

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
                    config.logger.error(f"Error in result callback for plugin {handler.__name__}: {e}")
                    config.AdminNotifier('ERROR', f"Error in result callback for plugin {handler.__name__}: {e}")

        except queue.Empty:
            config.logger.warning(f"Timeout waiting for plugin results after {maxWaitTime} seconds")
            config.AdminNotifier('WARNING', f"Timeout waiting for plugin results after {maxWaitTime} seconds")
            break

    # Cleanup threads
    for thread in threads:
        thread.join(timeout=1)
        if thread.is_alive():
            config.logger.warning(f"Thread still alive after receiving its result - possible bug")
            config.AdminNotifier('WARNING', f"Thread still alive after receiving its result - possible bug")

    # Return results in original order
    orderedResults = []
    for i in range(len(handlers)):
        orderedResults.append(results.get(i, None))

    return orderedResults


def RegistryInitializer() -> None:
    """Scan and load plugins, register event handlers."""
    config.PLUGIN_REGISTRY = {eventType: [] for eventType in config.EVENT_TYPES_}
    INITIALIZER_REGISTRY = []  # type: List[tuple]

    pluginsDir = config.CONFIG['PATHS']['plugins_dir']
    if not os.path.exists(pluginsDir):
        os.makedirs(pluginsDir)
        config.logger.info(f"Created plugins directory: {pluginsDir}")
        config.AdminNotifier('INFO', f"Created plugins directory: {pluginsDir}")

    if not os.path.isdir(pluginsDir):
        config.logger.critical(f"Plugins path is not a directory: {pluginsDir}")
        config.AdminNotifier('CRITICAL', f"Plugins path is not a directory: {pluginsDir}")
        sys.exit(1)

    pluginFiles = [f for f in os.listdir(pluginsDir) if f.endswith('.py') and not f.startswith('__')]

    if not pluginFiles:
        config.logger.warning(f"No plugin files found in {pluginsDir}")
        config.AdminNotifier('WARNING', f"No plugin files found in {pluginsDir}")
    else:
        config.logger.info(f"Found {len(pluginFiles)} plugin files: {pluginFiles}")
        config.AdminNotifier('INFO', f"Found {len(pluginFiles)} plugin files: {pluginFiles}")

    # Load each plugin file
    for pluginFile in pluginFiles:
        try:
            moduleName = pluginFile[:-3]
            if pluginsDir not in sys.path:
                sys.path.insert(0, pluginsDir)

            pluginModule = importlib.import_module(moduleName)

            if not hasattr(pluginModule, 'MANIFEST'):
                config.logger.error(f"Plugin {moduleName} has no MANIFEST, skipping")
                config.AdminNotifier('ERROR', f"Plugin {moduleName} has no MANIFEST, skipping")
                continue

            manifest = getattr(pluginModule, 'MANIFEST')
            if not isinstance(manifest, dict):
                config.logger.error(f"Plugin {moduleName} MANIFEST is not a dict, skipping")
                config.AdminNotifier('ERROR', f"Plugin {moduleName} MANIFEST is not a dict, skipping")
                continue

            for eventType, functionName in manifest.items():
                if eventType == "INITIALIZER":
                    if not isinstance(functionName, str):
                        config.logger.error(f"Plugin {moduleName} INITIALIZER must be string, skipping")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName} INITIALIZER must be string, skipping")
                        continue

                    if not hasattr(pluginModule, functionName):
                        config.logger.error(f"Plugin {moduleName} declares INITIALIZER function '{functionName}' but it doesn't exist")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName} declares INITIALIZER function '{functionName}' but it doesn't exist")
                        continue

                    handlerFunction = getattr(pluginModule, functionName)
                    if not callable(handlerFunction):
                        config.logger.error(f"Plugin {moduleName}.{functionName} is not callable")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} is not callable")
                        continue

                    sig = inspect.signature(handlerFunction)
                    allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                    actualParams = set(sig.parameters.keys())

                    unknownParams = actualParams - allowedParams
                    if unknownParams:
                        config.logger.error(f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        continue

                    INITIALIZER_REGISTRY.append((handlerFunction, moduleName))
                    config.logger.info(f"Registered {moduleName}.{functionName} for INITIALIZER event")
                    config.AdminNotifier('INFO', f"Registered {moduleName}.{functionName} for INITIALIZER event")
                    continue

                if eventType == "UNCONDITIONAL":
                    interval = 1  # Default: every minute
                    handlerName = functionName

                    if isinstance(functionName, list):
                        if len(functionName) == 2:
                            handlerName, interval = functionName
                        else:
                            config.logger.error(f"Plugin {moduleName} UNCONDITIONAL has invalid format, skipping")
                            config.AdminNotifier('ERROR', f"Plugin {moduleName} UNCONDITIONAL has invalid format, skipping")
                            continue
                    elif not isinstance(functionName, str):
                        config.logger.error(f"Plugin {moduleName} UNCONDITIONAL must be string or list, skipping")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName} UNCONDITIONAL must be string or list, skipping")
                        continue

                    if not hasattr(pluginModule, handlerName):
                        config.logger.error(f"Plugin {moduleName} declares UNCONDITIONAL function '{handlerName}' but it doesn't exist")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName} declares UNCONDITIONAL function '{handlerName}' but it doesn't exist")
                        continue

                    handlerFunction = getattr(pluginModule, handlerName)
                    if not callable(handlerFunction):
                        config.logger.error(f"Plugin {moduleName}.{handlerName} is not callable")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName}.{handlerName} is not callable")
                        continue

                    if not isinstance(interval, int) or interval <= 0 or interval > 60:
                        config.logger.error(f"Plugin {moduleName} UNCONDITIONAL interval must be integer 1-60, got {interval}")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName} UNCONDITIONAL interval must be integer 1-60, got {interval}")
                        continue

                    sig = inspect.signature(handlerFunction)
                    allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                    actualParams = set(sig.parameters.keys())

                    unknownParams = actualParams - allowedParams
                    if unknownParams:
                        config.logger.error(f"Plugin {moduleName}.{handlerName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        config.AdminNotifier('ERROR', f"Plugin {moduleName}.{handlerName} has unknown parameters: {unknownParams}. "
                                    f"Allowed parameters are: {allowedParams}")
                        continue

                    # Register in both registries
                    config.PLUGIN_REGISTRY["UNCONDITIONAL"].append((handlerFunction, interval))
                    config.logger.info(f"Registered {moduleName}.{handlerName} for UNCONDITIONAL event (interval: {interval})")
                    config.AdminNotifier('INFO', f"Registered {moduleName}.{handlerName} for UNCONDITIONAL event (interval: {interval})")
                    continue

                # Regular event types
                if eventType not in config.EVENT_TYPES_:
                    config.logger.error(f"Plugin {moduleName} declares invalid event type '{eventType}'. Valid types: {config.EVENT_TYPES_}")
                    config.AdminNotifier('ERROR', f"Plugin {moduleName} declares invalid event type '{eventType}'. Valid types: {config.EVENT_TYPES_}")
                    continue

                if not hasattr(pluginModule, functionName):
                    config.logger.error(f"Plugin {moduleName} declares function '{functionName}' but it doesn't exist")
                    config.AdminNotifier('ERROR', f"Plugin {moduleName} declares function '{functionName}' but it doesn't exist")
                    continue

                handlerFunction = getattr(pluginModule, functionName)
                if not callable(handlerFunction):
                    config.logger.error(f"Plugin {moduleName}.{functionName} is not callable")
                    config.AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} is not callable")
                    continue

                sig = inspect.signature(handlerFunction)
                allowedParams = {'simpleEvent', 'rawEvent', 'botContext'}
                actualParams = set(sig.parameters.keys())

                unknownParams = actualParams - allowedParams
                if unknownParams:
                    config.logger.error(f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                f"Allowed parameters are: {allowedParams}")
                    config.AdminNotifier('ERROR', f"Plugin {moduleName}.{functionName} has unknown parameters: {unknownParams}. "
                                f"Allowed parameters are: {allowedParams}")
                    continue

                config.PLUGIN_REGISTRY[eventType].append(handlerFunction)
                config.logger.info(f"Registered {moduleName}.{functionName} for event '{eventType}'")
                config.AdminNotifier('INFO', f"Registered {moduleName}.{functionName} for event '{eventType}'")

        except Exception as e:
            config.logger.error(f"Failed to load plugin {pluginFile}: {e}")
            config.AdminNotifier('ERROR', f"Failed to load plugin {pluginFile}: {e}")
            continue

    # Execute INITIALIZER functions serially
    failedPlugins = []
    if INITIALIZER_REGISTRY:
        config.logger.info(f"Executing {len(INITIALIZER_REGISTRY)} INITIALIZER plugins")
        config.AdminNotifier('INFO', f"Executing {len(INITIALIZER_REGISTRY)} INITIALIZER plugins")

        for handlerFunction, pluginName in INITIALIZER_REGISTRY:
            try:
                emptyRawEvent = {"post_type": "initializer", "time": int(time.time())}
                result = PluginCallerSingle(handlerFunction, None, emptyRawEvent)

                if isinstance(result, dict) and "_error" in result:
                    config.logger.error(f"INITIALIZER for plugin {pluginName} failed: {result['_error']}")
                    config.AdminNotifier('ERROR', f"INITIALIZER for plugin {pluginName} failed: {result['_error']}")
                    failedPlugins.append(pluginName)
                elif result is None:
                    config.logger.info(f"INITIALIZER for plugin {pluginName} completed successfully")
                    config.AdminNotifier('INFO', f"INITIALIZER for plugin {pluginName} completed successfully")
                else:
                    config.logger.error(f"INITIALIZER for plugin {pluginName} returned unexpected result: {result}")
                    config.AdminNotifier('ERROR', f"INITIALIZER for plugin {pluginName} returned unexpected result: {result}")

            except Exception as e:
                config.logger.error(f"INITIALIZER for plugin {pluginName} failed with exception: {e}")
                config.AdminNotifier('ERROR', f"INITIALIZER for plugin {pluginName} failed with exception: {e}")
                failedPlugins.append(pluginName)

    # Remove failed plugins from all registries
    for pluginName in failedPlugins:
        for eventType in config.PLUGIN_REGISTRY:
            correctlyInitalizedHandlers_ = []
            for entry in config.PLUGIN_REGISTRY[eventType]:
                if isinstance(entry, tuple):
                    handlerFunction = entry[0]
                else:
                    handlerFunction = entry
                if getattr(handlerFunction, '__module__', None) != pluginName:
                    correctlyInitalizedHandlers_.append(entry)
            config.PLUGIN_REGISTRY[eventType] = correctlyInitalizedHandlers_

        config.logger.error(f"Removed all functions for failed plugin: {pluginName}")
        config.AdminNotifier('ERROR', f"Removed all functions for failed plugin: {pluginName}")

    totalHandlers = sum(len(handlerList) for handlerList in config.PLUGIN_REGISTRY.values())
    totalUnconditional = len(config.PLUGIN_REGISTRY.get("UNCONDITIONAL", []))
    totalInitializers = len(INITIALIZER_REGISTRY)
    totalFailed = len(failedPlugins)

    config.logger.info(f"Plugin initialization complete. {totalHandlers} handlers registered for {len(config.PLUGIN_REGISTRY)} event types")
    config.AdminNotifier('INFO', f"Plugin initialization complete. {totalHandlers} handlers registered for {len(config.PLUGIN_REGISTRY)} event types")
    config.logger.info(f"UNCONDITIONAL plugins: {totalUnconditional}")
    config.AdminNotifier('INFO', f"UNCONDITIONAL plugins: {totalUnconditional}")
    config.logger.info(f"INITIALIZER plugins: {totalInitializers} executed, {totalFailed} failed")
    config.AdminNotifier('INFO', f"INITIALIZER plugins: {totalInitializers} executed, {totalFailed} failed")

    if failedPlugins:
        config.logger.error(f"Failed plugins removed: {', '.join(failedPlugins)}")
        config.AdminNotifier('ERROR', f"Failed plugins removed: {', '.join(failedPlugins)}")

    for eventType, handlerList in config.PLUGIN_REGISTRY.items():
        if handlerList:
            config.logger.debug(f"  {eventType}: {len(handlerList)} handlers")
            config.AdminNotifier('DEBUG', f"  {eventType}: {len(handlerList)} handlers")
