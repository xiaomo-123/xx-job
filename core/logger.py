
# 日志管理模块，负责记录任务执行日志

import os
from datetime import datetime

class TaskLogger:
    def __init__(self, storage):
        self.storage = storage

    def log_task_start(self, task_id, task_name):
        """记录任务开始执行"""
        log = {
            'task_id': task_id,
            'task_name': task_name,
            'event': 'start',
            'status': 'running',
            'message': f'任务 "{task_name}" 开始执行',
            'details': {}
        }
        self.storage.add_log(log)
        return log['id']

    def log_task_success(self, task_id, task_name, details=None):
        """记录任务执行成功"""
        log = {
            'task_id': task_id,
            'task_name': task_name,
            'event': 'complete',
            'status': 'success',
            'message': f'任务 "{task_name}" 执行成功',
            'details': details or {}
        }
        self.storage.add_log(log)
        return log['id']

    def log_task_failure(self, task_id, task_name, error, details=None):
        """记录任务执行失败"""
        log = {
            'task_id': task_id,
            'task_name': task_name,
            'event': 'complete',
            'status': 'failure',
            'message': f'任务 "{task_name}" 执行失败: {error}',
            'details': details or {}
        }
        self.storage.add_log(log)
        return log['id']

    def log_step_execution(self, task_id, task_name, step_index, step_name, step_result):
        """记录API步骤执行情况"""
        status = 'success' if step_result['success'] else 'failure'
        message = f'步骤 {step_index+1} "{step_name}" 执行{"成功" if status == "success" else "失败"}'

        if not step_result['success']:
            message += f': {step_result["error"]}'

        # 确保记录完整的请求信息，使用copy避免引用问题
        details = {
            'step_index': step_index,
            'step_name': step_name,
            'url': step_result.get('url', ''),
            'method': step_result.get('method', ''),
            'status_code': step_result.get('status_code'),
            'response': step_result.get('response'),
            'extracted_params': step_result.get('extracted_params', {}),
            'headers': step_result.get('headers', {}),
            'body': step_result.get('body', {})
        }

        # 确保请求头和请求体的引用值被正确处理和记录
        # 这样在查看日志时可以看到原始的引用值，如 "Authorization": "Bearer ${token}"

        # 记录步骤执行详情，便于调试
        print(f"=== 记录步骤 {step_index} ({step_name}) 日志 ===")
        print(f"请求URL: {details['url']}")
        print(f"请求方法: {details['method']}")

        # 检查请求头中是否有引用值被替换
        headers = details['headers']
        if isinstance(headers, dict) and 'Authorization' in headers:
            auth_header = headers['Authorization']
            if isinstance(auth_header, str) and 'Bearer' in auth_header:
                if '${token}' in auth_header:
                    print(f"请求头Authorization包含未替换的token引用: {auth_header}")
                else:
                    print(f"请求头Authorization已正确设置: {auth_header[:20]}...")  # 只显示前20个字符，避免泄露token
        print(f"请求头: {headers}")

        print(f"状态码: {details['status_code']}")
        print(f"提取的参数: {details['extracted_params']}")

        log = {
            'task_id': task_id,
            'task_name': task_name,
            'event': 'step',
            'status': status,
            'message': message,
            'details': details
        }
        self.storage.add_log(log)
        return log['id']

    def get_task_logs(self, task_id, limit=100):
        """获取特定任务的日志"""
        return self.storage.load_logs(task_id=task_id, limit=limit)

    def get_all_logs(self, limit=200):
        """获取所有任务的日志"""
        return self.storage.load_logs(limit=limit)
