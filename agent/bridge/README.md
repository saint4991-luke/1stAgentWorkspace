# ExtQuery Bridge

Session + ext_query 整合服務 - 電話號碼查詢系統

## 功能

- **Session 管理**：追蹤用戶會話，支援連續對話
- **意圖判斷**：自動判斷用戶問題是否需要查詢資料庫
- **對話記錄**：保存所有對話歷史到 SQLite
- **SSE 串流**：即時返回回答內容

## 快速啟動

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設置環境變數

```bash
# Session 配置
export SESSION_DB_PATH=/data/sessions.db

# 用戶識別
export USER_ID_HEADER=X-User-ID

# 服務配置
export BRIDGE_HOST=0.0.0.0
export BRIDGE_PORT=3006

# ext_query 配置（與 ext_query/ 共用）
export UBILM_GRANT_URL=https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant
export UBILM_API_KEY=YOUR_API_KEY
export UBILM_LLM_MODEL=qwen3-8b-fp8
export UBILM_EMBED_MODEL=qwen3-embedding-4b
export QDRANT_HOST=140.227.187.126
export QDRANT_PORT=6334
export QDRANT_COLLECTION=default_kb_832887850831363957
export UBIGPT_FQDN=https://g.ubitus.ai/v1/chat/completions
export UBIGPT_AUTH_KEY=Bearer YOUR_AUTH_KEY
export UBIGPT_MODEL=llama-4-maverick-fp8
```

### 3. 啟動服務

```bash
python bridge.py
```

或使用 uvicorn：

```bash
uvicorn bridge:app --host 0.0.0.0 --port 3006
```

## API 端點

### POST /query

統一查詢入口（SSE 串流）

**請求：**

```bash
curl -X POST http://localhost:3006/query \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user123" \
  -d '{"query": "我要找遠藤和也"}'
```

**回應（SSE 串流）：**

```
event: status
data: {"status":"searching","message":"正在搜尋：遠藤和也"}

event: text_chunk
data: {"text":"找到結果："}

event: text_chunk
data: {"text":"管理本部 経営企画部 次長 遠藤和也"}

event: text_chunk
data: {"text":"內線番号：1121"}

event: done
data: {"session_id":"EXT_ABC123","answer_length":50}
```

### GET /session/{session_id}

獲取 Session 詳情

**請求：**

```bash
curl http://localhost:3006/session/EXT_ABC123
```

**回應：**

```json
{
  "session_id": "EXT_ABC123",
  "metadata": {"user_id": "user123"},
  "created_at": "2026-04-28T10:00:00",
  "last_active": "2026-04-28T10:05:00",
  "ttl_hours": 24,
  "message_count": 2,
  "messages": [
    {"role": "user", "content": "我要找遠藤和也"},
    {"role": "assistant", "content": "找到結果：..."}
  ]
}
```

### GET /sessions

獲取所有活躍 Session 列表

**請求：**

```bash
curl http://localhost:3006/sessions
```

### DELETE /session/{session_id}

刪除 Session

**請求：**

```bash
curl -X DELETE http://localhost:3006/session/EXT_ABC123
```

### GET /health

健康檢查

**請求：**

```bash
curl http://localhost:3006/health
```

**回應：**

```json
{
  "status": "ok",
  "modules": {
    "session": "ready",
    "ext_query": "ready"
  }
}
```

## 檔案結構

```
agent/bridge/
├── __init__.py           # 模組初始化
├── bridge.py             # 主程式
├── requirements.txt      # 依賴清單
└── README.md             # 本文件
```

## 依賴模組

- **session/** - Session 管理（SQLite 存儲）
- **ext_query/** - 電話號碼查詢服務
  - `retrieval_agent.py` - 意圖判斷 + 資料庫搜尋
  - `final_agent.py` - 最終回答生成

## 注意事項

1. **Session ID**：首次請求會自動創建 Session，並透過 Cookie 返回 `session_id`
2. **連續對話**：後續請求自動攜帶 Cookie，即可使用同一 Session
3. **TTL**：Session 預設 24 小時過期（可透過 `ttl_hours` 調整）
4. **日誌**：所有對話會記錄到 SQLite 資料庫（`SESSION_DB_PATH`）

## 開發筆記

### 測試 SSE 串流

```bash
curl -N http://localhost:3006/query \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user" \
  -d '{"query": "我要找遠藤和也"}'
```

### 測試 Session 管理

```bash
# 首次請求（創建新 Session）
SESSION_ID=$(curl -s -X POST http://localhost:3006/query \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user" \
  -d '{"query": "測試"}' \
  -c - | grep session_id | awk '{print $7}')

# 查看 Session 詳情
curl http://localhost:3006/session/$SESSION_ID

# 刪除 Session
curl -X DELETE http://localhost:3006/session/$SESSION_ID
```

## 參考文件

- [BRIDGE_DESIGN.md](../../docs/BRIDGE_DESIGN.md) - 完整設計文檔
- [session/README.md](../../session/README.md) - Session 模組文件
- [ext_query/README.md](../ext_query/README.md) - ext_query 模組文件
