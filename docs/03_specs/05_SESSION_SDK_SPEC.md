# 📦 Session SDK 函數規格

**版本：** v1.0  
**日期：** 2026-04-09  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Session SDK 的函數接口與使用方式
- Python 嵌入式 SDK 的技術規格

---

## 📋 概述

Session SDK 提供**兩種操作模式**：

| 模式 | 使用場景 | 調用方式 |
|------|----------|----------|
| **HTTP API** | 獨立服務、遠程調用 | REST API |
| **函數 SDK** | 嵌入 Agent、本地調用 | Python 函數 |

本文件定義**函數 SDK** 的規格。HTTP API 規格見 `03_SESSION_API_SPEC.md`。

---

## 🏗️ 架構設計

```
┌─────────────────────────────────────────────────────────┐
│                    調用層 (Caller)                       │
│                                                         │
│  - Virtual Human API (`/vh/sessions`)                   │
│  - Agent API (`/chat`)                                  │
│  - Web UI 後端                                          │
└─────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   HTTP API 模式   │                  │   函數 SDK 模式   │
│  (獨立服務)       │                  │  (嵌入庫)        │
│  Port: 8000      │                  │  Python Import   │
│                  │                  │                  │
│ REST 端點         │                  │ SessionStore 類   │
│ - POST /sessions │                  │ - create_session()│
│ - GET /sessions  │                  │ - get_session()  │
│ - DELETE /sess  │                  │ - add_message()  │
└──────────────────┘                  └──────────────────┘
        ↓                                       ↓
┌─────────────────────────────────────────────────────────┐
│                    存儲層 (Storage)                      │
│                                                         │
│  - SQLite (`/data/sessions.db`)                         │
│  - 可擴展：Redis、PostgreSQL                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📐 數據模型

### Session 表結構

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,      -- 格式：{PREFIX}_{uuid}
    metadata TEXT,                    -- JSON 字串（可選）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_hours INTEGER DEFAULT 1
);
```

### Messages 表結構

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,          -- 'user' 或 'assistant'
    content TEXT NOT NULL,
    emotion TEXT,                -- 情緒標籤（可選）
    lang TEXT,                   -- 語言標籤（可選）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

---

## 🔧 SessionStore 類

### 初始化

```python
from session_module import SessionStore

store = SessionStore(db_path='/data/sessions.db')
```

| 參數 | 類型 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `db_path` | str | ❌ | `/data/sessions.db` | SQLite 數據庫路徑 |

---

### create_session()

創建新 Session。

```python
def create_session(
    prefix: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ttl_hours: int = 1
) -> Dict[str, Any]
```

| 參數 | 類型 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `prefix` | str | ❌ | `None` | Session ID 前綴（用於生成 ID，不存儲） |
| `metadata` | dict | ❌ | `None` | Metadata 字典（存儲為 JSON） |
| `ttl_hours` | int | ❌ | `1` | Session 存活時間（小時） |

**返回值：**
```python
{
    'session_id': 'UBICHAN_A1B2C3D4E5F6',
    'metadata': {'vh_char_config': {...}},
    'created_at': '2026-04-09T07:00:00',
    'last_active': '2026-04-09T07:00:00',
    'ttl_hours': 24
}
```

**Session ID 生成規則：**
- 格式：`{PREFIX}_{uuid}`（12 碼大寫 hex）
- 如果 `prefix` 為空，使用 `GENERAL`
- 範例：
  - `prefix="ubichan"` → `UBICHAN_A1B2C3D4E5F6`
  - `prefix=None` → `GENERAL_B2C3D4E5F6G7`

**使用範例：**
```python
# 創建虛擬人 Session
session = store.create_session(
    prefix='ubichan',
    metadata={
        'vh_char_config': {
            'persona_id': 'ubichan',
            'character_version': 'v2.0'
        }
    },
    ttl_hours=24
)
print(session['session_id'])  # UBICHAN_xxx

# 創建一般 Session
session = store.create_session(ttl_hours=1)
print(session['session_id'])  # GENERAL_xxx
```

---

