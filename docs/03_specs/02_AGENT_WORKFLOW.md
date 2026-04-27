# 🤖 Agent 工作流程規格書

**版本：** v2.0  
**日期：** 2026-04-17  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Agent 的完整工作流程（LLM1/LLM2 雙階段架構）
- Prompt 生成結構與組合邏輯

---

## 📋 概述

本系統採用**雙 LLM 協作架構**：
- **LLM1** - 快速回應（< 1 秒）+ RAG 判斷
- **LLM2** - 完整內容生成（10-30 秒）

**適用範圍：** `/vh/chat` 和 `/chat` 端點

---

## 🔄 完整工作流程

### 階段 0：前置準備

```
┌─────────────────────────────────────────────────────────┐
│  前置準備                                                │
├─────────────────────────────────────────────────────────┤
│  1. 載入 Persona 配置（config_loader）                   │
│  2. 載入風格 Prompt（style_manager）                     │
│  3. 初始化 Session Store（SQLite）                       │
│  4. 初始化 LLM Service（llm_providers.py）              │
└─────────────────────────────────────────────────────────┘
```

**涉及文件：**
- `agent/virtual_human/api.py` - 端點定義
- `agent/config_loader.py` - Persona 配置載入
- `agent/llm_providers.py` - LLM Provider

---

### 階段 1：LLM1 - 安撫話語生成 + RAG 判斷 ⚡

```
┌─────────────────────────────────────────────────────────┐
│  LLM1：安撫話語生成 + RAG 判斷                           │
├─────────────────────────────────────────────────────────┤
│  1. 有 knowledge_ids 嗎？                               │
│     ├─ YES → 取得 META 內容                             │
│     └─ NO → 無 META 內容                                │
│                                                         │
│  2. 組合 LLM1 Prompt                                    │
│     - 角色風格                                          │
│     - 輸出規格（僅 language + 斷句）                     │
│     - Knowledge Meta（如果有）                          │
│     - 對話歷史                                          │
│     - 用戶問題                                          │
│                                                         │
│  3. 呼叫 LLM1（enable_thinking: false）                 │
│     輸出：                                              │
│       - 安撫話語（永遠都要生成！）                      │
│       - 相關文件列表（可能為空）                        │
│                                                         │
│  4. ⚡ 立即發送安撫話語到前端（STREAM）                 │
│     時機：< 1 秒（關鍵！）                              │
│                                                         │
│  5. 載入相關文件內容（如果有）                          │
│     時機：可慢，不阻塞                                  │
└─────────────────────────────────────────────────────────┘
```

**關鍵原則：**
- 安撫話語永遠由 LLM 生成，不應該有任何條件判斷或硬編碼
- 立即發送是關鍵，不要在發送前做其他阻塞操作
- 文件載入可以與 LLM2 並行執行

**TIMING 記錄：**
- `rag_llm_ms`: LLM1 呼叫時間（永遠都有）
- `file_read_ms`: 文件讀取時間（如果有文件）
- `rag_retrieve_ms`: RAG 總時間（LLM1 + 文件讀取）

---

### 階段 2：LLM2 - 完整回答生成

```
┌─────────────────────────────────────────────────────────┐
│  LLM2：完整回答生成                                      │
├─────────────────────────────────────────────────────────┤
│  1. 組合 LLM2 Prompt                                    │
│     - 角色風格                                          │
│     - 輸出規格（完整版，含 emotion）                     │
│     - 知識庫完整內容（如果有）                          │
│     - 對話歷史                                          │
│     - 用戶問題                                          │
│                                                         │
│  2. 呼叫 LLM2（STREAM，enable_thinking: false）         │
│     - 使用 BlockChunker 分塊                            │
│     - 每 800-1200 字發送一次                            │
│                                                         │
│  3. 發送完成事件                                        │
│     - event: done                                       │
│     - 包含 timings 和 usage                             │
└─────────────────────────────────────────────────────────┘
```

**關鍵原則：**
- 必須關掉 reasoning/thinking（性能優化）
- 使用 STREAM 模式逐步發送
- 包含 TIMING 記錄供調試使用

---

## 📐 Prompt 生成結構

### Prompt 組成結構（5 部分）

```
┌─────────────────────────────────────────┐
│ 1. 角色風格 (Style)                     │ ← 從 style.md 載入
├─────────────────────────────────────────┤
│ 2. 輸出規格 (Output Format Spec)        │ ← 從 specs/*.md 載入（條件式）
├─────────────────────────────────────────┤
│ 3. 知識庫內容 (Knowledge/RAG)           │ ← 從 knowledge.folders 載入（條件式）
├─────────────────────────────────────────┤
│ 4. 對話歷史 (Conversation History)      │ ← 從 Session Store 獲取
├─────────────────────────────────────────┤
│ 5. 用戶問題 (User Message)              │ ← 從 API 請求獲取
└─────────────────────────────────────────┘
```

---

### 1. 角色風格 (Style)

