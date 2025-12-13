
# XX-Job 主程序入口

import os
import sys
import webbrowser
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# 添加核心模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from core.storage import Storage
from core.api_client import ApiClient
from core.logger import TaskLogger
from core.scheduler import TaskScheduler

# 创建Flask应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 确保JSON响应使用UTF-8编码

# 初始化核心组件
storage = Storage()
api_client = ApiClient()
logger = TaskLogger(storage)
scheduler = TaskScheduler(storage, api_client, logger)

# 路由定义
@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/tasks')
def tasks():
    """任务管理页面"""
    return render_template('tasks.html')

@app.route('/logs')
def logs():
    """日志查看页面"""
    return render_template('logs.html')

# API路由
@app.route('/api/stats')
def get_stats():
    """获取系统统计数据"""
    tasks = storage.load_tasks()
    active_tasks = [task for task in tasks if task['status'] == 'active']

    # 获取今日执行日志
    today = datetime.now().strftime('%Y-%m-%d')
    all_logs = storage.load_logs(limit=1000)
    today_logs = [log for log in all_logs if log['timestamp'].startswith(today)]

    # 计算成功率
    success_count = len([log for log in today_logs if log['status'] == 'success'])
    total_count = len([log for log in today_logs if log['status'] in ['success', 'failure']])
    success_rate = f"{int(success_count / total_count * 100)}%" if total_count > 0 else "0%"

    return jsonify({
        'total_tasks': len(tasks),
        'active_tasks': len(active_tasks),
        'today_executions': len(today_logs),
        'success_rate': success_rate
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    tasks = storage.load_tasks()
    # 过滤掉已删除的任务
    tasks = [task for task in tasks if task['status'] != 'deleted']
    return jsonify(tasks)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务"""
    task = storage.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(task)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        # 记录原始请求数据，便于调试
        print(f"收到的原始请求数据: {request.data}")

        # 获取请求数据
        task_data = request.json
        print(f"解析后的任务数据: {task_data}")

        # 验证必填字段
        if not task_data:
            return jsonify({'error': '请求数据不能为空'}), 400

        name = task_data.get('name', '').strip()
        if not name:
            return jsonify({'error': '任务名称不能为空'}), 400

        # 确保名称被正确处理
        task_data['name'] = name

        # 验证任务类型
        task_type = task_data.get('type')
        if task_type not in ['cron', 'interval']:
            return jsonify({'error': '无效的任务类型'}), 400

        # 验证调度配置
        if task_type == 'cron' and not task_data.get('cron_expression'):
            return jsonify({'error': 'Cron表达式不能为空'}), 400
        elif task_type == 'interval' and not task_data.get('interval_seconds'):
            return jsonify({'error': '执行间隔不能为空'}), 400

        # 验证API步骤
        steps = task_data.get('steps', [])
        if not steps:
            return jsonify({'error': '至少需要配置一个API步骤'}), 400

        # 验证每个步骤的必填字段
        for i, step in enumerate(steps):
            if not step.get('name'):
                return jsonify({'error': f'步骤 {i+1} 的名称不能为空'}), 400
            if not step.get('url'):
                return jsonify({'error': f'步骤 {i+1} 的URL不能为空'}), 400
            if not step.get('method'):
                return jsonify({'error': f'步骤 {i+1} 的请求方法不能为空'}), 400

        # 添加任务
        print(f"准备添加任务: {task_data}")
        task_id = scheduler.add_task(task_data)
        print(f"任务创建成功，ID: {task_id}")
        return jsonify({'id': task_id, 'message': '任务创建成功'})

    except Exception as e:
        # 捕获所有异常并返回错误信息
        print(f"创建任务时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'创建任务失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    task_data = request.json

    # 验证必填字段
    if not task_data:
        return jsonify({'error': '请求数据不能为空'}), 400

    name = task_data.get('name', '').strip()
    if not name:
        return jsonify({'error': '任务名称不能为空'}), 400

    # 确保名称被正确处理
    task_data['name'] = name

    # 验证任务类型
    task_type = task_data.get('type')
    if task_type not in ['cron', 'interval']:
        return jsonify({'error': '无效的任务类型'}), 400

    # 验证调度配置
    if task_type == 'cron' and not task_data.get('cron_expression'):
        return jsonify({'error': 'Cron表达式不能为空'}), 400
    elif task_type == 'interval' and not task_data.get('interval_seconds'):
        return jsonify({'error': '执行间隔不能为空'}), 400

    # 验证API步骤
    steps = task_data.get('steps', [])
    if not steps:
        return jsonify({'error': '至少需要配置一个API步骤'}), 400

    # 验证每个步骤的必填字段
    for i, step in enumerate(steps):
        if not step.get('name'):
            return jsonify({'error': f'步骤 {i+1} 的名称不能为空'}), 400
        if not step.get('url'):
            return jsonify({'error': f'步骤 {i+1} 的URL不能为空'}), 400
        if not step.get('method'):
            return jsonify({'error': f'步骤 {i+1} 的请求方法不能为空'}), 400

    # 更新任务
    success = scheduler.update_task(task_id, task_data)
    if success:
        return jsonify({'message': '任务更新成功'})
    else:
        return jsonify({'error': '任务不存在'}), 404

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    success = scheduler.delete_task(task_id)
    if success:
        return jsonify({'message': '任务删除成功'})
    else:
        return jsonify({'error': '任务不存在'}), 404

@app.route('/api/tasks/<int:task_id>/pause', methods=['POST'])
def pause_task(task_id):
    """暂停任务"""
    success = scheduler.pause_task(task_id)
    if success:
        return jsonify({'message': '任务已暂停'})
    else:
        return jsonify({'error': '任务不存在'}), 404

@app.route('/api/tasks/<int:task_id>/resume', methods=['POST'])
def resume_task(task_id):
    """恢复任务"""
    success = scheduler.resume_task(task_id)
    if success:
        return jsonify({'message': '任务已恢复'})
    else:
        return jsonify({'error': '任务不存在'}), 404

@app.route('/api/tasks/<int:task_id>/run', methods=['POST'])
def run_task_now(task_id):
    """立即运行任务"""
    success = scheduler.run_task_now(task_id)
    if success:
        return jsonify({'message': '任务已开始执行'})
    else:
        return jsonify({'error': '任务不存在'}), 404

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志列表"""
    task_id = request.args.get('task_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    # 获取所有日志
    logs = storage.load_logs(task_id=task_id, limit=1000)  # 先获取足够多的日志

    # 按状态过滤
    if status:
        logs = [log for log in logs if log['status'] == status]

    # 计算分页
    total_count = len(logs)
    total_pages = (total_count + limit - 1) // limit
    start_index = (page - 1) * limit
    end_index = start_index + limit
    page_logs = logs[start_index:end_index]

    return jsonify({
        'logs': page_logs,
        'page': page,
        'limit': limit,
        'total_count': total_count,
        'total_pages': total_pages
    })

@app.route('/api/logs', methods=['DELETE'])
def clear_logs():
    """清除所有日志"""
    try:
        # 清空日志文件，写入一个空数组
        with open(storage.logs_file, 'w', encoding='utf-8') as f:
            f.write('[]')
        return jsonify({'message': '所有日志已清除'})
    except Exception as e:
        return jsonify({'error': f'清除日志失败: {str(e)}'}), 500

@app.route('/api/logs/<int:log_id>', methods=['GET'])
def get_log(log_id):
    """获取单个日志详情"""
    logs = storage.load_logs(limit=1000)
    for log in logs:
        if log['id'] == log_id:
            # 确保返回完整的日志信息，特别是details字段
            if 'details' in log and isinstance(log['details'], dict):
                # 确保details中的所有字段都被保留
                details = log['details'].copy()

                # 确保所有步骤都有完整的请求信息
                if 'step_index' in details:
                    # 确保请求头和请求体字段存在
                    if 'headers' not in details:
                        details['headers'] = {}
                    if 'body' not in details:
                        details['body'] = {}
                    if 'url' not in details:
                        details['url'] = ''
                    if 'method' not in details:
                        details['method'] = ''
                    if 'status_code' not in details:
                        details['status_code'] = None
                    if 'response' not in details:
                        details['response'] = None
                    if 'extracted_params' not in details:
                        details['extracted_params'] = {}

                # 更新日志的details
                log['details'] = details

            return jsonify(log)

    return jsonify({'error': '日志不存在'}), 404

# 启动浏览器
def open_browser():
    """延迟2秒后打开浏览器"""
    time.sleep(2)
    webbrowser.open('http://localhost:8080')

# 主函数
def main():
    """主函数"""
    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    # 启动Flask应用
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

if __name__ == '__main__':
    main()
