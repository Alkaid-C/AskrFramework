# Askr Framework Technical Guide

**面向高级插件开发者和框架设计关注者的深度技术指南**

## 设计哲学与核心理念

### 统一的事件-响应范式

Askr Framework建立在一个简单的概念上：**一切皆事件，一切皆响应**。无论是来自QQ用户的消息、系统定时任务，还是插件初始化，都被抽象为"事件"。插件的唯一职责就是对事件做出响应。

这种设计带来了几个重要优势：

**概念简单性**：新手开发者只需理解"输入事件→处理逻辑→输出响应"这一模式，无需掌握复杂的异步编程、生命周期管理等概念。

**接口一致性**：所有插件都是纯函数，具有相同的接口模式。这种一致性让插件的行为可预测，框架的执行模型清晰。

**扩展性**：新的事件类型可以无缝集成到现有系统中，插件可以选择性地响应感兴趣的事件。

### 稳定性优先的设计权衡

在性能与稳定性之间，Askr Framework明确选择了稳定性。这个选择反映在几个关键设计决策中：

**进程隔离而不是协程并发**：虽然主流框架都采用协程模型追求更高性能，Askr选择了进程隔离。单个插件的错误、死循环或内存泄漏完全无法影响框架核心和其他插件。

**资源控制而不是运行效率**：框架主动限制插件的CPU时间、内存使用和执行时长。这些限制可能影响某些计算密集型插件的性能，但确保了系统的整体稳定性。

**防御性设计而不是信任开发者**：框架假设插件可能存在各种问题，并预先建立了多层保护机制，而不是信任开发者会编写完美的代码。

### 渐进式学习曲线

框架的接口设计支持从简单到复杂的渐进式学习：

**最小可用性**：一个3行代码的插件就能实现有意义的功能：
```python
MANIFEST = {"MESSAGE_PRIVATE": "复读机"}
def 复读机(simpleEvent):
    return simpleEvent["text_message"]
```

**按需复杂度**：开发者可以根据需要逐步引入更多概念（rawEvent、botContext、配置管理等），而不是一开始就面对全部复杂性。

**透明升级路径**：从简单插件到复杂插件的升级是平滑的，不需要推翻重写。

## 技术架构特性

### 混合并行架构

Askr Framework采用独特的"框架多线程 + 插件多进程"混合架构：

**框架层并发**：主框架使用多线程处理不同插件的启动和结果收集，实现真正的并行执行。

```python
def PluginCaller(handlers, simpleEvent, rawEvent, resultCallback):
    # 为每个插件创建独立线程
    for i, handler in enumerate(handlers):
        thread = threading.Thread(target=executePluginThread, args=(handler, i))
        thread.start()
    
    # 立即处理完成的插件结果
    while completedCount < len(handlers):
        handlerIndex, handler, result = resultQueue.get()
        if resultCallback and result is not None:
            resultCallback(result, rawEvent)
```

**插件层隔离**：每个插件在独立的子进程中运行，拥有完全隔离的内存空间和执行环境。

**通信机制**：通过multiprocessing.Pipe()进行进程间通信，传递事件数据和执行结果。

**立即响应机制**：插件完成即立即处理结果，无需等待其他插件，显著提升用户体验的响应速度。

这种架构实现了错误隔离、资源控制、并发性能和可调试性的完美结合。

### 智能事件过滤系统

框架扩展了OneBot 11标准，实现了多层次的事件过滤：

**群消息三级分类**：
```python
def EventTypeParser(rawEvent):
    if rawEvent.get("message_type") == "group":
        selfId = str(rawEvent.get("self_id", ""))
        messageSegments = rawEvent.get("message", [])
        
        # @mention有最高优先级
        for segment in messageSegments:
            if segment.get("type") == "at":
                atQQ = segment.get("data", {}).get("qq", "")
                if atQQ == selfId:
                    return "MESSAGE_GROUP_MENTION"
        
        # 检查指令前缀
        for segment in messageSegments:
            if segment.get("type") == "text":
                text = segment.get("data", {}).get("text", "")
                trimmedText = text.lstrip()
                if trimmedText and trimmedText[0] in ['.', '/', '\\']:
                    return "MESSAGE_GROUP_BOT"
                break
        
        return "MESSAGE_GROUP"
```

