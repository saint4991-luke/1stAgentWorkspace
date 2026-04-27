# 📊 LLM 性能監控技術規格

**版本：** v2.0.0  
**創建日期：** 2026-04-09  
**最後更新：** 2026-04-17  
**適用端點：** `/chat`, `/vh/chat`

---

## 🎯 文件職責

**本文檔說明：**
- LLM 性能監控的技術規格
- 計時點、Token Usage 測量標準
- 性能基準與瓶頸分析指南

---

## 📋 概述

本文檔記錄所有 LLM 調用點的計時與 Token Usage 測量位置，用於性能監控和優化分析。

---

## 📋 LLM 調用點總覽

### 總計：4 個 LLM 調用點

| 端點 | LLM #1（知識庫） | LLM #2（主回應） |
|------|----------------|----------------|
| `/chat` | ✅ `rag/knowledge_retriever.py:146` | ✅ `agent-api-streaming.py:643` |
| `/vh/chat` | ✅ `rag/knowledge_retriever.py:146` | ✅ `virtual_human/api.py:224` |

---

## 🔍 詳細計時點

### 1. `/chat` 端點（一般對話）

**文件：** `agent/agent-api-streaming.py`  
**函數：** `async def chat(request: ChatRequest)`  
**行數：** ~588

```
收到請求
  ↓
[1] _auto_search_knowledge(question)
    ├─ 文件：agent/agent-api-streaming.py
    ├─ 行數：~568
    ├─ 計時：rag_retrieve_ms（總時間）
    └─ 內部細分：
        ├─ meta_load_ms: META 載入
        ├─ rag_llm_ms: LLM 判斷耗時 ⭐
        └─ file_read_ms: 文件讀取（不是向量搜尋！）
  ↓
[2] Prompt 建構
    ├─ 文件：agent/agent-api-streaming.py
    ├─ 行數：~629-640
    └─ 計時：prompt_build_ms
  ↓
[3] LLM 調用 chat_with_tools()
    ├─ 文件：agent/agent-api-streaming.py
    ├─ 行數：~643
    ├─ 計時：llm_call_ms ⭐
    └─ Token Usage: ✅ 測量
  ↓
[4] Tool 執行（可選）
    └─ 計時：包含在 llm_call_ms 或单独計算
  ↓
[5] Session 保存（可選）
    └─ 不計時（後台操作）
  ↓
返回回應
```

---

### 2. `/vh/chat` 端點（虛擬人）

**文件：** `agent/virtual_human/api.py`  
**函數：** `async def chat(request: ChatRequest)`  
**行數：** ~123

```
收到請求
  ↓
[1] Session 讀取
    ├─ 文件：agent/virtual_human/api.py
    ├─ 行數：~128-135
    └─ 計時：session_load_ms
  ↓
[2] 載入 CONFIG + 風格 Prompt
    ├─ 文件：agent/virtual_human/api.py
    ├─ 行數：~143-162
    └─ 計時：config_load_ms
  ↓
[3] 知識庫檢索 MultiKnowledgeRetriever.query()
    ├─ 文件：agent/virtual_human/api.py
    ├─ 行數：~168-177
    ├─ 計時：rag_retrieve_ms（總時間）
    └─ 內部細分：
        ├─ meta_load_ms: META 載入
        ├─ rag_llm_ms: LLM 判斷耗時 ⭐
        └─ file_read_ms: 文件讀取（不是向量搜尋！）
  ↓
[4] System Prompt 組合
    ├─ 文件：agent/virtual_human/api.py
    ├─ 行數：~180-200
    └─ 計時：prompt_build_ms
  ↓
[5] LLM 調用 chat_for_virtual_human()
    ├─ 文件：agent/virtual_human/api.py
    ├─ 行數：~224
    ├─ 計時：llm_call_ms ⭐
    └─ Token Usage: ✅ 測量
  ↓
[6] Session 保存
    └─ 不計時（後台操作）
  ↓
返回回應
```

---

## 📍 知識庫 LLM 調用點（內部）

### `rag/knowledge_retriever.py`

**文件：** `agent/rag/knowledge_retriever.py`  
**函數：** `def _find_related_files(self, question: str)`  
**行數：** ~145-146

```python
# 目前程式碼
llm_response = self.llm.chat_for_knowledge_sync(prompt)

# 修改後（需要添加計時）
start = time.time()
llm_response = self.llm.chat_for_knowledge_sync(prompt)
llm_time = int((time.time() - start) * 1000)

# 儲存計時數據
self.timings = {
    'rag_llm_ms': llm_time,
    'rag_prompt_tokens': getattr(llm_response, 'usage', {}).prompt_tokens,
    'rag_completion_tokens': getattr(llm_response, 'usage', {}).completion_tokens
}
```

**計時：** `rag_llm_ms`（知識庫 LLM 判斷時間）  
**Token Usage：** `rag_prompt_tokens`, `rag_completion_tokens`

---

## 📊 輸出格式

### 完整模式（ENABLE_TIMING=true, ENABLE_TOKEN_USAGE=true）