**來源：** `workspace/personas/{persona_id}/style.md`

**Config 配置：**
```yaml
style:
  file: style.md
```

**內容結構：**
```markdown
# {角色名稱} 風格定義

## 角色設定
- 身份背景
- 性格特徵
- 說話風格

## 回覆規則
- 必須遵守的原則
- 禁止事項

## 範例
用戶：XXX
助手：XXX
```

**必要性：** ✅ 必要（所有角色都必須有風格定義）

---

### 2. 輸出規格 (Output Format Spec)

**來源：** `workspace/specs/{output_format}-output-spec.md`

**Config 配置：**
```yaml
output_format: virtual_human  # virtual_human | chat
```

**規格映射：**

| output_format | 規格文件 | 說明 |
|---------------|----------|------|
| `virtual_human` | `virtual-human-output-spec.md` | 情緒標籤 + 語言標籤 + 斷句符號 |
| `chat` | (無) | 一般文字回應，無特殊格式 |

**必要性：** ⚠️ 條件式（僅 virtual_human 需要）

---

### 3. 知識庫內容 (Knowledge/RAG)

**來源：** `workspace/knowledge/{folders}`

**Config 配置：**
```yaml
knowledge:
  enabled: true
  folders:
    - products/
    - company/
    - faq/
```

**LLM1 vs LLM2 差異：**
| 層面 | LLM1 | LLM2 |
|------|------|------|
| 內容 | Meta only（meta.json） | 完整內容（根據 LLM1 判斷） |
| Token 估算 | ~200 tokens | ~3000 tokens |

**必要性：** ⚠️ 條件式（僅 knowledge.enabled=true 時載入）

---

### 4. 對話歷史 (Conversation History)

**來源：** `session/session_store.py` - `get_messages(session_id)`

**獲取邏輯：**
```python
conversation_history = session_store.get_messages(session_id)
# 取最近 10 條消息
recent_history = conversation_history[-10:] if conversation_history else []
```

**必要性：** ✅ 必要（但可能為空）

---

### 5. 用戶問題 (User Message)

**來源：** API 請求參數

**必要性：** ✅ 必要

---

## 🔧 LLM1 vs LLM2 雙架構

### 雙 LLM 協作流程

```
用戶提問
    ↓
┌─────────────────────────────────────────────────────────┐
│  LLM1（快速回應）                                        │
│  - 載入：風格 + Session + Knowledge Meta                 │
│  - 輸出：1 句話快速反應（含分段符號、語系）               │
│  - 判斷：是否需要 LLM2 完整回應？                         │
└─────────────────────────────────────────────────────────┘
    ↓
    ├───────────────┴───────────────┐
    ↓ (不需要)                      ↓ (需要)
┌──────────────────┐       ┌─────────────────────────────────┐
│  返回 LLM1 回應    │       │  LLM2（完整回應）                │
│  <sbr>            │       │  - 載入：風格 + Session          │
│                   │       │  - 載入：完整 Knowledge          │
│                   │       │  - 輸出：完整內容（含規格）       │
└──────────────────┘       └─────────────────────────────────┘
```

### LLM1 vs LLM2 差異對照表

| 層面 | LLM1（快速回應） | LLM2（完整回應） |
|------|-----------------|-----------------|
| **用途** | 安撫話語 + 判斷 | 完整內容生成 |
| **回應長度** | 1 句話（<20 字） | 完整回答 |
| **風格** | style.md | style.md |
| **輸出規格** | virtual-human-output-spec.md（使用 language + 斷句） | virtual-human-output-spec.md（完整） |
| **情緒標籤** | ❌ 不需要 | ✅ 需要 |
| **知識庫** | Meta only（meta.json） | 完整內容（根據 LLM1 判斷） |
| **對話歷史** | ✅ Session（最近 10 條） | ✅ Session（最近 10 條） |
| **Prompt 大小** | ~2600 tokens | ~5400 tokens |
| **回應時間** | < 1 秒 | 10-30 秒 |

---

### LLM1 Prompt 組合範例

```python
async def _build_prompt_llm1(
    config: dict,
    user_message: str,
    conversation_history: List[dict],
    knowledge_meta: str,
    workspace_path: Path
) -> str:
    """LLM1 Prompt 組合 - 快速回應 + 判斷"""
    
    # 1. 載入角色風格
    style_file = config['style']['file']
    style_path = workspace_path / 'personas' / config['persona_id'] / style_file
    style_content = style_path.read_text(encoding='utf-8')
    
    # 2. 載入輸出規格
    spec_file = workspace_path / 'specs' / 'virtual-human-output-spec.md'
    spec_content = spec_file.read_text(encoding='utf-8')
    
    # 3. 知識庫 Meta
    # knowledge_meta 格式見下方章節
    
    # 4. 格式化對話歷史
    recent_history = conversation_history[-10:] if conversation_history else []
    history_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in recent_history
    ]) if recent_history else "（無）"
    
    # 5. 組合 Prompt
    prompt = f"""# 角色風格
{style_content}

# 輸出規格
{spec_content}

# 知識庫 Meta
{knowledge_meta if knowledge_meta else '無'}

# 對話歷史
{history_text}

# 用戶問題
{user_message}

# 回應要求
請用 1 句話快速回應（<20 字），並判斷是否需要查詢更多知識庫內容。
"""
    
    return prompt
```