- `MESSAGE_GROUP`：普通群消息
- `MESSAGE_GROUP_MENTION`：包含@机器人的消息  
- `MESSAGE_GROUP_BOT`：以指令前缀（`.` `/` `\`）开头的消息

**扩展事件机制**：
```python
EVENT_INHERITANCE = {
    "MESSAGE_GROUP_MENTION": ["MESSAGE_GROUP"],
    "MESSAGE_GROUP_BOT": ["MESSAGE_GROUP"],
}
```

`MESSAGE_GROUP_MENTION`和`MESSAGE_GROUP_BOT`类型的消息也会触发`MESSAGE_GROUP`类型的处理函数，让插件可以选择处理粗粒度或细粒度的事件。

**访问控制过滤**：
```python
def CheckPluginAccess(handler, rawEvent):
    pluginName = getattr(handler, '__module__', 'unknown')
    # 检查访问控制规则
    # 白名单 > 黑名单 > 默认策略
```

通过`PluginsAccessControl.json`配置文件，基于private/group上下文进行精确的ID过滤，避免创建不必要的进程。

**性能优化效果**：在典型的群聊机器人场景中，大部分普通群消息不会触发插件执行，显著减少了不必要的进程创建开销。

### botContext工具协议

Askr Framework为插件提供了标准化的工具接口：

**历史记录查询**：
```python
def SubprocessLibrarian(eventIdentifier, eventCount=50, interval=None, intervalMaxCount=2047, stringOutput=False):
    # 支持时间窗口查询的二分查询策略
    if interval is not None:
        fetch_count = 1
        while fetch_count <= intervalMaxCount:
            cursor.execute(query, query_params + [fetch_count])
            rows = cursor.fetchall()
            oldest_timestamp = rows[-1][1] if rows else current_time
            if oldest_timestamp >= cutoff_time:
                fetch_count = min(fetch_count * 2, intervalMaxCount)
            else:
                break
```

**配置管理**：
- `ConfigReader()` / `ConfigWriter(config)` - 自身配置管理
- `CrossOriginConfigReader(target)` / `CrossOriginConfigWriter(target, config)` - 跨域配置访问（需privilege权限）

**API调用**：
```python
def SubprocessApiCaller(action, data):
    baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
    fullUrl = f"{baseUrl}/{action}"
    response = requests.post(fullUrl, json=data, timeout=5.0)
    return response.json() if response.status_code == 200 else None
```

**设计特点**：
- **主子进程版本自适应**：框架自动选择合适的实现版本
- **错误容忍设计**：工具调用失败返回None或空值，不会中断插件执行
- **统一的错误处理策略**：所有工具都采用相同的错误处理模式
- **权限控制**：跨域访问需要显式授权，访问行为被记录

### 数据流分工设计

框架中的数据按照清晰的分工流动：

**输入数据分层**：
```python
def InbondMessageParser(rawEvent):
    # 为消息事件生成简化的simpleEvent
    eventType = EventTypeParser(rawEvent)
    if eventType.startswith("MESSAGE_"):
        messageSegments = rawEvent.get("message", [])
        textParts = []
        for segment in messageSegments:
            if segment.get("type") == "text":
                textParts.append(segment.get("data", {}).get("text", ""))
        return {
            "user_id": rawEvent.get("user_id"),
            "group_id": rawEvent.get("group_id"),  # 仅群消息
            "text_message": "".join(textParts)
        }
```

- `rawEvent`：完整的OneBot 11事件数据，供需要详细信息的插件使用
- `simpleEvent`：简化的事件数据，包含最常用的字段，降低使用门槛

**输出响应分类**：
```python
def OutbondMessageParser(pluginResponse, rawEvent):
    if isinstance(pluginResponse, str):
        # 自动转换为文本消息发送
    elif isinstance(pluginResponse, dict):
        # 直接作为OneBot 11 API调用
        NapCatSender(pluginResponse["action"], pluginResponse["data"])
    elif isinstance(pluginResponse, list):
        # 批量处理多个操作
        for item in pluginResponse:
            OutbondMessageParser(item, rawEvent)
