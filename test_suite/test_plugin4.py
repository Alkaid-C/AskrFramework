#!/usr/bin/env python3
"""
测试插件4：UNCONDITIONAL事件测试
验证定时任务机制，每2分钟自动执行一次
"""

import datetime

MANIFEST = {
    "UNCONDITIONAL": ["scheduled_task", 2]  # 每2分钟执行
}

def scheduled_task(rawEvent):
    """
    定时任务函数，每2分钟自动执行
    """
    # 获取当前调度时间
    current_time = datetime.datetime.fromtimestamp(rawEvent["time"])
    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "action": "send_private_msg",
        "data": {
            "user_id": 999999999,  # 测试用户ID
            "message": [{"type": "text", "data": {"text": f"[插件4] 定时任务执行 - 时间: {time_str}"}}]
        }
    }