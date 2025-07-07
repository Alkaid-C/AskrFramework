# Askr Framework API Reference

**插件开发者API参考文档**

## 版本信息

适用的框架版本：[Beta 0.2] - *You Asked for This*

文档版本：Beta 0.2.1

最后更新日期：2025-07-07


## MANIFEST声明规范

### 事件类型完整列表

#### 消息事件 (Message Events)

| 事件名称 | 事件代码 | 支持的入参 | 支持的返回值 |
|---------|---------|-----------|-------------|
| 私聊消息 | `MESSAGE_PRIVATE` | simpleEvent, rawEvent, botContext | string, dict, list |
| 群聊消息 | `MESSAGE_GROUP` | simpleEvent, rawEvent, botContext | string, dict, list |
| 群聊@消息 | `MESSAGE_GROUP_MENTION` | simpleEvent, rawEvent, botContext | string, dict, list |
| 群聊指令消息 | `MESSAGE_GROUP_BOT` | simpleEvent, rawEvent, botContext | string, dict, list |

#### 通知事件 (Notice Events)

| 事件名称 | 事件代码 | 支持的入参 | 支持的返回值 |
|---------|---------|-----------|-------------|
| 好友添加 | `NOTICE_FRIEND_ADD` | rawEvent, botContext | string, dict, list |
| 好友消息撤回 | `NOTICE_FRIEND_RECALL` | rawEvent, botContext | string, dict, list |
| 群消息撤回 | `NOTICE_GROUP_RECALL` | rawEvent, botContext | string, dict, list |
| 群成员增加 | `NOTICE_GROUP_INCREASE` | rawEvent, botContext | string, dict, list |
| 群成员减少 | `NOTICE_GROUP_DECREASE` | rawEvent, botContext | string, dict, list |
| 群管理员变动 | `NOTICE_GROUP_ADMIN` | rawEvent, botContext | string, dict, list |
| 群禁言 | `NOTICE_GROUP_BAN` | rawEvent, botContext | string, dict, list |
| 群文件上传 | `NOTICE_GROUP_UPLOAD` | rawEvent, botContext | string, dict, list |
| 群名片变更 | `NOTICE_GROUP_CARD` | rawEvent, botContext | string, dict, list |
| 群名变更 | `NOTICE_GROUP_NAME` | rawEvent, botContext | string, dict, list |
| 群头衔变更 | `NOTICE_GROUP_TITLE` | rawEvent, botContext | string, dict, list |
| 戳一戳 | `NOTICE_POKE` | rawEvent, botContext | string, dict, list |
| 个人资料点赞 | `NOTICE_PROFILE_LIKE` | rawEvent, botContext | string, dict, list |
| 输入状态 | `NOTICE_INPUT_STATUS` | rawEvent, botContext | string, dict, list |
| 精华消息 | `NOTICE_ESSENCE` | rawEvent, botContext | string, dict, list |
| 群消息表情回应 | `NOTICE_GROUP_MSG_EMOJI_LIKE` | rawEvent, botContext | string, dict, list |
| 机器人离线 | `NOTICE_BOT_OFFLINE` | rawEvent, botContext | 无 |

#### 请求事件 (Request Events)

| 事件名称 | 事件代码 | 支持的入参 | 支持的返回值 |
|---------|---------|-----------|-------------|
| 好友请求 | `REQUEST_FRIEND` | rawEvent, botContext | 无 |
| 群请求/邀请 | `REQUEST_GROUP` | rawEvent, botContext | string, dict, list |

#### 特殊事件 (Special Events)

| 事件名称 | 事件代码 | 支持的入参 | 支持的返回值 |
|---------|---------|-----------|-------------|
| 插件初始化 | `INITIALIZER` | botContext | None或抛出异常 |
| 无条件事件 | `UNCONDITIONAL` | rawEvent, botContext | dict, list |

#### 其他事件 (Other Events - 不建议监听)

