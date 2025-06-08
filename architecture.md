# Askr Framework Architecture Documentation

## 1. 执行流程图

### 初始化流程

#### 程序入口
```
开发环境 (python askr_framework.py):
multiprocessing.set_start_method() → Initializer() → Flask.run() → 监听HTTP事件

生产环境 (gunicorn):
multiprocessing.set_start_method() → Initializer() → HTTP服务器就绪 → 监听HTTP事件
```

#### Initializer() 执行流程
```
Initializer()
├── LoggingNotificationConfigurator()  # 配置日志QQ通知系统
├── DatabaseInitializer()              # 初始化SQLite数据库和表结构
├── PLUGIN_REGISTRY初始化              # 为每个事件类型创建空的处理函数列表
├── 插件文件发现和加载                   # 扫描plugins/目录，加载.py文件
│   ├── 解析MANIFEST声明                # 验证事件类型和函数名映射
│   ├── 验证函数存在性和参数签名          # 检查函数是否存在，参数是否合法
│   ├── 注册到相应注册表                # 根据事件类型分别注册到不同注册表
│   │   ├── 普通事件 → PLUGIN_REGISTRY
│   │   ├── UNCONDITIONAL → UNCONDITIONAL_REGISTRY  
│   │   └── INITIALIZER → INITIALIZER_REGISTRY
│   └── 记录加载错误但不中断初始化
├── 执行插件INITIALIZER函数             # 串行执行每个插件的初始化函数
│   ├── 为每个INITIALIZER函数调用PluginCallerSingle()
│   ├── 检测执行失败的插件
│   └── 从所有注册表中移除失败的插件
└── 启动UnconditionalScheduler线程      # 如果有UNCONDITIONAL插件则启动无条件事件调度器
```

#### 初始化流程说明

Askr Framework的初始化是一个多阶段的过程，核心目标是建立一个稳定可靠的插件执行环境。

**系统准备阶段**：框架首先建立基础设施，包括配置日志通知系统（如果启用）和初始化SQLite数据库。数据库不仅用于存储历史消息，还为插件提供配置持久化能力。

**插件发现与验证阶段**：框架扫描plugins/目录下的所有.py文件，通过解析每个文件的MANIFEST全局变量来了解插件的能力声明。MANIFEST是一个字典，键为事件类型字符串（如"MESSAGE_PRIVATE"、"UNCONDITIONAL"、"INITIALIZER"），值为对应的处理函数名。框架会严格验证：声明的事件类型是否合法、对应的函数是否存在、函数参数签名是否符合要求（只能使用simpleEvent、rawEvent、botContext这三个参数）。

**插件注册阶段**：通过验证的插件函数被注册到相应的全局注册表中。普通事件处理函数注册到PLUGIN_REGISTRY，定时任务注册到UNCONDITIONAL_REGISTRY，初始化函数注册到INITIALIZER_REGISTRY。

**插件初始化阶段**：框架串行执行所有插件的INITIALIZER函数。这些函数的作用是让插件完成启动前的准备工作，如验证API密钥、检查并创建默认配置、预加载数据等。INITIALIZER函数可以通过botContext访问框架提供的配置读写和API调用能力。通过INITIALIZER函数的预处理，插件的事件处理函数能够基于某些假设来运行（例如假设配置字典已存在且有效），从而避免在每次事件处理时进行重复检查，显著提升运行效率。作为这种设计的代价，如果某个插件的INITIALIZER执行失败，意味着该插件的处理函数赖以运行的假设条件无法建立，因此该插件的所有函数都会从注册表中移除，防止基于错误假设的代码运行。

**后台服务启动阶段**：如果有插件注册了UNCONDITIONAL事件处理函数，框架会启动一个无条件事件调度器线程，负责定期人工制造unconditional事件并分发给相应的处理函数。

**HTTP服务器启动阶段**：初始化完成后，框架建立HTTP服务器开始监听NapCat的事件上报。在开发环境中通过Flask.run()启动内置服务器，在生产环境中由gunicorn等WSGI服务器托管NAPCAT_LISTENER应用。服务器就绪后，框架即可接收和处理来自NapCat的QQ事件。

整个初始化过程采用"容错优先"的设计原则：单个插件的问题不会中断整体初始化，失败的插件会被优雅地移除，确保框架能够稳定启动并为可用的插件提供服务。

### 事件处理流程

#### HTTP请求处理流程
```
NapCat HTTP POST → NapCatListener() 
├── AdminDispatcher()                    # 检查管理员控制命令和系统静音状态
└── MainDispatcher()                     # 主要事件处理逻辑
```

