# Django Docker 环境构建提示词

## 📋 模板概述

基于现有成功的容器化配置，为 Django 项目生成完整的 Docker 环境构建方案，包括 Dockerfile、Docker Compose、以及相关依赖组件的配置。

## 🎯 核心原则

### 1. 基于现有成功配置
- 分析现有 Dockerfile、docker-compose.yml 和 docker-compose.dev.yml 的成功模式
- 提取通用的 Django 项目容器化配置模式
- 确保生成的配置经过验证和优化

### 2. 完整 Docker 环境构建方案
- **Dockerfile**：多阶段构建，优化镜像大小和安全性
- **Docker Compose**：生产环境和开发环境配置
- **依赖组件**：MySQL、Redis、Nginx 等完整配置
- **监控组件**：Flower、健康检查等

### 3. 环境分离设计
- **生产环境**：`docker-compose.yml` - 优化性能和安全性
- **开发环境**：`docker-compose.dev.yml` - 便于开发和调试

### 4. 服务架构模式
- **API 服务**：Django 应用主服务
- **Worker 服务**：Celery 异步任务处理
- **Scheduler 服务**：Celery Beat 定时任务
- **数据库服务**：MySQL/MariaDB
- **缓存服务**：Redis
- **Web 服务器**：Nginx（生产环境）
- **监控服务**：Flower（开发环境）

### 5. 容器命名规范
- **生产环境**：`[PROJECT_NAME]-[SERVICE_NAME]`（如：devify-api）
- **开发环境**：`[PROJECT_NAME]-[SERVICE_NAME]-dev`（如：devify-api-dev）
- **数据库**：`[PROJECT_NAME]-mariadb` / `[PROJECT_NAME]-mariadb-dev`
- **Redis**：`[PROJECT_NAME]-redis` / `[PROJECT_NAME]-redis-dev`

### 6. Entrypoint 差异
- **生产环境**：使用 `gunicorn` 命令启动生产级 WSGI 服务器
- **开发环境**：使用 `development` 命令启动开发服务器（通常包含 Django 开发服务器）

## 🔧 占位符系统

### 项目相关占位符
- `[PROJECT_NAME]`：项目名称（如：devify）
- `[PROJECT_DESCRIPTION]`：项目描述
- `[DJANGO_APP_NAME]`：Django 应用名称
- `[STATIC_FILES_PATH]`：静态文件路径
- `[MEDIA_FILES_PATH]`：媒体文件路径
- `[LOG_FILES_PATH]`：日志文件路径
- `[CACHE_PATH]`：缓存文件路径

### 端口配置占位符
- `[API_PORT]`：API 服务端口（默认：8000）
- `[NGINX_HTTP_PORT]`：Nginx HTTP 端口（默认：10080）
- `[NGINX_HTTPS_PORT]`：Nginx HTTPS 端口（默认：10443）
- `[FLOWER_PORT]`：Flower 监控端口（默认：5555）

### 数据库配置占位符
- `[DB_IMAGE]`：数据库镜像（默认：mariadb:11.6）
- `[DB_NAME]`：数据库名称
- `[DB_USER]`：数据库用户名
- `[DB_PASSWORD]`：数据库密码
- `[DB_ROOT_PASSWORD]`：数据库 root 密码

### 缓存配置占位符
- `[REDIS_IMAGE]`：Redis 镜像（默认：redis:alpine）
- `[REDIS_PASSWORD]`：Redis 密码（可选）

### 镜像配置占位符
- `[PROJECT_IMAGE]`：项目镜像名称
- `[REGISTRY_URL]`：镜像仓库地址（生产环境）
- `[USE_MIRROR]`：是否使用镜像源（开发环境：true，生产环境：false）

## 📁 完整 Docker 环境构建文件结构

### 1. Dockerfile 模板

