#!/usr/bin/env python3
"""
测试插件2：综合功能测试
测试simpleEvent、返回值类型、botContext工具、崩溃场景
"""

import time

MANIFEST = {"MESSAGE_PRIVATE": "comprehensive_handler"}

def comprehensive_handler(simpleEvent, rawEvent, botContext):
    message = simpleEvent["text_message"].strip()
    user_id = simpleEvent["user_id"]
    
    # 分支1：simpleEvent测试
    if message == "/test_simple":
        return f"[插件2] simpleEvent测试 - 用户ID: {user_id}, 消息: {message}"
    
    # 分支2：返回值类型测试
    elif message == "/test_str":
        return "[插件2] 字符串返回值测试"
    
    elif message == "/test_dict":
        return {
            "action": "send_private_msg",
            "data": {
                "user_id": user_id,
                "message": [{"type": "text", "data": {"text": "[插件2] 字典返回值测试"}}]
            }
        }
    
    elif message == "/test_list":
        return [
            "[插件2] 列表返回值测试 - 第1条",
            {
                "action": "send_private_msg", 
                "data": {
                    "user_id": user_id,
                    "message": [{"type": "text", "data": {"text": "[插件2] 列表返回值测试 - 第2条"}}]
                }
            }
        ]
    
    elif message == "/test_invalid":
        return 12345  # 非法返回值，应触发管理员通知
    
    # 分支3：botContext工具测试
    elif message == "/test_config_write":
        test_config = {"test_key": "test_value", "number": 42, "list": [1, 2, 3]}
        botContext["ConfigWriter"](test_config)
        return "[插件2] 配置写入测试完成"
    
    elif message == "/test_config_read":
        config = botContext["ConfigReader"]()
        expected = {"test_key": "test_value", "number": 42, "list": [1, 2, 3]}
        if config == expected:
            return "[插件2] 配置读取测试成功"
        else:
            return f"[插件2] 配置读取测试失败 - 期望: {expected}, 实际: {config}"
    
    elif message == "/test_librarian":
        history = botContext["Librarian"]({"type": "private", "user_id": user_id}, 5)
        return f"[插件2] 历史记录测试完成 - 查询到{len(history)}条记录"
    
    elif message == "/test_apicaller":
        result = botContext["ApiCaller"]("test_api", {"test_param": "test_value"})
        if result:
            return f"[插件2] API调用测试成功 - 返回: {result}"
        else:
            return "[插件2] API调用测试失败"
    
    # 分支4：崩溃场景测试
    elif message == "/test_exception":
        raise Exception("这是一个测试异常")
        return "[插件2] 异常测试 - 这条消息不应该发送"
    
    elif message == "/test_cpu":
        # CPU密集计算：计算大质数，应触发CPU时间限制
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0:
                    return False
            return True
        
        # 寻找大于100000的质数，这会消耗大量CPU时间
        num = 100000
        primes_found = 0
        while primes_found < 10000:  # 尝试找10000个质数，应该会超时
            if is_prime(num):
                primes_found += 1
            num += 1
        return f"[插件2] CPU测试完成 - 找到{primes_found}个质数"
    
    elif message == "/test_sleep":
        time.sleep(60)  # 睡眠60秒，应触发墙钟时间限制
        return "[插件2] 睡眠测试完成 - 这条消息不应该发送"
    
    elif message == "/test_memory":
        # 分配大量内存，应触发内存限制
        big_list = []
        for i in range(1000000):
            big_list.append([0] * 1000)  # 分配约4GB内存
        return f"[插件2] 内存测试完成 - 分配了{len(big_list)}个数组"
    
    else:
        return None  # 不处理其他消息