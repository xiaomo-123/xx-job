
# 存储模块，负责处理任务配置和日志的本地文件存储

import json
import os
from datetime import datetime

class Storage:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.tasks_file = os.path.join(data_dir, "tasks.json")
        self.logs_file = os.path.join(data_dir, "logs.json")

        # 确保数据目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # 初始化任务和日志文件
        if not os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        if not os.path.exists(self.logs_file):
            with open(self.logs_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load_tasks(self):
        """加载所有任务"""
        with open(self.tasks_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_tasks(self, tasks):
        """保存任务列表"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

    def add_task(self, task):
        """添加新任务"""
        tasks = self.load_tasks()
        task['id'] = len(tasks) + 1
        task['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task['status'] = 'active'  # active, paused, deleted
        tasks.append(task)
        self.save_tasks(tasks)
        return task['id']

    def update_task(self, task_id, updated_task):
        """更新任务"""
        tasks = self.load_tasks()
        for i, task in enumerate(tasks):
            if task['id'] == task_id:
                tasks[i] = {**tasks[i], **updated_task}
                self.save_tasks(tasks)
                return True
        return False

    def delete_task(self, task_id):
        """删除任务"""
        tasks = self.load_tasks()
        for i, task in enumerate(tasks):
            if task['id'] == task_id:
                tasks[i]['status'] = 'deleted'
                self.save_tasks(tasks)
                return True
        return False

    def get_task(self, task_id):
        """获取单个任务"""
        tasks = self.load_tasks()
        for task in tasks:
            if task['id'] == task_id and task['status'] != 'deleted':
                return task
        return None

    def load_logs(self, task_id=None, limit=100):
        """加载日志，可按任务ID过滤"""
        try:
            with open(self.logs_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                logs = json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        if task_id:
            logs = [log for log in logs if log['task_id'] == task_id]

        # 按时间倒序排序，并限制数量
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return logs[:limit]

    def add_log(self, log):
        """添加日志"""
        logs = self.load_logs()
        log['id'] = len(logs) + 1
        log['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logs.append(log)

        # 保存日志
        with open(self.logs_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
