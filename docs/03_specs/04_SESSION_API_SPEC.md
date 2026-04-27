# 📦 Session API 規格書

**版本：** v1.0  
**日期：** 2026-04-16  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Session API 的端點定義與請求/回應格式
- Session 創建、查詢、刪除、Metadata 更新的技術規格

---

## 📋 概述

Session API 提供**通用的 Session 管理**功能，包括：
- 創建 Session
- 查詢 Session
- 刪除 Session
- 查詢消息歷史

**基礎 URL:** `http://localhost:8000`

**適用範圍：** 所有需要 Session 管理的端點（`/vh/sessions`、`/chat` 等）

---

## 📡 API 端點

### 1. 創建 Session

**POST** `/sessions`

**請求：**
```json
{
  "prefix": "vh",
  "metadata": {
    "persona_id": "ubichan",
    "vh_char_config": {
      "persona_id": "ubichan",
      "character_version": "v2.0"
    }
  }
}
```

**欄位說明：**
| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `prefix` | string | ❌ | Session ID 前綴（預設：`s`） |
| `metadata` | object | ❌ | Metadata 擴展（JSON 物件） |

**回應：**
```json
{
  "session_id": "vh_abc123",
  "prefix": "vh",
  "metadata": {
    "persona_id": "ubichan"
  },
  "created_at": "2026-04-16T08:00:00Z"
}
```

**錯誤回應：**
```json
{
  "error": "Failed to create session",
  "detail": "Database connection failed"
}
```

---

### 2. 查詢 Session

**GET** `/sessions/{session_id}`

**回應：**
```json
{
  "session_id": "vh_abc123",
  "metadata": {
    "persona_id": "ubichan",
    "vh_char_config": {
      "persona_id": "ubichan",
      "character_version": "v2.0"
    }
  },
  "created_at": "2026-04-16T08:00:00Z",
  "last_active": "2026-04-16T09:00:00Z"
}
```

**錯誤回應：**
```json
{
  "error": "Session not found",
  "session_id": "vh_abc123"
}
```

---

### 3. 刪除 Session

**DELETE** `/sessions/{session_id}`

**回應：**
```json
{
  "message": "Session deleted successfully",
  "session_id": "vh_abc123"
}
```

**錯誤回應：**
```json
{
  "error": "Session not found",
  "session_id": "vh_abc123"
}
```

---

### 4. 查詢消息歷史

**GET** `/sessions/{session_id}/messages`

**查詢參數：**
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `limit` | int | 50 | 最大消息數量 |
| `before` | timestamp | - | 查詢此時間之前的消息 |

**回應：**
```json
{
  "session_id": "vh_abc123",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "你好",
      "created_at": "2026-04-16T08:00:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "你好！我是優必醬。",
      "emotion": "neutral",
      "lang": "tw (zh)",
      "created_at": "2026-04-16T08:00:05Z"
    }
  ],
  "total": 2
}
```

---

## 🔐 認證與授權

目前**無需認證**。未來可扩展：
- API Key 認證
- JWT Token 認證

---

## 📊 速率限制

目前**無速率限制**。未來可扩展：
- 每 IP 每分鐘請求數限制
- 每 Session 每分鐘請求數限制

---

## 🗄️ 數據存儲

### SQLite 表結構

**sessions 表：**
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    metadata TEXT,                    -- JSON 字串
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**messages 表：**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,               -- 'user' 或 'assistant'
    content TEXT NOT NULL,
    emotion TEXT,                     -- 情緒標籤（可選）
    lang TEXT,                        -- 語言標籤（可選）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

---

## 🧪 測試範例

### cURL 測試

```bash
# 1. 創建 Session
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"prefix":"vh","metadata":{"persona_id":"ubichan"}}'

# 2. 查詢 Session
curl http://localhost:8000/sessions/vh_abc123

# 3. 查詢消息歷史
curl http://localhost:8000/sessions/vh_abc123/messages

# 4. 刪除 Session
curl -X DELETE http://localhost:8000/sessions/vh_abc123
```

### Python 測試

```python
import requests

BASE_URL = "http://localhost:8000"

# 創建 Session
response = requests.post(f"{BASE_URL}/sessions", json={
    "prefix": "vh",
    "metadata": {"persona_id": "ubichan"}
})
session_id = response.json()["session_id"]

# 查詢 Session
response = requests.get(f"{BASE_URL}/sessions/{session_id}")
print(response.json())

# 查詢消息歷史
response = requests.get(f"{BASE_URL}/sessions/{session_id}/messages")
print(response.json())

# 刪除 Session
response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
print(response.json())
```

---

## 📝 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0 | 2026-04-16 | 初始版本 |
