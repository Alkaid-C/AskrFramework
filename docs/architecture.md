# Askr Framework 架构文档

**底层架构说明**

## 版本信息

适用的框架版本：[Beta 0.2] - *You Asked for This*

文档版本：Beta 0.2.1

最后更新日期：2025-07-07



## 1. 系统概览

Askr Framework 是一个基于事件驱动的 QQ 机器人框架，采用"框架多线程 + 插件多进程"的混合架构设计。

### 核心架构图

```
NapCat (QQ Client)
    │
    │ HTTP POST
    ▼
Flask/Gunicorn Server (:19219)
    │
    ▼
NapCatListener() ─────────────→ /health endpoint
    │
    ├─→ Initializer() [懒加载]
    ├─→ 解析 JSON
    ├─→ AdminDispatcher() → 返回 (如处理)
    ├─→ IS_MUTED 检查 → 返回 (如静音)
    └─→ MainDispatcher()
            │
            ├─→ EventTypeParser()
            ├─→ InbondMessageParser()
            ├─→ Historian()
            ├─→ 收集处理函数
            ├─→ CheckPluginAccess() [过滤]
            └─→ PluginCaller()
                    │
                    ├─→ [线程1] → PluginCallerSingle() → [进程1]
                    ├─→ [线程2] → PluginCallerSingle() → [进程2]
                    └─→ 收集结果 → OutbondMessageParser()
                                        │
                                        └─→ NapCatSender() → NapCat API
```

## 2. 网络入口函数

### 2.1 Flask 应用

**`NAPCAT_LISTENER`** - Flask 应用实例
- 全局 Flask 对象，处理 HTTP 请求

### 2.2 路由处理函数

**`NapCatListener() -> str`**
- **路由**: POST `/`
- **功能**: 主要的事件接收端点
- **流程**:
  1. 调用 `Initializer()` 进行懒加载初始化
  2. 使用 `request.get_json()` 获取事件数据
  3. 调用 `AdminDispatcher(rawEvent)` 检查管理员命令
  4. 检查 `IS_MUTED` 全局静音状态
  5. 调用 `MainDispatcher(rawEvent)` 处理普通事件
  6. 返回 'OK'

**`HealthCheck() -> dict`**
- **路由**: GET `/health`
- **功能**: 健康检查端点，用于监控系统状态
- **返回**: 包含状态、时间戳、静音状态、版本号、NapCat状态的字典

## 3. 初始化函数

### 3.1 初始化入口

**`Initializer() -> None`**
- **功能**: 懒加载初始化的入口，确保只初始化一次
- **实现**: 使用 `INIT_LOCK` 和 `INITIALIZED` 标志实现双重检查锁定

### 3.2 实际初始化

**`ActualInitializer() -> None`**
- **功能**: 执行实际的框架初始化
- **执行流程**:
  ```
  ActualInitializer()
  ├── FrameworkConfigReader()
  ├── PluginsAccessControlLoader()
  ├── DatabaseInitializer()
  ├── RegistryInitializer()
  │   ├── 扫描插件文件
  │   ├── 导入模块
  │   ├── 注册事件处理函数
  │   └── 执行 INITIALIZER 函数
  └── UnconditionalEventInitializer()
  ```

### 3.3 配置加载函数

**`FrameworkConfigReader() -> None`**
- **功能**: 读取并验证 `frameworkConfig.json` 配置文件
- **行为**: 深度合并配置，类型验证，创建必要目录

**`PluginsAccessControlLoader() -> None`**
- **功能**: 加载 `PluginsAccessControl.json` 访问控制规则
- **处理**: 验证规则格式，转换 List 为 Set 优化查询

### 3.4 系统初始化函数

**`DatabaseInitializer() -> None`**
- **功能**: 初始化 SQLite 数据库，创建必要的表和索引
- **创建表**: FRIEND_EVENTS, GROUP_EVENTS, OTHER_EVENTS, PLUGIN_CONFIGS

**`RegistryInitializer() -> None`**
- **功能**: 扫描并加载插件，注册事件处理函数
- **流程**:
  1. 扫描 `plugins/*.py` 文件
  2. 导入模块并读取 MANIFEST
  3. 验证函数签名
  4. 注册到相应的 registry
  5. 执行 INITIALIZER 函数
  6. 移除失败的插件