#### MainDispatcher() 执行流程
```
MainDispatcher(rawEvent)
├── EventTypeParser()                    # 解析事件类型
│   ├── 根据post_type进行初步分类
│   ├── GroupMessageAnalyzer()           # 群消息细分类（@提及/指令/普通）
│   └── 返回具体事件类型字符串
├── InbondMessageParser()                # 生成简化事件数据
│   ├── 提取消息文本内容
│   ├── 提取用户ID和群ID
│   └── 返回simpleEvent字典或None
├── Historian()                          # 同步存储事件历史
│   ├── 确定存储表（FRIEND/GROUP/OTHER_EVENTS）
│   ├── 序列化事件数据
│   └── 写入SQLite数据库
├── 收集触发的处理函数                    # 支持事件继承机制
│   ├── 获取主事件类型的处理函数
│   ├── 查找EVENT_INHERITANCE中的父事件
│   ├── 合并去重所有处理函数
│   └── 构建最终的handlers列表
└── PluginCaller()                       # 并行执行所有处理函数
    ├── 传入handlers、simpleEvent、rawEvent
    ├── 设置response_callback为OutbondMessageParser
    └── 立即返回（不等待插件执行完成）
```

#### 事件处理流程说明

事件处理是框架的核心工作流程，设计目标是高效、稳定地将QQ事件分发给相应的插件处理。

**请求接收阶段**：所有来自NapCat的HTTP POST请求都由Flask路由处理函数NapCatListener()接收。框架首先解析JSON格式的事件数据，然后进入处理流程。

**管理员控制检查**：AdminDispatcher()检查是否为管理员控制命令或系统是否处于静音状态，如果是则相应处理或跳过后续流程。

**事件解析与分类**：EventTypeParser()将原始的OneBot 11事件转换为框架内部的事件类型标识。对于群消息，还会通过GroupMessageAnalyzer()进行更细粒度的分类，区分普通群消息、@机器人的消息和以特定符号开头的指令消息，实现智能的事件过滤。

**数据简化与历史记录**：InbondMessageParser()为消息类事件生成简化的数据结构，提取插件最常用的信息。同时，Historian()同步地将完整的事件数据存储到SQLite数据库中，为插件的Librarian功能提供数据支撑。

**处理函数收集**：框架通过PLUGIN_REGISTRY查找注册了当前事件类型的所有处理函数。同时利用EVENT_INHERITANCE机制，如果当前事件有父事件类型，也会收集父事件的处理函数。这种继承机制让插件可以选择处理粗粒度或细粒度的事件。

**并行执行与响应**：最后，PluginCaller()接收所有需要执行的处理函数，启动多个独立进程并行执行插件代码。同时设置OutbondMessageParser作为响应回调，确保插件的返回值能够立即转换为对QQ的实际响应动作。

### 无条件事件调度流程

#### UnconditionalScheduler() 执行流程
```
UnconditionalScheduler()  (独立线程)
├── 计算到下一整分钟的等待时间
├── sleep(秒数到下一分钟 + 3秒缓冲)    # 确保在每分钟2-4秒执行，避免舍入误差
├── 检查IS_MUTED静音状态              # 静音时跳过事件制造
├── 根据当前分钟数和间隔筛选处理函数    # 例如：分钟数 % 间隔 == 0
├── 制造unconditional事件            # 创建人工事件数据
│   └── post_type: "unconditional", time: timestamp
├── 设置响应回调函数                 # OutbondMessageParser处理返回值
└── PluginCaller()                   # 分发事件给相应的处理函数
```

#### 无条件事件调度流程说明

无条件事件调度器体现了框架统一的"事件-响应"设计哲学。与普通插件响应NapCat事件、INITIALIZER插件响应初始化事件类似，UNCONDITIONAL插件响应的是框架定期人工制造的unconditional事件。

**调度时机保证**：调度器采用独特的"整分钟保证"设计，确保注册的处理函数在每个应执行的整分钟中都被调用一次，但不保证调用间隔的均匀性。

*设计示例*：预期的调度时序可能是8:00:01、8:01:59、8:02:01（尽管间隔极度不均匀，但8:00、8:01、8:02都被调用了一次），而8:00:01、8:00:59、8:02:01这样的时序是不被期望的（尽管间隔基本均匀，但8:00执行了两次，8:01被跳过）。