```dockerfile
# 多阶段构建 Dockerfile
FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r [PROJECT_NAME] && useradd -r -g [PROJECT_NAME] [PROJECT_NAME]

# 设置工作目录
WORKDIR /opt/[PROJECT_NAME]

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY [DJANGO_APP_NAME]/ .

# 设置权限
RUN chown -R [PROJECT_NAME]:[PROJECT_NAME] /opt/[PROJECT_NAME]

# 切换到非 root 用户
USER [PROJECT_NAME]

# 复制 entrypoint 脚本
COPY docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 暴露端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn"]
```

### 2. Entrypoint 脚本模板

#### 生产环境 entrypoint.sh
```bash
#!/bin/bash
set -e

# 等待数据库就绪
wait_for_db() {
    echo "Waiting for database..."
    while ! nc -z mysql 3306; do
        sleep 1
    done
    echo "Database is ready!"
}

# 等待 Redis 就绪
wait_for_redis() {
    echo "Waiting for Redis..."
    while ! nc -z redis 6379; do
        sleep 1
    done
    echo "Redis is ready!"
}

# 数据库迁移
run_migrations() {
    echo "Running database migrations..."
    python manage.py migrate --noinput
}

# 收集静态文件
collect_static() {
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
}

# 根据命令执行不同操作
case "$1" in
    gunicorn)
        wait_for_db
        wait_for_redis
        run_migrations
        collect_static
        exec gunicorn --bind 0.0.0.0:8000 [PROJECT_NAME].wsgi:application
        ;;
    celery)
        wait_for_db
        wait_for_redis
        exec celery -A [PROJECT_NAME] worker --loglevel=info
        ;;
    celery-beat)
        wait_for_db
        wait_for_redis
        exec celery -A [PROJECT_NAME] beat --loglevel=info
        ;;
    development)
        wait_for_db
        wait_for_redis
        run_migrations
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    flower)
        wait_for_redis
        exec celery -A [PROJECT_NAME] flower
        ;;
    *)
        exec "$@"
        ;;
esac
```

### 3. 依赖组件配置

#### MySQL/MariaDB 配置
```yaml
mysql:
  image: [DB_IMAGE]
  container_name: [PROJECT_NAME]-mariadb
  restart: unless-stopped
  environment:
    MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    MYSQL_DATABASE: ${MYSQL_DATABASE}
    MYSQL_USER: ${MYSQL_USER}
    MYSQL_PASSWORD: ${MYSQL_PASSWORD}
  volumes:
    - ./docker/mysql/etc/my.cnf:/etc/mysql/my.cnf
    - ./docker/mysql/initdb.d:/docker-entrypoint-initdb.d
    - ./data/mysql/data:/var/lib/mysql
    - ./data/logs/mysql:/var/log/mysql
  networks:
    - [PROJECT_NAME]_network
  healthcheck:
    test: ["CMD", "mariadb-admin", "ping", "-h", "127.0.0.1", "-u", "root", "-p$MYSQL_ROOT_PASSWORD"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
```

#### Redis 配置
```yaml
redis:
  image: [REDIS_IMAGE]
  container_name: [PROJECT_NAME]-redis
  restart: unless-stopped
  command: redis-server --appendonly yes
  volumes:
    - ./data/redis:/data
    - ./data/logs/redis:/var/log/redis
  networks:
    - [PROJECT_NAME]_network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### Nginx 配置（生产环境）
```yaml
nginx:
  image: nginx:latest
  container_name: [PROJECT_NAME]-nginx
  restart: unless-stopped
  volumes:
    - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    - ./docker/nginx/certs:/certs
    - ./[STATIC_FILES_PATH]:/staticfiles:ro
    - ./data/logs/nginx:/var/log/nginx
  ports:
    - "${NGINX_HTTP_PORT:-[NGINX_HTTP_PORT]}:80"
    - "${NGINX_HTTPS_PORT:-[NGINX_HTTPS_PORT]}:443"
  networks:
    - [PROJECT_NAME]_network
  depends_on:
    [PROJECT_NAME]-api:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "nginx", "-t"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### Flower 配置（开发环境）
