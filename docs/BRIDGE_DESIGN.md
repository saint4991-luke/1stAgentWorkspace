# Bridge.py 設計文檔

**版本：** v1.0  
**日期：** 2026-04-28  
**作者：** 皮皮蝦 🦐

---

## 📋 概述

本文檔描述 `bridge.py` 的設計架構，用於整合 `session/` 模組與 `ext_query/` 模組，提供統一的電話號碼查詢 API 接口。

---

## 🎯 目標

1. **Session 管理**：追蹤用戶會話，支援連續對話
2. **意圖判斷**：判斷用戶問題是否需要查詢資料庫
3. **對話記錄**：保存所有對話歷史到 Session
4. **統一接口**：提供單一的 HTTPS API 入口

---

## 🏗️ 系統架構

```
┌─────────────┐     HTTPS      ┌─────────────────────────────────────┐
│  User's     │ ─────────────> │  bridge.py (FastAPI)                │
│  Browser    │                │                                     │
└─────────────┘                │  POST /query                        │
                               │                                     │
                               │  1. Session 管理                    │
                               │     - 檢查/建立 session             │
                               │     - 追蹤用戶身份                  │
                               │                                     │
                               │  2. ext_query 判斷                  │
                               │     - 是否需要查詢資料庫？          │
                               │                                     │
                               │         ┌──────────────┐            │
                               │         │  需要查詢？  │            │
                               │         └──────┬───────┘            │
                               │                │                    │
                               │        ┌───────┴───────┐            │
                               │        │               │            │
                               │       YES             NO            │
                               │        │               │            │
                               │        ▼               │            │
                               │  ┌──────────┐         │            │
                               │  │ 查詢資料庫│         │            │
                               │  │ (Qdrant) │         │            │
                               │  └────┬─────┘         │            │
                               │       │               │            │
                               │       ▼               │            │
                               │  ┌──────────┐         │            │
                               │  │Final Agent│        │            │
                               │  │生成回答   │         │            │
                               │  └────┬─────┘         │            │
                               │       │               │            │
                               │       └───────┬───────┘            │
                               │               ▼                    │
                               │  3. Session 記錄對話               │
                               │     - 保存用戶問題                 │
                               │     - 保存系統回答                 │
                               │                                     │
                               │  4. SSE 串流返回結果               │
                               └─────────────────────────────────────┘
```

---

## 📁 檔案結構

```
1stAgentWorkspace/
├── agent/
│   ├── ext_query/
│   │   ├── retrieval_agent.py      # 電話號碼資料庫 Retrieval Agent
│   │   ├── final_agent.py          # 最終回答整理 Agent
│   │   ├── ubillm_client.py        # uBillm LLM API 客戶端
│   │   ├── ubillm_embedding.py     # uBillm Embedding API 客戶端
│   │   └── log_redirector.py       # 日誌重定向器
│   └── bridge/
│       └── bridge.py               # 【新增】Session + ext_query 橋接服務
├── session/
│   ├── session_store.py            # SQLite 存儲層（完整 CRUD）
│   ├── session_api.py              # FastAPI Router
│   └── __init__.py                 # 模組匯出
└── docs/
    └── BRIDGE_DESIGN.md            # 【新增】本設計文檔
```

---

## 🔍 Session/ 模組評估

### ✅ 現有功能（完整！）

| 功能 | 狀態 | 說明 |
|------|------|------|
| **Session 創建** | ✅ | 支援 prefix、metadata、TTL |
| **Session 查詢** | ✅ | 獲取詳情 + 訊息歷史 |
| **Session 列表** | ✅ | 活躍 Session 列表（自動過濾過期） |
| **Session 刪除** | ✅ | 連帶刪除訊息 |
| **訊息添加** | ✅ | 支援 role、content、emotion、lang |
| **訊息查詢** | ✅ | 按時間排序 |
| **TTL 自動清理** | ✅ | 背景任務定期清理 |
| **SQLite 持久化** | ✅ | 支援 `/data/sessions.db` |
| **FastAPI Router** | ✅ | 可嵌入任何 FastAPI 應用 |

### ⚠️ 需要注意的點

1. **用戶識別**：
   - 現有設計透過 `metadata` 傳遞 `user_id`
   - `bridge.py` 需要從 HTTP Header 提取用戶身份

2. **Session ID 生成**：
   - 格式：`{PREFIX}_{uuid}`
   - 建議使用 `EXT_QUERY` 或自定義 prefix