**设计目标**：这种设计让插件可以基于时间做简单判断。例如闹钟插件只需要检查`if 当前时间 == 8:00`就能确保8:00时刻发送消息，而无需处理复杂的调度逻辑。调度器通过sleep机制实现，实际执行时间通常在每分钟的2-4秒。

**间隔机制**：插件声明的"间隔"不是真正的时间间隔，而是指在每小时内当分钟数能被该间隔整除时执行。例如间隔为13的插件会在第0、13、26、39、52分钟执行。需要注意的是，跨小时的执行间隔可能不均匀（如8:52到9:00只有8分钟）。要获得均匀的时间间隔，必须使用能整除60的间隔数（如1、2、3、4、5、6、10、12、15、20、30、60）。

**事件制造**：对于需要执行的处理函数，调度器创建一个人工的unconditional事件，包含基本的事件标识和时间戳信息。这个事件与NapCat事件在结构上保持一致，确保插件处理的统一性。

**事件分发**：制造的unconditional事件通过PluginCaller()分发给相应的处理函数，这些函数可以像处理其他事件一样访问botContext和rawEvent（包含调度时间戳），调用API、读写配置、查询历史等。插件的返回值会通过OutbondMessageParser处理，支持dict和list类型的返回值（但不支持string，因为缺少发送目标信息）。

**静音支持**：调度器遵循全局静音机制，当系统处于静音状态时会跳过事件制造，确保管理员控制的一致性。

这种设计保持了框架接口的一致性：所有插件都是事件处理函数，只是响应的事件来源不同。

### 插件执行流程

#### PluginCaller() 执行流程
```
PluginCaller(handlers, simpleEvent, rawEvent, resultCallback)
├── 创建结果队列和存储字典
├── 为每个handler启动执行线程
│   ├── executePluginThread()               # 线程函数
│   │   ├── PluginCallerSingle()            # 执行单个插件
│   │   └── 结果放入队列
│   └── 所有线程并行启动
├── 等待结果收集
│   ├── 从队列中获取完成的插件结果
│   ├── 立即调用resultCallback()           # 成功结果立即处理
│   └── 存储结果到字典
├── 线程清理和超时处理
└── 返回按原顺序排列的结果列表
```

#### PluginCallerSingle() 执行流程
```
PluginCallerSingle(handler, simpleEvent, rawEvent)
├── 创建父子进程通信管道
├── 启动子进程
│   └── PluginWorker()                      # 在子进程中执行
├── 进程监控循环
│   ├── 检查管道是否有结果返回
│   ├── PluginMonitor()                     # 检查资源使用情况
│   │   ├── CPU时间检查
│   │   ├── 墙钟时间检查
│   │   └── 内存使用检查
│   └── 资源超限时终止进程
├── 进程清理
└── 返回插件结果或None
```

#### PluginWorker() 子进程执行
```
PluginWorker(handler, simpleEvent, rawEvent, resultPipe, memoryLimit)
├── 设置进程资源限制
├── 创建botContext                          # 包含子进程版本的API函数
├── 解析插件函数参数签名
├── 调用插件函数
│   └── handler(**callArgs)
├── 通过管道发送结果
└── 异常时发送错误信息
```

#### 响应处理流程
```
resultCallback (OutbondMessageParser)
├── 解析插件返回值类型
│   ├── 字符串 → 发送文本消息
│   ├── 字典 → 发送API调用
│   └── 列表 → 递归处理每个元素
├── 确定发送目标
│   ├── 根据rawEvent确定私聊/群聊
│   └── 构造请求数据
└── NapCatSender()                          # 发送到NapCat
```

#### 插件执行流程说明

插件执行流程采用"多线程+多进程"混合架构实现并行执行和进程隔离。

**并行启动阶段**：PluginCaller()接收需要执行的插件列表，为每个插件创建独立的执行线程。这些线程立即启动，实现真正的并行执行。

**进程隔离执行**：每个线程中的PluginCallerSingle()会创建一个独立的子进程来运行插件代码。子进程通过PluginWorker()函数执行实际的插件逻辑，任何插件的崩溃、死循环或内存泄漏都无法影响主框架和其他插件。

**资源控制机制**：主进程通过PluginMonitor()持续监控子进程的资源使用情况，包括CPU时间、墙钟时间和内存消耗。一旦发现资源使用超出配置限制，会立即终止相应的子进程。

**botContext构建**：在子进程中，PluginWorker()会为插件构建botContext字典，包含子进程版本的API调用、配置读写、历史查询等函数。插件通过这些函数访问框架功能。