| 事件名称 | 事件代码 | 支持的入参 | 支持的返回值 |
|---------|---------|-----------|-------------|
| 私聊消息发送 | `MESSAGE_SENT_PRIVATE` | rawEvent, botContext | 无 |
| 群聊消息发送 | `MESSAGE_SENT_GROUP` | rawEvent, botContext | 无 |
| 心跳包 | `META_HEARTBEAT` | rawEvent, botContext | 无 |
| 生命周期 | `META_LIFECYCLE` | rawEvent, botContext | 无 |

**注意**：
- **特殊事件**：`INITIALIZER`和`UNCONDITIONAL`是框架内置的特殊事件类型
- **其他事件**：除非你知道你在做什么，不要监听这些事件类型。

### MANIFEST格式规范

#### 基本格式

```python
MANIFEST = {
    "事件类型": "处理函数名",
    # 可以声明多个事件类型
}
```

#### 普通事件声明

```python
MANIFEST = {
    "MESSAGE_PRIVATE": "handle_private_message",
    "MESSAGE_GROUP": "handle_group_message",
    "NOTICE_FRIEND_ADD": "handle_friend_add"
}
```

#### UNCONDITIONAL事件声明

UNCONDITIONAL事件用于定时任务，支持两种格式：

**格式1：默认间隔（每分钟执行）**
```python
MANIFEST = {
    "UNCONDITIONAL": "scheduled_task"
}
```

**格式2：指定间隔**
```python
MANIFEST = {
    "UNCONDITIONAL": ["scheduled_task", 15]  # 每15分钟执行一次
}
```

**间隔说明**：
- 间隔值必须为1-60之间的整数
- 间隔N表示在分钟数能被N整除时执行（如间隔15：第0、15、30、45分钟执行）
- 要获得均匀的时间间隔，建议使用60的因数：1、2、3、4、5、6、10、12、15、20、30、60

#### INITIALIZER事件声明

INITIALIZER事件用于插件初始化，在框架启动时执行：

```python
MANIFEST = {
    "INITIALIZER": "plugin_init"
}
```

#### 组合声明示例

```python
MANIFEST = {
    "INITIALIZER": "init_plugin",           # 初始化函数
    "MESSAGE_PRIVATE": "handle_private",    # 私聊处理
    "MESSAGE_GROUP_BOT": "handle_command",  # 群指令处理
    "UNCONDITIONAL": ["daily_task", 60]    # 每小时执行的定时任务
}
```

### 事件扩展机制

某些事件类型具有扩展关系，子事件会同时触发父事件的处理函数：

- `MESSAGE_GROUP_MENTION` → 同时触发 `MESSAGE_GROUP`
- `MESSAGE_GROUP_BOT` → 同时触发 `MESSAGE_GROUP`

**技术行为**：
- 监听`MESSAGE_GROUP_MENTION`的插件：只接收@机器人的群消息
- 监听`MESSAGE_GROUP_BOT`的插件：只接收指令格式（以`.` `/` `\`开头）的群消息  
- 监听`MESSAGE_GROUP`的插件：接收所有群消息，包括上述两种

**使用示例**：
```python
# 指令机器人 - 只处理命令
MANIFEST = {"MESSAGE_GROUP_BOT": "handle_command"}

# AI对话机器人 - 只处理@消息
MANIFEST = {"MESSAGE_GROUP_MENTION": "handle_mention"}

# 群管理机器人 - 处理所有群消息
MANIFEST = {"MESSAGE_GROUP": "handle_all_messages"}
```

## 函数参数规范

### 入参选择规范

插件函数可以按需选择所需的参数，但有以下限制：

**允许的参数名**：`simpleEvent`、`rawEvent`、`botContext`

**参数数量要求**：
- **所有事件类型**：可以声明0个或多个参数，完全按需选择

**有效的函数声明示例**：
```python
#  各种有效的参数组合
def simple_handler():                           # 无参数（适用于所有事件类型）
def context_only(botContext):                   # 只需要框架工具
def event_only(rawEvent):                       # 只需要完整事件数据
def message_only(simpleEvent):                  # 只处理消息文本
def full_handler(simpleEvent, rawEvent, botContext):  # 全部参数
def partial_handler(simpleEvent, botContext):   # 部分参数组合

