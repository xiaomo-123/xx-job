
# XX-Job 任务定时执行器

XX-Job 是一个简单易用的 Web 可视化任务定时执行器，支持 API 调用、链式执行、定时调度等功能。

## 功能特点

- **开箱即用**：无需配置数据库，所有数据本地文件保存，运行即用。
- **可视化配置**：通过表单直观配置任务，支持 Cron 表达式和循环执行。
- **API 链式调用**：支持多步 API 链式调用，参数自动传递，容错处理。
- **执行日志**：详细记录任务执行过程，包括请求响应、参数提取等。
- **Docker 支持**：提供 Docker 部署方案，一键启动。

## 项目结构

```
xx-job/
│── app.py                 # 主程序入口
│── requirements.txt       # 项目依赖
│── Dockerfile             # Docker镜像构建文件
│── docker-compose.yml     # Docker Compose配置
│── README.md              # 项目说明文档
│
├── static/                # 静态文件目录
│   ├── css/
│   │   └── style.css      # 样式文件
│   └── js/
│       └── main.js        # JavaScript文件
│
├── templates/             # HTML模板目录
│   ├── index.html         # 主页面
│   ├── tasks.html         # 任务列表页面
│   └── logs.html          # 日志查看页面
│
└── core/                  # 核心模块目录
    ├── scheduler.py       # 定时任务调度器
    ├── storage.py         # 数据存储模块
    ├── api_client.py      # API调用模块
    └── logger.py          # 日志管理模块
```

## 核心模块说明

- **Web 服务**：基于 Flask 框架，提供 Web 界面和 API 接口。
- **定时任务调度**：基于 APScheduler，支持 Cron 表达式和间隔执行。
- **API 调用**：基于 requests 库，支持 GET/POST 请求，支持参数提取和传递。
- **数据存储**：基于 JSON 文件，存储任务配置和执行日志。
- **日志管理**：记录任务执行过程，包括请求响应、参数提取等。

## 本地运行

1. 克隆项目：
   ```
   git clone <项目地址>
   cd xx-job
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 运行程序：
   ```
   python app.py
   ```

4. 程序启动后会自动打开浏览器访问 http://localhost:8080

## Docker 部署

1. 构建并启动容器：
   ```
   docker-compose up -d
   ```

2. 访问 http://localhost:8080

## 使用说明

### 创建任务

1. 访问任务管理页面
2. 点击"创建新任务"
3. 填写任务基本信息：
   - 任务名称
   - 任务类型（定时任务/循环任务）
   - 调度规则（Cron表达式或执行间隔）
   - 失败重试次数

4. 配置API步骤：
   - 添加步骤：设置请求方法、URL、请求头、请求体
   - 参数提取：设置需要从响应中提取的参数
   - 链式调用：后续步骤可以使用前面步骤提取的参数

5. 保存任务，任务将自动按配置规则执行

### 查看日志

1. 访问日志查看页面
2. 可以按任务和状态筛选日志
3. 点击日志项查看详细信息，包括：
   - 请求URL、方法、参数
   - 响应状态码、内容
   - 参数提取过程
   - 错误信息（如果有）

### 任务管理

- 暂停/恢复任务
- 立即执行任务
- 编辑任务配置
- 删除任务

## 技术栈

- 后端：Python、Flask、APScheduler、requests
- 前端：HTML、CSS、JavaScript（原生）
- 数据存储：JSON文件
- 部署：Docker、Docker Compose

## 注意事项

- 所有数据存储在本地文件中，请定期备份 data 目录
- 任务执行时间精度取决于系统负载和调度器配置
- API 调用超时时间为 30 秒，可根据需要调整