**参数适配机制**：框架通过检查插件函数的参数签名，动态决定传入哪些参数（simpleEvent、rawEvent、botContext），让插件可以按需选择所需的数据。

**立即响应设计**：当插件执行完成并返回结果时，PluginCaller()会立即调用resultCallback将结果交给OutbondMessageParser处理，而不等待其他插件完成。

**响应解析与发送**：OutbondMessageParser()解析插件的返回值类型（字符串、字典、列表），根据原始事件的上下文确定发送目标（私聊还是群聊），然后构造相应的API请求交给NapCatSender()发送到NapCat服务器。

**错误容错处理**：插件异常不会影响其他插件，API发送失败会自动重试，资源超限会被及时制止。

### botContext工具协议流程

#### 插件执行中的botContext调用流程
```
框架调用插件函数(simpleEvent, rawEvent, botContext)
├── 插件分析事件内容
├── 插件判断是否需要框架提供的数据或功能
│   ├── 需要 → 调用botContext相应工具
│   │   ├── 查询历史记录
│   │   ├── 读取插件配置
│   │   ├── 调用NapCat查询API（get_xx类型）
│   │   └── 获取工具返回的数据
│   └── 不需要 → 继续处理
├── 插件进行业务逻辑处理
│   ├── 基于事件数据
│   ├── 基于工具获取的数据
│   └── 综合判断和计算
├── 插件判断是否需要更新状态
│   ├── 需要 → 调用botContext保存配置
│   └── 不需要 → 继续处理
├── 插件决定响应动作
└── 插件返回响应值 → 框架转换为NapCat行动API（send_xx/set_xx类型）
```

#### botContext工具协议说明

botContext为插件提供了类似MCP(Model Context Protocol)的标准化工具接口，让插件能够安全地访问框架功能而无需了解底层实现细节。

**统一工具接口**：插件通过botContext字典访问四种核心工具：历史记录查询、配置读写、NapCat API调用。插件根据业务逻辑需要选择性地调用这些工具。

**NapCat API分工机制**：OneBot 11 API分为两类用途。查询类API（get_friend_list、get_group_info等）主要通过botContext["ApiCaller"]调用，因为其返回数据用于指导插件的进一步决策。行动类API（send_msg、set_group_card等）主要通过插件返回值调用，因为这些API的返回值通常不重要，插件只需表达"想要执行什么动作"。

**工具隔离设计**：在主进程和子进程中，每个工具都有对应的实现版本。子进程版本确保插件在隔离环境中仍能访问所有功能。

**自动插件名识别**：配置相关的工具会自动识别调用插件的名称，为每个插件提供独立的配置命名空间。

**统一错误处理**：所有工具都采用统一的错误处理策略，失败时返回空值或None，并记录详细的错误日志。

### 管理员控制系统流程

#### AdminDispatcher 执行流程
```
AdminDispatcher(rawEvent)
├── 检查事件类型
│   └── 不是私聊消息 → 返回False（继续正常处理）
├── 检查发送者身份
│   ├── admin_qq未配置 → 返回False
│   └── 发送者不是管理员 → 返回False
├── 解析消息内容
│   ├── "mute" → 设置IS_MUTED=True，记录日志，返回True
│   ├── "unmute" → 设置IS_MUTED=False，记录日志，返回True
│   └── 其他内容 → 返回False（继续正常处理）
└── 返回True表示已处理，跳过后续事件处理
```

#### 管理员通知系统流程
```
日志记录触发 → NotificationEligibilityChecker()
├── 检查通知功能是否启用
├── 检查admin_qq是否配置
├── 检查日志级别是否达到通知阈值
└── 符合条件 → QQNotificationSender()
    ├── 检查防刷屏限制（基于消息hash）
    ├── 后台线程发送QQ消息给管理员
    └── 更新防刷屏时间戳
```

#### 静音机制影响流程
```
IS_MUTED状态影响
├── NapCatListener事件处理
│   └── IS_MUTED=True → 跳过MainDispatcher
├── UnconditionalScheduler定时任务
│   └── IS_MUTED=True → 跳过事件制造
└── 管理员控制命令
    └── IS_MUTED状态不影响AdminDispatcher执行
```

#### 管理员控制系统说明

管理员控制系统为框架提供紧急控制和错误通知能力，确保系统在异常情况下的可控性。

**身份验证机制**：系统通过配置中的admin_qq字段识别管理员身份。只有来自指定QQ号的私聊消息才会被识别为管理员命令。