**`UnconditionalEventInitializer() -> None`**
- **功能**: 启动无条件事件生成器线程
- **行为**: 创建并启动 daemon 线程运行 `UnconditionalEventGenerator()`

## 4. 事件处理函数

### 4.1 事件分发流程

```
MainDispatcher(rawEvent)
├── EventTypeParser(rawEvent) → 事件类型
├── 如果是 UNCONDITIONAL
│   └── 根据间隔筛选处理函数
├── 否则
│   ├── InbondMessageParser(rawEvent) → simpleEvent
│   ├── Historian(rawEvent)
│   ├── 收集事件处理函数（考虑继承）
│   └── CheckPluginAccess() 过滤
└── PluginCaller(handlers, simpleEvent, rawEvent, OutbondMessageParser)
```

### 4.2 主要事件处理函数

**`MainDispatcher(rawEvent: Dict) -> None`**
- **功能**: 主事件分发器，路由事件到相应插件
- **参数**: rawEvent - 原始事件数据
- **流程**: 解析事件类型 → 收集处理函数 → 访问控制过滤 → 并行执行插件

**`EventTypeParser(rawEvent: Dict) -> str`**
- **功能**: 解析原始事件，返回事件类型字符串
- **返回**: 事件类型代码（如 "MESSAGE_PRIVATE"）或 "UNEXPECTED"
- **特殊处理**: 群消息细分（普通/提及/指令）

**`InbondMessageParser(rawEvent: Dict) -> Union[Dict, None]`**
- **功能**: 为消息事件生成简化的 simpleEvent 数据
- **返回**: 包含 user_id、text_message、group_id（如果是群消息）的字典

**`Historian(rawEvent: Dict) -> None`**
- **功能**: 将事件存储到数据库供历史查询
- **行为**: 根据事件类型选择表，重试机制，跳过特定事件类型

### 4.3 管理员控制函数

**`AdminDispatcher(rawEvent: Dict) -> bool`**
- **功能**: 处理管理员控制命令（mute/unmute）
- **返回**: True 表示已处理（跳过后续处理），False 表示继续
- **命令**: "mute" 设置静音，"unmute" 取消静音

### 4.4 访问控制函数

**`CheckPluginAccess(handler: Callable, rawEvent: Dict) -> bool`**
- **功能**: 检查插件是否有权限处理该事件
- **参数**: handler - 插件函数，rawEvent - 事件数据
- **返回**: True 允许执行，False 拒绝
- **规则**: 插件规则 > global 规则

**`CheckPluginPrivilege(pluginName: str) -> bool`**
- **功能**: 检查插件是否有跨域配置访问权限
- **返回**: True 有权限，False 无权限

## 5. 插件执行函数

### 5.1 并行执行控制

**`PluginCaller(handlers: List[Callable], simpleEvent: Union[Dict, None], rawEvent: Dict, resultCallback: Optional[Callable]) -> List[Any]`**
- **功能**: 并行执行多个插件并立即处理结果
- **参数**:
  - handlers: 插件处理函数列表
  - simpleEvent: 简化事件数据
  - rawEvent: 完整事件数据
  - resultCallback: 结果回调函数（用于立即响应）
- **返回**: 按原顺序排列的插件结果列表

### 5.2 单插件执行

**`PluginCallerSingle(handler, simpleEvent: Union[Dict, None], rawEvent: Dict)`**
- **功能**: 在独立进程中执行单个插件
- **流程**:
  1. 创建父子进程通信管道
  2. 启动子进程运行 `PluginWorker`
  3. 循环监控资源使用（`PluginMonitor`）
  4. 接收结果或超时终止

**`PluginWorker(handler, simpleEvent, rawEvent, resultPipe, memoryLimit)`**
- **功能**: 在子进程中执行插件代码
- **参数**: 
  - handler: 插件函数
  - resultPipe: 结果传输管道
  - memoryLimit: 内存限制（字节）
- **行为**: 设置资源限制，构建 botContext，执行插件，返回结果

**`PluginMonitor(process, startTime, maxCpuTime, maxWallTime, memoryLimit) -> Union[str, None]`**
- **功能**: 监控插件进程资源使用
- **返回**: 终止原因字符串或 None（正常）
- **监控项**: CPU 时间、墙钟时间、内存使用

## 6. botContext 工具函数

### 6.1 配置管理

**`SubprocessConfigReader(pluginName: str) -> Dict`**
- **功能**: 读取指定插件的配置（子进程版本）
- **返回**: 配置字典或空字典