**LLM1 回應格式：**
```
安撫話：[一句友善的回應，含<sbr>斷句]
相關文件：["file1.md", "file2.md"]
```

---

### LLM2 Prompt 組合範例

```python
async def _build_prompt_llm2(
    config: dict,
    user_message: str,
    conversation_history: List[dict],
    knowledge_content: str,
    workspace_path: Path
) -> str:
    """LLM2 Prompt 組合 - 完整內容生成"""
    
    # 1. 載入角色風格
    style_file = config['style']['file']
    style_path = workspace_path / 'personas' / config['persona_id'] / style_file
    style_content = style_path.read_text(encoding='utf-8')
    
    # 2. 載入輸出規格（完整版，含 emotion）
    spec_file = workspace_path / 'specs' / 'virtual-human-output-spec.md'
    spec_content = spec_file.read_text(encoding='utf-8')
    
    # 3. 知識庫完整內容
    # knowledge_content 由 LLM1 判斷的文件列表載入
    
    # 4. 格式化對話歷史
    recent_history = conversation_history[-10:] if conversation_history else []
    history_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in recent_history
    ]) if recent_history else "（無）"
    
    # 5. 組合 Prompt
    prompt = f"""# 角色風格
{style_content}

# 輸出規格
{spec_content}

# 知識庫內容
{knowledge_content if knowledge_content else '無'}

# 對話歷史
{history_text}

# 用戶問題
{user_message}
"""
    
    return prompt
```

---

### 知識庫 Meta 格式

**位置：** `/knowledge/{knowledge_id}/meta.json`

**格式：**
```json
{
  "knowledge_id": "ubichan",
  "metadata": {
    "category": "customer_service",
    "tags": ["產品", "客服", "常見問題"],
    "language": "zh-TW",
    "version": "1.0"
  }
}
```

**欄位說明：**

| 欄位 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `knowledge_id` | string | 知識庫唯一識別 | `"ubichan"` |
| `metadata.category` | string | 分類 | `"customer_service"` |
| `metadata.tags` | array | 標籤列表 | `["產品", "客服"]` |
| `metadata.language` | string | 語言 | `"zh-TW"` |
| `metadata.version` | string | 版本 | `"1.0"` |

**LLM1 使用方式：**
- 讀取 `meta.json`
- 將 meta 資訊加入 Prompt
- 用於判斷哪些文件相關

---

### Token 估算（雙 LLM 架構）

| 部分 | LLM1 | LLM2 |
|------|------|------|
| 風格文件 | ~500 tokens | ~500 tokens |
| 輸出規格 | ~800 tokens | ~800 tokens |
| 知識庫 | ~200 tokens（Meta） | ~3000 tokens（完整） |
| 對話歷史 | ~1000 tokens | ~1000 tokens |
| 用戶問題 | ~100 tokens | ~100 tokens |
| **總計** | **~2600 tokens** | **~5400 tokens** |

---

## 📊 時序圖

```
用戶請求
   │
   ▼
┌─────────────────┐
│ 1. 檢查          │ ⏱️ < 10ms
│    knowledge_ids │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ 2. 呼叫 LLM1    │ ⏱️ 2-5 秒
│    生成安撫話語  │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ 3. ⚡ 立即發送   │ ⏱️ < 100ms ← 關鍵！
│    安撫話語      │
└─────────────────┘
   │
   ▼ (並行)
┌─────────────────┐
│ 4. 載入文件     │ ⏱️ 可慢
│    (如果有)     │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ 5. 呼叫 LLM2    │ ⏱️ 10-30 秒
│    生成回答      │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ 6. 更新 Session │ ⏱️ < 50ms
└─────────────────┘
   │
   ▼
返回完整回答
```

**TIMING 記錄（done 事件）：**
```json
{
  "timings": {
    "rag_llm_ms": 755,        // LLM1 時間
    "file_read_ms": 0,        // 文件讀取時間
    "rag_retrieve_ms": 755,   // RAG 總時間
    "llm_call_ms": 5773,      // LLM2 時間
    "total_ms": 6543          // 總時間
  }
}
```

---

## 📝 使用範例

### 完整對話流程

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

# STREAM 回應：
# event: text_chunk
# data: {"chunk":"哈哈，你好呀！讓我來看看..."}
#
# event: text_chunk
# data: {"chunk":"<!-- emotion:happy --><!-- lang:tw (zh) -->\n嗨嗨～你好啊！<br>\n..."}
#
# event: done
# data: {"timings":{"total_ms":6234,"llm_call_ms":5892}}
```

---

**文檔結束**
