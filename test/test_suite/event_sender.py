#!/usr/bin/env python3
"""
Event Sender - 向 Askr Framework 发送测试事件
"""
import json
import argparse
import time
import requests
import sys
from datetime import datetime
from typing import List, Dict, Any

class EventSender:
    def __init__(self, port: int, testname: str, test_json_path: str):
        self.port = port
        self.testname = testname
        self.test_json_path = test_json_path
        self.base_url = f"http://localhost:{port}"
        
        # 加载要发送的事件
        self.events_to_send = self.load_events_to_send()
        
    def load_events_to_send(self) -> List[Dict]:
        """加载当前测试要发送的事件"""
        with open(self.test_json_path, 'r', encoding='utf-8') as f:
            test_suite = json.load(f)
        
        # 找到对应的测试
        for test in test_suite:
            if test['testname'] == self.testname:
                return test.get('events_to_send', [])
        
        return []
    
    def send_event(self, event_data: Dict) -> bool:
        """发送单个事件到 Askr Framework"""
        try:
            response = requests.post(
                f"{self.base_url}/",
                json=event_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"  警告: 收到非 200 响应 - {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"  错误: 请求超时")
            return False
        except requests.exceptions.ConnectionError:
            print(f"  错误: 无法连接到 Askr Framework")
            return False
        except Exception as e:
            print(f"  错误: {e}")
            return False
    
    def run(self):
        """执行发送流程"""
        print(f"Event Sender 开始工作")
        print(f"目标地址: {self.base_url}")
        print(f"测试名称: {self.testname}")
        print(f"事件数量: {len(self.events_to_send)}")
        print("-" * 40)
        
        if not self.events_to_send:
            print("没有要发送的事件")
            return
        
        # 按顺序发送事件
        for i, event_config in enumerate(self.events_to_send, 1):
            # 获取延迟时间（毫秒）
            delay_ms = event_config.get('delay', 1000)  # 默认1秒
            delay_seconds = delay_ms / 1000.0
            
            # 获取事件数据
            event_data = event_config.get('event', {})
            
            # 显示发送信息
            event_type = event_data.get('post_type', 'unknown')
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            print(f"\n[{timestamp}] 发送事件 {i}/{len(self.events_to_send)}")
            print(f"  类型: {event_type}")
            
            # 根据事件类型显示更多信息
            if event_type == 'message':
                message_type = event_data.get('message_type', '')
                raw_message = event_data.get('raw_message', '')
                print(f"  消息类型: {message_type}")
                print(f"  消息内容: {raw_message[:50]}..." if len(raw_message) > 50 else f"  消息内容: {raw_message}")
            elif event_type == 'notice':
                notice_type = event_data.get('notice_type', '')
                print(f"  通知类型: {notice_type}")
            elif event_type == 'request':
                request_type = event_data.get('request_type', '')
                print(f"  请求类型: {request_type}")
            
            # 延迟
            if delay_seconds > 0:
                print(f"  延迟: {delay_ms}ms")
                time.sleep(delay_seconds)
            
            # 发送事件
            print(f"  发送中...")
            success = self.send_event(event_data)
            
            if success:
                print(f"  ✓ 发送成功")
            else:
                print(f"  ✗ 发送失败")
        
        print("\n" + "-" * 40)
        print("所有事件发送完成")
        
        # 检查是否需要等待 UNCONDITIONAL 事件
        if any('unconditional' in str(event_config).lower() for event_config in self.events_to_send):
            print("\n注意：测试包含 UNCONDITIONAL 相关内容")
            print("请确保主程序设置了足够的 extra_wait_seconds")


def main():
    parser = argparse.ArgumentParser(description='Event Sender')
    parser.add_argument('--port', type=int, default=19219, help='Askr Framework 端口')
    parser.add_argument('--testname', required=True, help='测试名称')
    parser.add_argument('--test-json', required=True, help='测试配置文件路径')
    
    args = parser.parse_args()
    
    sender = EventSender(args.port, args.testname, args.test_json)
    
    try:
        sender.run()
    except KeyboardInterrupt:
        print("\n\n发送中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n发送器错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