**`SubprocessConfigWriter(pluginName: str, config: Dict) -> None`**
- **功能**: 写入插件配置（子进程版本）
- **行为**: 完全覆盖现有配置，支持重试

**`SubprocessCrossOriginConfigReader(caller_plugin: str, target_plugin: str) -> Union[Dict, None]`**
- **功能**: 跨域读取其他插件配置
- **权限**: 需要 caller_plugin 有 privilege 权限
- **返回**: 目标配置或 None（无权限）

**`SubprocessCrossOriginConfigWriter(caller_plugin: str, target_plugin: str, config: Dict) -> Union[bool, None]`**
- **功能**: 跨域写入其他插件配置
- **权限**: 需要 caller_plugin 有 privilege 权限
- **返回**: True 成功，None 无权限

### 6.2 历史查询

**`SubprocessLibrarian(eventIdentifier: Dict, eventCount: int = 50, interval: Optional[int] = None, intervalMaxCount: int = 2047, stringOutput: bool = False) -> Union[List[Dict], str]`**
- **功能**: 查询事件历史（子进程版本）
- **参数**:
  - eventIdentifier: 查询条件（type + id）
  - eventCount: 返回数量
  - interval: 时间窗口（秒）
  - intervalMaxCount: interval 查询的最大尝试数
  - stringOutput: 是否返回格式化字符串
- **策略**: 使用二分查询优化时间窗口查询

**`HistoryParser(events: List[Dict]) -> str`**
- **功能**: 将事件列表转换为格式化字符串
- **返回**: 多行文本格式的历史记录

### 6.3 API 调用

**`SubprocessApiCaller(action: str, data: Dict) -> Union[Dict, None]`**
- **功能**: 调用 NapCat API（子进程版本）
- **参数**: action - API 动作名，data - API 参数
- **返回**: API 响应数据或 None（失败）

## 7. 响应处理函数

**`OutbondMessageParser(pluginResponse: Any, rawEvent: Dict) -> None`**
- **功能**: 解析插件返回值并执行相应动作
- **支持类型**:
  - 字符串: 自动回复文本消息
  - 字典: 执行 API 调用
  - 列表: 递归处理每个元素
- **行为**: 根据原始事件确定发送目标

**`NapCatSender(actionEndpoint: str, requestBody: Dict) -> None`**
- **功能**: 向 NapCat API 发送请求
- **特性**: 支持重试，错误诊断，状态检查

## 8. 特殊事件生成

**`UnconditionalEventGenerator() -> None`**
- **功能**: 在独立线程中生成 UNCONDITIONAL 事件
- **行为**: 
  1. 计算到下一分钟的等待时间
  2. 休眠并在整分钟执行
  3. 创建事件并通过 HTTP 自调用发送

## 9. 管理员通知系统

**`AdminNotifier(messageLevel: str, message: str) -> None`**
- **功能**: 发送管理员 QQ 通知
- **参数**: messageLevel - 日志级别，message - 通知消息
- **特性**: 防刷屏机制，异步发送

**内部辅助函数**:
- `MessageHasher(message: str) -> str`: 生成消息哈希用于去重
- `AdminNotificationDictCleaner()`: 清理过期的通知记录
- `AdminNotificationSender()`: 实际发送通知的内部函数

## 10. 全局变量说明

### 初始化控制
- `INIT_LOCK`: 初始化锁
- `INITIALIZED`: 初始化完成标志

### 事件系统
- `EVENT_TYPES_`: 所有支持的事件类型列表
- `EVENT_INHERITANCE`: 事件继承关系映射
- `PLUGIN_REGISTRY`: 事件类型到处理函数的映射

### 配置存储
- `CONFIG`: 运行时配置字典
- `PLUGIN_ACCESS_RULES`: 访问控制规则

### 管理员系统
- `IS_MUTED`: 全局静音状态
- `AdminNotificationLast`: 通知防刷屏记录

## 11. 数据流总结

1. **事件接收**: NapCat → HTTP POST → NapCatListener
2. **事件分发**: MainDispatcher → EventTypeParser → 插件筛选
3. **插件执行**: PluginCaller → 多线程 → PluginCallerSingle → 子进程
4. **结果处理**: 插件返回值 → OutbondMessageParser → NapCatSender
5. **数据持久化**: Historian → SQLite 数据库