```yaml
flower:
  image: [PROJECT_IMAGE]:latest
  container_name: [PROJECT_NAME]-flower-dev
  restart: unless-stopped
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
  ports:
    - "${FLOWER_HOST_PORT:-[FLOWER_PORT]}:5555"
  depends_on:
    [PROJECT_NAME]-api:
      condition: service_started
    redis:
      condition: service_started
  command: flower
  networks:
    - [PROJECT_NAME]_network
```

### 5. 生产环境配置（docker-compose.yml）

```yaml
services:
  [PROJECT_NAME]-api:
    image: [REGISTRY_URL]/[PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-api
    restart: unless-stopped
    build:
      context: .
      dockerfile: Dockerfile
      args:
        USE_MIRROR: ${USE_MIRROR:-false}
    env_file:
      - ./.env
    volumes:
      - ./[STATIC_FILES_PATH]:/opt/[PROJECT_NAME]/core/staticfiles
      - ./[CACHE_PATH]:/opt/cache
      - ./[LOG_FILES_PATH]/api:/var/log/gunicorn
      - ./[DJANGO_APP_NAME]:/opt/[PROJECT_NAME]
      - ./[MEDIA_FILES_PATH]:/opt/[MEDIA_FILES_PATH]
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      - mysql
    command: gunicorn
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s

  [PROJECT_NAME]-worker:
    image: [REGISTRY_URL]/[PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-worker
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - ./[CACHE_PATH]:/opt/cache
      - ./[LOG_FILES_PATH]/worker:/var/log/celery
      - ./[DJANGO_APP_NAME]:/opt/[PROJECT_NAME]
      - ./[MEDIA_FILES_PATH]:/opt/[MEDIA_FILES_PATH]
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      [PROJECT_NAME]-api:
        condition: service_started
      mysql:
        condition: service_started
      redis:
        condition: service_started
    command: celery

  [PROJECT_NAME]-scheduler:
    image: [REGISTRY_URL]/[PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-scheduler
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - ./[LOG_FILES_PATH]/scheduler:/var/log/celery
      - ./[DJANGO_APP_NAME]:/opt/[PROJECT_NAME]
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      [PROJECT_NAME]-api:
        condition: service_started
      mysql:
        condition: service_started
      redis:
        condition: service_started
    command: celery-beat

  nginx:
    image: nginx:latest
    container_name: [PROJECT_NAME]-nginx
    restart: unless-stopped
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./docker/nginx/certs:/certs
      - ./[STATIC_FILES_PATH]:/staticfiles:ro
      - ./[LOG_FILES_PATH]/nginx:/var/log/nginx
    ports:
      - "${NGINX_HTTP_PORT:-[NGINX_HTTP_PORT]}:80"
      - "${NGINX_HTTPS_PORT:-[NGINX_HTTPS_PORT]}:443"
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      [PROJECT_NAME]-api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  mysql:
    image: [DB_IMAGE]
    container_name: [PROJECT_NAME]-mariadb
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - ./docker/mysql/etc/my.cnf:/etc/mysql/my.cnf
      - ./docker/mysql/initdb.d:/docker-entrypoint-initdb.d
      - ./[LOG_FILES_PATH]/mysql:/var/log/mysql
    networks:
      - [PROJECT_NAME]_network

  redis:
    image: [REDIS_IMAGE]
    container_name: [PROJECT_NAME]-redis
    restart: unless-stopped
    command: redis-server
    volumes:
      - ./[LOG_FILES_PATH]/redis:/var/log/redis
    networks:
      - [PROJECT_NAME]_network

networks:
  [PROJECT_NAME]_network:
    driver: bridge
```

### 6. 开发环境配置（docker-compose.dev.yml）

