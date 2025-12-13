
// 任务管理页面JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初始化任务列表
    loadTasks();

    // 绑定事件
    document.getElementById('add-task-btn').addEventListener('click', showAddTaskModal);
    document.getElementById('cancel-btn').addEventListener('click', hideTaskModal);
    document.getElementById('task-form').addEventListener('submit', saveTask);
    document.getElementById('add-step-btn').addEventListener('click', addStep);

    // 任务类型切换
    document.querySelectorAll('input[name="type"]').forEach(radio => {
        radio.addEventListener('change', toggleTaskType);
    });

    // Cron预设选择
    document.getElementById('cron-preset').addEventListener('change', function() {
        if (this.value) {
            document.getElementById('cron-expression').value = this.value;
        }
    });

    // 初始化第一个步骤
    if (document.getElementById('steps-container').children.length === 0) {
        addStep();
    }
});

// 加载任务列表
function loadTasks() {
    fetch('/api/tasks')
        .then(response => response.json())
        .then(tasks => {
            const tbody = document.getElementById('tasks-tbody');
            tbody.innerHTML = '';

            if (tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">暂无任务</td></tr>';
                return;
            }

            tasks.forEach(task => {
                const row = document.createElement('tr');

                // 状态样式
                let statusClass = '';
                let statusText = '';

                switch(task.status) {
                    case 'active':
                        statusClass = 'status-active';
                        statusText = '运行中';
                        break;
                    case 'paused':
                        statusClass = 'status-paused';
                        statusText = '已暂停';
                        break;
                    case 'deleted':
                        statusClass = 'status-deleted';
                        statusText = '已删除';
                        break;
                }

                // 调度规则显示
                let scheduleText = '';
                if (task.type === 'cron') {
                    scheduleText = task.cron_expression;
                } else {
                    scheduleText = `每 ${task.interval_seconds} 秒`;
                }

                row.innerHTML = `
                    <td>${task.id}</td>
                    <td>${task.name}</td>
                    <td>${task.type === 'cron' ? '定时任务' : '循环任务'}</td>
                    <td>${scheduleText}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td>${formatDateTime(task.created_at)}</td>
                    <td class="task-actions">
                        ${task.status === 'active' ? 
                            `<button class="btn btn-secondary btn-sm" onclick="pauseTask(${task.id})">暂停</button>` :
                            `<button class="btn btn-secondary btn-sm" onclick="resumeTask(${task.id})">恢复</button>`
                        }
                        <button class="btn btn-secondary btn-sm" onclick="runTaskNow(${task.id})">立即执行</button>
                        <button class="btn btn-primary btn-sm" onclick="editTask(${task.id})">编辑</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteTask(${task.id})">删除</button>
                    </td>
                `;

                tbody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading tasks:', error);
            showNotification('加载任务列表失败', 'error');
        });
}

// 显示添加任务模态框
function showAddTaskModal() {
    document.getElementById('modal-title').textContent = '创建新任务';
    document.getElementById('task-form').reset();
    document.getElementById('task-form').setAttribute('data-task-id', '');

    // 重置步骤容器
    const stepsContainer = document.getElementById('steps-container');
    stepsContainer.innerHTML = '';
    addStep();

    // 显示Cron配置，隐藏间隔配置
    document.getElementById('cron-config').style.display = 'block';
    document.getElementById('interval-config').style.display = 'none';

    openModal(document.getElementById('task-modal'));
}

// 显示编辑任务模态框
function editTask(taskId) {
    fetch(`/api/tasks/${taskId}`)
        .then(response => response.json())
        .then(task => {
            document.getElementById('modal-title').textContent = '编辑任务';
            document.getElementById('task-form').setAttribute('data-task-id', taskId);

            // 填充表单
            document.getElementById('task-name').value = task.name;
            document.querySelector(`input[name="type"][value="${task.type}"]`).checked = true;

            if (task.type === 'cron') {
                document.getElementById('cron-expression').value = task.cron_expression;
            } else {
                document.getElementById('interval-seconds').value = task.interval_seconds;
            }

            document.getElementById('retry-times').value = task.retry_times;

            // 切换任务类型显示
            toggleTaskType();

            // 加载步骤
            const stepsContainer = document.getElementById('steps-container');
            stepsContainer.innerHTML = '';

            if (task.steps && task.steps.length > 0) {
                task.steps.forEach(step => {
                    const stepElement = addStep();

                    // 填充步骤数据
                    stepElement.querySelector('.step-name').value = step.name || '';
                    stepElement.querySelector('.step-method').value = step.method || 'GET';
                    stepElement.querySelector('.step-url').value = step.url || '';

                    // 确保请求头和请求体中的引用值被正确保留
                    // 特别注意处理像 "Authorization": "Bearer ${token}" 这样的引用
                    const headers = step.headers || {};
                    const body = step.body || {};

                    // 记录原始数据，便于调试
                    console.log(`步骤 ${step.name || ''} 原始数据:`, { headers, body });

                    stepElement.querySelector('.step-headers').value = JSON.stringify(headers, null, 2);
                    stepElement.querySelector('.step-body').value = JSON.stringify(body, null, 2);

                    // 记录填充后的数据，便于调试
                    const headersValue = stepElement.querySelector('.step-headers').value;
                    const bodyValue = stepElement.querySelector('.step-body').value;

                    console.log(`步骤 ${step.name || ''} 填充后的数据:`, {
                        headersValue,
                        bodyValue
                    });

                    // 检查请求头中是否有token引用
                    if (headersValue.includes('${token}')) {
                        console.log(`步骤 ${step.name || ''} 请求头中包含token引用，将在执行时被替换`);
                    } else if (headersValue.includes('Authorization') && headersValue.includes('Bearer')) {
                        console.log(`步骤 ${step.name || ''} 请求头中包含Bearer token`);
                    }

                    // 加载提取参数配置
                    if (step.extract_params && step.extract_params.length > 0) {
                        const extractParamsContainer = stepElement.querySelector('.extract-params-container');
                        extractParamsContainer.innerHTML = '';

                        step.extract_params.forEach(param => {
                            const paramElement = addExtractParam(extractParamsContainer);
                            paramElement.querySelector('.param-name').value = param.name || '';
                            paramElement.querySelector('.param-path').value = param.path || '';
                            paramElement.querySelector('.param-type').value = param.type || 'string';
                        });
                    }

                    // 更新Curl命令预览
                    updateCurlPreview(stepElement);
                });
            } else {
                addStep();
            }

            openModal(document.getElementById('task-modal'));
        })
        .catch(error => {
            console.error('Error loading task:', error);
            showNotification('加载任务详情失败', 'error');
        });
}

// 隐藏任务模态框
function hideTaskModal() {
    closeModal(document.getElementById('task-modal'));
}

// 切换任务类型
function toggleTaskType() {
    const taskType = document.querySelector('input[name="type"]:checked').value;

    if (taskType === 'cron') {
        document.getElementById('cron-config').style.display = 'block';
        document.getElementById('interval-config').style.display = 'none';
    } else {
        document.getElementById('cron-config').style.display = 'none';
        document.getElementById('interval-config').style.display = 'block';
    }
}

// 添加步骤
function addStep() {
    const stepsContainer = document.getElementById('steps-container');
    const stepTemplate = document.getElementById('step-template');
    const stepElement = stepTemplate.content.cloneNode(true).querySelector('.step-config');

    // 设置步骤编号
    const stepNumber = stepsContainer.children.length + 1;
    stepElement.querySelector('.step-number').textContent = stepNumber;

    // 添加删除步骤事件
    stepElement.querySelector('.remove-step-btn').addEventListener('click', function() {
        if (stepsContainer.children.length > 1) {
            stepsContainer.removeChild(stepElement);
            updateStepNumbers();
        } else {
            showNotification('至少需要保留一个步骤', 'warning');
        }
    });

    // 添加表单变化事件
    stepElement.querySelectorAll('input, select, textarea').forEach(element => {
        element.addEventListener('input', function() {
            updateCurlPreview(stepElement);
        });
        element.addEventListener('change', function() {
            updateCurlPreview(stepElement);
        });
    });

    // 添加参数事件
    stepElement.querySelector('.add-param-btn').addEventListener('click', function() {
        const container = stepElement.querySelector('.extract-params-container');
        addExtractParam(container);
    });

    // 初始化参数
    const extractParamsContainer = stepElement.querySelector('.extract-params-container');
    addExtractParam(extractParamsContainer);

    // 添加到DOM
    stepsContainer.appendChild(stepElement);

    // 更新Curl命令预览
    updateCurlPreview(stepElement);

    return stepElement;
}

// 添加提取参数
function addExtractParam(container) {
    const paramElement = document.createElement('div');
    paramElement.className = 'extract-param';

    paramElement.innerHTML = `
        <input type="text" class="param-name" placeholder="参数名">
        <input type="text" class="param-path" placeholder="JSON路径，如 $.data.id">
        <select class="param-type">
            <option value="string">字符串</option>
            <option value="number">数字</option>
            <option value="boolean">布尔值</option>
        </select>
        <button type="button" class="remove-param-btn btn btn-danger">删除</button>
    `;

    // 添加删除参数事件
    paramElement.querySelector('.remove-param-btn').addEventListener('click', function() {
        const paramsContainer = paramElement.parentNode;
        if (paramsContainer.children.length > 1) {
            paramsContainer.removeChild(paramElement);
        } else {
            showNotification('至少需要保留一个参数配置', 'warning');
        }
    });

    // 添加变化事件，更新Curl预览
    paramElement.querySelectorAll('input, select').forEach(element => {
        element.addEventListener('input', function() {
            updateCurlPreview(container.closest('.step-config'));
        });
        element.addEventListener('change', function() {
            updateCurlPreview(container.closest('.step-config'));
        });
    });

    container.appendChild(paramElement);

    return paramElement;
}

// 更新步骤编号
function updateStepNumbers() {
    const stepsContainer = document.getElementById('steps-container');
    const steps = stepsContainer.querySelectorAll('.step-config');

    steps.forEach((step, index) => {
        step.querySelector('.step-number').textContent = index + 1;
    });
}

// 更新Curl命令预览
function updateCurlPreview(stepElement) {
    const method = stepElement.querySelector('.step-method').value;
    const url = stepElement.querySelector('.step-url').value;

    let headers = '';
    try {
        const headersObj = JSON.parse(stepElement.querySelector('.step-headers').value || '{}');
        headers = Object.entries(headersObj)
            .map(([key, value]) => ` -H "${key}: ${value}"`)
            .join('');
    } catch (e) {
        // 忽略JSON解析错误
    }

    let body = '';
    if (method !== 'GET') {
        try {
            const bodyObj = JSON.parse(stepElement.querySelector('.step-body').value || '{}');
            body = ` -d '${JSON.stringify(bodyObj)}'`;
        } catch (e) {
            // 忽略JSON解析错误
        }
    }

    const curlCommand = `curl -X ${method}"${url}"${headers}${body}`;
    stepElement.querySelector('.curl-preview').value = curlCommand;
}

// 收集步骤数据
function collectStepsData() {
    const steps = [];
    const stepElements = document.querySelectorAll('#steps-container .step-config');

    stepElements.forEach(stepElement => {
        const step = {
            name: stepElement.querySelector('.step-name').value,
            method: stepElement.querySelector('.step-method').value,
            url: stepElement.querySelector('.step-url').value,
            extract_params: []
        };

        // 解析请求头
        try {
            step.headers = JSON.parse(stepElement.querySelector('.step-headers').value || '{}');
        } catch (e) {
            step.headers = {};
        }

        // 解析请求体
        if (step.method !== 'GET') {
            try {
                step.body = JSON.parse(stepElement.querySelector('.step-body').value || '{}');
            } catch (e) {
                step.body = {};
            }
        }

        // 收集提取参数
        const paramElements = stepElement.querySelectorAll('.extract-param');
        paramElements.forEach(paramElement => {
            const name = paramElement.querySelector('.param-name').value;
            const path = paramElement.querySelector('.param-path').value;
            const type = paramElement.querySelector('.param-type').value;

            if (name && path) {
                step.extract_params.push({
                    name,
                    path,
                    type
                });
            }
        });

        steps.push(step);
    });

    return steps;
}

// 保存任务
function saveTask(e) {
    e.preventDefault();

    const taskId = document.getElementById('task-form').getAttribute('data-task-id');
    const taskType = document.querySelector('input[name="type"]:checked').value;

    // 收集表单数据
    const taskData = {
        name: document.getElementById('task-name').value,
        type: taskType,
        retry_times: parseInt(document.getElementById('retry-times').value),
        steps: collectStepsData()
    };

    // 根据任务类型添加特定字段
    if (taskType === 'cron') {
        taskData.cron_expression = document.getElementById('cron-expression').value;
    } else {
        taskData.interval_seconds = parseInt(document.getElementById('interval-seconds').value);
    }

    // 发送请求
    const url = taskId ? `/api/tasks/${taskId}` : '/api/tasks';
    const method = taskId ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(taskData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '操作失败');
            });
        }
        return response.json();
    })
    .then(data => {
        showNotification(taskId ? '任务更新成功' : '任务创建成功', 'success');
        hideTaskModal();
        loadTasks();
    })
    .catch(error => {
        console.error('Error saving task:', error);
        showNotification('保存任务失败', 'error');
    });
}

