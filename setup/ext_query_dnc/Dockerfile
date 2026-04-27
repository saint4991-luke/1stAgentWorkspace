# 🦐 蝦米 Agent - Docker Image (Qdrant + UBIGPT 版本)
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY setup/ext_query_dnc/requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式程式碼（從 agent 目錄）
COPY agent/log_redirector.py .
COPY agent/retrieval_agent.py .
COPY agent/ubillm_client.py .
COPY agent/ubillm_embedding.py .
COPY agent/final_agent.py .

# 建立非 root 用戶（安全最佳實踐）
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/shared/logs /app/shared/prompts && \
    chown -R appuser:appuser /app/shared
USER appuser

# 暴露端口（從環境變數讀取，預設 22001）
EXPOSE 22001

# 健康檢查
HEALTHCHECK --interval=3600s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:22001/health || exit 1

# 啟動命令（retrieval_agent.py 內建 FastAPI app）
CMD ["python", "retrieval_agent.py"]

# 開發環境可改用：
# CMD ["uvicorn", "retrieval_agent:app", "--host", "0.0.0.0", "--port", "22001", "--reload"]