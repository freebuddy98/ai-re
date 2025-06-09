# 使用一个标准的、轻量的Python镜像
FROM python:3.10-slim

# 设置环境变量
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

# 设置工作目录
WORKDIR /app

# [安全实践] 创建一个非root用户来运行应用
RUN useradd --create-home --shell /bin/bash appuser

# 将所有共享库 和 服务的代码复制到镜像中
# 注意：源路径是相对于构建上下文（项目根目录）的
COPY --chown=appuser:appuser ./libs /app/libs
COPY --chown=appuser:appuser ./services/input-service/src/ /app/input-service
COPY --chown=appuser:appuser ./services/input-service/requirements.txt /app/

# 复制配置文件
COPY --chown=appuser:appuser ./config /app/config

USER appuser

# 暴露端口
EXPOSE 8000

# 容器启动时运行的命令
CMD ["python", "-m", "input-service.main"] 