**控制命令处理**：支持两个核心控制命令。"mute"命令立即停止所有bot活动，包括事件处理和定时任务，适用于插件失控或系统维护场景。"unmute"命令恢复正常运行。命令处理优先级最高，即使在静音状态下也能执行。

**全局静音机制**：IS_MUTED状态影响框架的所有事件处理流程。普通QQ事件在静音状态下会被直接忽略，定时任务调度器也会跳过事件制造，但管理员控制命令始终有效，确保管理员能够恢复系统。

**错误通知系统**：当启用时，系统会监控所有logging调用，将达到配置级别的错误信息自动发送到管理员QQ。通过消息内容哈希实现防刷屏机制，相同类型的错误在配置时间内只通知一次。通知发送在后台线程执行，避免影响主要功能。

**设计权衡**：管理员功能优先考虑紧急控制能力而非功能完整性。系统只提供最基本但最关键的控制命令，确保在任何情况下管理员都能有效控制bot行为。

## 2. 全局变量说明

### 事件系统相关
- **`EVENT_TYPES_`**: `List[str]` - 所有支持的OneBot 11事件类型的完整列表，包括消息事件、通知事件、请求事件、元事件
- **`EVENT_INHERITANCE`**: `Dict[str, List[str]]` - 事件继承关系映射，如MESSAGE_GROUP_MENTION会同时触发MESSAGE_GROUP的处理函数
- **`NAPCAT_LISTENER`**: `Flask` - Flask应用实例，处理来自NapCat的HTTP请求

### 插件注册系统
- **`PLUGIN_REGISTRY`**: `Dict[str, List[callable]]` - 主要的插件注册表，键为事件类型，值为处理该事件的函数列表
- **`UNCONDITIONAL_REGISTRY`**: `List[tuple[callable, int]]` - 无条件事件插件注册表，存储(函数, 执行间隔分钟数)元组
- **`INITIALIZER_REGISTRY`**: `List[tuple[callable, str]]` - 初始化插件注册表，存储(函数, 插件名称)元组

### 配置系统
- **`CONFIG`**: `Dict` - 框架配置字典，包含NapCat连接、数据库路径、插件执行限制、管理员通知等所有配置项

### 管理员控制系统
- **`IS_MUTED`**: `bool` - 全局静音状态，管理员可通过"mute"/"unmute"命令控制，影响所有事件处理和定时任务
- **`LOGGING_LEVELS`**: `Dict[str, int]` - 日志级别到数值的映射，用于判断是否发送QQ通知
- **`AdminNotificationInProgress`**: `bool` - 防止通知发送并发的锁定标志
- **`AdminNotificationLast`**: `Dict[str, float]` - 消息hash到上次发送时间的映射，用于防刷屏限制

## 3. 函数说明

### 系统初始化相关

#### `multiprocessing.set_start_method()`
- **用途**: 设置多进程创建方法为'spawn'，确保子进程环境隔离
- **调用时机**: 模块导入时立即执行
- **重要性**: 必须在创建任何进程前调用，为插件进程隔离奠定基础

#### `Initializer() -> None`
- **用途**: 框架初始化的主控函数，完成所有启动前准备工作
- **执行步骤**:
  1. 配置管理员通知系统
  2. 初始化数据库结构
  3. 初始化插件注册表
  4. 扫描和加载插件文件
  5. 执行插件INITIALIZER函数
  6. 启动后台调度器
- **错误处理**: 插件加载失败会被记录但不影响其他插件，INITIALIZER函数执行失败的插件会被从所有注册表中移除

#### `DatabaseInitializer() -> None`
- **用途**: 创建SQLite数据库和所有必要的表结构
- **创建的表**:
  - `FRIEND_EVENTS`: 私聊相关事件存储
  - `GROUP_EVENTS`: 群聊相关事件存储  
  - `OTHER_EVENTS`: 其他类型事件存储
  - `PLUGIN_CONFIGS`: 插件配置数据存储
- **性能优化**: 启用WAL模式，创建时间戳索引
- **错误处理**: 数据库创建失败会记录错误但不中断初始化

