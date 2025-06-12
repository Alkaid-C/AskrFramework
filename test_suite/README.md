# Askr Framework 自动化测试使用说明

## 文件结构

确保你的项目目录包含以下文件：

```
askr_project/
├── askr_framework.py           # 主框架文件
├── plugins/                    # 插件目录
│   ├── test_all_events.py      # 测试插件1 - 全事件类型测试
│   ├── test_comprehensive.py   # 测试插件2 - 综合功能测试
│   ├── test_init_failure.py    # 测试插件3 - 初始化失败测试
│   └── test_unconditional.py   # 测试插件4 - 定时任务测试
├── fake_napcat.py              # 伪NapCat服务器
└── run_tests.py                # 主测试脚本
```

## 运行测试

### 方法1：直接运行完整测试套件

```bash
python run_tests.py
```

这将自动执行所有测试，包括：
- 环境设置（30秒）
- 事件分发测试（60秒）
- 综合功能测试（120秒）
- 崩溃场景测试（180秒，每个崩溃测试等待45秒）
- 定时任务测试（140秒）

### 方法2：手动启动组件（调试用）

如果需要调试，可以手动分步骤运行：

1. **启动伪NapCat服务器：**
```python
from fake_napcat import FakeNapCat, TestEventGenerator

config = {
    "listen_host": "localhost",
    "listen_port": 19217,
    "framework_url": "http://localhost:19218",
    "bot_qq": 123456789,
    "admin_qq": 999999999,
    "test_user_qq": 111111111,
    "test_group_id": 222222222
}

fake_napcat = FakeNapCat(config)
fake_napcat.start_server()
```

2. **修改框架配置：**
确保 `askr_framework.py` 中的 CONFIG 设置正确：
```python
CONFIG = {
    'NAPCAT_SERVER': {
        'api_url': 'http://localhost:19217',  # 对应伪服务器端口
    },
    'NAPCAT_LISTEN': {
        'host': '0.0.0.0',
        'port': 19218
    },
    'ADMIN_NOTIFICATION': {
        'enabled': True,
        'admin_qq': 999999999,  # 与测试配置一致
        'notify_level': 'ERROR',
    }
}
```

3. **启动框架：**
```bash
python askr_framework.py
```

## 测试内容说明

### 插件1：全事件类型测试
- 为每个OneBot 11事件类型注册单独的处理函数
- 验证事件分类和分发机制
- 测试事件继承关系（MESSAGE_GROUP_MENTION 同时触发 MESSAGE_GROUP）
- **测试的完整事件列表**：
  - **消息事件**：私聊消息、群聊消息、群聊@消息、群聊指令消息
  - **好友通知**：好友添加、好友消息撤回
  - **群聊通知**：群消息撤回、群成员增减、群管理变动、群禁言、群文件上传、群名片变更、群名变更、群头衔变更、精华消息、群消息表情回应
  - **其他通知**：戳一戳、个人资料点赞、输入状态、机器人离线
  - **请求事件**：好友请求、群请求

### 插件2：综合功能测试
包含多个测试分支，通过不同的私聊消息触发：

**正常功能测试：**
- `/test_simple` - simpleEvent 参数测试
- `/test_str` - 字符串返回值测试
- `/test_dict` - 字典返回值测试
- `/test_list` - 列表返回值测试
- `/test_config_write` - 配置写入测试
- `/test_config_read` - 配置读取测试
- `/test_librarian` - 历史记录查询测试
- `/test_apicaller` - API调用测试

**异常处理测试：**
- `/test_invalid` - 非法返回值（应触发管理员通知）
- `/test_exception` - 异常处理（应触发管理员通知）
- `/test_cpu` - CPU时间限制测试（质数计算，应触发管理员通知）
- `/test_sleep` - 墙钟时间限制测试（60秒睡眠，应触发管理员通知）
- `/test_memory` - 内存限制测试（大量内存分配，应触发管理员通知）

### 插件3：初始化失败测试
- INITIALIZER函数故意抛出异常
- 验证插件移除机制是否正确工作
- 发送消息后不应收到来自此插件的任何响应

### 插件4：定时任务测试
- 每2分钟自动执行一次（需手动启用）
- 通过私聊消息控制定时任务状态：
  - `/定时测试开始` - 启用定时任务
  - `/定时测试停止` - 禁用定时任务
- 验证UNCONDITIONAL事件机制
- 默认禁用状态，避免干扰其他测试

## 预期结果

### 成功的测试应该看到：

1. **环境启动：**
   - 伪NapCat服务器成功启动
   - Askr框架成功启动
   - 插件1、2、4加载成功
   - 插件3因初始化失败被移除

2. **事件分发：**
   - 每个事件都能收到预期数量的响应
   - MESSAGE_GROUP_MENTION 和 MESSAGE_GROUP_BOT 收到2个响应（继承关系）

3. **功能测试：**
   - 所有 `/test_*` 命令都收到预期响应
   - 配置读写工作正常
   - 历史记录查询返回数据
   - API调用返回测试数据

4. **崩溃处理：**
   - 崩溃命令仍收到插件1的响应，但不收到插件2的成功响应
   - 管理员QQ收到错误通知
   - 系统继续正常运行

5. **定时任务：**
   - 启用定时任务后在2分钟内收到执行消息
   - 测试结束后自动停用定时任务

### 测试报告

测试完成后会生成详细的JSON报告，包括：
- 测试概要（通过率、响应时间等）
- 性能指标（平均/最大响应时间、API调用统计）
- 每个测试的详细结果

## 故障排除

### 常见问题：

1. **端口冲突：**
   - 确保19217和19218端口未被占用
   - 可以修改配置中的端口号

2. **框架启动失败：**
   - 检查依赖是否安装完整
   - 查看错误输出确定具体问题

3. **插件加载失败：**
   - 确保plugins目录存在且包含所有测试插件
   - 检查插件语法是否正确

4. **测试超时：**
   - 某些测试（如定时任务）需要较长时间
   - 崩溃测试需要等待45秒
   - 可以适当调整超时时间

5. **管理员通知不工作：**
   - 确保框架配置中的admin_qq与测试配置一致
   - 检查通知功能是否启用