```yaml
services:
  [PROJECT_NAME]-api:
    image: [PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-api-dev
    restart: unless-stopped
    build:
      context: .
      dockerfile: Dockerfile
      args:
        USE_MIRROR: ${USE_MIRROR:-true}
    ports:
      - "${DJANGO_HOST_PORT:-[API_PORT]}:8000"
    env_file:
      - ./.env
    volumes:
      - ./[STATIC_FILES_PATH]:/opt/[PROJECT_NAME]/core/staticfiles
      - ./[LOG_FILES_PATH]/api:/var/log/gunicorn
      - ./[DJANGO_APP_NAME]:/opt/[PROJECT_NAME]
      - ./[MEDIA_FILES_PATH]:/opt/[MEDIA_FILES_PATH]
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      - mysql
    command: development
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s

  [PROJECT_NAME]-worker:
    image: [PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-worker-dev
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - ./[CACHE_PATH]:/opt/cache
      - ./[LOG_FILES_PATH]/worker:/var/log/celery
      - ./[DJANGO_APP_NAME]:/opt/[PROJECT_NAME]
      - ./[MEDIA_FILES_PATH]:/opt/[MEDIA_FILES_PATH]
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      [PROJECT_NAME]-api:
        condition: service_started
      mysql:
        condition: service_started
      redis:
        condition: service_started
    command: celery

  [PROJECT_NAME]-scheduler:
    image: [PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-scheduler-dev
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - ./[LOG_FILES_PATH]/scheduler:/var/log/celery
      - ./[DJANGO_APP_NAME]:/opt/[PROJECT_NAME]
    networks:
      - [PROJECT_NAME]_network
    depends_on:
      [PROJECT_NAME]-api:
        condition: service_started
      mysql:
        condition: service_started
      redis:
        condition: service_started
    command: celery-beat

  mysql:
    image: [DB_IMAGE]
    container_name: [PROJECT_NAME]-mariadb-dev
    restart: unless-stopped
    env_file:
      - ./.env
    volumes:
      - ./docker/mysql/etc/my.cnf:/etc/mysql/my.cnf
      - ./docker/mysql/initdb.d:/docker-entrypoint-initdb.d
      - ./docker/mysql/scripts:/opt/[PROJECT_NAME]/scripts
      - ./[LOG_FILES_PATH]/mysql:/var/log/mysql
    networks:
      - [PROJECT_NAME]_network

  redis:
    image: [REDIS_IMAGE]
    container_name: [PROJECT_NAME]-redis-dev
    restart: unless-stopped
    command: redis-server
    volumes:
      - ./[LOG_FILES_PATH]/redis:/var/log/redis
    networks:
      - [PROJECT_NAME]_network

  flower:
    image: [PROJECT_IMAGE]:latest
    container_name: [PROJECT_NAME]-flower-dev
    restart: unless-stopped
    env_file:
      - ./.env
    ports:
      - "${FLOWER_HOST_PORT:-[FLOWER_PORT]}:5555"
    depends_on:
      [PROJECT_NAME]-api:
        condition: service_started
      redis:
        condition: service_started
    command: flower
    networks:
      - [PROJECT_NAME]_network

networks:
  [PROJECT_NAME]_network:
    driver: bridge
```

### 7. 环境变量配置模板（.env.example）

```bash
# 项目配置
PROJECT_NAME=[PROJECT_NAME]
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-secret-key-here

# 数据库配置
DB_ENGINE=django.db.backends.mysql
MYSQL_DATABASE=[DB_NAME]
MYSQL_USER=[DB_USER]
MYSQL_PASSWORD=[DB_PASSWORD]
MYSQL_ROOT_PASSWORD=[DB_ROOT_PASSWORD]
MYSQL_HOST=mysql
MYSQL_PORT=3306

# Redis 配置
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# 端口配置
API_PORT=8000
NGINX_HTTP_PORT=10080
NGINX_HTTPS_PORT=10443
FLOWER_PORT=5555

# 镜像配置
PROJECT_IMAGE=[PROJECT_IMAGE]
REGISTRY_URL=[REGISTRY_URL]
USE_MIRROR=false

# 文件路径配置
STATIC_FILES_PATH=./data/django/staticfiles
MEDIA_FILES_PATH=./data/media
LOG_FILES_PATH=./data/logs
CACHE_PATH=./cache
```