#### `UnconditionalScheduler() -> None`
- **用途**: 在独立线程中运行的无条件事件调度器，定期制造unconditional事件
- **设计哲学**: 保持"事件-响应"模式的一致性，UNCONDITIONAL插件响应人工制造的事件而非直接执行定时任务
- **调度保证**: 确保处理函数在每个应执行的整分钟中被调用一次，但不保证调用间隔均匀
- **时机控制**: 通过sleep(到下一分钟秒数+3秒缓冲)实现，通常在每分钟2-4秒执行，避免舍入误差
- **间隔机制**: "间隔N"表示在分钟数能被N整除时执行，而非每隔N分钟执行（要均匀间隔需使用60的因数）
- **事件制造**: 为筛选出的处理函数创建包含基本标识和时间戳的unconditional事件
- **事件分发**: 通过PluginCaller()将制造的事件分发给相应的处理函数，支持并行执行和返回值处理
- **静音支持**: 检查IS_MUTED状态，静音时跳过事件制造
- **生命周期**: daemon线程，随主程序退出而终止

### 事件处理相关

#### `NapCatListener() -> str`
- **用途**: Flask路由处理函数，接收NapCat的HTTP POST请求
- **处理流程**: 
  1. 解析JSON格式的事件数据
  2. 调用AdminDispatcher()检查管理员控制命令
  3. 检查IS_MUTED静音状态
  4. 调用MainDispatcher()进行主要事件处理
- **返回值**: 始终返回"OK"字符串作为HTTP响应
- **错误处理**: 所有异常都被内部函数处理，不会向NapCat返回错误状态

#### `MainDispatcher(rawEvent: Dict) -> None`
- **用途**: 事件处理的主控函数，协调整个处理流程
- **处理步骤**:
  1. 事件类型解析和分类
  2. 生成简化事件数据
  3. 存储事件历史
  4. 收集相关处理函数（包括继承关系）
  5. 启动并行插件执行
- **并发特性**: 同时处理历史存储和插件执行，提高响应速度

#### `EventTypeParser(rawEvent: Dict) -> str`
- **用途**: 将OneBot 11格式的原始事件转换为框架内部的事件类型标识
- **分类逻辑**: 
  - 根据post_type进行初步分类（message/notice/request/meta_event）
  - 根据子类型进行进一步细分
  - 对群消息调用GroupMessageAnalyzer()进行特殊处理
- **返回值**: 事件类型字符串（如"MESSAGE_PRIVATE"）或"UNEXPECTED"
- **扩展性**: 支持新增事件类型，便于框架功能扩展

#### `GroupMessageAnalyzer(rawEvent: Dict) -> str`
- **用途**: 对群消息进行细粒度分类，实现智能事件过滤
- **分类规则**:
  - **MESSAGE_GROUP_MENTION**: 消息中包含@机器人
  - **MESSAGE_GROUP_BOT**: 消息以指令前缀（.、/、\）开头
  - **MESSAGE_GROUP**: 普通群消息
- **性能优化**: 通过事件过滤减少不必要的插件调用，提高系统效率
- **优先级**: @提及优先级最高，指令前缀次之，普通消息最低

#### `InbondMessageParser(rawEvent: Dict) -> Union[Dict, None]`
- **用途**: 为消息类事件生成简化的数据结构，提取插件常用信息
- **处理范围**: 仅处理MESSAGE_PRIVATE、MESSAGE_GROUP系列事件
- **提取内容**: 
  - 从message字段中提取所有text类型段的文本内容
  - 提取用户ID、群ID等标识信息
  - 拼接多个文本段为完整消息
- **返回值**: 包含user_id、text_message等字段的字典，或None（非消息事件）

#### `Historian(rawEvent: Dict) -> None`
- **用途**: 将事件数据同步存储到SQLite数据库，为Librarian功能提供数据支撑
- **同步设计原因**: 确保后续执行的插件能够通过Librarian读取到包含当前事件在内的完整、最新的历史记录
- **存储策略**: 
  - 根据事件类型选择存储表（FRIEND_EVENTS/GROUP_EVENTS/OTHER_EVENTS）
  - 过滤高频无用事件（如NOTICE_INPUT_STATUS）
  - JSON序列化完整事件数据
- **性能考虑**: 使用连接池和事务，支持重试机制
- **错误处理**: 存储失败不影响事件处理，记录错误日志

### 插件执行相关

#### `PluginCaller(handlers: List[Callable], simpleEvent: Union[Dict, None], rawEvent: Dict, resultCallback: Optional[Callable]) -> List[Any]`
- **用途**: 并行执行多个插件的主控函数，实现框架的核心执行能力
- **并行机制**: 为每个插件创建独立线程，所有插件同时启动执行
- **立即响应**: 插件完成后立即调用resultCallback处理结果，不等待其他插件
- **错误处理**: 插件异常转换为None，不影响其他插件执行
- **超时控制**: 设置最大等待时间，防止无限等待
- **返回值**: 按原始插件顺序返回结果列表

