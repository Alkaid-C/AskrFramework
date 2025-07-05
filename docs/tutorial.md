# Askr Framework 教程

## 设计理念

Askr Framework基于一个简单而强大的概念：**一切皆事件，一切皆响应**。

任何来自QQ的通知（私聊消息、群成员变动、好友申请等）都被视为一个**事件**。机器人的工作就是对这些事件做出**响应**——回复消息、执行管理操作、保存数据等。

插件开发者需要做的是实现**事件处理函数**，这些函数接收事件信息作为**输入参数**，返回响应动作作为**返回值**。

Askr Framework关注函数的三个要素：
- **声明**：声明函数能处理哪些事件类型
- **入参**：函数需要哪些事件信息
- **返回值**：函数要执行什么响应动作

## 核心概念

### 事件类别和声明

QQ机器人会收到各种各样的事件：私聊消息、群聊消息、戳一戳、好友申请等。不同的事件有不同的特征，需要不同的处理方式。

插件需要声明每个事件处理函数能够处理的事件，这样处理函数就能假设事件有一定特征。例如私聊消息事件（`MESSAGE_PRIVATE`）一定包含"消息内容"和"发送者QQ号"两条信息，但是好友申请事件则不一定包含消息内容。

Askr Framework将在收到QQ事件后对其进行分类，然后投递至那些**声明**能够处理该类型事件的处理函数。通过事件分类机制，我们避免处理函数遇到预料之外的事件，同时减少了对插件的不必要调用。

**注意**：单个插件中一个事件类型只能有一个处理函数。

#### MANIFEST声明方式

想要撰写声明，需要在插件中定义一个全局变量`MANIFEST`。全局变量指的是在函数之外被定义的变量，通常写在插件的第一行或最后一行。

`MANIFEST`是字典类型的变量。字典的键（key）需要是一个代表了事件类别的字符串，字典的值（value）需要是一个字符串，内容是处理函数的函数名称。

**基本格式**：
```python
MANIFEST = {
    "事件类型": "处理函数名"
}
```

**示例**：
```python
MANIFEST = {"MESSAGE_PRIVATE": "my_handler"}
```

上面的声明将"my_handler"函数声明为处理私聊消息事件（`MESSAGE_PRIVATE`）的函数。

**多事件处理**：
```python
MANIFEST = {
    "MESSAGE_PRIVATE": "handle_private_message",
    "MESSAGE_GROUP": "handle_group_message",
    "NOTICE_POKE": "handle_poke"
}
```

### 入参类型

符合直觉地，处理函数需要以事件的相关信息作为入参。Askr Framework提供三个可选的入参：`simpleEvent`（简化事件）、`rawEvent`（完整事件）、和`botContext`（情景函数）。函数可以从三者中任意选择需要的参数。

#### simpleEvent（简化事件）

只包含最常用信息的简化数据结构，**仅消息事件可用**。适合新手开发者快速上手。

```python
def simple_handler(simpleEvent):
    # 对于私聊消息：
    # simpleEvent = {
    #     "user_id": 12345678,        # 发送者QQ号
    #     "text_message": "你好"       # 消息文本内容
    # }
```

#### rawEvent（完整事件）

包含完整的OneBot 11格式事件数据，提供所有可用信息。当需要详细信息或处理非消息事件时使用。

```python
def raw_handler(rawEvent):
    # 包含完整的事件信息，格式根据事件类型而定
    # 具体格式参见OneBot 11文档
```

#### botContext（情景函数）

框架提供的工具函数集合，包含配置管理、历史查询、API调用等功能。

```python
def context_handler(botContext):
    config = botContext["ConfigReader"]()
    # 使用其他工具函数...
```

**参数组合使用**：
```python
def full_handler(simpleEvent, rawEvent, botContext):
    # 可以同时使用多种参数类型
```

### 返回值类型

函数通过返回值告知Askr Framework应当做出怎样的行动，无论是回复消息、执行API调用，还是进行复合操作。

Askr Framework接收四种返回值：字符串、字典、列表和空（None）。

#### 字符串返回值

返回字符串意味着在当前对话窗口发送文本消息。框架会自动根据事件上下文确定发送目标（私聊或群聊）。

```python
def hello_handler():
    return "你好！"  # 自动回复到原对话
```

#### 字典返回值

