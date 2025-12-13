
// 日志页面JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    loadTasks();
    loadLogs();

    // 绑定事件
    document.getElementById('refresh-btn').addEventListener('click', loadLogs);
    document.getElementById('task-filter').addEventListener('change', loadLogs);
    document.getElementById('status-filter').addEventListener('change', loadLogs);
    document.getElementById('prev-page').addEventListener('click', goToPrevPage);
    document.getElementById('next-page').addEventListener('click', goToNextPage);

    // 添加清除日志按钮事件
    const clearLogsBtn = document.getElementById('clear-logs-btn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', clearAllLogs);
    }

    // 初始化模态框
    const modal = document.getElementById('log-detail-modal');
    modal.querySelector('.close').addEventListener('click', function() {
        closeModal(modal);
    });

    // 点击模态框外部关闭
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal(modal);
        }
    });
});

// 当前页码
let currentPage = 1;
const pageSize = 20;

// 加载任务列表（用于筛选）
function loadTasks() {
    fetch('/api/tasks')
        .then(response => response.json())
        .then(tasks => {
            const taskFilter = document.getElementById('task-filter');

            // 保留"所有任务"选项
            taskFilter.innerHTML = '<option value="">所有任务</option>';

            // 添加任务选项
            tasks.forEach(task => {
                const option = document.createElement('option');
                option.value = task.id;
                option.textContent = task.name;
                taskFilter.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading tasks:', error);
            showNotification('加载任务列表失败', 'error');
        });
}

// 加载日志列表
function loadLogs() {
    const taskId = document.getElementById('task-filter').value;
    const status = document.getElementById('status-filter').value;

    // 构建查询参数
    const params = new URLSearchParams({
        page: currentPage,
        limit: pageSize
    });

    if (taskId) params.append('task_id', taskId);
    if (status) params.append('status', status);

    fetch(`/api/logs?${params}`)
        .then(response => response.json())
        .then(data => {
            displayLogs(data.logs);
            updatePagination(data.page, data.total_pages, data.total_count);
        })
        .catch(error => {
            console.error('Error loading logs:', error);
            showNotification('加载日志失败', 'error');
        });
}

// 显示日志列表
function displayLogs(logs) {
    const logsContainer = document.getElementById('logs-container');

    if (logs.length === 0) {
        logsContainer.innerHTML = '<p style="text-align: center;">暂无日志记录</p>';
        return;
    }

    logsContainer.innerHTML = '';

    logs.forEach(log => {
        const logItem = document.createElement('div');
        logItem.className = 'log-item';
        logItem.addEventListener('click', () => showLogDetail(log.id));

        // 状态样式
        const statusClass = {
            'success': 'status-success',
            'failure': 'status-failure',
            'running': 'status-running'
        }[log.status] || '';

        logItem.innerHTML = `
            <div class="log-header">
                <div class="log-timestamp">${formatDateTime(log.timestamp)}</div>
                <div class="log-status ${statusClass}">${getStatusText(log.status)}</div>
            </div>
            <div class="log-message">${log.message}</div>
            <div class="log-task">任务: ${log.task_name} (ID: ${log.task_id})</div>
        `;

        logsContainer.appendChild(logItem);
    });
}

// 获取状态文本
function getStatusText(status) {
    return {
        'success': '成功',
        'failure': '失败',
        'running': '运行中'
    }[status] || status;
}

// 更新分页信息
function updatePagination(page, totalPages, totalCount) {
    currentPage = page;

    document.getElementById('page-info').textContent = `第 ${page} 页 (共 ${totalPages} 页, ${totalCount} 条记录)`;

    document.getElementById('prev-page').disabled = page <= 1;
    document.getElementById('next-page').disabled = page >= totalPages;
}

// 上一页
function goToPrevPage() {
    if (currentPage > 1) {
        currentPage--;
        loadLogs();
    }
}

// 下一页
function goToNextPage() {
    currentPage++;
    loadLogs();
}

// 清除所有日志
function clearAllLogs() {
    if (confirm('确定要清除所有日志吗？此操作不可恢复。')) {
        fetch('/api/logs', {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || '清除日志失败');
                });
            }
            return response.json();
        })
        .then(data => {
            showNotification('所有日志已清除', 'success');
            // 重新加载日志列表
            currentPage = 1;
            loadLogs();
        })
        .catch(error => {
            console.error('Error clearing logs:', error);
            showNotification(error.message || '清除日志失败', 'error');
        });
    }
}

