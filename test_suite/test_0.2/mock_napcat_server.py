#!/usr/bin/env python3
"""
Mock NapCat Server - 模拟 NapCat HTTP API 服务器用于测试
"""
import json
import argparse
import time
from datetime import datetime
from flask import Flask, request, jsonify
from typing import List, Dict, Any
import threading
import sys

class MockNapCatServer:
    def __init__(self, port: int, testname: str, test_json_path: str):
        self.port = port
        self.testname = testname
        self.test_json_path = test_json_path
        self.app = Flask(__name__)
        
        # 记录收到的 API 调用
        self.received_calls = []
        self.lock = threading.Lock()
        
        # 加载预期的响应
        self.expected_responses = self.load_expected_responses()
        
        # 设置路由
        self.setup_routes()
        
    def load_expected_responses(self) -> List[Dict]:
        """加载当前测试的预期响应"""
        with open(self.test_json_path, 'r', encoding='utf-8') as f:
            test_suite = json.load(f)
        
        # 找到对应的测试
        for test in test_suite:
            if test['testname'] == self.testname:
                return test.get('expected_responses', [])
        
        return []
    
    def setup_routes(self):
        """设置所有路由"""
        # 健康检查
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({"status": "ok", "testname": self.testname}), 200
        
        # 通用 API 处理器
        @self.app.route('/<path:api_path>', methods=['POST'])
        def handle_api(api_path):
            # 特殊处理结束测试的请求
            if api_path == 'finish_test':
                self.generate_report()
                return '', 200
            
            # 记录 API 调用
            try:
                request_data = request.get_json()
                api_call = {
                    "action": api_path,
                    "data": request_data
                }
                
                with self.lock:
                    self.received_calls.append(api_call)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到 API 调用: {api_path}")
                
            except Exception as e:
                print(f"错误: 处理 API 调用失败 - {e}")
            
            # 返回标准的 OneBot 响应
            return '', 200
        
        # GET 请求处理（如 get_status）
        @self.app.route('/<path:api_path>', methods=['GET'])
        def handle_get_api(api_path):
            # 模拟一些常用的 GET API
            if api_path == 'get_status':
                return jsonify({
                    "status": "ok",
                    "retcode": 0,
                    "data": {
                        "online": True,
                        "good": True
                    }
                }), 200
            
            # 其他 GET 请求返回空数据
            return jsonify({
                "status": "ok",
                "retcode": 0,
                "data": {}
            }), 200
    
    def compare_dicts(self, d1: Dict, d2: Dict) -> bool:
        """深度比较两个字典是否相等"""
        if type(d1) != type(d2):
            return False
        
        if isinstance(d1, dict):
            if set(d1.keys()) != set(d2.keys()):
                return False
            return all(self.compare_dicts(d1[k], d2[k]) for k in d1.keys())
        elif isinstance(d1, list):
            if len(d1) != len(d2):
                return False
            return all(self.compare_dicts(d1[i], d2[i]) for i in range(len(d1)))
        else:
            return d1 == d2
    
    def generate_report(self):
        """生成测试报告"""
        print(f"\n生成测试报告: {self.testname}")
        
        # 复制列表用于处理
        received_copy = self.received_calls.copy()
        expected_copy = self.expected_responses.copy()
        
        # 找出匹配的调用
        matched = []
        for expected in expected_copy[:]:
            for i, received in enumerate(received_copy):
                if self.compare_dicts(expected, received):
                    matched.append((expected, received))
                    expected_copy.remove(expected)
                    received_copy.pop(i)
                    break
        
        # 生成报告
        report_lines = []
        report_lines.append(f"测试报告: {self.testname}")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 60)
        
        # 统计信息
        report_lines.append(f"\n统计信息:")
        report_lines.append(f"  预期响应数: {len(self.expected_responses)}")
        report_lines.append(f"  实际收到数: {len(self.received_calls)}")
        report_lines.append(f"  匹配成功数: {len(matched)}")
        
        # 应该收到但没收到的
        report_lines.append(f"\n\n应该收到但没收到的响应 ({len(expected_copy)} 个):")
        report_lines.append("-" * 40)
        if expected_copy:
            for i, expected in enumerate(expected_copy, 1):
                report_lines.append(f"\n{i}. {json.dumps(expected, ensure_ascii=False, indent=2)}")
        else:
            report_lines.append("无")
        
        # 不应该收到但收到了的
        report_lines.append(f"\n\n不应该收到但收到了的响应 ({len(received_copy)} 个):")
        report_lines.append("-" * 40)
        if received_copy:
            for i, received in enumerate(received_copy, 1):
                report_lines.append(f"\n{i}. {json.dumps(received, ensure_ascii=False, indent=2)}")
        else:
            report_lines.append("无")
        
        # 成功匹配的（可选，用于调试）
        report_lines.append(f"\n\n成功匹配的响应 ({len(matched)} 个):")
        report_lines.append("-" * 40)
        if matched:
            for i, (expected, received) in enumerate(matched, 1):
                report_lines.append(f"\n{i}. {json.dumps(expected, ensure_ascii=False, indent=2)}")
        else:
            report_lines.append("无")
        
        # 测试结果
        report_lines.append("\n\n" + "=" * 60)
        if not expected_copy and not received_copy:
            report_lines.append("测试结果: 通过 ✓")
        else:
            report_lines.append("测试结果: 失败 ✗")
        
        # 写入文件
        report_filename = f"test_result_{self.testname}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"报告已保存到: {report_filename}")
    
    def run(self):
        """启动服务器"""
        print(f"Mock NapCat Server 启动在端口 {self.port}")
        print(f"测试名称: {self.testname}")
        print(f"预期响应数: {len(self.expected_responses)}")
        
        # 禁用 Flask 的启动信息
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        self.app.run(host='0.0.0.0', port=self.port, debug=False)


def main():
    parser = argparse.ArgumentParser(description='Mock NapCat Server')
    parser.add_argument('--port', type=int, default=29218, help='服务器端口')
    parser.add_argument('--testname', required=True, help='测试名称')
    parser.add_argument('--test-json', required=True, help='测试配置文件路径')
    
    args = parser.parse_args()
    
    server = MockNapCatServer(args.port, args.testname, args.test_json)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n服务器停止")
        sys.exit(0)


if __name__ == '__main__':
    main()