#  无效的声明
def invalid_handler(unknown_param):             # 未知参数名
```

**参数可用性对照**：

| 事件类型 | simpleEvent | rawEvent | botContext | 最少参数数 |
|---------|-------------|----------|------------|-----------|
| 消息事件 | 可用 | 可用 | 可用 | 0 |
| 通知事件 | 不可用 | 可用 | 可用 | 0 |
| 请求事件 | 不可用 | 可用 | 可用 | 0 |
| INITIALIZER | 不可用 | 不可用 | 可用 | 0 |
| UNCONDITIONAL | 不可用 | 可用 | 可用 | 0 |

### simpleEvent参数

`simpleEvent`是框架为消息事件提供的简化数据结构，只包含插件最常用的字段。

#### 私聊消息事件

```python
def handle_private(simpleEvent):
    # simpleEvent结构：
    {
        "user_id": 12345678,      # int: 发送者QQ号
        "text_message": "你好"     # str: 纯文本消息内容
    }
```

#### 群聊消息事件

```python  
def handle_group(simpleEvent):
    # simpleEvent结构：
    {
        "user_id": 12345678,      # int: 发送者QQ号
        "group_id": 87654321,     # int: 群号
        "text_message": "你好"     # str: 纯文本消息内容
    }
```

**说明**：
- `text_message`字段会自动提取所有text类型消息段的内容并拼接
- 图片、表情等非文本内容会被忽略
- 消息中的@、回复等特殊格式也会被过滤，只保留纯文本
- 非消息事件不支持`simpleEvent`参数

### rawEvent参数

`rawEvent`包含完整的OneBot 11格式事件数据，提供所有可用信息。

#### 标准事件

对于来自NapCat的标准事件（消息、通知、请求、元事件），请参考OneBot 11官方文档：

**📖 [OneBot 11 事件文档](https://napneko.github.io/onebot/event)**

#### UNCONDITIONAL事件

UNCONDITIONAL事件的rawEvent是框架人工制造的：

```python
def scheduled_task(rawEvent):
    # rawEvent结构：
    {
        "post_type": "unconditional",    # str: 事件类型标识
        "time": 1703123456               # int: Unix时间戳，插件被调度的时间
    }
```

**使用示例**：
```python
import datetime

def daily_reminder(rawEvent):
    # 获取当前调度时间
    schedule_time = rawEvent["time"]
    current_time = datetime.datetime.fromtimestamp(schedule_time)
    
    # 基于时间进行逻辑判断
    if current_time.hour == 9 and current_time.minute == 0:
        return {
            "action": "send_group_msg",
            "data": {
                "group_id": 123456,
                "message": [{"type": "text", "data": {"text": "早上好！"}}]
            }
        }
```

### botContext参数

`botContext`是一个字典，包含框架提供的工具函数，支持历史查询、配置管理、API调用等功能。

#### Librarian - 历史记录查询

```python
def my_plugin(botContext):
    # 基本查询 - 获取最近50条记录
    private_history = botContext["Librarian"](
        {"type": "private", "user_id": 12345}
    )
    
    # 指定数量查询
    group_history = botContext["Librarian"](
        {"type": "group", "group_id": 67890},
        eventCount=100  # 最近100条
    )
    
    # 时间窗口查询
    recent_messages = botContext["Librarian"](
        {"type": "group", "group_id": 67890},
        interval=300  # 最近5分钟
    )
    
    # 组合查询 - 时间窗口内的有限数量
    limited_recent = botContext["Librarian"](
        {"type": "group", "group_id": 67890},
        eventCount=50,      # 最多50条
        interval=600,       # 最近10分钟内
        intervalMaxCount=200  # interval查询时最多尝试200条
    )
    
    # 格式化输出
    history_text = botContext["Librarian"](
        {"type": "private", "user_id": 12345},
        interval=3600,
        stringOutput=True  # 返回格式化字符串
    )
