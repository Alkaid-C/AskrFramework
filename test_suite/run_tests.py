#!/usr/bin/env python3
"""
Askr Framework 自动化测试脚本
协调伪NapCat服务器和测试流程，生成详细测试报告
"""

import os
import sys
import time
import json
import subprocess
import signal
from datetime import datetime

# 导入伪NapCat服务器
from fake_napcat import FakeNapCat, TestEventGenerator

class AskrTestRunner:
    def __init__(self):
        # 测试配置
        self.config = {
            "listen_host": "localhost",
            "listen_port": 29217,        # 接收框架API调用
            "framework_url": "http://localhost:29218",  # 向框架发送事件
            "bot_qq": 123456789,         # 机器人QQ号
            "admin_qq": 999999999,       # 管理员QQ号（用于接收错误通知）
            "test_user_qq": 111111111,   # 测试用户QQ号
            "test_group_id": 222222222   # 测试群号
        }
        
        self.fake_napcat = FakeNapCat(self.config)
        self.event_generator = TestEventGenerator(self.config)
        self.framework_process = None
        self.test_results = {
            "start_time": None,
            "end_time": None,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "response_times": [],
            "test_details": []
        }
    
    def setup_test_environment(self):
        """设置测试环境"""
        print("=== 设置测试环境 ===")
        
        
        # 启动伪NapCat服务器
        print("启动伪NapCat服务器...")
        self.fake_napcat.start_server()
        print(f"伪NapCat服务器已启动: {self.config['listen_host']}:{self.config['listen_port']}")
        
        # 启动Askr框架
        print("启动Askr框架...")
        try:
            self.framework_process = subprocess.Popen(
                [sys.executable, "askr_framework.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待框架初始化
            print("等待框架初始化...")
            time.sleep(10)
            
            # 检查框架是否成功启动
            if self.framework_process.poll() is not None:
                stdout, stderr = self.framework_process.communicate()
                print(f"框架启动失败:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
            
            print("Askr框架已启动")
            return True
            
        except Exception as e:
            print(f"启动框架失败: {e}")
            return False
    
    def test_event_dispatch(self):
        """测试事件分发功能"""
        print("\n=== 测试事件分发功能 ===")
        
        # 定义测试用例：(事件生成器方法, 预期响应数量, 描述)
        test_cases = [
            # 消息事件
            ("generate_message_private", 1, "私聊消息"),
            ("generate_message_group", 1, "群聊消息"),
            ("generate_message_group_mention", 2, "群聊@消息(继承)"),
            ("generate_message_group_bot", 2, "群聊指令消息(继承)"),
            
            # 通知事件 - 好友相关
            ("generate_notice_friend_add", 1, "好友添加"),
            ("generate_notice_friend_recall", 1, "好友消息撤回"),
            
            # 通知事件 - 群聊相关
            ("generate_notice_group_recall", 1, "群消息撤回"),
            ("generate_notice_group_increase", 1, "群成员增加"),
            ("generate_notice_group_decrease", 1, "群成员减少"),
            ("generate_notice_group_admin", 1, "群管理员变动"),
            ("generate_notice_group_ban", 1, "群禁言"),
            ("generate_notice_group_upload", 1, "群文件上传"),
            ("generate_notice_group_card", 1, "群名片变更"),
            ("generate_notice_group_name", 1, "群名变更"),
            ("generate_notice_group_title", 1, "群头衔变更"),
            ("generate_notice_essence", 1, "精华消息"),
            ("generate_notice_group_msg_emoji_like", 1, "群消息表情回应"),
            
            # 通知事件 - 其他
            ("generate_notice_poke", 1, "戳一戳通知"),
            ("generate_notice_profile_like", 1, "个人资料点赞"),
            ("generate_notice_input_status", 1, "输入状态"),
            ("generate_notice_bot_offline", 1, "机器人离线"),
            
            # 请求事件
            ("generate_request_friend", 1, "好友请求"),
            ("generate_request_group", 1, "群请求"),
        ]
        
        for method_name, expected_count, description in test_cases:
            print(f"\n测试: {description}")
            
            # 在发送事件前记录当前API调用数量
            initial_api_count = len(self.fake_napcat.api_call_log)
            
            # 生成事件
            event_generator_method = getattr(self.event_generator, method_name)
            if method_name == "generate_message_group_bot":
                event_data = event_generator_method("/test_command")
            else:
                event_data = event_generator_method()
            
            # 记录发送时间
            send_time = time.time()
            
            # 发送事件
            success = self.fake_napcat.send_event(event_data)
            if not success:
                self.record_test_result(description, False, "发送事件失败", 0)
                continue
            
            # 等待响应
            responses = self.fake_napcat.wait_for_responses(expected_count, timeout=5, start_from_count=initial_api_count)
            response_time = (time.time() - send_time) * 1000  # 转换为毫秒
            
            # 验证结果
            if len(responses) == expected_count:
                self.record_test_result(description, True, f"收到{len(responses)}个响应", response_time)
                self.test_results["response_times"].append(response_time)
            else:
                self.record_test_result(description, False, f"期望{expected_count}个响应，实际{len(responses)}个", response_time)
    
    def test_comprehensive_functionality(self):
        """测试综合功能"""
        print("\n=== 测试综合功能 ===")
        
        # 确保定时任务处于停用状态，避免干扰测试
        print("确保定时任务停用...")
        self.run_private_message_test("/定时测试停止", "停用定时任务", True, 5)
        
        # simpleEvent测试
        self.run_private_message_test("/test_simple", "simpleEvent测试", True, 5)
        
        # 返回值类型测试
        self.run_private_message_test("/test_str", "字符串返回值", True, 5)
        self.run_private_message_test("/test_dict", "字典返回值", True, 5)
        self.run_private_message_test("/test_list", "列表返回值", True, 5, expected_count=2)
        
        # 非法返回值测试（应触发管理员通知）
        print("\n测试: 非法返回值")
        initial_api_count = len(self.fake_napcat.api_call_log)
        send_time = time.time()
        
        event_data = self.event_generator.generate_message_private("/test_invalid")
        self.fake_napcat.send_event(event_data)
        
        # 过滤器：排除管理员通知，只看普通响应
        def is_normal_response(call):
            return (call["action"] == "send_private_msg" and 
                   call["data"].get("user_id") != self.config["admin_qq"])
        
        # 过滤器：检查管理员通知
        def is_admin_notification(call):
            return (call["action"] == "send_private_msg" and 
                   call["data"].get("user_id") == self.config["admin_qq"])
        
        # 等待所有响应（普通响应 + 管理员通知）
        all_responses = self.fake_napcat.wait_for_responses(2, timeout=10, start_from_count=initial_api_count)
        
        # 分类响应
        normal_responses = [r for r in all_responses if is_normal_response(r)]
        admin_notifications = [r for r in all_responses if is_admin_notification(r)]
        
        # 检查是否有来自插件2的正常响应（不应该有，因为返回值非法）
        plugin2_normal = any("插件2" in str(r.get("data", "")) and 
                           "收到" in str(r.get("data", "")) for r in normal_responses)
        
        response_time = (time.time() - send_time) * 1000
        
        if not plugin2_normal and len(admin_notifications) > 0 and len(normal_responses) >= 1:
            self.record_test_result("非法返回值", True, "正确触发管理员通知", response_time)
        else:
            self.record_test_result("非法返回值", False, f"未按预期触发通知，总响应:{len(all_responses)}，正常响应:{len(normal_responses)}，插件2正常响应:{plugin2_normal}，管理员通知:{len(admin_notifications)}", response_time)
        
        # botContext工具测试
        print("\n测试botContext工具...")
        self.run_private_message_test("/test_config_write", "配置写入", True, 5)
        self.run_private_message_test("/test_config_read", "配置读取", True, 5)
        self.run_private_message_test("/test_librarian", "历史记录查询", True, 5)
        self.run_private_message_test("/test_apicaller", "API调用", True, 5)
    
    def test_crash_scenarios(self):
        """测试崩溃场景"""
        print("\n=== 测试崩溃场景 ===")
        
        crash_tests = [
            {
                "command": "/test_exception",
                "name": "异常处理",
                "timeout": 45
            },
            {
                "command": "/test_cpu", 
                "name": "CPU时间限制",
                "timeout": 45
            },
            {
                "command": "/test_sleep",
                "name": "墙钟时间限制", 
                "timeout": 45
            },
            {
                "command": "/test_memory",
                "name": "内存限制",
                "timeout": 45
            }
        ]
        
        for test in crash_tests:
            print(f"\n测试: {test['name']}")
            initial_api_count = len(self.fake_napcat.api_call_log)
            send_time = time.time()
            
            # 发送崩溃测试命令
            event_data = self.event_generator.generate_message_private(test["command"])
            self.fake_napcat.send_event(event_data)
            
            # 过滤器：排除管理员通知，只看普通响应
            def is_normal_response(call):
                return (call["action"] == "send_private_msg" and 
                       call["data"].get("user_id") != self.config["admin_qq"])
            
            # 过滤器：检查管理员通知
            def is_admin_notification(call):
                return (call["action"] == "send_private_msg" and 
                       call["data"].get("user_id") == self.config["admin_qq"])
            
            # 等待所有响应，崩溃测试可能需要更长时间才能触发通知
            all_responses = self.fake_napcat.wait_for_responses(2, timeout=test["timeout"], start_from_count=initial_api_count)
            
            # 分类响应
            normal_responses = [r for r in all_responses if is_normal_response(r)]
            admin_notifications = [r for r in all_responses if is_admin_notification(r)]
            
            # 检查是否有来自插件2的成功响应（不应该有）
            plugin2_success = any("测试完成" in str(r.get("data", "")) or 
                                "测试成功" in str(r.get("data", "")) for r in normal_responses)
            
            response_time = (time.time() - send_time) * 1000
            
            if not plugin2_success and len(admin_notifications) > 0 and len(normal_responses) >= 1:
                self.record_test_result(test["name"], True, "正确处理崩溃并通知管理员", response_time)
            else:
                self.record_test_result(test["name"], False, 
                    f"崩溃处理异常，总响应:{len(all_responses)}，正常响应:{len(normal_responses)}，插件2成功:{plugin2_success}，管理员通知:{len(admin_notifications)}", response_time)
            
            # 给系统时间恢复
            time.sleep(2)
    
    def test_unconditional_events(self):
        """测试定时任务"""
        print("\n=== 测试定时任务 ===")
        
        # 首先启用定时任务
        print("启用定时任务...")
        self.run_private_message_test("/定时测试开始", "启用定时任务", True, 5)
        
        print("等待定时任务执行（间隔2分钟）...")
        
        # 等待定时任务执行，最多等待140秒
        start_time = time.time()
        max_wait = 140
        
        def is_scheduled_response(call):
            return (call["action"] == "send_private_msg" and 
                   "定时任务执行" in str(call["data"]))
        
        # 记录当前API调用数量，避免计入之前的调用
        initial_api_count = len(self.fake_napcat.api_call_log)
        
        while time.time() - start_time < max_wait:
            responses = self.fake_napcat.wait_for_responses(1, timeout=10, 
                                                           filter_func=is_scheduled_response,
                                                           start_from_count=initial_api_count)
            if responses:
                response_time = (time.time() - start_time) * 1000
                self.record_test_result("定时任务", True, f"定时任务成功执行", response_time)
                
                # 停用定时任务，避免干扰后续测试
                print("停用定时任务...")
                self.run_private_message_test("/定时测试停止", "停用定时任务", True, 5)
                return
        
        # 超时未收到定时任务响应
        self.record_test_result("定时任务", False, "定时任务未在预期时间内执行", max_wait * 1000)
    
    def test_plugin_removal(self):
        """测试插件移除机制"""
        print("\n=== 测试插件移除机制 ===")
        
        # 向应该被移除的插件3发送消息
        print("测试插件3是否已被移除...")
        initial_api_count = len(self.fake_napcat.api_call_log)
        send_time = time.time()
        
        event_data = self.event_generator.generate_message_private("/test_plugin3")
        self.fake_napcat.send_event(event_data)
        
        # 过滤器：排除管理员通知，只看普通响应
        def is_normal_response(call):
            return (call["action"] == "send_private_msg" and 
                   call["data"].get("user_id") != self.config["admin_qq"])
        
        # 等待可能的响应
        responses = self.fake_napcat.wait_for_responses(1, timeout=5, 
                                                       filter_func=is_normal_response,
                                                       start_from_count=initial_api_count)
        response_time = (time.time() - send_time) * 1000
        
        # 检查是否有来自插件3的响应
        plugin3_response = any("[插件3]" in str(r.get("data", "")) for r in responses)
        
        if not plugin3_response:
            self.record_test_result("插件移除", True, "插件3已正确移除", response_time)
        else:
            self.record_test_result("插件移除", False, "插件3未被正确移除", response_time)
    
    def run_private_message_test(self, command, test_name, expect_response, timeout, expected_count=1):
        """运行私聊消息测试"""
        print(f"\n测试: {test_name}")
        send_time = time.time()
        
        # 在发送事件前记录当前API调用数量
        initial_api_count = len(self.fake_napcat.api_call_log)
        
        event_data = self.event_generator.generate_message_private(command)
        success = self.fake_napcat.send_event(event_data)
        
        if not success:
            self.record_test_result(test_name, False, "发送事件失败", 0)
            return
        
        if expect_response:
            responses = self.fake_napcat.wait_for_responses(expected_count, timeout=timeout, start_from_count=initial_api_count)
            response_time = (time.time() - send_time) * 1000
            
            if len(responses) == expected_count:
                self.record_test_result(test_name, True, f"收到{len(responses)}个响应", response_time)
                self.test_results["response_times"].append(response_time)
            else:
                self.record_test_result(test_name, False, f"期望{expected_count}个响应，实际{len(responses)}个", response_time)
        else:
            response_time = (time.time() - send_time) * 1000
            self.record_test_result(test_name, True, "按预期无响应", response_time)
    
    def record_test_result(self, test_name, passed, message, response_time):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "response_time_ms": response_time,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results["test_details"].append(result)
        self.test_results["total_tests"] += 1
        
        if passed:
            self.test_results["passed_tests"] += 1
            print(f"✅ {test_name}: {message} ({response_time:.1f}ms)")
        else:
            self.test_results["failed_tests"] += 1
            print(f"❌ {test_name}: {message} ({response_time:.1f}ms)")
    
    def generate_test_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        self.test_results["end_time"] = end_time.isoformat()
        
        # 计算统计信息
        response_times = self.test_results["response_times"]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            min_response = min(response_times)
        else:
            avg_response = max_response = min_response = 0
        
        success_rate = (self.test_results["passed_tests"] / self.test_results["total_tests"] * 100) if self.test_results["total_tests"] > 0 else 0
        
        # API调用统计
        api_summary = self.fake_napcat.get_api_calls_summary()
        
        report = {
            "test_summary": {
                "start_time": self.test_results["start_time"],
                "end_time": self.test_results["end_time"],
                "duration_seconds": (end_time - datetime.fromisoformat(self.test_results["start_time"])).total_seconds(),
                "total_tests": self.test_results["total_tests"],
                "passed_tests": self.test_results["passed_tests"],
                "failed_tests": self.test_results["failed_tests"],
                "success_rate": f"{success_rate:.1f}%"
            },
            "performance_metrics": {
                "avg_response_time_ms": f"{avg_response:.1f}",
                "max_response_time_ms": f"{max_response:.1f}",
                "min_response_time_ms": f"{min_response:.1f}",
                "total_api_calls": len(self.fake_napcat.api_call_log),
                "api_call_summary": api_summary
            },
            "test_details": self.test_results["test_details"]
        }
        
        # 保存报告到文件
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 打印摘要
        print("\n" + "="*60)
        print("测试完成！")
        print(f"总测试数: {self.test_results['total_tests']}")
        print(f"通过: {self.test_results['passed_tests']}")
        print(f"失败: {self.test_results['failed_tests']}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"平均响应时间: {avg_response:.1f}ms")
        print(f"详细报告已保存到: {report_file}")
        print("="*60)
        
        return report
    
    def cleanup(self):
        """清理测试环境"""
        print("\n清理测试环境...")
        
        if self.framework_process:
            try:
                self.framework_process.terminate()
                self.framework_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.framework_process.kill()
            except Exception as e:
                print(f"清理框架进程时出错: {e}")
        
        print("测试环境清理完成")
    
    def run_all_tests(self):
        """运行所有测试"""
        self.test_results["start_time"] = datetime.now().isoformat()
        
        try:
            # 环境设置
            if not self.setup_test_environment():
                print("环境设置失败，测试终止")
                return None
            
            # 运行测试
            self.test_plugin_removal()      # 首先测试插件移除
            
            # 确保定时任务初始状态为关闭
            print("\n确保定时任务初始状态为关闭...")
            self.run_private_message_test("/定时测试停止", "初始化定时任务状态", True, 5)
            
            self.test_event_dispatch()      # 事件分发测试
            self.test_comprehensive_functionality()  # 综合功能测试
            self.test_crash_scenarios()     # 崩溃场景测试
            self.test_unconditional_events() # 定时任务测试
            
            # 生成报告
            return self.generate_test_report()
            
        except KeyboardInterrupt:
            print("\n测试被用户中断")
            return None
        except Exception as e:
            print(f"\n测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self.cleanup()

def main():
    print("Askr Framework 自动化测试")
    print("=" * 60)
    
    runner = AskrTestRunner()
    
    try:
        report = runner.run_all_tests()
        if report:
            # 根据测试结果确定退出码
            exit_code = 0 if report["test_summary"]["failed_tests"] == 0 else 1
            sys.exit(exit_code)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n测试被中断")
        sys.exit(1)

if __name__ == "__main__":
    main()