
# 定时任务调度器模块，负责管理和执行定时任务

import threading
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

class TaskScheduler:
    def __init__(self, storage, api_client, logger):
        self.storage = storage
        self.api_client = api_client
        self.logger = logger
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.running = False
        self.lock = threading.Lock()

        # 加载并启动所有活跃任务
        self._load_and_start_tasks()

    def _load_and_start_tasks(self):
        """加载并启动所有活跃任务"""
        tasks = self.storage.load_tasks()
        for task in tasks:
            if task['status'] == 'active':
                self._schedule_task(task)

    def _schedule_task(self, task):
        """调度单个任务"""
        task_id = task['id']
        task_name = task['name']

        if task['type'] == 'cron':
            # Cron表达式任务
            cron_expr = task.get('cron_expression', '')
            if not cron_expr:
                self.logger.log_task_failure(
                    task_id, task_name, 
                    "无效的Cron表达式", 
                    {"task": task}
                )
                return

            try:
                # 解析Cron表达式
                trigger = CronTrigger.from_crontab(cron_expr)
                self.scheduler.add_job(
                    func=self._execute_task,
                    trigger=trigger,
                    args=[task],
                    id=f"task_{task_id}",
                    name=task_name,
                    replace_existing=True
                )
            except Exception as e:
                self.logger.log_task_failure(
                    task_id, task_name, 
                    f"Cron表达式解析错误: {str(e)}", 
                    {"task": task}
                )

        elif task['type'] == 'interval':
            # 间隔执行任务
            interval_seconds = task.get('interval_seconds', 60)
            try:
                trigger = IntervalTrigger(seconds=interval_seconds)
                self.scheduler.add_job(
                    func=self._execute_task,
                    trigger=trigger,
                    args=[task],
                    id=f"task_{task_id}",
                    name=task_name,
                    replace_existing=True
                )
            except Exception as e:
                self.logger.log_task_failure(
                    task_id, task_name, 
                    f"间隔配置错误: {str(e)}", 
                    {"task": task}
                )

    def _execute_task(self, task):
        """执行任务"""
        task_id = task['id']
        task_name = task['name']

        # 使用锁确保任务不会并发执行
        with self.lock:
            # 记录任务开始
            log_id = self.logger.log_task_start(task_id, task_name)

            try:
                # 执行API调用链
                steps = task.get('steps', [])
                retry_times = task.get('retry_times', 1)

                if not steps:
                    self.logger.log_task_failure(
                        task_id, task_name, 
                        "任务没有配置API步骤", 
                        {"task": task}
                    )
                    return

                # 执行API链
                result = self.api_client.execute_chain(steps, retry_times)

                # 记录每个步骤的执行情况
                for step_result in result['steps']:
                    self.logger.log_step_execution(
                        task_id, task_name,
                        step_result['step_index'],
                        step_result['step_name'],
                        step_result['result']
                    )

                # 记录任务最终结果
                if result['success']:
                    self.logger.log_task_success(
                        task_id, task_name,
                        {"execution_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    )
                else:
                    self.logger.log_task_failure(
                        task_id, task_name, 
                        result['error'], 
                        {"steps": result['steps']}
                    )

            except Exception as e:
                self.logger.log_task_failure(
                    task_id, task_name, 
                    f"任务执行异常: {str(e)}", 
                    {"task": task}
                )

    def add_task(self, task):
        """添加新任务"""
        task_id = self.storage.add_task(task)
        task['id'] = task_id

        if task['status'] == 'active':
            self._schedule_task(task)

        return task_id

    def update_task(self, task_id, updated_task):
        """更新任务"""
        # 先从调度器中移除旧任务
        try:
            self.scheduler.remove_job(f"task_{task_id}")
        except:
            pass

        # 更新任务数据
        success = self.storage.update_task(task_id, updated_task)

        if success:
            # 获取更新后的任务
            task = self.storage.get_task(task_id)
            if task and task['status'] == 'active':
                self._schedule_task(task)

        return success

    def delete_task(self, task_id):
        """删除任务"""
        # 先从调度器中移除任务
        try:
            self.scheduler.remove_job(f"task_{task_id}")
        except:
            pass

        # 更新任务状态为已删除
        return self.storage.delete_task(task_id)

    def pause_task(self, task_id):
        """暂停任务"""
        # 先从调度器中移除任务
        try:
            self.scheduler.remove_job(f"task_{task_id}")
        except:
            pass

        # 更新任务状态为暂停
        return self.storage.update_task(task_id, {'status': 'paused'})

    def resume_task(self, task_id):
        """恢复任务"""
        # 更新任务状态为活跃
        success = self.storage.update_task(task_id, {'status': 'active'})

        if success:
            # 重新调度任务
            task = self.storage.get_task(task_id)
            if task:
                self._schedule_task(task)

        return success

    def run_task_now(self, task_id):
        """立即运行任务"""
        task = self.storage.get_task(task_id)
        if task:
            # 在新线程中执行任务，避免阻塞
            thread = threading.Thread(target=self._execute_task, args=[task])
            thread.daemon = True
            thread.start()
            return True
        return False

    def get_all_tasks(self):
        """获取所有任务"""
        return self.storage.load_tasks()

    def get_task(self, task_id):
        """获取单个任务"""
        return self.storage.get_task(task_id)

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