#### `PluginCallerSingle(handler, simpleEvent: Union[Dict, None], rawEvent: Dict)`
- **用途**: 执行单个插件的核心函数，提供进程隔离和资源控制
- **进程管理**: 创建独立子进程运行插件代码，提供绝对错误隔离
- **资源监控**: 持续监控子进程的CPU、内存、执行时间
- **通信机制**: 使用multiprocessing.Pipe()与子进程通信
- **错误类型**: 区分插件异常和系统错误（超时、资源超限等）
- **清理机制**: 确保子进程在各种情况下都能被正确清理
- **返回值**: 插件的实际返回值或错误信息字典或None

#### `PluginWorker(handler, simpleEvent, rawEvent, resultPipe, memoryLimit)`
- **用途**: 在子进程中实际执行插件代码的工作函数
- **资源限制**: 设置进程级别的内存限制（Linux only）
- **环境构建**: 创建子进程版本的botContext，包含API、配置、历史记录功能
- **参数适配**: 根据插件函数签名动态选择传入的参数
- **结果传递**: 通过管道将执行结果或异常信息发送回主进程
- **错误封装**: 将异常转换为结构化的错误信息

#### `PluginMonitor(process, startTime, maxCpuTime, maxWallTime, memoryLimit)`
- **用途**: 监控插件进程的资源使用情况，实现资源保护
- **监控项目**: CPU时间、墙钟时间、内存使用量
- **检查间隔**: 按配置的监控间隔定期检查
- **终止条件**: 任一资源指标超限时返回终止原因
- **错误处理**: 进程已结束时静默处理
- **返回值**: None表示正常，字符串表示终止原因

### 响应处理相关

#### `OutbondMessageParser(pluginResponse: Any, rawEvent: Dict) -> None`
- **用途**: 解析插件返回值并转换为相应的QQ操作
- **支持类型**: 字符串（文本消息）、字典（API调用）、列表（批量操作）
- **上下文识别**: 根据rawEvent确定发送目标（私聊/群聊/通知场景）
- **消息构造**: 将字符串包装为OneBot 11消息格式
- **API透传**: 将字典格式直接作为API调用传递
- **递归处理**: 对列表类型递归调用自身处理每个元素
- **错误处理**: 无效格式时记录警告并跳过

#### `NapCatSender(actionEndpoint: str, requestBody: Dict) -> None`
- **用途**: 向NapCat服务器发送API请求的底层函数
- **重试机制**: 支持可配置的重试次数和超时设置
- **错误分类**: 区分客户端错误（4xx）和服务器错误（5xx）
- **状态检查**: API失败时自动查询机器人状态辅助诊断
- **超时处理**: 防止网络问题导致的长时间阻塞
- **日志记录**: 详细记录请求失败的原因和状态

### botContext工具函数 (插件开发者接口)

#### `Librarian(eventIdentifier: Dict, eventCount: int = 50) -> List[Dict]`
- **用途**: 查询历史事件记录，为插件提供上下文信息
- **入参**: 
  - `eventIdentifier`: 查询标识字典，必须包含type字段
    - `{"type": "private", "user_id": 123456}` - 查询与特定用户的私聊历史
    - `{"type": "group", "group_id": 789012}` - 查询特定群聊的历史
    - `{"type": "other", "event_type": "REQUEST_FRIEND"}` - 查询特定类型的其他事件
  - `eventCount`: 返回的事件数量，默认50，按时间倒序
- **返回值**: 事件列表，每个事件为完整的OneBot 11格式字典，按时间正序排列
- **使用场景**: 分析用户行为模式、实现对话记忆、统计功能等

#### `ConfigReader() -> Dict`
- **用途**: 读取当前插件的配置数据
- **入参**: 无（自动识别调用插件的名称）
- **返回值**: 配置字典，如果插件尚无配置则返回空字典`{}`
- **数据持久化**: 配置存储在SQLite数据库中，重启后保持
- **使用场景**: 获取API密钥、用户偏好设置、插件状态信息等

#### `ConfigWriter(config: Dict) -> None`
- **用途**: 保存当前插件的配置数据
- **入参**: 
  - `config`: 配置字典，必须是可JSON序列化的dict类型
- **返回值**: None
- **覆盖策略**: 完全覆盖现有配置，不进行合并
- **错误处理**: 无效配置格式会记录错误并忽略写入操作
- **使用场景**: 保存API密钥、更新用户设置、记录插件状态等

