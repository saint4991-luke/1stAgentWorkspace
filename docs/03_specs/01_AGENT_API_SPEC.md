# 🤖 Agent API 規格書

**版本：** v1.0  
**日期：** 2026-04-17  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Agent API 的端點定義與請求/回應格式
- 一般對話、虛擬人對話、健康檢查的技術規格

---

## 📋 概述

Agent API 提供**一般對話**和**虛擬人對話**功能。

**基礎 URL:** `http://localhost:8000`

**API 分類：**
| 類別 | 端點 | 說明 |
|------|------|------|
| 健康檢查 | `GET /health` | 服務狀態檢查 |
| 一般對話 | `POST /chat` | 無風格對話（STREAM） |
| 虛擬人對話 | `POST /vh/sessions` | 創建虛擬人 Session |
| 虛擬人對話 | `POST /vh/chat` | 帶風格對話（STREAM） |
| 虛擬人切換 | `POST /vh/sessions/{id}/switch` | 切換 Persona |
| 統計 | `GET /vh/sessions/stats` | Session 統計 |

---

## 🔒 認證

目前無需認證（開發階段）。

---

## 📡 API 端點

### 1. 健康檢查

**GET** `/health`

**回應：**
```json
{
  "status": "healthy",
  "version": "v1.0",
  "provider": "openai",
  "model": "Qwen/Qwen3.5-397B-A17B-FP8",
  "workspace": "/workspace",
  "session_support": true,
  "knowledge_support": true,
  "virtual_human_support": true,
  "knowledge_count": 1,
  "persona_count": 2
}
```

**欄位說明：**
| 欄位 | 類型 | 說明 |
|------|------|------|
| `status` | string | 服務狀態（`healthy` / `unhealthy`） |
| `version` | string | API 版本 |
| `provider` | string | LLM Provider |
| `model` | string | 模型名稱 |
| `workspace` | string | 工作區路徑 |
| `session_support` | boolean | Session 功能支援 |
| `knowledge_support` | boolean | Knowledge 功能支援 |
| `virtual_human_support` | boolean | 虛擬人功能支援 |
| `knowledge_count` | integer | 知識庫數量 |
| `persona_count` | integer | Persona 數量 |

---

### 2. 一般對話（STREAM-ONLY）

**POST** `/chat`

**說明：** `/chat` 端點現在**僅支援 STREAM 模式**。

**請求：**
```json
{
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "session_id": "abc123",
  "knowledge_ids": ["kb1"]
}
```

**欄位說明：**
| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `messages` | array | ✅ | 對話歷史陣列 |
| `session_id` | string | ❌ | Session ID（可選） |
| `knowledge_ids` | array | ❌ | 知識庫 ID 列表（可選，用於 RAG） |

**回應：** SSE 流式傳輸

**STREAM 事件格式：**
```
event: text_chunk
data: {"event":"text_chunk","data":{"chunk":"嗨嗨～有什麼我可以幫你的嗎？","is_block":false}}

event: done
data: {"event":"done","data":{"timings":{"rag_llm_ms":755,"file_read_ms":0,"rag_retrieve_ms":755,"llm_call_ms":5773,"total_ms":6543}}}
```

---

### 3. 創建虛擬人 Session

**POST** `/vh/sessions`

**請求：**
```json
{
  "persona_id": "ubichan",
  "metadata": {
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
| `persona_id` | string | ✅ | Persona ID |
| `metadata` | object | ❌ | Metadata 擴展 |

**回應：**
```json
{
  "session_id": "vh_abc123",
  "persona_id": "ubichan",
  "created_at": "2026-04-17T08:00:00Z",
  "expires_at": "2026-04-18T08:00:00Z"
}
```

---

### 4. 虛擬人對話（STREAM 模式）

**POST** `/vh/chat`

**說明：** 虛擬人對話**僅支援 STREAM 模式**，支援風格、情緒、語言標籤。

**請求：**
```json
{
  "session_id": "vh_abc123",
  "messages": [
    {"role": "user", "content": "你好，講個笑話"}
  ]
}
```

**欄位說明：**
| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `session_id` | string | ✅ | Session ID |
| `messages` | array | ✅ | 對話歷史（支援多輪） |

**回應格式：** Server-Sent Events (SSE)

**STREAM 事件類型：**

| 事件 | 說明 | 格式 |
|------|------|------|
| `text_chunk` | 文字片段（安撫話語或回答） | `{"event":"text_chunk","data":{"chunk":"...","is_block":false}}` |
| `done` | 完成事件 | `{"event":"done","data":{"timings":{...}}}` |

**STREAM 流程：**
```
1. 立即發送安撫話語（< 1 秒）
   event: text_chunk
   data: {"chunk":"哈哈，你好呀！讓我來看看..."}