```json
{
  "response": "好的，讓我來幫你分析...",
  "session_id": "CHAT_abc123",
  "message_count": 5,
  "timings": {
    "meta_load_ms": 5,           // META 載入耗時
    "rag_llm_ms": 450,           // 知識庫 LLM 判斷耗時
    "vector_search_ms": 120,     // 向量搜尋耗時
    "rag_retrieve_ms": 575,      // 知識庫檢索總耗時 (=5+450+120)
    "prompt_build_ms": 45,       // Prompt 建構耗時
    "llm_call_ms": 880,          // 主 LLM 調用耗時
    "total_ms": 1500             // 總耗時
  },
  "usage": {
    "rag_prompt_tokens": 234,    // 知識庫 LLM 輸入 token
    "rag_completion_tokens": 56, // 知識庫 LLM 輸出 token
    "main_prompt_tokens": 1234,  // 主 LLM 輸入 token
    "main_completion_tokens": 567, // 主 LLM 輸出 token
    "total_prompt_tokens": 1468, // 總輸入 token
    "total_completion_tokens": 623, // 總輸出 token
    "total_tokens": 2091         // 總 token
  }
}
```

### 最小模式（ENABLE_TIMING=false, ENABLE_TOKEN_USAGE=false）

```json
{
  "response": "好的，讓我來幫你分析...",
  "session_id": "CHAT_abc123",
  "message_count": 5
}
```

---

## 🔧 .env 開關參數

**文件：** `agent/.env`, `agent/.env.example`

```bash
# 計時與 Token Usage 開關
ENABLE_TIMING=true           # 是否輸出耗時分析
ENABLE_TOKEN_USAGE=true      # 是否輸出 Token 統計
```

**預設值：** `false`（生產環境建議關閉，減少輸出）

---

## 📋 實作狀態

**最後更新：** 2026-04-17

| # | 文件 | 修改內容 | 狀態 |
|---|------|---------|------|
| 1 | `agent/.env` | 新增 `ENABLE_TIMING`, `ENABLE_TOKEN_USAGE` | ✅ |
| 2 | `agent/.env.example` | 新增範例 | ✅ |
| 3 | `agent/rag/knowledge_retriever.py` | 知識庫 LLM 計時 + Token | ✅ |
| 4 | `agent/agent-api-streaming.py` | /chat 端點整合 | ✅ |
| 5 | `agent/virtual_human/api.py` | /vh/chat 端點整合 | ✅ |
| 6 | `agent/llm_service.py` | 確保 usage 回傳 | ✅ |
| 7 | `agent/llm_providers.py` | 確保 usage 回傳 | ✅ |
| 8-12 | 前端模板 | 狀態欄顯示 | ⏳ 待實作 |

---

## 🧪 測試計劃

### 測試案例

| ID | 案例 | 條件 | 預期結果 |
|----|------|------|---------|
| T1 | 計時開關 | ENABLE_TIMING=true | 回應包含 `timings` |
| T2 | 計時開關 | ENABLE_TIMING=false | 回應不包含 `timings` |
| T3 | Token 開關 | ENABLE_TOKEN_USAGE=true | 回應包含 `usage` |
| T4 | Token 開關 | ENABLE_TOKEN_USAGE=false | 回應不包含 `usage` |
| T5 | 知識庫 LLM | 有知識庫檢索 | `rag_llm_ms` > 0 |
| T6 | 知識庫 LLM | 無知識庫檢索 | `rag_llm_ms` = 0 |
| T7 | 主 LLM | 所有請求 | `llm_call_ms` > 0 |
| T8 | Token 統計 | 所有請求 | `total_tokens` = `prompt_tokens` + `completion_tokens` |

---

## 📈 性能基準

### 預期耗時範圍

| 項目 | 正常範圍 | 說明 |
|------|---------|------|
| `meta_load_ms` | 1-10ms | 讀取 meta.json |
| `rag_llm_ms` | 200-600ms | 知識庫 LLM 判斷 |
| `file_read_ms` | 50-200ms | 讀取相關文件內容 |
| `rag_retrieve_ms` | 250-800ms | 知識庫檢索總時間 |
| `prompt_build_ms` | 10-50ms | Prompt 字串組合 |
| `llm_call_ms` | 500-2000ms | 主 LLM 調用 |
| `total_ms` | 800-3000ms | 總耗時 |

---

## 🔍 瓶頸分析指南

### 如何解讀數據

**情境 1：知識庫檢索慢**
```json
{
  "rag_retrieve_ms": 1500,
  "rag_llm_ms": 1200,    // ⚠️ LLM 判斷太慢
  "vector_search_ms": 100
}
```
**分析：** LLM 判斷佔了 80% 時間  
**優化：** 简化 prompt、減少文件清單

**情境 2：主 LLM 慢**
```json
{
  "llm_call_ms": 3000,   // ⚠️ 太慢
  "rag_llm_ms": 300
}
```
**分析：** 主 LLM 回應太慢  
**優化：** 減少 prompt 長度、限制 max_tokens

**情境 3：文件讀取慢**
```json
{
  "rag_retrieve_ms": 800,
  "rag_llm_ms": 100,
  "file_read_ms": 650  // ⚠️ 文件讀取太慢
}
```
**分析：** 文件讀取太慢（可能是文件太多或太大）  
**優化：** 減少知識庫文件數量、使用快取、限制最大讀取行數

---

## 📝 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0.0 | 2026-04-08 | 初始版本 |
| v1.1.0 | 2026-04-09 | 新增知識庫 LLM 細分計時 |
| v2.0.0 | 2026-04-17 | 移至 03_specs/，更新文件職責與實作狀態 |

---

**維護者：** 蝦蝦開發團隊  
**最後更新：** 2026-04-17