3. **數據庫路徑**：
   - 預設：`/data/sessions.db`
   - 可透過環境變數配置

### ✅ 整合評估

**`session/` 模組已經非常完整，可以直接整合！**

```python
# bridge.py 可以直接這樣用
from session.session_store import SessionStore

# 初始化
store = SessionStore(db_path='/data/sessions.db')

# 創建/獲取 Session
session = store.create_session(
    prefix="EXT_QUERY",
    metadata={"user_id": "user123"}
)
session_id = session['session_id']

# 記錄對話
store.add_message(session_id, role="user", content="我要找遠藤和也")
store.add_message(session_id, role="assistant", content="找到結果...")
```

---

## 🎯 Bridge.py 核心流程

### 流程圖

```
┌─────────────────────────────────────────────────────────────┐
│                     bridge.py (FastAPI)                     │
│                                                             │
│  POST /query                                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. 用戶識別                                         │  │
│  │     user_id = request.headers.get("X-User-ID")      │  │
│  │     session_id = request.cookies.get("session_id")  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  2. Session 管理 (使用 session/)                      │  │
│  │     if session_id:                                   │  │
│  │       session = store.get_session(session_id)        │  │
│  │     else:                                            │  │
│  │       session = store.create_session(                │  │
│  │         prefix="EXT",                                │  │
│  │         metadata={"user_id": user_id}                │  │
│  │       )                                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  3. 記錄用戶問題                                     │  │
│  │     store.add_message(session_id, "user", query)    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  4. ext_query 判斷 (呼叫 retrieval_agent)            │  │
│  │     keywords, display = await extract_keywords()    │  │
│  │                                                      │  │
│  │     if keywords:                                     │  │
│  │       # 需要查詢                                    │  │
│  │       results = await search_by_keywords()          │  │
│  │       answer = await final_agent.generate()         │  │
│  │     else:                                            │  │
│  │       # 不需要查詢                                  │  │
│  │       answer = await chat_only(query)               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  5. 記錄系統回答                                     │  │
│  │     store.add_message(session_id, "assistant", ...) │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  6. SSE 串流返回                                     │  │
│  │     yield {"event": "text_chunk", "data": answer}   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 詳細流程

#### 1. 用戶識別

```python
# 從 Header 獲取用戶 ID
user_id = request.headers.get("X-User-ID")
if not user_id:
    raise HTTPException(status_code=400, detail="Missing X-User-ID header")

# 從 Cookie 獲取 Session ID（如果存在）
session_id = request.cookies.get("session_id")
```

#### 2. Session 管理

```python
# 檢查是否為連續對話
if session_id:
    session = store.get_session(session_id)
    if not session:
        session_id = None  # Session 過期，重新創建

# 創建新 Session
if not session_id:
    session = store.create_session(
        prefix="EXT",
        metadata={"user_id": user_id},
        ttl_hours=24
    )
    session_id = session['session_id']
```

#### 3. ext_query 判斷流程

```python
# 呼叫 uBillm 判斷意圖
keywords, display = await retrieval_agent.extract_keywords_from_query(user_query)

if keywords:
    # 需要查詢 → 呼叫 Qdrant + Final Agent
    results = await retrieval_agent.search_by_keywords(keywords)
    answer = await final_agent.generate_answer_stream(user_query, results)
else:
    # 不需要查詢 → 直接對話
    answer = "請問您想查詢什麼？"
```

#### 4. Session 記錄

```python
# 保存用戶問題
store.add_message(session_id, role="user", content=user_query)

# 保存系統回答
store.add_message(session_id, role="assistant", content=answer)
```

#### 5. SSE 串流返回

```python
async def event_generator():
    # Step A: 判斷是否需要查詢
    keywords, display = await retrieval_agent.extract_keywords_from_query(user_query)
    
    if keywords:
        # 需要查詢 → 呼叫資料庫
        yield {"event": "status", "data": f"正在搜尋：{display}"}
        
        results = await retrieval_agent.search_by_keywords(keywords)
        
        # Step B: Final Agent 生成回答
        async for chunk in final_agent.generate_answer_stream(user_query, results):
            if chunk == "[DONE]":
                break
            yield {"event": "text_chunk", "data": chunk}
    else:
        # 不需要查詢 → 直接對話
        answer = "請問您想查詢什麼？"
        yield {"event": "text_chunk", "data": answer}
    
    # 記錄系統回答
    store.add_message(session_id, role="assistant", content=answer)

