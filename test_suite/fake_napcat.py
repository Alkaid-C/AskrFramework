#!/usr/bin/env python3
"""
伪NapCat服务器
模拟NapCat的HTTP服务器，接收框架API调用并记录结果
同时提供HTTP客户端功能，向框架发送测试事件
"""

import json
import time
import threading
import requests
from flask import Flask, request, jsonify
from datetime import datetime

class FakeNapCat:
    def __init__(self, config):
        self.config = config
        self.app = Flask(__name__)
        self.api_call_log = []  # 记录所有API调用
        self.sent_events = []   # 记录发送的事件
        self.start_time = time.time()
        
        # 设置路由
        self.setup_routes()
        
    def setup_routes(self):
        """设置API路由"""
        
        @self.app.route('/send_private_msg', methods=['POST'])
        def handle_send_private_msg():
            data = request.get_json()
            self.log_api_call('send_private_msg', data)
            
            # 模拟成功响应
            return jsonify({
                "status": "ok",
                "retcode": 0,
                "data": {"message_id": int(time.time())}
            })
        
        @self.app.route('/send_group_msg', methods=['POST']) 
        def handle_send_group_msg():
            data = request.get_json()
            self.log_api_call('send_group_msg', data)
            
            return jsonify({
                "status": "ok", 
                "retcode": 0,
                "data": {"message_id": int(time.time())}
            })
        
        @self.app.route('/get_login_info', methods=['POST'])
        def handle_get_login_info():
            data = request.get_json()
            self.log_api_call('get_login_info', data)
            
            return jsonify({
                "status": "ok",
                "retcode": 0, 
                "data": {
                    "user_id": self.config["bot_qq"],
                    "nickname": "测试机器人"
                }
            })
        
        @self.app.route('/test_api', methods=['POST'])
        def handle_test_api():
            data = request.get_json()
            self.log_api_call('test_api', data)
            
            return jsonify({
                "status": "ok",
                "retcode": 0,
                "data": {
                    "test_response": "success",
                    "received_param": data.get("test_param", "")
                }
            })
        
        @self.app.route('/get_status', methods=['GET', 'POST'])
        def handle_get_status():
            # 框架在API失败时会查询状态
            return jsonify({
                "status": "ok",
                "retcode": 0,
                "data": {
                    "online": True,
                    "good": True
                }
            })
        
        # 其他可能用到的API
        @self.app.route('/<path:action>', methods=['POST'])
        def handle_other_api(action):
            data = request.get_json()
            self.log_api_call(action, data)
            
            # 通用成功响应
            return jsonify({
                "status": "ok",
                "retcode": 0,
                "data": {}
            })
    
    def log_api_call(self, action, data):
        """记录API调用"""
        call_record = {
            "timestamp": time.time(),
            "action": action,
            "data": data,
            "relative_time": time.time() - self.start_time
        }
        self.api_call_log.append(call_record)
        print(f"[API] {action}: {data}")
    
    def send_event(self, event_data, expect_response=True):
        """向框架发送事件"""
        try:
            response = requests.post(
                self.config["framework_url"],
                json=event_data,
                timeout=5
            )
            
            event_record = {
                "timestamp": time.time(),
                "event": event_data,
                "expect_response": expect_response,
                "relative_time": time.time() - self.start_time,
                "http_status": response.status_code
            }
            self.sent_events.append(event_record)
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"发送事件失败: {e}")
            return False
    
    def wait_for_responses(self, expected_count, timeout=5, filter_func=None, start_from_count=None):
        """等待指定数量的API调用响应"""
        start_time = time.time()
        
        # 如果没有指定起始数量，使用当前数量
        if start_from_count is None:
            initial_count = len(self.api_call_log)
        else:
            initial_count = start_from_count
        
        while time.time() - start_time < timeout:
            current_responses = self.api_call_log[initial_count:]
            
            if filter_func:
                filtered_responses = [r for r in current_responses if filter_func(r)]
            else:
                filtered_responses = current_responses
                
            if len(filtered_responses) >= expected_count:
                return filtered_responses[:expected_count]
            
            time.sleep(0.1)
        
        # 返回超时时的所有响应
        final_responses = self.api_call_log[initial_count:]
        if filter_func:
            return [r for r in final_responses if filter_func(r)]
        return final_responses
    
    def check_admin_notification(self, timeout=45):
        """检查是否收到管理员通知"""
        def is_admin_notification(call):
            return (call["action"] == "send_private_msg" and 
                   call["data"].get("user_id") == self.config["admin_qq"])
        
        # 从当前时间开始等待管理员通知
        initial_count = len(self.api_call_log)
        responses = self.wait_for_responses(1, timeout, is_admin_notification, initial_count)
        return len(responses) > 0
    
    def get_api_calls_summary(self):
        """获取API调用统计"""
        summary = {}
        for call in self.api_call_log:
            action = call["action"]
            summary[action] = summary.get(action, 0) + 1
        return summary
    
    def clear_logs(self):
        """清除日志记录"""
        self.api_call_log.clear()
        self.sent_events.clear()
        self.start_time = time.time()
    
    def start_server(self):
        """启动HTTP服务器"""
        def run_server():
            # 禁用Flask的日志输出
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            
            self.app.run(
                host=self.config["listen_host"],
                port=self.config["listen_port"],
                debug=False,
                use_reloader=False
            )
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(2)
        
        return server_thread