```

**函数签名**：
```python
Librarian(
    eventIdentifier: Dict, 
    eventCount: int = 50,
    interval: Optional[int] = None,
    intervalMaxCount: int = 2047,
    stringOutput: bool = False
) -> Union[List[Dict], str]
```

**参数说明**：
- `eventIdentifier`: 查询条件字典
  - `{"type": "private", "user_id": QQ号}` - 私聊历史
  - `{"type": "group", "group_id": 群号}` - 群聊历史
  - `{"type": "other", "event_type": "事件类型"}` - 其他事件历史
- `eventCount`: 返回记录数量，默认50；设置为0时返回全部
- `interval`: 时间窗口（秒），查询最近N秒内的事件
- `intervalMaxCount`: 使用interval时的最大查询数量，默认2047
- `stringOutput`: 是否返回格式化字符串，默认False

**返回值**：
- 默认返回事件列表（List[Dict]），按时间从旧到新排序
- `stringOutput=True`时返回格式化的多行字符串

**查询策略**：
- 当提供`interval`参数时，使用二分查询法避免一次加载过多数据
- 当同时提供`eventCount`和`interval`时，先按时间过滤，再限制数量
- `intervalMaxCount`防止时间跨度过大导致的性能问题

#### ConfigReader - 配置读取

```python
def my_plugin(botContext):
    # 读取当前插件的配置
    config = botContext["ConfigReader"]()
    
    # 获取配置项（需要处理配置不存在的情况）
    api_key = config.get("api_key", "")
    user_settings = config.get("user_settings", {})
```

**函数签名**：`ConfigReader() -> Dict`

**参数说明**：无参数，自动识别调用插件的名称

**返回值**：配置字典，如果插件尚无配置则返回空字典`{}`

#### ConfigWriter - 配置写入

```python
def my_plugin(botContext):
    # 准备配置数据
    new_config = {
        "api_key": "your_api_key_here",
        "user_settings": {
            "language": "zh-CN",
            "notifications": True
        }
    }
    
    # 保存配置（完全覆盖现有配置）
    botContext["ConfigWriter"](new_config)
```

**函数签名**：`ConfigWriter(config: Dict) -> None`

**参数说明**：
- `config`: 配置字典，必须是可JSON序列化的dict类型

**返回值**：None

**注意事项**：
- 采用完全覆盖策略，不会与现有配置合并
- 配置会持久化存储，重启后保持
- 每个插件拥有独立的配置命名空间

#### CrossOriginConfigReader - 跨域配置读取

```python
def admin_plugin(botContext):
    # 读取其他插件的配置（需要privilege权限）
    target_config = botContext["CrossOriginConfigReader"]("target_plugin")
    
    if target_config is None:
        # 权限不足或读取失败
        return "无法读取目标插件配置"
    
    # 使用获取的配置
    api_key = target_config.get("api_key", "")
```

**函数签名**：`CrossOriginConfigReader(target_plugin: str) -> Union[Dict, None]`

**参数说明**：
- `target_plugin`: 目标插件名（可以带或不带.py后缀）

**返回值**：
- 成功时返回目标插件的配置字典
- 权限不足或失败时返回None

**权限要求**：
- 调用插件必须在`PluginsAccessControl.json`中设置`"privilege": true`
- 访问会记录INFO级别日志

#### CrossOriginConfigWriter - 跨域配置写入

```python
def admin_plugin(botContext):
    # 修改其他插件的配置（需要privilege权限）
    new_config = {
        "enabled": False,
        "reason": "Disabled by admin"
    }
    
    result = botContext["CrossOriginConfigWriter"]("target_plugin", new_config)
    
    if result is None:
        return "权限不足，无法修改配置"
    
    return "配置已更新"