return EventSourceResponse(event_generator())
```

---

## 📝 API 設計

### POST /query

**描述：** 統一查詢入口

**請求：**
```http
POST /query
Content-Type: application/json
X-User-ID: user123
Cookie: session_id=EXT_ABC123

{
    "query": "我要找遠藤和也"
}
```

**回應（SSE 串流）：**
```
event: status
data: 正在搜尋：遠藤和也

event: text_chunk
data: 找到結果：

event: text_chunk
data: 管理本部 経営企画部 次長 遠藤和也

event: text_chunk
data: 內線番号：1121

event: done
data: {}
```

### GET /session/{session_id}

**描述：** 獲取 Session 詳情（用於除錯）

**請求：**
```http
GET /session/EXT_ABC123
```

**回應：**
```json
{
    "session_id": "EXT_ABC123",
    "metadata": {"user_id": "user123"},
    "created_at": "2026-04-28T10:00:00",
    "last_active": "2026-04-28T10:05:00",
    "ttl_hours": 24,
    "message_count": 4,
    "messages": [
        {"role": "user", "content": "我要找遠藤和也"},
        {"role": "assistant", "content": "找到結果：..."}
    ]
}
```

### GET /health

**描述：** 健康檢查

**回應：**
```json
{"status": "ok"}
```

---

## 🔧 環境變數配置

```bash
# bridge.py 環境變數

# Session 數據庫路徑
SESSION_DB_PATH=/data/sessions.db

# 用戶識別 Header 名稱
USER_ID_HEADER=X-User-ID

# ext_query 配置（與現有 ext_query 共用）
UBILM_GRANT_URL=https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant
UBILM_API_KEY=YOUR_API_KEY
UBILM_LLM_MODEL=qwen3-8b-fp8
UBILM_EMBED_MODEL=qwen3-embedding-4b
QDRANT_HOST=140.227.187.126
QDRANT_PORT=6334
QDRANT_COLLECTION=default_kb_832887850831363957
UBIGPT_FQDN=https://g.ubitus.ai/v1/chat/completions
UBIGPT_AUTH_KEY=Bearer YOUR_AUTH_KEY
UBIGPT_MODEL=llama-4-maverick-fp8

# 服務配置
BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=3006
```

---

## 🤔 設計討論點

### 1. 用戶識別方式

| 選項 | 優點 | 缺點 |
|------|------|------|
| **Header (X-User-ID)** | 簡單、明確 | 需要前端配合 |
| **Cookie** | 自動攜帶 | 跨域問題 |
| **JWT Token** | 安全、可驗證 | 需要簽發機制 |

**建議：** 先用 Header，後續可擴展

### 2. Session ID 傳遞

- **方案 A：** Cookie（自動攜帶）
- **方案 B：** 回應中返回，前端手動保存

**建議：** Cookie + Header 雙支援

### 3. ext_query 判斷邏輯

目前 `retrieval_agent.extract_keywords_from_query()` 已經負責判斷：
- 有 keywords → 需要查詢
- 無 keywords → 不需要查詢

**需要討論：** 是否需要更複雜的判斷邏輯？

### 4. Final Agent 的兩種模式

- **查詢模式：** 基於資料庫結果生成回答
- **對話模式：** 純聊天（需要額外設計 prompt）

**建議：** 可以先聚焦查詢模式，對話模式後續擴展

---

## ✅ 總結

### Session/ 模組評估
- **功能完整性：** ✅ 非常完整
- **可直接整合：** ✅ 是
- **需要修改：** ⚠️ 只需要在 `bridge.py` 中調用

### Bridge.py 設計要點
1. 使用 `session.SessionStore` 管理 Session
2. 從 Header 獲取 `user_id`
3. 調用 `retrieval_agent` 判斷是否需要查詢
4. 記錄對話到 Session
5. SSE 串流返回結果

### 下一步
1. 確認用戶識別方式
2. 確認 ext_query 判斷邏輯是否需要調整
3. 確認 Final Agent 的對話模式需求

---

## 📚 參考文件

- [session/session_store.py](../session/session_store.py)
- [session/session_api.py](../session/session_api.py)
- [agent/ext_query/retrieval_agent.py](../agent/ext_query/retrieval_agent.py)
- [agent/ext_query/final_agent.py](../agent/ext_query/final_agent.py)
