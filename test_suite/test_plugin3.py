#!/usr/bin/env python3
"""
测试插件3：初始化失败测试
INITIALIZER函数故意抛出异常，验证插件移除机制
"""

MANIFEST = {
    "INITIALIZER": "init_failure",
    "MESSAGE_PRIVATE": "handle_message"
}

def init_failure(botContext):
    """
    故意失败的初始化函数
    """
    raise Exception("插件3初始化故意失败 - 测试插件移除机制")

def handle_message(simpleEvent):
    """
    这个函数不应该被调用，因为插件会在初始化阶段被移除
    """
    return "[插件3] 这条消息不应该发送 - 插件应该已被移除"