// 暂停任务
function pauseTask(taskId) {
    fetch(`/api/tasks/${taskId}/pause`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '操作失败');
            });
        }
        return response.json();
    })
    .then(data => {
        showNotification('任务已暂停', 'success');
        loadTasks();
    })
    .catch(error => {
        console.error('Error pausing task:', error);
        showNotification(error.message || '暂停任务失败', 'error');
    });
}

// 恢复任务
function resumeTask(taskId) {
    fetch(`/api/tasks/${taskId}/resume`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '操作失败');
            });
        }
        return response.json();
    })
    .then(data => {
        showNotification('任务已恢复', 'success');
        loadTasks();
    })
    .catch(error => {
        console.error('Error resuming task:', error);
        showNotification(error.message || '恢复任务失败', 'error');
    });
}

// 立即执行任务
function runTaskNow(taskId) {
    fetch(`/api/tasks/${taskId}/run`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '操作失败');
            });
        }
        return response.json();
    })
    .then(data => {
        showNotification('任务已提交执行', 'success');
    })
    .catch(error => {
        console.error('Error running task:', error);
        showNotification(error.message || '执行任务失败', 'error');
    });
}

// 删除任务
function deleteTask(taskId) {
    confirmAction('确定要删除这个任务吗？此操作不可恢复。', function() {
        fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('任务已删除', 'success');
                loadTasks();
            } else {
                showNotification(data.message || '操作失败', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting task:', error);
            showNotification('删除任务失败', 'error');
        });
    });
}