```

**函数签名**：`CrossOriginConfigWriter(target_plugin: str, config: Dict) -> Union[bool, None]`

**参数说明**：
- `target_plugin`: 目标插件名（可以带或不带.py后缀）
- `config`: 要写入的配置字典

**返回值**：
- 成功时返回True
- 权限不足或失败时返回None

**权限要求**：
- 调用插件必须在`PluginsAccessControl.json`中设置`"privilege": true`
- 访问会记录INFO级别日志

#### ApiCaller - API调用

```python
def my_plugin(botContext):
    # 获取好友列表
    friends = botContext["ApiCaller"]("get_friend_list", {})
    
    # 获取群信息
    group_info = botContext["ApiCaller"]("get_group_info", {
        "group_id": 123456
    })
    
    # 检查群成员信息
    member_info = botContext["ApiCaller"]("get_group_member_info", {
        "group_id": 123456,
        "user_id": 789012
    })
    
    # 基于查询结果进行处理
    if group_info and group_info.get("member_count", 0) > 100:
        # 大群逻辑
        pass
```

**函数签名**：`ApiCaller(action: str, data: Dict) -> Union[Dict, None]`

**参数说明**：
- `action`: OneBot 11 API动作名，推荐使用查询类API（get_开头）
- `data`: API参数字典，格式按OneBot 11规范

**返回值**：
- 成功时返回API响应的data字段（Dict类型）
- 失败时返回None（网络错误、超时、API错误等）

**使用建议**：
- 主要用于查询类API，获取数据用于决策
- 行动类API（send_msg等）推荐通过插件返回值调用
- 设置了5秒超时，防止插件被阻塞
- 需要处理返回None的情况

**API分工原则**：
```python
def example_plugin(simpleEvent, botContext):
    # 使用ApiCaller查询信息
    group_info = botContext["ApiCaller"]("get_group_info", {
        "group_id": simpleEvent["group_id"]
    })
    
    if group_info and group_info.get("member_count", 0) > 50:
        # 使用返回值执行行动
        return "这是一个大群！"
    
    # 不推荐：用ApiCaller执行行动类API
    # botContext["ApiCaller"]("send_group_msg", {...})
```

**API文档参考**：
- **ApiCaller支持的API列表** [OneBot 11 API文档](https://github.com/botuniverse/onebot-11/blob/master/api/public.md)

## 返回值规范

插件函数的返回值决定了框架将执行的动作。不同事件类型支持不同的返回值格式。

### 支持的返回值类型

#### string - 文本消息

**适用事件**：消息事件、通知事件（除`NOTICE_BOT_OFFLINE`）、部分请求事件

**处理逻辑**：框架根据原始事件的上下文自动确定发送目标（私聊或群聊）

**示例**：
```python
def handle_message(simpleEvent):
    return "你好！"  # 自动回复到原对话

def handle_group_increase(rawEvent):
    return f"欢迎新成员！"  # 发送到相关群聊
```

**限制**：
- `UNCONDITIONAL`事件不支持string返回值（缺少发送目标信息）
- `NOTICE_BOT_OFFLINE`事件不支持（机器人离线时无法发送）
- `REQUEST_FRIEND`事件不支持（未添加好友无法发送私聊）

#### dict - API调用

**适用事件**：除`INITIALIZER`外的所有事件

**格式要求**：
```python
{
    "action": "API动作名",
    "data": {
        # API参数字典
    }
}
```

**处理逻辑**：框架将dict直接作为OneBot 11 API调用发送到NapCat

**示例**：
```python
def send_custom_message():
    return {
        "action": "send_group_msg",
        "data": {
            "group_id": 123456,
            "message": [
                {"type": "text", "data": {"text": "Hello "}},
                {"type": "at", "data": {"qq": "789012"}},
                {"type": "text", "data": {"text": "!"}}
            ]
        }
    }