// 显示日志详情
function showLogDetail(logId) {
    fetch(`/api/logs/${logId}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || '加载日志详情失败');
                });
            }
            return response.json();
        })
        .then(log => {
            const modal = document.getElementById('log-detail-modal');
            const content = document.getElementById('log-detail-content');

            // 状态样式
            const statusClass = {
                'success': 'status-success',
                'failure': 'status-failure',
                'running': 'status-running'
            }[log.status] || '';

            // 基本信息
            let html = `
                <div class="log-detail-section">
                    <h4>基本信息</h4>
                    <div class="detail-item">
                        <span class="detail-label">日志ID:</span>
                        <div class="detail-value">${log.id}</div>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">任务ID:</span>
                        <div class="detail-value">${log.task_id}</div>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">任务名称:</span>
                        <div class="detail-value">${log.task_name}</div>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">事件类型:</span>
                        <div class="detail-value">${log.event}</div>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">执行状态:</span>
                        <div class="detail-value">
                            <span class="log-status ${statusClass}">${getStatusText(log.status)}</span>
                        </div>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">执行时间:</span>
                        <div class="detail-value">${formatDateTime(log.timestamp)}</div>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">执行消息:</span>
                        <div class="detail-value">${log.message}</div>
                    </div>
                </div>
            `;

            // 详细信息
            if (log.details && Object.keys(log.details).length > 0) {
                html += `
                    <div class="log-detail-section">
                        <h4>详细信息</h4>
                `;

                // 如果是步骤日志，显示API调用详情
                if (log.event === 'step' && log.details) {
                    const details = log.details;

                    // 确保所有字段都有值，即使是undefined或null
                    const stepName = details.step_name || '';
                    const stepIndex = (details.step_index !== undefined ? details.step_index : 0) + 1;
                    const url = details.url || '';
                    const method = details.method || '';
                    const headers = details.headers ? JSON.stringify(details.headers, null, 2) : '{}';
                    const body = details.body ? JSON.stringify(details.body, null, 2) : '{}';
                    const statusCode = details.status_code || '';

                    html += `
                        <div class="detail-item">
                            <span class="detail-label">步骤名称:</span>
                            <div class="detail-value">${stepName}</div>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">步骤索引:</span>
                            <div class="detail-value">${stepIndex}</div>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">请求URL:</span>
                            <div class="detail-value">${url}</div>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">请求方法:</span>
                            <div class="detail-value">${method}</div>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">请求头:</span>
                            <div class="detail-value">${headers}</div>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">请求参数:</span>
                            <div class="detail-value">${body}</div>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">状态码:</span>
                            <div class="detail-value">${statusCode}</div>
                        </div>
                    `;

                    // 响应内容
                    if (details.response !== undefined && details.response !== null) {
                        const responseContent = typeof details.response === 'object' 
                            ? JSON.stringify(details.response, null, 2)
                            : details.response;

                        html += `
                            <div class="detail-item">
                                <span class="detail-label">响应内容:</span>
                                <div class="detail-value">${responseContent}</div>
                            </div>
                        `;
                    }

                    // 提取的参数
                    if (details.extracted_params !== undefined && details.extracted_params !== null && Object.keys(details.extracted_params).length > 0) {
                        html += `
                            <div class="detail-item">
                                <span class="detail-label">提取的参数:</span>
                                <div class="detail-value">${JSON.stringify(details.extracted_params, null, 2)}</div>
                            </div>
                        `;
                    }
                } else {
                    // 其他类型的日志详情
                    html += `
                        <div class="detail-item">
                            <span class="detail-label">详情:</span>
                            <div class="detail-value">${JSON.stringify(log.details, null, 2)}</div>
                        </div>
                    `;
                }

                html += `</div>`;
            }

            content.innerHTML = html;
            openModal(modal);
        })
        .catch(error => {
            console.error('Error loading log detail:', error);
            showNotification(error.message || '加载日志详情失败', 'error');
        });
}