用于调用OneBot 11 API，实现复杂的QQ功能。

```python
def api_handler():
    return {
        "action": "send_group_msg",
        "data": {
            "group_id": 123456,
            "message": [{"type": "text", "data": {"text": "Hello"}}]
        }
    }
```

#### 列表返回值

用于执行多个连续操作，列表中的每个元素可以是字符串或字典。

```python
def multi_handler():
    return [
        "这是第一条消息",
        {
            "action": "set_group_card",
            "data": {"group_id": 123456, "user_id": 789012, "card": "新群名片"}
        },
        "这是第二条消息"
    ]
```

#### None返回值

表示不执行任何动作。当不需要响应某个事件时使用。

```python
def silent_handler():
    return None  # 或者不写return语句
```

以上是Askr Framework的基础概念。通过这些简单而强大的机制，你可以轻松创建功能丰富的QQ机器人。接下来我们将通过七个渐进式教程，逐步掌握所有概念的实际应用。

---

## 教程目录

1. [复读机器人](#1-复读机器人) - 基础概念：MANIFEST声明、simpleEvent、字符串返回值
2. [戳一戳回应器](#2-戳一戳回应器) - rawEvent的使用场景
3. [群欢迎机器人](#3-群欢迎机器人) - 字典返回值和API调用
4. [群聊签到机器人](#4-群聊签到机器人) - botContext工具和配置管理
5. [配置检查机器人](#5-配置检查机器人) - INITIALIZER事件和插件初始化
6. [群管理机器人](#6-群管理机器人) - 列表返回值和复合操作
7. [天气推送机器人](#7-天气推送机器人) - UNCONDITIONAL事件和定时任务

---

## 1. 复读机器人

**学习目标**：掌握Askr Framework的基础概念

### 功能描述
制作一个简单的复读机器人，用户发送什么消息，机器人就回复什么消息。

### 代码实现

```python
MANIFEST = {"MESSAGE_PRIVATE": "echo_handler"}

def echo_handler(simpleEvent):
    return simpleEvent["text_message"]
```

### 代码解释

1. **MANIFEST声明**：声明`echo_handler`函数处理私聊消息事件（`MESSAGE_PRIVATE`）
2. **函数定义**：函数接收`simpleEvent`作为参数
3. **simpleEvent结构**：对于私聊消息，包含以下字段：
   ```python
   simpleEvent = {
       "user_id": 12345678,        # 发送者QQ号（整数）
       "text_message": "你好"       # 消息文本内容（字符串）
   }
   ```
4. **返回值处理**：返回字符串会自动发送到原对话窗口

### 扩展：群聊复读机器人

```python
import random

MANIFEST = {
    "MESSAGE_PRIVATE": "echo_handler",
    "MESSAGE_GROUP": "group_echo_handler"
}

def echo_handler(simpleEvent):
    return simpleEvent["text_message"]

def group_echo_handler(simpleEvent):
    # 10%概率回复，避免群聊刷屏
    if random.randint(0, 9) == 0:
        return simpleEvent["text_message"]
    else:
        return None  # 不回复
```

### 小结

通过这个例子学到的概念：
- **MANIFEST声明**：事件类型与处理函数的映射
- **simpleEvent参数**：框架提供的简化事件数据
- **字符串返回值**：自动回复到原对话
- **return None**：告诉框架不执行任何动作
- **多事件处理**：一个插件可以处理多种事件类型

---

## 2. 戳一戳回应器

**学习目标**：理解何时需要使用rawEvent获取完整事件信息

### 功能描述
当有人戳机器人时，机器人会做出回应。需要区分是否戳的是机器人自己。

### 为什么需要rawEvent？

戳一戳事件不是消息事件，所以没有`simpleEvent`。同时我们需要知道：
- 谁戳了谁（`user_id`和`target_id`）
- 机器人自己的QQ号（`self_id`）

这些信息只有`rawEvent`才包含。

### rawEvent结构

戳一戳事件的rawEvent格式：
```python
rawEvent = {
    "post_type": "notice",
    "notice_type": "notify", 
    "sub_type": "poke",
    "group_id": 123456789,      # 群号（群聊中的戳一戳）
    "user_id": 987654321,       # 戳人的用户QQ号
    "target_id": 111222333,     # 被戳的用户QQ号
    "self_id": 111222333,       # 机器人QQ号
    "time": 1703123456          # 事件时间戳
}
```

### 代码实现

```python
MANIFEST = {"NOTICE_POKE": "poke_handler"}

def poke_handler(rawEvent):
    poker_id = rawEvent["user_id"]      # 戳人的用户
    target_id = rawEvent["target_id"]   # 被戳的用户
    bot_id = rawEvent["self_id"]        # 机器人QQ号
    
    # 判断是否戳的是机器人
    if target_id == bot_id:
        return "诶！你戳我干嘛 (╯‵□′)╯︵┻━┻"
    else:
        return None  # 不是戳机器人就不回应
```

### 小结

通过这个例子学到的概念：
- **何时使用rawEvent**：当需要simpleEvent没有的详细信息时
- **rawEvent特点**：包含完整的OneBot 11格式事件数据
- **事件类型多样性**：除消息事件外还有通知事件、请求事件等
- **文档查阅**：rawEvent具体内容需参考[OneBot 11文档](https://napneko.github.io/onebot/event)

---

## 3. 群欢迎机器人

**学习目标**：学会使用字典返回值调用复杂的QQ API

### 功能描述
当新成员加入群聊时，机器人发送欢迎消息并@新成员。

### 为什么需要字典返回值？

要@某个用户，需要使用OneBot 11的消息段格式，单纯的字符串无法实现。

### 字典返回值格式

```python
{
    "action": "API动作名",    # OneBot 11 API名称
    "data": {                # API参数
        # 具体参数根据API决定
    }
}
```

### 消息段格式

OneBot 11使用"消息段"表示复杂消息：
```python
{
    "type": "消息段类型",     # 如"text"、"at"、"image"等
    "data": {               # 消息段数据
        # 具体数据根据类型决定
    }
}
```

常用消息段：
- 文本：`{"type": "text", "data": {"text": "文本内容"}}`
- @用户：`{"type": "at", "data": {"qq": "用户QQ号"}}`

### 代码实现

```python
MANIFEST = {"NOTICE_GROUP_INCREASE": "welcome_handler"}

def welcome_handler(rawEvent):
    group_id = rawEvent["group_id"]
    new_member_id = rawEvent["user_id"]
    
    return {
        "action": "send_group_msg",
        "data": {
            "group_id": group_id,
            "message": [
                {"type": "text", "data": {"text": "欢迎新成员 "}},
                {"type": "at", "data": {"qq": str(new_member_id)}},
                {"type": "text", "data": {"text": " 加入群聊！"}}
            ]
        }
    }
```

### 代码解释

1. **事件监听**：`NOTICE_GROUP_INCREASE`监听群成员增加事件
2. **数据提取**：从rawEvent提取群号和新成员QQ号
3. **API调用**：使用`send_group_msg` API发送群消息
4. **消息构造**：
   - 第一段：文本"欢迎新成员 "
   - 第二段：@新成员（QQ号需转为字符串）
   - 第三段：文本" 加入群聊！"

### 小结

通过这个例子学到的概念：
- **字典返回值格式**：`action`和`data`字段的作用
- **OneBot 11 API调用**：通过返回值调用QQ功能
- **消息段系统**：构造包含@、图片等复杂消息的方法
- **数据类型要求**：某些API字段需要特定数据类型

---

## 4. 群聊签到机器人

**学习目标**：学会使用botContext工具进行数据持久化

### 功能描述
支持群聊签到功能，包含以下指令：
- `/签到` - 每日签到获得积分
- `/查看我的积分` - 显示个人签到信息
- `/查看群内排名` - 显示群内积分排行榜

### botContext工具介绍

`botContext`包含四个工具函数：
- **ConfigReader()**：读取插件配置
- **ConfigWriter(config)**：保存插件配置
- **Librarian(eventIdentifier, eventCount)**：查询历史事件
- **ApiCaller(action, data)**：调用查询类API

### 配置数据结构设计

```python
config = {
    "群id": {
        "用户id": {
            "points": 100,
            "consecutive_days": 5,
            "last_checkin_date": "2024-01-15"
        }
    }
}
```

### 代码实现

```python
import datetime

MANIFEST = {"MESSAGE_GROUP_BOT": "command_handler"}

def command_handler(simpleEvent, rawEvent, botContext):
    message = simpleEvent["text_message"].strip()
    user_id = str(simpleEvent["user_id"])
    group_id = str(simpleEvent["group_id"])
    
    if message == "/签到":
        return handle_checkin(user_id, group_id, botContext)
    elif message == "/查看我的积分":
        return show_my_points(user_id, group_id, botContext)
    elif message == "/查看群内排名":
        return show_ranking(group_id, botContext)
    else:
        return None

def handle_checkin(user_id, group_id, botContext):
    config = botContext["ConfigReader"]()
    
    # 确保数据结构存在
    if group_id not in config:
        config[group_id] = {}
    if user_id not in config[group_id]:
        config[group_id][user_id] = {
            "points": 0,
            "consecutive_days": 0,
            "last_checkin_date": ""
        }
    
    user_data = config[group_id][user_id]
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # 检查是否今天已签到
    if user_data["last_checkin_date"] == today:
        return "你今天已经签到过了！"
    
    # 检查连续签到
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if user_data["last_checkin_date"] == yesterday:
        user_data["consecutive_days"] += 1
    else:
        user_data["consecutive_days"] = 1
    
    # 更新积分和日期
    earned_points = user_data["consecutive_days"]
    user_data["points"] += earned_points
    user_data["last_checkin_date"] = today
    
    # 保存配置
    botContext["ConfigWriter"](config)
    
    return f"签到成功！获得 {earned_points} 积分，当前积分：{user_data['points']}，连续签到：{user_data['consecutive_days']} 天"

def show_my_points(user_id, group_id, botContext):
    config = botContext["ConfigReader"]()
    
    if group_id not in config or user_id not in config[group_id]:
        return "你还没有签到记录哦，发送 /签到 开始签到吧！"
    
    user_data = config[group_id][user_id]
    return f"你的积分：{user_data['points']}，连续签到：{user_data['consecutive_days']} 天"

def show_ranking(group_id, botContext):
    config = botContext["ConfigReader"]()
    
    if group_id not in config or not config[group_id]:
        return "本群还没有人签到过哦！"
    
    # 按积分排序
    user_list = [(user_id, data["points"]) for user_id, data in config[group_id].items()]
    user_list.sort(key=lambda x: x[1], reverse=True)
    
    # 构造排名信息（显示前5名）
    ranking_text = "📊 群内签到排行榜（前5名）\n"
    for i, (user_id, points) in enumerate(user_list[:5]):
        ranking_text += f"{i+1}. {user_id}: {points} 积分\n"
    
    return ranking_text.strip()
```

### 小结

通过这个例子学到的概念：
- **botContext作用**：提供插件运行时需要的工具函数
- **ConfigReader/Writer**：实现数据的持久化存储
- **复杂数据结构管理**：多层嵌套配置的设计和维护
- **参数声明要求**：函数需要声明所需的参数类型

---

## 5. 配置检查机器人

**学习目标**：理解INITIALIZER事件的作用和重要性

### 功能描述
演示如何使用INITIALIZER事件确保插件拥有正确的初始配置，避免运行时错误。

### 为什么需要INITIALIZER？

**问题场景**：如果插件首次运行时配置为空，可能导致错误：
```python
def some_handler(botContext):
    config = botContext["ConfigReader"]()  # 可能返回 {}
    max_users = config["settings"]["max_users"]  # KeyError!
```

**解决方案**：使用INITIALIZER在启动时创建默认配置：
```python
def init_config(botContext):
    config = botContext["ConfigReader"]()
    if not config:
        default_config = {"settings": {"max_users": 1000}}
        botContext["ConfigWriter"](default_config)

def some_handler(botContext):
    config = botContext["ConfigReader"]()  # 确保有配置
    max_users = config["settings"]["max_users"]  # 安全访问
```

### INITIALIZER特点

- **执行时机**：框架启动时，处理任何事件之前
- **执行顺序**：所有插件的INITIALIZER串行执行
- **失败处理**：如果执行失败，插件会被完全移除
- **设计目标**：让事件处理函数基于假设运行，提高效率

### 代码实现

```python
MANIFEST = {
    "INITIALIZER": "init_config",
    "MESSAGE_PRIVATE": "message_handler"
}

def init_config(botContext):
    """
    插件初始化函数：检查和创建必要的配置
    """
    config = botContext["ConfigReader"]()
    
    # 检查是否需要初始化
    needs_init = False
    
    if "settings" not in config:
        needs_init = True
    elif "user_data" not in config:
        needs_init = True
    elif "version" not in config:
        needs_init = True
    
    if needs_init:
        # 创建默认配置
        default_config = {
            "settings": {
                "welcome_message": "欢迎使用配置检查机器人！",
                "max_users": 1000,
                "debug_mode": False
            },
            "user_data": {},
            "version": "1.0.0",
            "initialized_at": "2024-01-01"
        }
        
        botContext["ConfigWriter"](default_config)
        print("配置检查机器人：已创建默认配置")
    else:
        print("配置检查机器人：配置已存在，无需初始化")
    
    return None

def message_handler(simpleEvent, botContext):
    """
    由于INITIALIZER保证，可以安全地假设配置结构正确
    """
    user_id = str(simpleEvent["user_id"])
    message = simpleEvent["text_message"]
    
    # 安全地读取配置
    config = botContext["ConfigReader"]()
    
    if message == "/状态":
        user_count = len(config["user_data"])
        max_users = config["settings"]["max_users"]
        version = config["version"]
        
        return f"🤖 插件状态\n版本：{version}\n当前用户数：{user_count}/{max_users}\n初始化时间：{config['initialized_at']}"
    
    elif message == "/注册":
        if user_id in config["user_data"]:
            return "您已经注册过了！"
        
        user_count = len(config["user_data"])
        max_users = config["settings"]["max_users"]
        
        if user_count >= max_users:
            return f"抱歉，用户数量已达上限（{max_users}）"
        
        # 添加新用户
        config["user_data"][user_id] = {
            "register_time": "2024-01-01",
            "usage_count": 0
        }
        
        botContext["ConfigWriter"](config)
        
        welcome_message = config["settings"]["welcome_message"]
        return f"{welcome_message}\n您已成功注册！"
    
    elif message == "/我的信息":
        if user_id not in config["user_data"]:
            return "您还没有注册，请发送 /注册"
        
        user_info = config["user_data"][user_id]
        return f"📊 您的信息\n注册时间：{user_info['register_time']}\n使用次数：{user_info['usage_count']}"
    
    else:
        return "可用命令：/状态、/注册、/我的信息"
```

### INITIALIZER失败处理

如果INITIALIZER抛出异常，插件会被移除：

```python
def init_config(botContext):
    # 检查必要依赖
    try:
        import requests
    except ImportError:
        raise Exception("缺少requests库，请安装：pip install requests")
    
    # 检查API连接
    result = botContext["ApiCaller"]("get_login_info", {})
    if not result:
        raise Exception("无法连接到QQ服务，请检查NapCat状态")
    
    return None
```

### 小结

通过这个例子学到的概念：
- **INITIALIZER作用**：在插件启动时进行必要的初始化
- **配置验证和创建**：确保插件拥有正确的初始配置
- **假设驱动设计**：让事件处理函数基于假设运行
- **错误处理策略**：初始化失败导致插件移除

---

## 6. 群管理机器人

**学习目标**：学会使用列表返回值执行多个连续操作

### 功能描述
监控群聊消息，检测违禁词并自动处理：发送警告消息 + 禁言违规用户。

### 什么是列表返回值？

列表返回值允许在一个事件中执行多个操作：
```python
return [
    "这是一条警告消息",           # 字符串：发送文本
    {                          # 字典：调用API
        "action": "set_group_ban",
        "data": {...}
    }
]
```

### 代码实现

```python
MANIFEST = {"MESSAGE_GROUP": "check_violation"}

def check_violation(simpleEvent, rawEvent):
    message_content = simpleEvent["text_message"]
    user_id = rawEvent["user_id"] 
    group_id = rawEvent["group_id"]
    
    # 违禁词列表（实际使用时填入具体词汇）
    banned_words = []
    
    # 检查违禁词
    has_violation = False
    for word in banned_words:
        if word in message_content:
            has_violation = True
            break
    
    if has_violation:
        # 返回列表：警告消息 + 禁言操作
        return [
            "⚠️ 检测到违禁词，用户已被禁言1分钟！",
            {
                "action": "set_group_ban",
                "data": {
                    "group_id": group_id,
                    "user_id": user_id,
                    "duration": 60  # 禁言60秒
                }
            }
        ]
    else:
        return None
```

### 执行顺序

框架按列表顺序执行操作：
1. 发送警告消息："⚠️ 检测到违禁词，用户已被禁言1分钟！"
2. 调用`set_group_ban` API禁言用户

### 注意事项

- **类型限制**：列表中只能包含字符串和字典
- **执行顺序**：框架严格按列表顺序执行
- **权限要求**：机器人需要管理员权限才能禁言
- **错误隔离**：单个操作失败不影响其他操作

### 小结

通过这个例子学到的概念：
- **列表返回值用途**：在一个事件中执行多个连续操作
- **混合操作类型**：可以组合字符串和字典返回值
- **执行顺序保证**：框架按列表顺序依次执行
- **实际应用场景**：群管理、自动化处理等复杂业务逻辑

---

## 7. 天气推送机器人

**学习目标**：学会使用UNCONDITIONAL事件实现定时任务

### 功能描述
完整的天气推送服务：
- **用户订阅**：`/订阅 纬度40 经度116`、`/取消订阅`
- **自动推送**：每天8:00发送天气预报，每小时检查降雨提醒

### UNCONDITIONAL事件介绍

UNCONDITIONAL是框架人工制造的定时事件：
- **触发机制**：按设定间隔定期执行
- **独立于用户**：不依赖任何用户操作
- **声明格式**：`{"UNCONDITIONAL": ["函数名", 间隔分钟数]}`

### 间隔说明

- 间隔N表示在分钟数能被N整除时执行
- 例如间隔60：每小时执行（第0、60分钟）
- 例如间隔15：每15分钟执行（第0、15、30、45分钟）

### 配置数据结构

```python
config = {
    "12345678": {  # 用户QQ号
        "latitude": 40.0,
        "longitude": 116.0
    }
}
```

### 代码实现

```python
import datetime
import requests

MANIFEST = {
    "MESSAGE_PRIVATE": "subscription_handler",
    "UNCONDITIONAL": ["weather_task", 1]  # 每分钟检查
}

def subscription_handler(simpleEvent, botContext):
    message = simpleEvent["text_message"].strip()
    user_id = str(simpleEvent["user_id"])
    
    if message.startswith("/订阅"):
        return handle_subscribe(message, user_id, botContext)
    elif message == "/取消订阅":
        return handle_unsubscribe(user_id, botContext)
    else:
        return None

def handle_subscribe(message, user_id, botContext):
    # 解析命令：/订阅 纬度40 经度116
    parts = message.split()
    if len(parts) != 3:
        return "格式错误！请使用：/订阅 纬度40 经度116"
    
    try:
        lat_part = parts[1]  # "纬度40"
        lon_part = parts[2]  # "经度116"
        
        if not lat_part.startswith("纬度") or not lon_part.startswith("经度"):
            return "格式错误！请使用：/订阅 纬度40 经度116"
        
        latitude = float(lat_part[2:])   # 去掉"纬度"
        longitude = float(lon_part[2:])  # 去掉"经度"
        
        # 验证坐标范围
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return "坐标超出范围！纬度应在-90到90之间，经度应在-180到180之间"
        
        # 保存订阅
        config = botContext["ConfigReader"]()
        config[user_id] = {
            "latitude": latitude,
            "longitude": longitude
        }
        botContext["ConfigWriter"](config)
        
        return f"订阅成功！已为您订阅纬度{latitude}，经度{longitude}的天气推送"
        
    except ValueError:
        return "坐标格式错误！请确保纬度和经度是有效数字"

def handle_unsubscribe(user_id, botContext):
    config = botContext["ConfigReader"]()
    
    if user_id in config:
        del config[user_id]
        botContext["ConfigWriter"](config)
        return "已取消天气订阅"
    else:
        return "您还没有订阅天气推送"

def weather_task(rawEvent, botContext):
    # 获取当前时间
    current_time = datetime.datetime.fromtimestamp(rawEvent["time"])
    
    if current_time.hour == 8 and current_time.minute == 0:
        # 每天8点：发送日常天气预报
        return send_daily_weather(botContext)
    elif current_time.minute == 0:
        # 每小时整点：检查降雨提醒
        return check_rain_alert(botContext)
    else:
        return None

def send_daily_weather(botContext):
    config = botContext["ConfigReader"]()
    
    if not config:
        return None
    
    messages = []
    
    for user_id, location in config.items():
        latitude = location["latitude"]
        longitude = location["longitude"]
        
        weather_info = get_daily_weather(latitude, longitude)
        
        if weather_info:
            messages.append({
                "action": "send_private_msg",
                "data": {
                    "user_id": int(user_id),
                    "message": [{"type": "text", "data": {"text": f"🌤️ 今日天气预报\n{weather_info}"}}]
                }
            })
    
    return messages if messages else None

def check_rain_alert(botContext):
    config = botContext["ConfigReader"]()
    
    if not config:
        return None
    
    messages = []
    
    for user_id, location in config.items():
        latitude = location["latitude"]
        longitude = location["longitude"]
        
        rain_probability = get_rain_probability(latitude, longitude)
        
        if rain_probability and rain_probability > 50:
            messages.append({
                "action": "send_private_msg",
                "data": {
                    "user_id": int(user_id),
                    "message": [{"type": "text", "data": {"text": f"🌧️ 降雨提醒\n下小时降雨概率：{rain_probability}%，请注意携带雨具！"}}]
                }
            })
    
    return messages if messages else None

def get_daily_weather(latitude, longitude):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # 获取今天的天气数据
            weather_code = data["daily"]["weather_code"][0]
            max_temp = data["daily"]["temperature_2m_max"][0]
            min_temp = data["daily"]["temperature_2m_min"][0]
            
            weather_desc = get_weather_description(weather_code)
            
            return f"天气：{weather_desc}\n最高温度：{max_temp}°C\n最低温度：{min_temp}°C"
        
    except Exception:
        return None

def get_rain_probability(latitude, longitude):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=precipitation_probability&forecast_hours=2&timezone=auto"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # 获取下小时的降雨概率
            if len(data["hourly"]["precipitation_probability"]) >= 2:
                return data["hourly"]["precipitation_probability"][1]
        
    except Exception:
        return None

def get_weather_description(weather_code):
    code_map = {
        0: "晴朗", 1: "基本晴朗", 2: "部分多云", 3: "阴天",
        45: "有雾", 48: "雾凇", 51: "小雨", 53: "中雨", 55: "大雨",
        61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪",
        80: "阵雨", 81: "中等阵雨", 82: "强阵雨", 95: "雷暴"
    }
    
    return code_map.get(weather_code, "未知天气")
```

### UNCONDITIONAL事件的rawEvent

```python
rawEvent = {
    "post_type": "unconditional",
    "time": 1703123456  # Unix时间戳
}
```

通过`datetime.datetime.fromtimestamp(rawEvent["time"])`获取当前调度时间。

### 小结

通过这个例子学到的概念：
- **UNCONDITIONAL事件作用**：实现定时任务和主动推送
- **多事件处理**：一个插件同时处理多种事件类型
- **时间条件判断**：基于时间执行不同业务逻辑
- **外部API集成**：调用真实第三方服务获取数据
- **列表返回值实际应用**：批量发送消息给多个用户

---

## 总结

通过这七个渐进式教程，我们完整学习了Askr Framework的所有核心概念：

### 学习路径回顾

1. **复读机器人** - 掌握基础的MANIFEST声明、simpleEvent参数和字符串返回值
2. **戳一戳回应器** - 学会使用rawEvent获取完整事件信息
3. **群欢迎机器人** - 掌握字典返回值和OneBot 11 API调用
4. **群聊签到机器人** - 学会使用botContext工具进行配置管理
5. **配置检查机器人** - 理解INITIALIZER事件的重要作用
6. **群管理机器人** - 掌握列表返回值实现多操作组合
7. **天气推送机器人** - 学会UNCONDITIONAL事件实现定时任务

### 核心技能掌握

- **事件系统**：理解不同事件类型的特点和使用场景
- **数据管理**：掌握配置读写、历史查询等数据操作
- **API调用**：学会通过返回值调用各种QQ功能
- **错误处理**：了解如何编写稳定可靠的插件代码
- **实际应用**：具备开发实用QQ机器人的完整技能

现在你已经掌握了使用Askr Framework开发QQ机器人的所有必要技能！可以开始创造属于自己的智能助手了。

更多详细的API参考和高级功能，请查阅[API参考文档](api_reference.md)和[技术指南](technical_guide.md)。