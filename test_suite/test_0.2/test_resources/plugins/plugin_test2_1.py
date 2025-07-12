# plugin_test2_1.py - 测试botContext工具函数

MANIFEST = {
    "MESSAGE_PRIVATE": "handle_private_message"
}

def handle_private_message(simpleEvent, botContext):
    """根据不同的消息内容测试不同的botContext功能"""
    message = simpleEvent["text_message"]
    user_id = simpleEvent["user_id"]
    
    if message == "TEST_CONFIG_WRITE":
        # 测试ConfigWriter
        test_config = {
            "test_key": "test_value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {
                "inner_key": "inner_value"
            }
        }
        botContext["ConfigWriter"](test_config)
        return "ConfigWriter success: test_key=test_value"
    
    elif message == "TEST_CONFIG_READ":
        # 测试ConfigReader
        config = botContext["ConfigReader"]()
        if config and "test_key" in config:
            return f"ConfigReader result: test_key={config['test_key']}"
        else:
            return "ConfigReader error: no config found"
    
    elif message == "TEST_LIBRARIAN_COUNT":
        # 测试Librarian的条数查询
        # 查询最近10条私聊消息
        history = botContext["Librarian"](
            {"type": "private", "user_id": user_id},
            eventCount=10
        )
        count = len(history)
        return f"Librarian count: found {count} messages"
    
    elif message == "TEST_LIBRARIAN_TIME":
        # 测试Librarian的时间窗口查询
        # 查询最近3秒内的私聊消息
        history = botContext["Librarian"](
            {"type": "private", "user_id": user_id},
            interval=3
        )
        count = len(history)
        return f"Librarian time: found {count} messages in last 3 seconds"
    
    elif message == "TEST_LIST_CORRECT":
        # 测试正确的list返回值（string和dict混合）
        return [
            "First message from list",
            {
                "action": "send_private_msg",
                "data": {
                    "user_id": user_id,
                    "message": [{"type": "text", "data": {"text": "Second message from list"}}]
                }
            },
            {
                "action": "send_group_msg",
                "data": {
                    "group_id": 123456789,
                    "message": [{"type": "text", "data": {"text": "Third message from list"}}]
                }
            }
        ]
    
    elif message == "TEST_LIST_ERROR":
        # 测试错误的list返回值（包含非string/dict元素）
        # 框架应该忽略错误元素，只处理正确的元素
        return [
            "Valid string in error list",
            123,  # 错误：int类型
            None,  # 错误：None类型
            {
                "action": "send_group_msg",
                "data": {
                    "group_id": 123456789,
                    "message": [{"type": "text", "data": {"text": "Another valid message"}}]
                }
            },
            [1, 2, 3],  # 错误：嵌套list
            {"invalid": "dict"},  # 错误：缺少action和data字段
            True,  # 错误：bool类型
        ]
    
    else:
        # 其他消息不处理
        return None
