FROM python:3.11-slim

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 套件
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製 Shared 模組（共享功能）
COPY agent/shared/ ./shared/

# 複製 Virtual Human Agent
COPY agent/virtual_human/ ./virtual_human/

# 複製 Backend Operator Agent
COPY agent/backend_operator/ ./backend_operator/

# 複製 Session 模組（獨立模組）
COPY session/ ./session/

# 複製 Frontend
COPY frontend/ ./frontend/

# 複製 Web UI app.py
COPY agent/app.py ./app.py

# UTF-8 環境
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# KNOWLEDGE 目錄
ENV KNOWLEDGE_BASE_PATH=/knowledge
RUN mkdir -p /knowledge && chmod 755 /knowledge

# 預設啟動 Backend Operator Agent（包含 VH Router）
CMD ["python", "backend_operator/api.py"]