# 测试事件生成器
class TestEventGenerator:
    def __init__(self, config):
        self.config = config
    
    def generate_message_private(self, message="测试消息"):
        """生成私聊消息事件"""
        return {
            "post_type": "message",
            "message_type": "private", 
            "sub_type": "friend",
            "message_id": int(time.time()),
            "user_id": self.config["test_user_qq"],
            "message": [{"type": "text", "data": {"text": message}}],
            "raw_message": message,
            "font": 0,
            "sender": {
                "user_id": self.config["test_user_qq"],
                "nickname": "测试用户",
                "sex": "unknown",
                "age": 0
            },
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_message_group(self, message="测试群消息"):
        """生成群聊消息事件"""
        return {
            "post_type": "message",
            "message_type": "group",
            "sub_type": "normal",
            "message_id": int(time.time()),
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "anonymous": None,
            "message": [{"type": "text", "data": {"text": message}}],
            "raw_message": message,
            "font": 0,
            "sender": {
                "user_id": self.config["test_user_qq"],
                "nickname": "测试用户",
                "card": "",
                "sex": "unknown", 
                "age": 0,
                "area": "",
                "level": "1",
                "role": "member",
                "title": ""
            },
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_message_group_mention(self, message="@机器人 测试"):
        """生成群聊@消息事件"""
        return {
            "post_type": "message",
            "message_type": "group",
            "sub_type": "normal",
            "message_id": int(time.time()),
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "anonymous": None,
            "message": [
                {"type": "at", "data": {"qq": str(self.config["bot_qq"])}},
                {"type": "text", "data": {"text": f" {message}"}}
            ],
            "raw_message": f"[CQ:at,qq={self.config['bot_qq']}] {message}",
            "font": 0,
            "sender": {
                "user_id": self.config["test_user_qq"],
                "nickname": "测试用户",
                "card": "",
                "sex": "unknown",
                "age": 0,
                "area": "",
                "level": "1", 
                "role": "member",
                "title": ""
            },
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_message_group_bot(self, message="/测试指令"):
        """生成群聊指令消息事件"""
        return {
            "post_type": "message",
            "message_type": "group", 
            "sub_type": "normal",
            "message_id": int(time.time()),
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "anonymous": None,
            "message": [{"type": "text", "data": {"text": message}}],
            "raw_message": message,
            "font": 0,
            "sender": {
                "user_id": self.config["test_user_qq"],
                "nickname": "测试用户",
                "card": "",
                "sex": "unknown",
                "age": 0,
                "area": "",
                "level": "1",
                "role": "member", 
                "title": ""
            },
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_poke(self):
        """生成戳一戳事件"""
        return {
            "post_type": "notice",
            "notice_type": "notify",
            "sub_type": "poke",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "target_id": self.config["bot_qq"],
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_increase(self):
        """生成群成员增加事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_increase",
            "sub_type": "approve",
            "group_id": self.config["test_group_id"],
            "operator_id": self.config["test_user_qq"],
            "user_id": 333333333,  # 新成员ID
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_request_friend(self):
        """生成好友请求事件"""
        return {
            "post_type": "request",
            "request_type": "friend",
            "user_id": 444444444,
            "comment": "测试好友申请",
            "flag": "test_flag_123",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_friend_add(self):
        """生成好友添加事件"""
        return {
            "post_type": "notice",
            "notice_type": "friend_add",
            "user_id": 555555555,  # 新好友ID
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_friend_recall(self):
        """生成好友消息撤回事件"""
        return {
            "post_type": "notice",
            "notice_type": "friend_recall",
            "user_id": self.config["test_user_qq"],
            "message_id": 123456789,
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_recall(self):
        """生成群消息撤回事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_recall",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "operator_id": self.config["test_user_qq"],
            "message_id": 987654321,
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_decrease(self):
        """生成群成员减少事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_decrease",
            "sub_type": "leave",
            "group_id": self.config["test_group_id"],
            "operator_id": 0,
            "user_id": 666666666,  # 离开的成员ID
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_admin(self):
        """生成群管理员变动事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_admin",
            "sub_type": "set",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_ban(self):
        """生成群禁言事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_ban",
            "sub_type": "ban",
            "group_id": self.config["test_group_id"],
            "operator_id": self.config["admin_qq"],
            "user_id": self.config["test_user_qq"],
            "duration": 600,  # 禁言10分钟
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_upload(self):
        """生成群文件上传事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_upload",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "file": {
                "id": "test_file_id",
                "name": "测试文件.txt",
                "size": 1024,
                "busid": 102
            },
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_card(self):
        """生成群名片变更事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_card",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "card_new": "新群名片",
            "card_old": "旧群名片",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_name(self):
        """生成群名变更事件"""
        return {
            "post_type": "notice",
            "notice_type": "notify",
            "sub_type": "group_name",
            "group_id": self.config["test_group_id"],
            "operator_id": self.config["admin_qq"],
            "group_name": "新群名称",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_title(self):
        """生成群头衔变更事件"""
        return {
            "post_type": "notice",
            "notice_type": "notify",
            "sub_type": "title",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "title": "新专属头衔",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_profile_like(self):
        """生成个人资料点赞事件"""
        return {
            "post_type": "notice",
            "notice_type": "notify",
            "sub_type": "profile_like",
            "user_id": self.config["test_user_qq"],
            "operator_id": self.config["test_user_qq"],
            "times": 1,
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_input_status(self):
        """生成输入状态事件"""
        return {
            "post_type": "notice",
            "notice_type": "notify",
            "sub_type": "input_status",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "status": "typing",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_essence(self):
        """生成精华消息事件"""
        return {
            "post_type": "notice",
            "notice_type": "essence",
            "sub_type": "add",
            "group_id": self.config["test_group_id"],
            "sender_id": self.config["test_user_qq"],
            "operator_id": self.config["admin_qq"],
            "message_id": 111111111,
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_group_msg_emoji_like(self):
        """生成群消息表情回应事件"""
        return {
            "post_type": "notice",
            "notice_type": "group_msg_emoji_like",
            "group_id": self.config["test_group_id"],
            "user_id": self.config["test_user_qq"],
            "message_id": 222222222,
            "likes": [
                {"emoji_id": "1", "count": 1}
            ],
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_notice_bot_offline(self):
        """生成机器人离线事件"""
        return {
            "post_type": "notice",
            "notice_type": "bot_offline",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }
    
    def generate_request_group(self):
        """生成群请求事件"""
        return {
            "post_type": "request",
            "request_type": "group",
            "sub_type": "add",
            "group_id": self.config["test_group_id"],
            "user_id": 777777777,
            "comment": "测试群申请",
            "flag": "test_group_flag_456",
            "time": int(time.time()),
            "self_id": self.config["bot_qq"]
        }