def set_group_card(rawEvent):
    return {
        "action": "set_group_card", 
        "data": {
            "group_id": rawEvent["group_id"],
            "user_id": rawEvent["user_id"],
            "card": "新群名片"
        }
    }
```

#### list - 批量操作

**适用事件**：除`INITIALIZER`外的所有事件

**格式要求**：列表中的每个元素必须是string或dict类型

**处理逻辑**：框架递归处理列表中的每个元素，按顺序执行

**示例**：
```python
def multi_action(simpleEvent):
    return [
        "首先发送文本消息",
        {
            "action": "send_group_msg",
            "data": {
                "group_id": 123456,
                "message": [{"type": "text", "data": {"text": "然后发送到指定群"}}]
            }
        },
        "最后再发送一条消息"
    ]

def welcome_package(rawEvent):
    user_id = rawEvent["user_id"]
    return [
        f"欢迎 @{user_id}！",
        {
            "action": "set_group_card",
            "data": {
                "group_id": rawEvent["group_id"],
                "user_id": user_id,
                "card": "新成员"
            }
        }
    ]
```

**注意事项**：
- 列表中不能包含其他类型的元素（如int、bool等）
- 无效元素会被跳过并记录警告
- UNCONDITIONAL事件中的string元素会被忽略（无发送目标）

#### None - 无动作

**适用事件**：所有事件

**处理逻辑**：框架不执行任何动作

**使用场景**：
```python
def conditional_handler(simpleEvent):
    if not simpleEvent["text_message"].startswith("/"):
        return None  # 非指令消息不处理
    
    # 处理指令逻辑...
    return "指令执行完成"

def quiet_observer(rawEvent):
    # 只记录日志，不发送任何消息
    logging.info(f"观察到事件: {rawEvent['post_type']}")
    return None  # 推荐显式返回None
```

**INITIALIZER特殊机制**：
```python
def plugin_init(botContext):
    try:
        # 检查API密钥有效性
        config = botContext["ConfigReader"]()
        api_key = config.get("api_key")
        
        if not api_key:
            # 创建默认配置
            default_config = {"api_key": "", "enabled": False}
            botContext["ConfigWriter"](default_config)
            raise Exception("API密钥未配置，请设置后重启")
        
        # 验证API密钥
        result = botContext["ApiCaller"]("test_api", {"key": api_key})
        if not result:
            raise Exception("API密钥无效")
        
        # 初始化成功
        return None
        
    except Exception as e:
        # 初始化失败，插件将被移除
        raise e
```

### 返回值处理时机

**立即处理**：插件返回值会立即被框架处理，无需等待其他插件完成

**错误容忍**：如果返回值格式错误，框架会记录警告并跳过该返回值，不影响其他插件

**并发安全**：多个插件的返回值可以同时处理，框架确保线程安全

### 最佳实践

**选择合适的返回值类型**：
- 简单文本回复：使用string
- 复杂消息或特定API：使用dict
- 多个连续操作：使用list
- 不需要输出：显式返回None（推荐明确写出return None）

**错误处理**：
```python
def robust_handler(simpleEvent, botContext):
    try:
        # 业务逻辑
        result = some_complex_operation()
        return f"操作成功：{result}"
    except Exception as e:
        # 记录错误但不崩溃
        logging.error(f"处理失败: {e}")
        return None  # 显式返回None，表示无动作

def conditional_handler(simpleEvent):
    if simpleEvent["text_message"] == "ping":
        return "pong"
    # 显式返回None，代码意图更清晰
    return None
