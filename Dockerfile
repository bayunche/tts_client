# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 设置国内 PyPI 源为默认
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 安装依赖之前先更新系统包管理器索引，并安装 ffmpeg
RUN echo "deb [trusted=yes] http://mirrors.aliyun.com/debian buster main contrib non-free" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://mirrors.aliyun.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://mirrors.aliyun.com/debian-security buster/updates main contrib non-free" >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 将当前目录内容复制到容器中的 /app
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口（根据你的服务监听的端口）
EXPOSE 4552

# 设置容器启动时默认执行的命令
CMD ["python", "app.py"]