### 8. Nginx 配置模板（docker/nginx/default.conf）

```nginx
upstream django {
    server [PROJECT_NAME]-api:8000;
}

server {
    listen 80;
    server_name localhost;

    # 静态文件
    location /static/ {
        alias /staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 媒体文件
    location /media/ {
        alias /opt/[MEDIA_FILES_PATH]/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API 请求
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # 健康检查
    location /health {
        proxy_pass http://django;
        access_log off;
    }
}
```

## 🔄 环境差异说明

### 生产环境特点
- 使用镜像仓库地址
- 包含 Nginx 反向代理
- 优化性能和安全性
- 不暴露内部端口
- 使用 `gunicorn` 命令
- 容器命名：`[PROJECT_NAME]-[SERVICE_NAME]`
- 数据库数据持久化到 `./data/mysql/data`

### 开发环境特点
- 使用本地镜像
- 暴露 API 端口便于调试
- 包含 Flower 监控界面
- 使用 `development` 命令
- 启用镜像源加速
- 容器命名：`[PROJECT_NAME]-[SERVICE_NAME]-dev`
- 数据库数据持久化到 `./data/mysql/data`
- 包含开发脚本目录挂载

### Entrypoint 命令差异

#### 生产环境命令
```yaml
command: gunicorn
# 等价于：gunicorn --bind 0.0.0.0:8000 [PROJECT_NAME].wsgi:application
```

#### 开发环境命令
```yaml
command: development
# 等价于：python manage.py runserver 0.0.0.0:8000
# 或者：gunicorn --reload --bind 0.0.0.0:8000 [PROJECT_NAME].wsgi:application
```

### 容器命名规范详解

#### 生产环境命名
- API 服务：`[PROJECT_NAME]-api`
- Worker 服务：`[PROJECT_NAME]-worker`
- Scheduler 服务：`[PROJECT_NAME]-scheduler`
- 数据库：`[PROJECT_NAME]-mariadb`
- Redis：`[PROJECT_NAME]-redis`
- Nginx：`[PROJECT_NAME]-nginx`

#### 开发环境命名
- API 服务：`[PROJECT_NAME]-api-dev`
- Worker 服务：`[PROJECT_NAME]-worker-dev`
- Scheduler 服务：`[PROJECT_NAME]-scheduler-dev`
- 数据库：`[PROJECT_NAME]-mariadb-dev`
- Redis：`[PROJECT_NAME]-redis-dev`
- Flower：`[PROJECT_NAME]-flower-dev`

## 📋 完整 Docker 环境构建检查清单

### 1. Dockerfile 检查
- [ ] 多阶段构建配置正确
- [ ] 非 root 用户创建
- [ ] 系统依赖安装完整
- [ ] Python 依赖安装正确
- [ ] 工作目录设置正确
- [ ] 权限设置合理
- [ ] Entrypoint 脚本复制和权限设置

### 2. Entrypoint 脚本检查
- [ ] 等待数据库就绪功能
- [ ] 等待 Redis 就绪功能
- [ ] 数据库迁移功能
- [ ] 静态文件收集功能
- [ ] 不同命令的处理逻辑
- [ ] 错误处理机制

### 3. 依赖组件检查
- [ ] MySQL/MariaDB 配置完整
- [ ] Redis 配置正确
- [ ] Nginx 配置（生产环境）
- [ ] Flower 配置（开发环境）
- [ ] 健康检查配置
- [ ] 数据持久化配置

### 4. 环境变量检查
- [ ] 项目配置变量
- [ ] 数据库连接变量
- [ ] Redis 连接变量
- [ ] 端口配置变量
- [ ] 镜像配置变量
- [ ] 文件路径配置变量

### 5. 网络配置检查
- [ ] 服务间网络通信正常
- [ ] 端口映射正确
- [ ] 健康检查配置合理
- [ ] 容器命名规范正确

