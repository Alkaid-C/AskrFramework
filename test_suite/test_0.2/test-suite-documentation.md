# Askr Framework 测试套件文档

## 目录

1. [测试套件架构概述](#测试套件架构概述)
2. [核心组件说明](#核心组件说明)
3. [测试配置文件格式](#测试配置文件格式)
4. [编写新测试的步骤](#编写新测试的步骤)
5. [常见测试场景示例](#常见测试场景示例)
6. [调试和故障排除](#调试和故障排除)

---

## 测试套件架构概述

### 设计理念

测试套件采用**黑盒测试**方法，模拟真实的 NapCat 环境来测试 Askr Framework 的行为。整个测试流程完全自动化，通过比对预期响应和实际响应来验证框架功能。

### 工作流程

```
1. Test Runner 读取测试配置
   ↓
2. 清理环境，复制测试文件
   ↓
3. 启动 Mock NapCat Server (端口 29218)
   ↓
4. 启动 Askr Framework (端口 19219)
   ↓
5. 启动 Event Sender 发送测试事件
   ↓
6. Askr Framework 处理事件，调用插件
   ↓
7. 插件返回响应，框架调用 NapCat API
   ↓
8. Mock Server 记录所有 API 调用
   ↓
9. 测试完成，生成对比报告
```

### 组件职责

- **Test Runner** (`test_runner.py`)：测试流程控制器
- **Mock NapCat Server** (`mock_napcat_server.py`)：模拟 QQ 客户端 API
- **Event Sender** (`event_sender.py`)：模拟用户发送各种事件
- **Test Suite JSON**：定义测试用例的配置文件

---

## 核心组件说明

### Test Runner

主测试程序，负责：
- 读取测试配置
- 管理测试环境（清理、准备文件）
- 启动和停止各个进程
- 控制测试流程

### Mock NapCat Server

模拟 NapCat HTTP API 服务器：
- 监听端口 29218
- 接收并记录所有 API 调用
- 返回标准 OneBot 11 响应
- 生成测试报告

### Event Sender

事件发送器：
- 读取 `events_to_send` 配置
- 按顺序向 Askr Framework 发送事件
- 支持自定义延迟
- 模拟各种 QQ 事件

---

## 测试配置文件格式

### 基本结构

```json
[
  {
    "testname": "测试名称",
    "plugins": ["插件文件列表"],
    "configs": ["配置文件列表"],
    "extra_wait_seconds": 等待时间,
    "events_to_send": [...],
    "expected_responses": [...]
  }
]
```

### 字段说明

#### testname
- **类型**：字符串
- **说明**：测试的唯一标识符，用于生成报告文件名
- **示例**：`"basic_echo_test"`

#### plugins
- **类型**：字符串数组
- **说明**：需要复制到 `plugins/` 目录的插件文件名
- **示例**：`["echo_plugin.py", "admin_plugin.py"]`

#### configs
- **类型**：字符串数组
- **说明**：需要复制的配置文件名
- **规则**：
  - `config_*` 开头的文件会被重命名为 `frameworkConfig.json`
  - `plugin_access_*` 开头的文件会被重命名为 `PluginsAccessControl.json`
  - 其他文件保持原名
- **示例**：`["config_test1", "plugin_access_whitelist"]`

#### extra_wait_seconds
- **类型**：整数
- **说明**：发送完所有事件后的额外等待时间（秒）
- **用途**：
  - 等待异步处理完成
  - 等待 UNCONDITIONAL 事件触发（需要 65+ 秒）
- **示例**：`5` 或 `65`

#### events_to_send
- **类型**：对象数组
- **说明**：要发送的事件列表
- **格式**：
  ```json
  {
    "delay": 1000,  // 发送前延迟（毫秒）
    "event": {      // OneBot 11 标准事件格式
      "post_type": "message",
      "message_type": "private",
      // ... 其他字段
    }
  }
  ```

#### expected_responses
- **类型**：对象数组
- **说明**：预期的 API 调用列表
- **格式**：
  ```json
  {
    "action": "send_private_msg",  // API 动作名
    "data": {                      // API 参数
      "user_id": 12345,
      "message": [...]
    }
  }
  ```
- **匹配规则**：完全匹配（深度比较所有字段）

---

## 编写新测试的步骤

### 步骤 1：确定测试目标

明确要测试的功能：
- 事件分发机制？
- 返回值处理？
- botContext 工具？
- 访问控制？
- 资源限制？

### 步骤 2：编写测试插件

在 `AllTestFiles/plugins/` 目录创建插件文件：

```python
# plugin_example.py
MANIFEST = {
    "MESSAGE_PRIVATE": "handle_message"
}

def handle_message(simpleEvent):
    # 根据消息内容执行不同测试
    text = simpleEvent["text_message"]
    
    if text == "TEST_CASE_1":
        return "Response for test case 1"
    elif text == "TEST_CASE_2":
        return {
            "action": "send_group_msg",
            "data": {
                "group_id": 123456,
                "message": [{"type": "text", "data": {"text": "Test 2"}}]
            }
        }
    
    return None
```

### 步骤 3：准备配置文件

在 `AllTestFiles/Configs/` 目录创建配置文件：

```json
// config_example
{
  "version": "1.0",
  "NAPCAT_SERVER": {
    "api_url": "http://localhost:29218"
  },
  "NAPCAT_LISTEN": {
    "port": 19219
  }
}
```

### 步骤 4：设计测试事件

根据 OneBot 11 标准构造事件：

```json
{
  "delay": 1000,
  "event": {
    "post_type": "message",
    "message_type": "private",
    "user_id": 12345678,
    "message": [
      {"type": "text", "data": {"text": "TEST_CASE_1"}}
    ],
    "raw_message": "TEST_CASE_1",
    "time": 1700000001,
    "self_id": 88888888,
    "sender": {
      "user_id": 12345678,
      "nickname": "TestUser"
    }
  }
}
```

### 步骤 5：定义预期响应

根据插件行为定义预期的 API 调用：

```json
{
  "action": "send_private_msg",
  "data": {
    "user_id": 12345678,
    "message": [
      {"type": "text", "data": {"text": "Response for test case 1"}}
    ]
  }
}
```

### 步骤 6：组装测试配置

将以上内容整合到测试配置中：

```json
{
  "testname": "my_new_test",
  "plugins": ["plugin_example.py"],
  "configs": ["config_example"],
  "extra_wait_seconds": 5,
  "events_to_send": [...],
  "expected_responses": [...]
}
```

---

## 常见测试场景示例

### 场景 1：测试事件继承机制

测试 MESSAGE_GROUP_MENTION 同时触发 MESSAGE_GROUP：

```json
{
  "events_to_send": [{
    "event": {
      "post_type": "message",
      "message_type": "group",
      "message": [
        {"type": "at", "data": {"qq": "88888888"}},
        {"type": "text", "data": {"text": " hello"}}
      ]
    }
  }],
  "expected_responses": [
    // 预期两个插件都响应
    {"action": "...", "data": {...}},  // MESSAGE_GROUP_MENTION 插件
    {"action": "...", "data": {...}}   // MESSAGE_GROUP 插件
  ]
}
```

### 场景 2：测试访问控制

配置白名单/黑名单：

```json
// plugin_access_whitelist
{
  "version": "1.0",
  "default_policy": "deny",
  "rules": {
    "test_plugin.py": {
      "private": {
        "WhiteList": [12345678]  // 只允许这个 QQ
      }
    }
  }
}
```

### 场景 3：测试 UNCONDITIONAL 事件

```json
{
  "extra_wait_seconds": 65,  // 等待超过 1 分钟
  "events_to_send": [
    // 可以发送一个普通事件触发插件加载
    {"event": {"post_type": "message", ...}}
  ],
  "expected_responses": [
    // UNCONDITIONAL 插件的输出
    {"action": "send_private_msg", ...}
  ]
}
```

### 场景 4：测试 botContext 工具

```python
def test_handler(simpleEvent, botContext):
    cmd = simpleEvent["text_message"]
    
    if cmd == "TEST_HISTORY":
        # 测试 Librarian
        history = botContext["Librarian"](
            {"type": "private", "user_id": 12345},
            eventCount=5
        )
        return f"Found {len(history)} messages"
    
    elif cmd == "TEST_CONFIG":
        # 测试配置读写
        botContext["ConfigWriter"]({"key": "value"})
        config = botContext["ConfigReader"]()
        return f"Config: {config}"
```

### 场景 5：测试资源限制

```python
def memory_limit_test(simpleEvent):
    if simpleEvent["text_message"] == "TRIGGER_MEMORY_LIMIT":
        # 分配大量内存触发限制
        big_list = [0] * (1024 * 1024 * 1024)  # 1GB
        return "Should not reach here"
```

预期结果：
- 插件被终止
- 没有响应消息
- 管理员收到通知

### 场景 6：测试列表返回值

```python
def list_return_test():
    return [
        "First message",
        {"action": "send_group_msg", "data": {...}},
        123,  # 错误元素，会被忽略
        "Second message"
    ]
```

预期结果：
- 发送两条文本消息
- 执行一个 API 调用
- 忽略整数元素

---

## 调试和故障排除

### 查看测试报告

每个测试生成 `test_result_<testname>.txt`：

```
测试报告: basic_echo_test
生成时间: 2024-01-01 12:00:00
============================================================

统计信息:
  预期响应数: 5
  实际收到数: 4
  匹配成功数: 4

应该收到但没收到的响应 (1 个):
----------------------------------------
1. {
  "action": "send_private_msg",
  "data": {
    "user_id": 99999,
    "message": [{"type": "text", "data": {"text": "Missing"}}]
  }
}

不应该收到但收到了的响应 (0 个):
----------------------------------------
无

测试结果: 失败 ✗
```

### 常见问题

#### 1. Mock Server 启动失败
- 检查端口 29218 是否被占用
- 确认 Flask 已安装

#### 2. Askr Framework 启动失败
- 检查端口 19219 是否被占用
- 确认配置文件格式正确
- 查看框架日志

#### 3. 事件未被处理
- 检查插件是否正确注册事件
- 验证事件格式符合 OneBot 11 标准
- 检查访问控制配置

#### 4. 响应不匹配
- 使用完全相同的字段顺序
- 确保数据类型正确（如 user_id 应为整数）
- 检查消息段格式

### 调试技巧

1. **单独运行组件**：
   ```bash
   # 单独测试 Mock Server
   python mock_napcat_server.py --port 29218 --testname test1 --test-json test.json
   
   # 单独测试 Event Sender
   python event_sender.py --port 19219 --testname test1 --test-json test.json
   ```

2. **添加调试输出**：
   在插件中添加日志或返回调试信息

3. **简化测试用例**：
   从最简单的单个事件开始，逐步增加复杂度

4. **检查进程输出**：
   Test Runner 会显示各组件的启动状态

---

## 最佳实践

1. **测试命名**：使用描述性名称，如 `access_control_whitelist_test`

2. **插件设计**：
   - 使用消息内容作为测试分支条件
   - 每个测试用例返回可识别的响应
   - 避免依赖外部状态

3. **事件设计**：
   - 使用有意义的 user_id 和 group_id
   - 包含必要的 self_id 字段
   - 时间戳可以是任意值

4. **等待时间**：
   - 普通测试 5-10 秒足够
   - UNCONDITIONAL 测试需要 65+ 秒
   - 复杂异步操作可能需要更长

5. **模块化**：
   - 每个测试专注于一个功能点
   - 复用通用的配置文件
   - 保持测试相互独立

---

通过遵循这个文档，你应该能够轻松创建新的测试用例来验证 Askr Framework 的各种功能。