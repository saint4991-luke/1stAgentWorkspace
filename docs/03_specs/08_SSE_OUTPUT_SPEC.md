# 05_SSE_OUTPUT_SPEC.md - SSE 流式輸出規格

**版本：** 2.0  
**最後更新：** 2026-04-20  
**維護者：** 蝦米 Agent 團隊  
**相關文件：** 01_AGENT_API_SPEC.md, 02_PERSONA_SPEC.md

---

## 📋 目錄

- [概述](#概述)
- [架構設計](#架構設計)
- [事件類型](#事件類型)
- [UBICHAN 格式](#ubichan-格式)
- [OpenAI Compatible 格式](#openai-compatible-格式)
- [Persona Config 配置](#persona-config-配置)
- [實作指南](#實作指南)

---

## 概述

### 目的

本文檔定義虛擬人 Agent 的 SSE (Server-Sent Events) 流式輸出格式規範。

### 設計目標

1. **多格式支持** - 通過 Persona Config 配置不同輸出格式
2. **扁平結構** - 前端解析簡單，減少嵌套
3. **易於擴展** - 支持未來新增字段（usage、metrics 等）
4. **向後兼容** - 保留現有 UBICHAN 格式

### 適用範圍

- 虛擬人聊天 API (`/api/chat`)
- 流式回應場景
- 需要實時輸出的應用

---

## 架構設計

### 核心概念

```
┌─────────────────────────────────────────┐
│           Persona Config                │
│  ┌─────────────────────────────────┐    │
│  │  sse_format:                    │    │
│  │    type: ubichan                │    │
│  │    text_chunk: {...}            │    │
│  │    done: {...}                  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           StreamEvent                   │
│  - event: str                           │
│  - message: Optional[str]               │
│  - created: Optional[int]               │
│  - id: Optional[str]                    │
│  - timing: Optional[Dict]               │
│  - usage: Optional[Dict]                │
│  - format_config: Optional[Config]      │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         SSE Format Formatter            │
│  - 根據 format_config 生成對應格式      │
│  - 支持 ubichan / openai_compatible     │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│            Frontend                     │
│  - EventSource('/api/stream')           │
│  - addEventListener('text_chunk', ...)  │
│  - addEventListener('done', ...)        │
└─────────────────────────────────────────┘
```

### 數據流

```
用戶請求 → 載入 Persona Config → 創建 StreamEvent → 格式化 → SSE 輸出
```

---

## 事件類型

### 核心事件

| 事件 | 說明 | 必要字段 | 可選字段 |
|------|------|----------|----------|
| `text_chunk` | 文字區塊 | `message`, `created`, `id` | - |
| `done` | 回應完成 | `created`, `id` | `timing`, `usage` |
| `error` | 錯誤 | `error` | `created`, `id` |

### 保留事件（未來擴充）

| 事件 | 說明 | 狀態 |
|------|------|------|
| `start` | 開始回應 | 保留 |
| `thinking` | 思考過程 | 保留 |

---

## UBICHAN 格式

### 設計原則

1. **扁平結構** - 所有字段在同一層級
2. **統一命名** - `created`（時間戳）、`id`（事件 ID）
3. **Unix 時間戳** - 使用數字格式（秒）
4. **事件 ID** - `session_id + "_" + created`

### text_chunk 格式

```json
{
  "event": "text_chunk",
  "message": "讓我調查",
  "created": 1776416929,
  "id": "session_123_1776416929"
}
```

**字段說明：**

| 字段 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `event` | string | 事件類型 | `"text_chunk"` |
| `message` | string | 文字內容 | `"讓我調查"` |
| `created` | number | Unix 時間戳（秒） | `1776416929` |
| `id` | string | 事件 ID | `"session_123_1776416929"` |

### 結束標記 `[DONE]`

UBICHAN 格式在 `done` 事件後會發送額外標記：

```
event: done
data: {"event":"done","created":1776416929,"id":"session_123_1776416929","timing":{...}}

data: [DONE]    ← 結束標記
```

**理由：**
- 明確告知前端「這是流式結尾」
- 避免前端等待超時
- 符合行業慣例（OpenAI 也使用）

**配置：**
```yaml
sse_format:
  type: ubichan
  include_done_marker: true  # 啟用 [DONE] 標記
```

### done 格式

```json
{
  "event": "done",
  "created": 1776416929,
  "id": "session_123_1776416929",
  "timing": {
    "rag_llm_ms": 535,
    "file_read_ms": 3,
    "rag_retrieve_ms": 120,
    "llm_call_ms": 2100,
    "total_ms": 2658
  },
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

**完整 SSE 流（含 `[DONE]` 標記）：**

```
event: text_chunk
data: {"event":"text_chunk","message":"讓我調查","created":1776416929,"id":"session_123_1776416929"}

event: text_chunk
data: {"event":"text_chunk","message":"這是回應","created":1776416929,"id":"session_123_1776416929"}

event: done
data: {"event":"done","created":1776416929,"id":"session_123_1776416929","timing":{...},"usage":{...}}

data: [DONE]
```

**字段說明：**

| 字段 | 類型 | 說明 | 必要 |
|------|------|------|------|
| `event` | string | 事件類型 | ✅ |
| `created` | number | Unix 時間戳 | ✅ |
| `id` | string | 事件 ID | ✅ |
| `timing` | object | 計時數據 | ❌ |
| `usage` | object | Token 用量 | ❌ |

### timing 字段結構

```json
{
  "timing": {
    "rag_llm_ms": 535,
    "file_read_ms": 3,
    "rag_retrieve_ms": 120,
    "llm_call_ms": 2100,
    "total_ms": 2658
  }
}
```

| 字段 | 說明 | 單位 |
|------|------|------|
| `rag_llm_ms` | RAG + LLM1 時間 | ms |
| `file_read_ms` | 文件讀取時間 | ms |
| `rag_retrieve_ms` | RAG 檢索時間 | ms |
| `llm_call_ms` | LLM2 調用時間 | ms |
| `total_ms` | 總耗時 | ms |

### usage 字段結構

```json
{
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

| 字段 | 說明 |
|------|------|
| `prompt_tokens` | 提示詞 Token 數 |
| `completion_tokens` | 回應 Token 數 |
| `total_tokens` | 總 Token 數 |

### error 格式

```json
{
  "event": "error",
  "error": "錯誤訊息",
  "created": 1776416929,
  "id": "session_123_1776416929"
}
```

---

## OpenAI Compatible 格式

### 說明

兼容 OpenAI Chat Completion API 的 SSE 格式，用於支持第三方前端。

### text_chunk 格式

```json
{
  "event": "chunk",
  "id": "chatcmpl-123",
  "object": "chat.completion.chunk",
  "created": 1776416929,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "delta": {
        "content": "讓我調查"
      },
      "finish_reason": null
    }
  ]
}
```

### done 格式

```json
{
  "event": "done",
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1776416929,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "完整回應"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

**完整 SSE 流（含 `[DONE]` 標記）：**

```
event: chunk
data: {"id":"chatcmpl-123","object":"chat.completion.chunk",...}

event: done
data: {"id":"chatcmpl-123","object":"chat.completion",...}

data: [DONE]    ← OpenAI 約定
```

**配置：**
```yaml
sse_format:
  type: openai_compatible
  include_done_marker: true  # 啟用 [DONE] 標記（兼容 OpenAI SDK）
```

---

## Persona Config 配置

### UBICHAN 配置範例

```yaml
# workspace/personas/ubichan/config.yaml
persona_id: ubichan
display_name: 優必醬
output_format: virtual_human

# SSE 格式配置
sse_format:
  type: ubichan
  version: "2.0"
  include_done_marker: true  # 啟用 [DONE] 標記
  
  # text_chunk 字段映射
  text_chunk:
    event_field: "event"
    content_field: "message"
    timestamp_field: "created"
    timestamp_type: "unix"        # unix 數字格式
    id_field: "id"
    id_format: "{session_id}_{created}"
  
  # done 字段映射
  done:
    event_field: "event"
    timestamp_field: "created"
    id_field: "id"
    id_format: "{session_id}_{created}"
    include_timing: true
    include_usage: true
    timing_field: "timing"
    usage_field: "usage"
  
  # error 字段映射
  error:
    event_field: "event"
    error_field: "error"
    timestamp_field: "created"
    id_field: "id"
```

### OpenAI Compatible 配置範例

```yaml
# workspace/personas/openai-bot/config.yaml
persona_id: openai-bot
display_name: OpenAI Bot
output_format: chat

sse_format:
  type: openai_compatible
  version: "1.0"
  include_done_marker: true  # 啟用 [DONE] 標記（兼容 OpenAI SDK）
  
  text_chunk:
    event_field: "event"
    content_field: "content"
    timestamp_field: "created"
    timestamp_type: "unix"
    id_field: "id"
    id_format: "chatcmpl-{random}"
    extra_fields:
      object: "chat.completion.chunk"
      model: "gpt-4"
  
  done:
    event_field: "event"
    timestamp_field: "created"
    id_field: "id"
    include_usage: true
    usage_field: "usage"
    extra_fields:
      object: "chat.completion"
      model: "gpt-4"
```

---

## 實作指南

### StreamEvent 類別

```python
# agent/stream_events.py
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

class StreamEvent(BaseModel):
    """SSE 流式事件"""
    
    event: str
    message: Optional[str] = None
    created: Optional[int] = None
    id: Optional[str] = None
    timing: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_sse(self, include_done_marker: bool = False) -> str:
        """
        轉換為 SSE 格式
        
        Args:
            include_done_marker: 是否在 done/error 事件後添加 [DONE] 標記
        """
        data = self._build_data()
        json_str = json.dumps(data, separators=(',', ':'))
        sse = f"event: {self.event}\ndata: {json_str}\n\n"
        
        # 在 done/error 事件後添加 [DONE] 標記
        if include_done_marker and self.event in ["done", "error"]:
            sse += "data: [DONE]\n\n"
        
        return sse
    
    def _build_data(self) -> Dict[str, Any]:
        """構建數據字典"""
        data = {"event": self.event}
        
        if self.event == "text_chunk":
            data["message"] = self.message
            data["created"] = self.created
            data["id"] = self.id
        elif self.event == "done":
            data["created"] = self.created
            data["id"] = self.id
            if self.timing:
                data["timing"] = self.timing
            if self.usage:
                data["usage"] = self.usage
        elif self.event == "error":
            data["error"] = self.error
            data["created"] = self.created
            data["id"] = self.id
        
        return data
    
    @classmethod
    def create_text_chunk(
        cls,
        message: str,
        created: int,
        event_id: str
    ) -> "StreamEvent":
        """創建 text_chunk 事件"""
        return cls(
            event="text_chunk",
            message=message,
            created=created,
            id=event_id
        )
    
    @classmethod
    def create_done(
        cls,
        created: int,
        event_id: str,
        timing: Optional[Dict] = None,
        usage: Optional[Dict] = None
    ) -> "StreamEvent":
        """創建 done 事件"""
        return cls(
            event="done",
            created=created,
            id=event_id,
            timing=timing,
            usage=usage
        )
    
    @classmethod
    def create_error(
        cls,
        error: str,
        created: int,
        event_id: str
    ) -> "StreamEvent":
        """創建 error 事件"""
        return cls(
            event="error",
            error=error,
            created=created,
            id=event_id
        )


def format_sse_event(event: StreamEvent, include_done_marker: bool = False) -> str:
    """
    格式化 SSE 事件
    
    Args:
        event: StreamEvent 對象
        include_done_marker: 是否在 done/error 事件後添加 [DONE] 標記
    """
    return event.to_sse(include_done_marker=include_done_marker)
```

### API 端點使用

```python
# agent/virtual_human/api.py
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from stream_events import StreamEvent, format_sse_event

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    """聊天 API（流式回應）"""
    
    # 獲取時間戳（請求開始時）
    created = int(time.time())
    
    # 生成事件 ID
    session_id = request.session_id
    event_id = f"{session_id}_{created}"
    
    # 載入 Persona Config
    persona_config = config_loader.get(request.persona_id)
    sse_format = persona_config.get('sse_format', {})
    
    # 獲取 [DONE] 標記配置（每種格式獨立配置）
    include_done_marker = sse_format.get('include_done_marker', False)
    
    async def generate_stream():
        # 發送 text_chunk
        event = StreamEvent.create_text_chunk(
            message="讓我調查",
            created=created,
            event_id=event_id
        )
        yield format_sse_event(event, include_done_marker=include_done_marker)
        
        # 發送更多 text_chunk...
        
        # 發送 done（含 timing + usage）
        event = StreamEvent.create_done(
            created=created,
            event_id=event_id,
            timing={
                "rag_llm_ms": 535,
                "llm_call_ms": 2100,
                "total_ms": 2658
            },
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        )
        yield format_sse_event(event, include_done_marker=include_done_marker)
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )
```

### 前端解析

```javascript
// Frontend JavaScript
const eventSource = new EventSource('/api/stream');

eventSource.addEventListener('text_chunk', (event) => {
    const data = JSON.parse(event.data);
    console.log('文字:', data.message);
    console.log('時間:', data.created);
    console.log('ID:', data.id);
    
    // 更新 UI
    appendMessage(data.message);
});

eventSource.addEventListener('done', (event) => {
    const data = JSON.parse(event.data);
    console.log('完成');
    console.log('計時:', data.timing);
    console.log('用量:', data.usage);
    
    // 關閉連接
    eventSource.close();
});

eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    console.error('錯誤:', data.error);
    
    // 顯示錯誤訊息
    showError(data.error);
    eventSource.close();
});
```

---

## 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0 | 2026-04-17 | 初始版本（嵌套結構） |
| 2.0 | 2026-04-20 | 扁平結構、Unix 時間戳、多格式支持 |

---

## 相關文件

- [01_AGENT_API_SPEC.md](./01_AGENT_API_SPEC.md) - Agent API 規格
- [02_PERSONA_SPEC.md](./02_PERSONA_SPEC.md) - Persona 配置規格
- [03_SESSION_API_SPEC.md](./03_SESSION_API_SPEC.md) - Session API 規格