```

**INITIALIZER最佳实践**：
```python
def plugin_init(botContext):
    """
    INITIALIZER函数应该：
    1. 成功完成时返回None
    2. 遇到无法恢复的错误时抛出异常
    """
    try:
        # 检查必要的配置
        config = botContext["ConfigReader"]()
        
        if "api_key" not in config:
            # 创建默认配置
            botContext["ConfigWriter"]({"api_key": "", "enabled": False})
            raise Exception("请配置API密钥后重启")
        
        # 验证外部依赖
        if not validate_external_service():
            raise Exception("外部服务不可用")
        
        # 初始化成功
        return None
        
    except Exception:
        # 让异常向上传播，框架会移除此插件
        raise
```

```

**API文档参考**：
- **dict返回值的action和data格式**： [OneBot 11 API文档](https://github.com/botuniverse/onebot-11/blob/master/api/public.md)

## 配置文件格式

### PluginsAccessControl.json

插件访问控制配置文件，控制插件的触发条件和权限。

```json
{
  "version": "1.0",
  "default_policy": "allow",
  "rules": {
    "global": {
      "private": {
        "BlackList": [999999]
      },
      "group": {
        "BlackList": [666666]
      },
      "privilege": false
    },
    "admin_plugin.py": {
      "private": {
        "WhiteList": [123456, 789012]
      },
      "group": {
        "WhiteList": [111111, 222222]
      },
      "privilege": true
    },
    "normal_plugin.py": {
      "private": {},
      "group": {
        "WhiteList": [333333]
      }
      // 没有privilege字段，使用global默认值
    }
  }
}
```

**字段说明**：

- **`version`**: 配置文件版本
- **`default_policy`**: 默认策略，`"allow"`或`"deny"`
- **`rules`**: 访问规则配置
  - **`global`**: 全局默认规则
    - **`private`**: 私聊规则
      - **`WhiteList`**: 白名单用户QQ号列表
      - **`BlackList`**: 黑名单用户QQ号列表
    - **`group`**: 群聊规则
      - **`WhiteList`**: 白名单群号列表
      - **`BlackList`**: 黑名单群号列表
    - **`privilege`**: 是否有跨域配置访问权限
  - **`插件名.py`**: 插件特定规则（格式同global）

**规则优先级**：
1. 插件特定规则 > global规则
2. WhiteList（白名单）> BlackList（黑名单）
3. 未匹配任何规则时使用`default_policy`

**privilege权限**：
- 设置为`true`的插件可以使用`CrossOriginConfigReader/Writer`
- 未设置时使用global的默认值
- 跨域访问会在日志中记录

### frameworkConfig.json

框架配置文件（可选），用于覆盖默认配置。

```json
{
  "version": "1.0",
  "NAPCAT_SERVER": {
    "api_url": "http://localhost:3000"
  },
  "NAPCAT_LISTEN": {
    "host": "0.0.0.0",
    "port": 19218
  },
  "PATHS": {
    "plugins_dir": "./plugins",
    "database_file": "./EventHistory.db",
    "access_control": "./PluginsAccessControl.json"
  },
  "PLUGIN_EXECUTION": {
    "max_cpu_time_seconds": 3.0,
    "max_wall_time_seconds": 30.0,
    "memory_limit_mb": 1024,
    "monitor_interval_seconds": 0.1,
    "process_creation_method": "spawn"
  },
  "ADMIN_NOTIFICATION": {
    "enabled": true,
    "admin_qq": 123456789,
    "notify_level": "ERROR",
    "rate_limit_seconds": 1200,
    "message_format": "Askr Alert \n[{level}] {time}\n{message}"
  },
  "GRACEFUL_SHUTDOWN": {
    "enabled": true,
    "max_wait_seconds": 30,
    "notify_admin_on_shutdown": true
  },
  "UNCONDITIONAL_SCHEDULER": {
    "enabled": true,
    "self_invoke_key": null
  }
}
```

**说明**：
- 只需提供要修改的配置项
- 未提供的配置项使用默认值
- 配置错误不会阻止框架启动