### get_session()

獲取 Session 詳情（包含 messages）。

```python
def get_session(session_id: str) -> Optional[Dict[str, Any]]
```

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `session_id` | str | ✅ | Session ID |

**返回值：**
- 成功：`Dict[str, Any]`（Session 詳情）
- 失敗：`None`（Session 不存在）

**返回結構：**
```python
{
    'session_id': 'UBICHAN_A1B2C3D4E5F6',
    'metadata': {'vh_char_config': {...}},
    'created_at': '2026-04-09T07:00:00',
    'last_active': '2026-04-09T07:05:00',
    'ttl_hours': 24,
    'messages': [
        {'role': 'user', 'content': '你好', 'emotion': None, 'lang': None},
        {'role': 'assistant', 'content': '你好！', 'emotion': 'happy', 'lang': 'tw (zh)'}
    ]
}
```

**使用範例：**
```python
session = store.get_session('UBICHAN_A1B2C3D4E5F6')
if session:
    print(f"Messages: {len(session['messages'])}")
else:
    print("Session 不存在")
```

---

### list_sessions()

獲取所有活躍 Session 列表。

```python
def list_sessions() -> List[Dict[str, Any]]
```

**返回值：** Session 列表（按 `last_active` 降序）

**返回結構：**
```python
[
    {
        'session_id': 'UBICHAN_A1B2C3D4E5F6',
        'created_at': '2026-04-09T07:00:00',
        'last_active': '2026-04-09T07:05:00',
        'ttl_hours': 24,
        'metadata': {...},
        'message_count': 5
    },
    # ...
]
```

**使用範例：**
```python
sessions = store.list_sessions()
print(f"活躍 Session 數量：{len(sessions)}")
```

---

### delete_session()

刪除 Session 及其所有 messages。

```python
def delete_session(session_id: str) -> bool
```

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `session_id` | str | ✅ | Session ID |

**返回值：**
- `True`：刪除成功
- `False`：Session 不存在

**使用範例：**
```python
success = store.delete_session('UBICHAN_A1B2C3D4E5F6')
if success:
    print("刪除成功")
```

---

### get_messages()

獲取 Session 的消息歷史。

```python
def get_messages(session_id: str) -> List[Dict[str, Any]]
```

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `session_id` | str | ✅ | Session ID |

**返回值：** 消息列表（按 `created_at` 升序）

**返回結構：**
```python
[
    {
        'id': 1,
        'role': 'user',
        'content': '你好',
        'emotion': None,
        'lang': None,
        'created_at': '2026-04-09T07:00:00'
    },
    {
        'id': 2,
        'role': 'assistant',
        'content': '你好！有什麼可以幫你？',
        'emotion': 'happy',
        'lang': 'tw (zh)',
        'created_at': '2026-04-09T07:00:01'
    }
]
```

**使用範例：**
```python
messages = store.get_messages('UBICHAN_A1B2C3D4E5F6')
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

---

### add_message()

添加消息到 Session。

```python
def add_message(
    session_id: str,
    role: str,
    content: str,
    emotion: Optional[str] = None,
    lang: Optional[str] = None
) -> bool
```

| 參數 | 類型 | 必填 | 預設 | 說明 |
|------|------|------|------|------|
| `session_id` | str | ✅ | — | Session ID |
| `role` | str | ✅ | — | `'user'` 或 `'assistant'` |
| `content` | str | ✅ | — | 消息內容 |
| `emotion` | str | ❌ | `None` | 情緒標籤（如 `happy`, `sad`） |
| `lang` | str | ❌ | `None` | 語言標籤（如 `tw (zh)`, `en`） |

**返回值：**
- `True`：添加成功
- `False`：Session 不存在

**使用範例：**
```python
# 添加用戶消息
store.add_message(session_id, 'user', '你好')

# 添加助手消息（帶情緒和語言）
store.add_message(
    session_id,
    'assistant',
    '你好！有什麼可以幫你？',
    emotion='happy',
    lang='tw (zh)'
)
```

---

### cleanup_expired()

清理過期的 Session。

```python
def cleanup_expired() -> int
```

**返回值：** 清理的 Session 數量

**使用範例：**
```python
count = store.cleanup_expired()
print(f"清理了 {count} 個過期 Session")
```

**背景任務：**
```python
import asyncio