2. 分段發送完整回答
   event: text_chunk
   data: {"chunk":"<笑話內容>..."}

3. 發送完成事件
   event: done
   data: {"timings":{"total_ms":6234,"llm_call_ms":5892}}
```

**完整回應範例：**
```
event: text_chunk
data: {"event":"text_chunk","data":{"chunk":"哈哈，你好呀！讓我來看看資料庫裡有沒有儲存笑話可以分享給你～","is_block":false}}

event: text_chunk
data: {"event":"text_chunk","data":{"chunk":"<!-- emotion:happy --><!-- lang:tw (zh) -->\n嗨嗨～你好啊！<br>\n想聽笑話嗎？人家最擅長這個了～♪<br>\n<!-- emotion:neutral -->","is_block":false}}

event: done
data: {"event":"done","data":{"timings":{"rag_llm_ms":0,"file_read_ms":0,"rag_retrieve_ms":0,"llm_call_ms":4473,"total_ms":6979}}}
```

**計時資訊說明：**
| 欄位 | 說明 |
|------|------|
| `rag_llm_ms` | RAG LLM 判斷耗時 |
| `file_read_ms` | 文件讀取耗時 |
| `rag_retrieve_ms` | RAG 檢索總耗時 |
| `llm_call_ms` | LLM2 完整回答生成耗時 |
| `total_ms` | 總耗時 |

---

### 5. 切換虛擬人 ⚠️

**POST** `/vh/sessions/{session_id}/switch`

> **⚠️ 已棄用** - 此功能偏離原始設計，預計未來移除。
>
> **替代方案：** 直接創建新的 Session（`POST /vh/sessions`）並指定新的 `persona_id`。

**請求：**
```json
{
  "persona_id": "nurse"
}
```

**回應：**
```json
{
  "success": true,
  "session_id": "vh_abc123",
  "old_persona_id": "ubichan",
  "new_persona_id": "nurse",
  "message": "已切換至護士姐姐"
}
```

---

### 6. Session 統計 ⚠️

**GET** `/vh/sessions/{session_id}/stats`

> **⚠️ 已棄用** - 此功能偏離原始設計，預計未來移除。
>
> **用途：** 獲取單一 Session 的統計資訊（消息數量、創建時間等）。

**回應：**
```json
{
  "session_id": "vh_abc123",
  "persona_id": "ubichan",
  "message_count": 10,
  "user_message_count": 5,
  "assistant_message_count": 5,
  "created_at": "2026-04-17T08:00:00Z",
  "last_active": "2026-04-17T09:00:00Z"
}
```

---

### 7. 所有 Sessions 統計 ⚠️

**GET** `/vh/sessions/stats`

> **⚠️ 已棄用** - 此功能偏離原始設計，預計未來移除。
>
> **用途：** 獲取所有 Sessions 的總體統計資訊（總 Session 數、各 Persona 使用情況）。

**回應：**
```json
{
  "total_sessions": 5,
  "active_sessions": 3,
  "total_messages": 100,
  "persona_stats": [
    {"persona_id": "ubichan", "session_count": 3, "message_count": 60},
    {"persona_id": "nurse", "session_count": 2, "message_count": 40}
  ]
}
```

---

## ❌ 錯誤處理

### 錯誤格式

```json
{
  "error": "error_code",
  "message": "錯誤描述"
}
```

### 常見錯誤

| 錯誤代碼 | HTTP 狀態碼 | 說明 |
|----------|-------------|------|
| `session_not_found` | 404 | Session ID 不存在 |
| `persona_not_found` | 404 | Persona ID 不存在 |
| `llm_error` | 500 | LLM 調用失敗 |
| `knowledge_error` | 500 | 知識庫檢索失敗 |

---

## 📝 使用範例

### 一般對話（無狀態）

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 虛擬人完整對話流程

```bash
# 1. 創建虛擬人 Session
curl -X POST http://localhost:8000/vh/sessions \
  -H "Content-Type: application/json" \
  -d '{"persona_id": "ubichan"}'

# 回應：{"session_id": "vh_abc123", "persona_id": "ubichan"}

# 2. 發送對話（STREAM）
curl -X POST http://localhost:8000/vh/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "vh_abc123",
    "messages": [{"role": "user", "content": "你是誰"}]
  }'

# 3. 切換虛擬人
curl -X POST http://localhost:8000/vh/sessions/vh_abc123/switch \
  -H "Content-Type: application/json" \
  -d '{"persona_id": "nurse"}'
```

---

**文檔結束**
