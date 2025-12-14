#!/usr/bin/env python3
"""
Askr Framework Test Suite - Main Test Runner
"""
import json
import os
import shutil
import subprocess
import time
import sys
import signal
import requests
from typing import List, Dict, Optional

class TestRunner:
    def __init__(self, test_json_path: str, version: str = "0.2"):
        self.test_json_path = test_json_path
        self.version = version
        self.processes = []

        # 路径配置 - 基于当前脚本位置
        script_dir = os.path.dirname(os.path.abspath(__file__))
        test_base = os.path.dirname(script_dir)  # test/
        project_root = os.path.dirname(test_base)  # AskrFramework/

        # Sandbox 目录（测试运行时工作目录）
        self.sandbox_dir = os.path.join(script_dir, "test_sandbox")
        self.plugins_dir = os.path.join(self.sandbox_dir, "plugins")

        # 测试结果目录
        self.results_dir = os.path.join(script_dir, "test_results", version)
        os.makedirs(self.results_dir, exist_ok=True)

        # 测试资源目录
        self.test_res_dir = os.path.join(test_base, "test_res", version)
        self.test_plugins_dir = os.path.join(self.test_res_dir, "plugins")
        self.test_configs_dir = os.path.join(self.test_res_dir, "configs")

        # 框架核心文件路径
        self.framework_files = [
            "askr_framework.py"
        ]
        self.project_root = project_root

        # 端口配置
        self.mock_server_port = 29218  # Mock NapCat server
        self.askr_framework_port = 29219  # Askr Framework listener
        
    def load_test_suite(self) -> List[Dict]:
        """加载测试套件JSON文件"""
        with open(self.test_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def cleanup_sandbox(self):
        """清空测试沙箱（测试前后都调用）"""
        print("清理测试沙箱...")

        # 完全删除并重建 sandbox 目录
        if os.path.exists(self.sandbox_dir):
            shutil.rmtree(self.sandbox_dir)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        os.makedirs(self.plugins_dir, exist_ok=True)
        print(f"  已清空 {self.sandbox_dir}")
    
    def prepare_test_files(self, test_config: Dict):
        """准备测试所需的文件"""
        test_name = test_config['testname']
        print(f"\n准备测试 '{test_name}' 的文件...")

        # 复制框架核心文件到 sandbox
        print("  复制框架核心文件...")
        for framework_file in self.framework_files:
            src = os.path.join(self.project_root, framework_file)
            dst = os.path.join(self.sandbox_dir, framework_file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"    {framework_file}")
            else:
                print(f"  警告: 框架文件不存在 {src}")

        # 复制插件文件
        plugins = test_config.get('plugins', [])
        for plugin_file in plugins:
            src = os.path.join(self.test_plugins_dir, plugin_file)
            dst = os.path.join(self.plugins_dir, plugin_file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  复制插件: {plugin_file}")
            else:
                print(f"  警告: 插件文件不存在 {src}")
        
        # 复制配置文件到 sandbox（自动添加 .json 扩展名）
        configs = test_config.get('configs', [])
        for config_name in configs:
            # 源文件路径（自动添加 .json 扩展名如果不存在）
            src = os.path.join(self.test_configs_dir, config_name)
            if not os.path.exists(src):
                src = src + '.json'

            # 根据配置名确定目标文件
            if config_name.startswith('config_'):
                dst = os.path.join(self.sandbox_dir, "frameworkConfig.json")
            elif config_name.startswith('plugin_access_'):
                dst = os.path.join(self.sandbox_dir, "PluginsAccessControl.json")
            else:
                # 其他文件保持原名（但添加 .json）
                dst_name = config_name if config_name.endswith('.json') else config_name + '.json'
                dst = os.path.join(self.sandbox_dir, dst_name)

            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  复制配置: {config_name} -> {os.path.basename(dst)}")
            else:
                print(f"  警告: 配置文件不存在 {src}")
    
    def start_mock_server(self, test_name: str) -> subprocess.Popen:
        """启动 Mock NapCat Server"""
        print(f"启动 Mock Server (端口 {self.mock_server_port})...")
        cmd = [
            sys.executable,
            "mock_napcat_server.py",
            "--port", str(self.mock_server_port),
            "--testname", test_name,
            "--test-json", self.test_json_path,
            "--version", self.version
        ]
        process = subprocess.Popen(cmd)
        self.processes.append(process)
        
        # 等待服务器启动
        time.sleep(2)
        
        # 检查服务器是否启动成功
        try:
            response = requests.get(f"http://localhost:{self.mock_server_port}/health", timeout=5)
            if response.status_code == 200:
                print("  Mock Server 启动成功")
            else:
                raise Exception(f"Mock Server 健康检查失败: {response.status_code}")
        except Exception as e:
            print(f"  Mock Server 启动失败: {e}")
            self.cleanup_processes()
            sys.exit(1)
        
        return process
    
    def start_askr_framework(self) -> subprocess.Popen:
        """启动 Askr Framework（在 sandbox 目录中运行）"""
        print(f"启动 Askr Framework (端口 {self.askr_framework_port})...")

        # 尝试使用 gunicorn，如果不可用则使用 Flask 开发服务器
        gunicorn_available = shutil.which("gunicorn") is not None

        if gunicorn_available:
            cmd = [
                "gunicorn",
                "-w", "1",
                "--threads", "8",
                "-b", f"0.0.0.0:{self.askr_framework_port}",
                "askr_framework:NAPCAT_LISTENER"
            ]
        else:
            # 使用 Flask 开发服务器（通过环境变量配置）
            cmd = [
                sys.executable,
                "-c",
                f"from askr_framework import NAPCAT_LISTENER; "
                f"NAPCAT_LISTENER.run(host='0.0.0.0', port={self.askr_framework_port}, debug=False)"
            ]

        # 关键：指定工作目录为 sandbox
        process = subprocess.Popen(cmd, cwd=self.sandbox_dir)
        self.processes.append(process)
        
        # 等待框架启动
        time.sleep(3)
        
        # 检查框架是否启动成功
        try:
            response = requests.get(f"http://localhost:{self.askr_framework_port}/health", timeout=5)
            if response.status_code == 200:
                print("  Askr Framework 启动成功")
            else:
                raise Exception(f"Askr Framework 健康检查失败: {response.status_code}")
        except Exception as e:
            print(f"  Askr Framework 启动失败: {e}")
            self.cleanup_processes()
            sys.exit(1)
        
        return process
    
    def start_event_sender(self, test_name: str) -> subprocess.Popen:
        """启动 Event Sender"""
        print("启动 Event Sender...")
        cmd = [
            sys.executable,
            "event_sender.py",
            "--port", str(self.askr_framework_port),
            "--testname", test_name,
            "--test-json", self.test_json_path
        ]
        process = subprocess.Popen(cmd)
        self.processes.append(process)
        return process
    
    def cleanup_processes(self):
        """清理所有子进程"""
        print("\n清理进程...")
        for process in self.processes:
            if process.poll() is None:  # 进程还在运行
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        self.processes.clear()
    
    def run_single_test(self, test_config: Dict):
        """运行单个测试"""
        test_name = test_config['testname']
        print(f"\n{'='*60}")
        print(f"开始测试: {test_name}")
        print(f"{'='*60}")
        
        try:
            # 1. 清理 sandbox
            self.cleanup_sandbox()

            # 2. 准备测试文件到 sandbox
            self.prepare_test_files(test_config)
            
            # 3. 启动 Mock Server
            server_process = self.start_mock_server(test_name)
            
            # 4. 启动 Askr Framework
            framework_process = self.start_askr_framework()
            
            # 5. 启动 Event Sender
            sender_process = self.start_event_sender(test_name)
            
            # 6. 等待 Sender 完成
            print("等待事件发送完成...")
            sender_process.wait()
            print("  事件发送完成")
            
            # 7. 额外等待，确保所有响应都被处理
            wait_time = test_config.get('extra_wait_seconds', 5)
            print(f"等待 {wait_time} 秒以确保所有响应被处理...")
            time.sleep(wait_time)
            
            # 8. 通知 Mock Server 测试结束
            print("通知 Mock Server 测试结束...")
            try:
                response = requests.post(f"http://localhost:{self.mock_server_port}/finish_test")
                if response.status_code == 200:
                    print("  测试结束通知发送成功")
                else:
                    print(f"  警告: 测试结束通知返回 {response.status_code}")
            except Exception as e:
                print(f"  错误: 无法发送测试结束通知 - {e}")
            
            # 9. 等待 Mock Server 生成报告
            time.sleep(2)

            print(f"\n测试 '{test_name}' 完成")
            report_path = os.path.join(self.results_dir, f"test_result_{test_name}.txt")
            print(f"结果已保存到: {report_path}")

        finally:
            # 清理所有进程
            self.cleanup_processes()

            # 清理 sandbox（测试后）
            self.cleanup_sandbox()
    
    def run_all_tests(self):
        """运行所有测试"""
        test_suite = self.load_test_suite()
        total_tests = len(test_suite)
        
        print(f"加载了 {total_tests} 个测试")
        
        for i, test_config in enumerate(test_suite, 1):
            print(f"\n\n进度: {i}/{total_tests}")
            self.run_single_test(test_config)
            
            # 测试之间稍作停顿
            if i < total_tests:
                print("\n等待 3 秒后开始下一个测试...")
                time.sleep(3)
        
        print(f"\n\n{'='*60}")
        print("所有测试完成！")
        print(f"{'='*60}")


def main():
    if len(sys.argv) != 2:
        print("用法: python test_runner.py <test_suite.json>")
        sys.exit(1)
    
    test_json_path = sys.argv[1]
    
    if not os.path.exists(test_json_path):
        print(f"错误: 测试文件不存在 - {test_json_path}")
        sys.exit(1)
    
    # 设置信号处理
    runner = TestRunner(test_json_path)
    
    def signal_handler(signum, frame):
        print("\n\n收到中断信号，清理进程...")
        runner.cleanup_processes()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        runner.run_all_tests()
    except Exception as e:
        print(f"\n测试运行器错误: {e}")
        runner.cleanup_processes()
        sys.exit(1)


if __name__ == "__main__":
    main()