async def cleanup_task(store: SessionStore, interval_hours: int = 1):
    while True:
        await asyncio.sleep(interval_hours * 3600)
        store.cleanup_expired()
```

---

## 📝 Metadata 設計

### 命名空間模式

使用命名空間避免衝突：

```python
metadata={
    'vh_char_config': {
        'persona_id': 'ubichan',
        'character_version': 'v2.0'
    },
    'game_state': {
        'level': 5,
        'score': 1000
    },
    'analytics': {
        'source': 'web',
        'campaign': 'spring2026'
    }
}
```

### 常見命名空間

| 命名空間 | 說明 | 使用場景 |
|----------|------|----------|
| `vh_char_config` | 虛擬人配置 | `/vh/*` 端點 |
| `game_state` | 遊戲狀態 | 遊戲模組 |
| `analytics` | 分析數據 | 追蹤來源 |

---

## 🔀 兩種模式對比

| 層面 | HTTP API | 函數 SDK |
|------|----------|----------|
| **調用方式** | REST API (`curl`, `requests`) | Python 函數 (`SessionStore`) |
| **部署** | 獨立服務（Docker） | 嵌入庫（import） |
| **網絡** | 需要網絡連接 | 本地調用 |
| **性能** | 網絡延遲 | 直接調用（快速） |
| **使用場景** | 微服務架構 | 單體應用、測試 |

---

## 📋 使用範例

### 完整流程（函數 SDK）

```python
from session_module import SessionStore

# 1. 初始化
store = SessionStore('/data/sessions.db')

# 2. 創建 Session
session = store.create_session(
    prefix='ubichan',
    metadata={'vh_char_config': {'persona_id': 'ubichan'}},
    ttl_hours=24
)
session_id = session['session_id']

# 3. 添加用戶消息
store.add_message(session_id, 'user', '優必達有什麼產品？')

# 4. （調用 LLM...）

# 5. 添加助手消息
store.add_message(
    session_id,
    'assistant',
    '優必達的產品包括...',
    emotion='happy',
    lang='tw (zh)'
)

# 6. 獲取完整對話
session = store.get_session(session_id)
for msg in session['messages']:
    print(f"{msg['role']}: {msg['content']}")
```

### 完整流程（HTTP API）

```bash
# 1. 創建 Session
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "prefix": "ubichan",
    "metadata": {"vh_char_config": {"persona_id": "ubichan"}},
    "ttl_hours": 24
  }'

# 2. 添加用戶消息
curl -X POST http://localhost:8000/sessions/UBICHAN_xxx/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "優必達有什麼產品？"}'

# 3. 獲取對話
curl http://localhost:8000/sessions/UBICHAN_xxx
```

---

## ⚠️ 注意事項

### 1. Session ID 格式

- 格式：`{PREFIX}_{uuid}`（12 碼大寫 hex）
- `prefix` 轉大寫：`ubichan` → `UBICHAN`
- 預設前綴：`GENERAL`

### 2. Metadata 序列化

- 存儲：Python dict → JSON 字串
- 讀取：JSON 字串 → Python dict
- 注意：JSON 不支援的類型（如 `datetime`）需要自行處理

### 3. TTL 過期

- 過期判斷：`last_active + ttl_hours > now`
- 清理時機：背景任務（每小時）或手動調用
- 過期 Session：`get_session()` 返回 `None`

### 4. 線程安全

- SQLite 支援並發讀取
- 寫入操作建議加鎖或使用連接池

---

## 🔗 相關文檔

- `03_SESSION_API_SPEC.md` — HTTP API 規格
- `04_SESSION_METADATA_DESIGN.md` — Metadata 設計
- `01_AGENT_API_SPEC.md` — Agent API 規格

---

**維護者：** 蝦米 Agent 團隊  
**最後更新：** 2026-04-09