#### `ApiCaller(action: str, data: Dict) -> Union[Dict, None]`
- **用途**: 向NapCat发送查询类API请求并获取响应数据
- **设计用途**: 主要用于调用OneBot 11的查询类API（get_friend_list、get_group_info、get_group_member_list等），获取返回数据用于指导插件的进一步决策
- **入参**:
  - `action`: OneBot 11 API动作名，通常是"get_"开头的查询类API
  - `data`: API参数字典，格式按OneBot 11规范
- **返回值**: 
  - 成功时返回API响应的data字段(Dict)
  - 失败时返回None（网络错误、超时、API错误等）
- **与返回值的分工**: 行动类API（send_msg、set_group_card等）推荐通过插件返回值调用，因为这些API的返回值通常不重要
- **超时设置**: 5秒超时，防止插件被阻塞
- **使用场景**: 获取好友列表、查询群信息、检查权限等需要返回数据的操作

#### 子进程版本函数差异

在子进程执行环境中，botContext工具有专门的实现版本：

- `SubprocessConfigReader(pluginName: str) -> Dict`
- `SubprocessConfigWriter(pluginName: str, config: Dict) -> None`  
- `SubprocessApiCaller(action: str, data: Dict) -> Union[Dict, None]`
- `SubprocessLibrarian(eventIdentifier: Dict, eventCount: int = 50) -> List[Dict]`

这些函数与主进程版本的接口完全相同，但在实现上适配了子进程环境的特殊需求（如数据库连接管理、错误处理等）。插件开发者无需关心这些差异，框架会自动选择合适的版本。

### 管理员控制系统相关

#### `AdminDispatcher(rawEvent: Dict) -> bool`
- **用途**: 检查和处理管理员控制命令，提供紧急控制能力
- **检查条件**: 
  - 事件类型必须为私聊消息（post_type="message", message_type="private"）
  - 发送者QQ号必须与CONFIG['ADMIN_NOTIFICATION']['admin_qq']匹配
  - admin_qq必须已配置（非0值）
- **命令处理**:
  - `"mute"`: 设置IS_MUTED=True，停止所有bot活动
  - `"unmute"`: 设置IS_MUTED=False，恢复正常运行
  - 其他内容: 不作为管理员命令处理
- **返回值**: True表示已处理管理员命令，应跳过后续事件处理；False表示继续正常流程
- **优先级**: 在事件处理流程中优先级最高，即使在静音状态下也能执行

#### `LoggingNotificationConfigurator() -> None`
- **用途**: 通过monkey patch增强标准logging模块，添加QQ通知功能
- **实现机制**: 
  - 保存原始logging函数（debug, info, warning, error, critical）
  - 创建增强版本，在调用原函数后检查是否需要QQ通知
  - 替换logging模块中的函数引用
- **影响范围**: 全局生效，所有使用标准logging模块的代码都将获得通知能力
- **调用时机**: 在框架初始化阶段执行，仅在启用通知功能时生效

#### `MessageHasher(message: str) -> str`
- **用途**: 为错误消息生成短哈希，用于防刷屏机制中识别相同类型错误
- **入参**: `message` - 错误消息字符串
- **返回值**: 8位MD5哈希字符串
- **应用**: 相同哈希的错误消息在rate_limit_seconds时间内只通知一次

#### `NotificationEligibilityChecker(recordLevelName: str) -> bool`
- **用途**: 检查指定日志级别是否应该触发QQ通知
- **入参**: `recordLevelName` - 日志级别名称（"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"）
- **检查项**: 
  - 通知功能是否启用（CONFIG['ADMIN_NOTIFICATION']['enabled']）
  - 管理员QQ是否配置（CONFIG['ADMIN_NOTIFICATION']['admin_qq']）
  - 日志级别是否达到通知阈值（CONFIG['ADMIN_NOTIFICATION']['notify_level']）
- **返回值**: True表示应该发送通知，False表示不需要通知

#### `QQNotificationSender(level: str, message: str) -> None`
- **用途**: 在后台线程中向管理员QQ发送错误通知
- **入参**: 
  - `level` - 日志级别字符串
  - `message` - 错误消息内容
- **防刷屏机制**: 基于消息哈希实现，相同类型错误在rate_limit_seconds内只发送一次
- **并发控制**: 使用AdminNotificationInProgress标志防止并发发送
- **异步执行**: 在daemon线程中执行，不阻塞主流程
- **错误处理**: 静默失败，避免通知系统错误引起递归