```

**API调用分工**：
- **查询类API**（get_*）：通过`botContext["ApiCaller"]`调用，返回值用于决策
- **行动类API**（send_*、set_*）：通过插件返回值调用，返回值通常不重要

## 生产环境特性

### 外部配置系统

框架支持通过`frameworkConfig.json`进行配置，实现了配置与代码的分离：

**配置加载机制**：
```python
def FrameworkConfigReader():
    # 深度合并配置，只需提供要修改的配置项
    if 'NAPCAT_SERVER' in fileConfig:
        if 'api_url' in fileConfig['NAPCAT_SERVER']:
            CONFIG['NAPCAT_SERVER']['api_url'] = fileConfig['NAPCAT_SERVER']['api_url']
```

- 在框架初始化时读取配置文件
- 深度合并机制：只需提供要修改的配置项
- 类型验证：自动检查配置值的类型和范围
- 容错设计：配置错误不会阻止框架启动

### 插件访问控制

通过`PluginsAccessControl.json`实现细粒度的访问控制：

**控制机制**：
```python
def CheckPluginAccess(handler, rawEvent):
    # 获取插件名和事件信息
    pluginName = getattr(handler, '__module__', 'unknown')
    groupID = rawEvent.get('group_id')
    contextID = groupID if groupID else rawEvent.get('user_id', 0)
    
    # 检查白名单/黑名单
    def OnListChecker(rules, contextID):
        whitelist_ = rules.get('WhiteList', set())
        blacklist_ = rules.get('BlackList', set())
        
        if whitelist_:
            return contextID in whitelist_
        elif blacklist_:
            return contextID not in blacklist_
        return None
    
    # 插件规则 > global规则 > 默认策略
```

- 基于private/group上下文的分离控制
- 支持WhiteList/BlackList模式
- 全局规则（使用"global"作为键）
- 默认策略配置（allow/deny）
- 集成的privilege权限管理

### 跨域配置访问

框架支持有权限的插件访问其他插件的配置：

**权限模型**：
```python
def CheckPluginPrivilege(pluginName):
    all_rules = PLUGIN_ACCESS_RULES.get('rules', {})
    if pluginName in all_rules:
        localRules = all_rules[pluginName]
        if 'privilege' in localRules:
            return localRules['privilege']
    # 回退到global默认值
    global_rules = all_rules.get('global', {})
    return global_rules.get('privilege', False)
```

- 在`PluginsAccessControl.json`中设置`"privilege": true`
- 未设置privilege的插件使用global默认值
- 所有跨域访问被记录到日志

### 增强的历史查询

Librarian工具支持时间窗口查询，使用二分搜索策略优化性能：

**二分查询策略**：
```python
def SubprocessLibrarian(eventIdentifier, interval=None, intervalMaxCount=2047):
    if interval is not None:
        fetch_count = 1
        while fetch_count <= intervalMaxCount:
            # 查询fetch_count条记录
            cursor.execute(query, query_params + [fetch_count])
            rows = cursor.fetchall()
            
            oldest_timestamp = rows[-1][1] if rows else current_time
            if oldest_timestamp >= cutoff_time:
                # 需要更多数据，翻倍查询数量
                fetch_count = min(fetch_count * 2, intervalMaxCount)
            else:
                # 已经查询到足够的历史数据
                break
```

这种策略避免了一次性加载过多数据，同时确保能够获取指定时间窗口内的完整数据。

### UNCONDITIONAL事件统一化

UNCONDITIONAL事件现在作为普通事件类型处理，保持了框架的一致性：

**实现机制**：
```python
def UnconditionalEventGenerator():
    while True:
        now = datetime.datetime.now()
        secondsToNextMinute = 60 - now.second + 3  # +3s缓冲
        time.sleep(secondsToNextMinute)
        
        unconditional_event = {
            "post_type": "unconditional",
            "time": int(time.time())
        }
        
        # 通过HTTP自调用发送到主事件处理器
        url = f"http://localhost:{CONFIG['NAPCAT_LISTEN']['port']}/"
        requests.post(url, json=unconditional_event, timeout=5.0)
```

**调度机制**：
```python
def MainDispatcher(rawEvent):
    if eventType == "UNCONDITIONAL":
        currentMinute = datetime.datetime.fromtimestamp(rawEvent["time"]).minute
        for handler, interval in PLUGIN_REGISTRY.get("UNCONDITIONAL", []):
            if currentMinute % interval == 0:
                HandlersToExecute_.append(handler)
