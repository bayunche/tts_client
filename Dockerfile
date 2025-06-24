# 使用官方Python运行时作为父镜像
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器中的/app
COPY . /app

# 安装所需的包
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 安装ffmpeg，pydub需要它来处理音频文件
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get -o Acquire::AllowInsecureRepositories=true \
            -o Acquire::AllowDowngradeToInsecureRepositories=true update && \
    apt-get install -y --allow-unauthenticated ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 暴露端口
EXPOSE 4552

# 定义环境变量
# 运行app.py
CMD ["python", "app.py"]