### 6. 卷挂载检查
- [ ] 静态文件路径正确
- [ ] 媒体文件路径正确
- [ ] 日志文件路径正确
- [ ] 缓存文件路径正确
- [ ] 数据库数据持久化
- [ ] 配置文件挂载正确

## 🚀 使用指南

### 1. 替换占位符
根据项目实际情况替换所有占位符：
- 项目名称和描述
- 端口配置
- 文件路径
- 数据库配置
- 镜像配置

### 2. 环境变量配置
确保 `.env` 文件包含必要的环境变量：
- 数据库连接信息
- Redis 连接信息
- Django 配置
- 端口配置

### 3. 目录结构准备
确保以下目录结构存在：
```
project_root/
├── docker/
│   ├── entrypoint.sh
│   └── nginx/
│       └── default.conf
├── data/
│   ├── django/staticfiles/
│   ├── media/
│   ├── logs/
│   │   ├── api/
│   │   ├── worker/
│   │   ├── scheduler/
│   │   ├── mysql/
│   │   ├── redis/
│   │   └── nginx/
│   ├── mysql/data/
│   └── redis/
├── cache/
├── requirements.txt
├── .env
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── docker-compose.dev.yml
```

### 4. 启动服务
```bash
# 生产环境
docker-compose up -d

# 开发环境
docker-compose -f docker-compose.dev.yml up -d
```

## 🔧 自定义配置

### 添加新服务
- 在 `services` 部分添加新服务配置
- 配置服务依赖关系
- 添加必要的卷挂载和网络配置

### 修改端口配置
- 更新 `ports` 配置
- 确保端口不冲突
- 更新环境变量

### 调整资源限制
- 添加 `deploy` 配置
- 设置内存和 CPU 限制
- 配置重启策略

## 📝 注意事项

### 容器命名注意事项
- **生产环境**：容器名称简洁，便于管理和监控
- **开发环境**：添加 `-dev` 后缀，避免与生产环境冲突
- **数据库容器**：生产环境使用 `mariadb`，开发环境使用 `mariadb-dev`
- **服务发现**：容器名称用于服务间通信，确保命名一致性

### Entrypoint 脚本注意事项
- **生产环境**：使用 `gunicorn` 提供高性能 WSGI 服务
- **开发环境**：使用 `development` 命令启动 Django 开发服务器
- **日志级别**：生产环境使用 `info`，开发环境使用 `debug`
- **热重载**：开发环境支持代码变更自动重载
- **Flower 监控**：仅在开发环境提供，便于任务监控

### 安全考虑
- 生产环境不暴露内部端口
- 使用环境变量管理敏感信息
- 定期更新基础镜像
- 容器命名避免敏感信息泄露

### 性能优化
- 合理配置健康检查间隔
- 优化卷挂载性能
- 使用多阶段构建
- 生产环境使用 gunicorn 多进程模式

### 维护建议
- 定期备份数据库数据
- 监控日志文件大小
- 定期清理无用镜像
- 区分生产环境和开发环境的容器管理

## 🎯 模板优势

### 1. 完整性
- 包含 Dockerfile、Docker Compose、依赖组件等完整配置
- 支持生产环境和开发环境的不同需求
- 提供完整的监控和健康检查机制

### 2. 可复用性
- 基于占位符系统，支持不同项目快速适配
- 包含详细的替换指南和检查清单
- 支持多种项目架构和配置需求

### 3. 最佳实践
- 基于现有成功配置提取的模式
- 遵循 Docker 和 Django 的最佳实践
- 包含安全性和性能优化考虑

### 4. 易用性
- 提供完整的使用指南和示例
- 包含详细的检查清单和故障排除
- 支持快速上手和部署

这个模板基于现有成功的 Docker 环境配置，为 Django 项目提供了完整的 Docker 环境构建方案，支持生产环境和开发环境的不同需求，适用于新项目创建和现有项目优化。