```

间隔N表示在分钟数能被N整除时执行，如间隔15在第0、15、30、45分钟执行。

### 优雅关闭机制

框架支持优雅关闭，确保插件能够正常完成执行：

**关闭流程**：
1. 接收SIGTERM/SIGINT信号
2. 设置SHUTDOWN_REQUESTED标志
3. 拒绝新的HTTP请求（返回503）
4. 等待所有活跃插件完成
5. 超时后强制退出

**活跃插件跟踪**：框架维护活跃插件计数器，用于判断是否可以安全关闭。

### 健康检查端点

新增`/health`端点提供系统状态信息：

```python
@NAPCAT_LISTENER.route('/health', methods=['GET'])
def HealthCheck():
    # 检查NapCat服务器状态
    NapCatServerStatus = 'Unreachable'
    try:
        baseUrl = CONFIG['NAPCAT_SERVER']['api_url']
        statusUrl = f"{baseUrl}/get_status"
        statusResponse = requests.get(statusUrl, timeout=CONFIG['HTTP']['status_check_timeout'])
        if statusResponse.status_code == 200:
            statusData = statusResponse.json()
            if statusData.get('status', '') == 'ok':
                NapCatServerStatus = 'OK'
    except:
        pass
    
    return {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'is_muted': IS_MUTED,
        'version': 'Beta 0.98',
        'NapCatServerStatus': NapCatServerStatus
    }
```

### 管理员通知系统

框架提供智能的管理员通知功能：

**防刷屏机制**：
```python
def AdminNotifier(messageLevel, message):
    def MessageHasher(message):
        return hashlib.md5(message.encode('utf-8')).hexdigest()[:8]
    
    messageHash = MessageHasher(message)
    currentTime = time.time()
    rateLimit = CONFIG['ADMIN_NOTIFICATION']['rate_limit_seconds']
    
    with AdminNotificationLock:
        lastTime = AdminNotificationLast.get(messageHash, 0)
        if currentTime - lastTime < rateLimit:
            return  # 跳过重复通知
        AdminNotificationLast[messageHash] = currentTime
```

- 相同消息在配置时间内只通知一次（默认1200秒）
- 基于消息内容的hash值判断重复
- 支持可配置的通知级别过滤
- 异步发送，不阻塞主流程

## 插件执行模型详解

### 初始化阶段
```python
def RegistryInitializer():
    for handlerFunction, pluginName in INITIALIZER_REGISTRY:
        try:
            emptyRawEvent = {"post_type": "initializer", "time": int(time.time())}
            result = PluginCallerSingle(handlerFunction, None, emptyRawEvent)
            
            if isinstance(result, dict) and "_error" in result:
                failedPlugins.append(pluginName)
        except Exception:
            failedPlugins.append(pluginName)
```

- **时机**：框架启动时串行执行
- **用途**：检查配置、验证API密钥、预加载数据
- **失败处理**：初始化失败的插件会被完全移除

### 资源控制与监控

**资源限制**：
```python
def PluginWorker(handler, simpleEvent, rawEvent, resultPipe, memoryLimit):
    try:
        # 设置内存限制
        resource.setrlimit(resource.RLIMIT_AS, (memoryLimit, memoryLimit))
    except Exception:
        pass  # Linux专有功能，其他系统跳过
```

- **CPU时间限制**：防止死循环和计算密集型任务
- **内存限制**：防止内存泄漏影响系统  
- **墙钟时间限制**：防止阻塞调用导致的超时

**监控机制**：
```python
def PluginMonitor(process, startTime, maxCpuTime, maxWallTime, memoryLimit):
    try:
        pluginProcess = psutil.Process(process.pid)
        cpuTimes = pluginProcess.cpu_times()
        totalCpuTime = cpuTimes.user + cpuTimes.system
        
        if totalCpuTime > maxCpuTime:
            return f"cpu_time_exceeded ({totalCpuTime:.2f}s > {maxCpuTime}s)"
        
        wallTime = time.time() - startTime
        if wallTime > maxWallTime:
            return f"wall_time_exceeded ({wallTime:.2f}s > {maxWallTime}s)"
        
        memInfo = pluginProcess.memory_info()
        if memInfo.rss > memoryLimit:
            memUsageMB = memInfo.rss / (1024 * 1024)
            memLimitMB = memoryLimit / (1024 * 1024)
            return f"memory_exceeded ({memUsageMB:.1f}MB > {memLimitMB:.1f}MB)"
    except psutil.NoSuchProcess:
        return None
```

使用psutil库在主进程中持续监控子进程资源使用情况，一旦发现异常立即采取措施。